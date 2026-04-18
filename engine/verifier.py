"""
Mechanical verifier — the adult in the room.

The single most important file in this repo. No LLM calls. No fuzzy matching.
No "looks good to me." Every iteration of the autoresearch loop passes through
here before its result is accepted, and anything that fails here is LOGGED AS
FAILED and the loop moves on.

LLMs cannot be trusted to verify their own work. They skip steps, invent
results, and favor "looks reasonable" over "mechanically true." The verifier
exists because a human will eventually ask "are we sure this experiment
actually ran?" and the only acceptable answer is "yes, here's the Python that
proved it, and here's the TSV row it produced."

This file is ~200 lines. It should never grow much larger. When in doubt, say
no.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


# --------------------------------------------------------------------------- #
# Verification result
# --------------------------------------------------------------------------- #

@dataclass
class VerificationResult:
    """Outcome of running the checklist against one iteration."""
    passed: bool
    failed_checks: list[str]
    score: float
    lift_vs_control: float
    z_statistic: float
    note: str

    def to_tsv_result(self) -> str:
        """The 'result' column value written to TSV."""
        return "kept" if self.passed else "discarded"


# --------------------------------------------------------------------------- #
# Primitive checks
# --------------------------------------------------------------------------- #

def _not_duplicate(candidate_text: str, recent_corpus: list[str], threshold: float = 0.88) -> bool:
    """Character-trigram Jaccard similarity. Not perfect, but deterministic.

    We deliberately avoid embedding-based similarity here because the verifier
    must be fast and offline. Embedding similarity belongs in the hypothesis
    generator, not the verifier.
    """
    if not candidate_text or not recent_corpus:
        return True

    def _trigrams(s: str) -> set[str]:
        s = s.lower()
        return {s[i:i+3] for i in range(len(s) - 2)} if len(s) >= 3 else {s}

    c = _trigrams(candidate_text)
    for other in recent_corpus:
        o = _trigrams(other)
        if not c or not o:
            continue
        jaccard = len(c & o) / len(c | o)
        if jaccard >= threshold:
            return False
    return True


def _data_is_fresh(metrics_fetched_at: datetime, max_age: timedelta = timedelta(hours=24)) -> bool:
    """Metrics must have been pulled from the platform within the last 24 hours."""
    now = datetime.now(timezone.utc)
    if metrics_fetched_at.tzinfo is None:
        metrics_fetched_at = metrics_fetched_at.replace(tzinfo=timezone.utc)
    return (now - metrics_fetched_at) <= max_age


def _min_sample_size(impressions: int, threshold: int = 200) -> bool:
    """We don't decide on < 200 impressions. That's noise, not signal."""
    return impressions >= threshold


def _tier_quota_respected(tier: str, tier_c_shipped_today: int, total_shipped_today: int, cap: float = 0.10) -> bool:
    """Tier C cannot exceed 10% of daily volume. Tier D is never allowed."""
    if tier == "D":
        return False
    if tier == "C":
        if total_shipped_today == 0:
            return True
        return (tier_c_shipped_today + 1) / (total_shipped_today + 1) <= cap
    return True


def _z_test_two_proportion(control_rate: float, control_n: int, variant_rate: float, variant_n: int) -> float:
    """Two-proportion z-test. |z| >= 1.96 ≈ p < 0.05 two-sided."""
    if control_n == 0 or variant_n == 0:
        return 0.0
    c_conv = control_rate * control_n
    v_conv = variant_rate * variant_n
    p_pool = (c_conv + v_conv) / (control_n + variant_n)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / control_n + 1 / variant_n))
    return (variant_rate - control_rate) / se if se else 0.0


# --------------------------------------------------------------------------- #
# The checklist
# --------------------------------------------------------------------------- #

@dataclass
class IterationInput:
    """Everything the verifier needs to make a decision. Passed explicitly so
    the verifier has no hidden dependencies."""
    candidate_text:          str
    candidate_tier:          str
    recent_shipped_corpus:   list[str]
    metrics_fetched_at:      datetime
    impressions:             int
    engagement_rate:         float
    score_vs_weight_map:     float
    ship_threshold:          float
    # For control comparison
    control_rate:            float
    control_n:               int
    # For quota enforcement
    tier_c_shipped_today:    int
    total_shipped_today:     int


def verify(inp: IterationInput) -> VerificationResult:
    """Run the checklist. Return pass/fail + full provenance."""
    failures: list[str] = []

    if not _not_duplicate(inp.candidate_text, inp.recent_shipped_corpus):
        failures.append("duplicate_of_recent_post")

    if not _data_is_fresh(inp.metrics_fetched_at):
        failures.append("metrics_stale")

    if not _min_sample_size(inp.impressions):
        failures.append("insufficient_sample_size")

    if inp.score_vs_weight_map < inp.ship_threshold:
        failures.append("below_ship_threshold")

    if not _tier_quota_respected(inp.candidate_tier, inp.tier_c_shipped_today, inp.total_shipped_today):
        failures.append("tier_quota_violation")

    z = _z_test_two_proportion(
        control_rate = inp.control_rate,
        control_n    = inp.control_n,
        variant_rate = inp.engagement_rate,
        variant_n    = inp.impressions,
    )
    lift = (inp.engagement_rate / inp.control_rate - 1.0) if inp.control_rate else 0.0

    # Only accept lift if both (a) positive and (b) statistically distinguishable
    if lift < 0 or abs(z) < 1.96:
        failures.append("lift_not_significant")

    passed = len(failures) == 0
    note = (
        f"{'+' if lift >= 0 else ''}{lift * 100:.1f}% vs ctl, n={inp.impressions}, z={z:+.2f}"
        if not failures
        else "failed: " + ",".join(failures)
    )

    return VerificationResult(
        passed=passed,
        failed_checks=failures,
        score=inp.score_vs_weight_map,
        lift_vs_control=lift,
        z_statistic=z,
        note=note,
    )


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    good = IterationInput(
        candidate_text="A thread about reverse-engineering ranking functions",
        candidate_tier="A",
        recent_shipped_corpus=["Some unrelated post", "Another unrelated post"],
        metrics_fetched_at=datetime.now(timezone.utc),
        impressions=4200,
        engagement_rate=0.046,
        score_vs_weight_map=32.1,
        ship_threshold=5.0,
        control_rate=0.015,
        control_n=3800,
        tier_c_shipped_today=0,
        total_shipped_today=5,
    )
    result = verify(good)
    print(f"Passed: {result.passed}")
    print(f"Note:   {result.note}")

    bad = IterationInput(
        candidate_text="Some clickbait",
        candidate_tier="C",
        recent_shipped_corpus=[],
        metrics_fetched_at=datetime.now(timezone.utc) - timedelta(days=3),
        impressions=42,
        engagement_rate=0.001,
        score_vs_weight_map=1.2,
        ship_threshold=5.0,
        control_rate=0.015,
        control_n=3800,
        tier_c_shipped_today=3,
        total_shipped_today=5,
    )
    result = verify(bad)
    print(f"Passed: {result.passed}")
    print(f"Note:   {result.note}")
