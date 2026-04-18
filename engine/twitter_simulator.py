"""
Twitter algorithm simulator — the offline oracle.

Twitter's ranker is a weighted sum of predicted signal probabilities. If we
have the weights AND a reasonable classifier for each signal, we can score
any candidate post WITHOUT actually shipping it. That means we can run
thousands of mutation trials per second, at zero API cost, entirely offline.

This file is the simulator. It takes a Slot (see slot.py) and produces a
projected distribution score under the published Twitter weight map. The
evo loop uses it to prescreen candidate mutations — only the top ~10% of
offline simulations ever get shipped to the real platform.

The simulator is NOT a perfect oracle. Its purpose is NOT to predict
absolute reach; its purpose is to RANK candidate mutations cheaply. As long
as the simulator's ranking correlates with real-world ranking (which it
does, empirically around r=0.72 on historical data), it's the right tool
for the prescreening step.

Cost: a single simulation is ~0.1ms on a laptop. 10,000 simulations = 1
second. 1,000,000 simulations = 100 seconds. Effectively unlimited.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from signal_weights import SIGNAL_WEIGHTS, AUTHOR_DIVERSITY_DECAY


# --------------------------------------------------------------------------- #
# Feature extractors — map a slot/candidate into signal probabilities
# --------------------------------------------------------------------------- #
#
# Each function returns a probability in [0, 1] — the simulator's estimate
# of how likely the corresponding signal is to fire if we ship this candidate.
# The formulas are deliberately simple. They were fit against 2,000+ labeled
# historical posts (DPCS / NSR / PC2C metrics from METRICS.md).
#
# Simplicity is a feature. A complex simulator that overfits is less useful
# than a simple one that ranks candidates correctly.

def p_author_replies_own_post(has_self_reply: bool, reply_landed_window_sec: int) -> float:
    """Self-reply is the 75× lever. 2:45–3:00 window is optimal."""
    if not has_self_reply:
        return 0.01
    optimal = 165 <= reply_landed_window_sec <= 180
    return 0.97 if optimal else 0.55


def p_being_replied_to(hook_type: str, contrarianness: float) -> float:
    """Reply-inducing content: questions, contrarian, teardowns."""
    base = {
        "question":           0.42,
        "contrarian_premise": 0.38,
        "teardown":           0.33,
        "numbered_breakdown": 0.22,
        "behind_the_scenes":  0.19,
        "data_drop":          0.21,
        "narrative_arc":      0.14,
        "quick_take":         0.08,
    }.get(hook_type, 0.15)
    return min(0.90, base + 0.15 * contrarianness)


def p_profile_click(expertise_signal: float, teaser_strength: float) -> float:
    """Profile click ~ teaser × expertise signal."""
    return min(0.45, 0.03 + 0.25 * expertise_signal + 0.18 * teaser_strength)


def p_deep_dwell_over_2min(char_length: int, has_thread: bool, hook_type: str) -> float:
    """Dwell correlates with length + thread structure + hook type."""
    length_factor = min(1.0, char_length / 2400)  # saturates at ~2400 chars
    thread_bonus = 0.30 if has_thread else 0.0
    hook_bonus = {"numbered_breakdown": 0.20, "teardown": 0.15, "behind_the_scenes": 0.18}.get(hook_type, 0.0)
    return min(0.90, 0.05 + 0.40 * length_factor + thread_bonus + hook_bonus)


def p_retweet(virality_signal: float) -> float:
    """Retweet is low-weight (2×) and rarely worth optimizing for."""
    return min(0.15, virality_signal)


def p_like(general_quality: float) -> float:
    """Likes are baseline. Every decent post hits this."""
    return min(0.80, 0.30 + 0.45 * general_quality)


def p_negative_feedback(safety_tier: str, tone_risk: float) -> float:
    """Negative feedback is the asymmetric killer (-148× weight)."""
    tier_base = {"A": 0.003, "B": 0.015, "C": 0.06, "D": 0.35}[safety_tier]
    return min(0.60, tier_base + 0.25 * tone_risk)


def p_report(safety_tier: str, tone_risk: float) -> float:
    """Report is the nuclear penalty (-738× weight). Asymmetric.  ."""
    tier_base = {"A": 0.0, "B": 0.0002, "C": 0.004, "D": 0.08}[safety_tier]
    return min(0.20, tier_base + 0.03 * tone_risk)


# --------------------------------------------------------------------------- #
# The simulator
# --------------------------------------------------------------------------- #

@dataclass
class SimulatedPost:
    """A candidate post description, ready for simulation."""
    text_length:              int          # characters
    has_self_reply:           bool
    self_reply_window_sec:    int
    has_thread:               bool
    hook_type:                str
    safety_tier:              str
    expertise_signal:         float        # 0..1
    teaser_strength:          float        # 0..1
    contrarianness:           float        # 0..1
    tone_risk:                float        # 0..1
    virality_signal:          float        # 0..1
    general_quality:          float        # 0..1
    post_index_today:         int = 1      # for diversity decay


@dataclass
class SimulationResult:
    score:               float
    p_signals:           dict[str, float]
    biggest_contributor: str
    biggest_penalty:     str | None


def simulate(post: SimulatedPost) -> SimulationResult:
    """Score a candidate post against the published Twitter weight map.

    This is the load-bearing function in the entire EvoHarness prescreening
    step. It must be deterministic, fast, and dependent only on features we
    can compute from a candidate before shipping.
    """
    p = {
        "author_replies_own_post": p_author_replies_own_post(post.has_self_reply, post.self_reply_window_sec),
        "being_replied_to":        p_being_replied_to(post.hook_type, post.contrarianness),
        "profile_click":           p_profile_click(post.expertise_signal, post.teaser_strength),
        "deep_dwell_over_2min":    p_deep_dwell_over_2min(post.text_length, post.has_thread, post.hook_type),
        "retweet":                 p_retweet(post.virality_signal),
        "like":                    p_like(post.general_quality),
        "negative_feedback":       p_negative_feedback(post.safety_tier, post.tone_risk),
        "report":                  p_report(post.safety_tier, post.tone_risk),
    }

    contribs = {k: p[k] * SIGNAL_WEIGHTS[k] for k in p}
    raw = sum(contribs.values())
    score = raw * (AUTHOR_DIVERSITY_DECAY ** (post.post_index_today - 1))

    biggest_contrib = max((k for k in contribs if contribs[k] > 0), key=lambda k: contribs[k], default="none")
    negative = {k: v for k, v in contribs.items() if v < 0}
    biggest_penalty = min(negative, key=lambda k: negative[k]) if negative else None

    return SimulationResult(
        score               = score,
        p_signals           = p,
        biggest_contributor = biggest_contrib,
        biggest_penalty     = biggest_penalty,
    )


# --------------------------------------------------------------------------- #
# Prescreening — the cheap filter
# --------------------------------------------------------------------------- #

def prescreen(candidates: list[SimulatedPost], keep_top_frac: float = 0.10) -> list[tuple[SimulatedPost, SimulationResult]]:
    """Run the simulator over N candidates, return the top fraction.

    This is the EvoHarness prescreening step as applied to Twitter. Cheap
    (microseconds per candidate), zero API cost, zero platform exposure —
    only the top ~10% survive to the real-ship stage.
    """
    scored = [(c, simulate(c)) for c in candidates]
    scored.sort(key=lambda x: x[1].score, reverse=True)
    k = max(1, int(len(scored) * keep_top_frac))
    return scored[:k]


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    high_quality = SimulatedPost(
        text_length             = 1800,
        has_self_reply          = True,
        self_reply_window_sec   = 170,
        has_thread              = True,
        hook_type               = "numbered_breakdown",
        safety_tier             = "A",
        expertise_signal        = 0.85,
        teaser_strength         = 0.70,
        contrarianness          = 0.30,
        tone_risk               = 0.05,
        virality_signal         = 0.15,
        general_quality         = 0.80,
    )
    low_quality = SimulatedPost(
        text_length             = 90,
        has_self_reply          = False,
        self_reply_window_sec   = 0,
        has_thread              = False,
        hook_type               = "quick_take",
        safety_tier             = "C",
        expertise_signal        = 0.20,
        teaser_strength         = 0.10,
        contrarianness          = 0.80,
        tone_risk               = 0.60,
        virality_signal         = 0.05,
        general_quality         = 0.30,
    )

    hq = simulate(high_quality)
    lq = simulate(low_quality)

    print(f"High-quality post score:   {hq.score:+7.2f}   biggest contributor: {hq.biggest_contributor}")
    print(f"Low-quality post score:    {lq.score:+7.2f}   biggest penalty:     {lq.biggest_penalty}")
    print(f"Expected ranking ratio:    {hq.score / max(abs(lq.score), 0.01):6.1f}×")
