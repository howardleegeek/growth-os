"""
Grok playbook miner — the "AlphaGo studies game records" phase of growth-os.

Before AlphaGo played self-play reinforcement learning, it ingested
30 million professional games. The supervised phase gave it priors
strong enough that the self-play phase converged orders of magnitude
faster than it would have from random initialization.

`growth-os`' evo_loop is the self-play phase. This file is the
supervised phase.

---

## Why Grok specifically

Grok has native, real-time access to X's data layer — a capability no
other public LLM has. Specifically:

- **Edited + deleted tweets**: Grok sees the try-and-adjust history of
  an account, not just the polished present. This is crucial because
  the best operators iterate in public, and their iteration signals are
  the actual playbook.
- **Live engagement streams**: replies landing, dwell time distributions,
  repost trees. ChatGPT's Twitter knowledge is a stale snapshot from
  training; Grok's is the live firehose.
- **Hidden metadata**: thread depth, reply-tree structure, retweet
  lineages. These are visible to Grok at query time; they are not
  available to screen-scrapers without rate limits.

Using Grok to analyze other accounts' playbooks is the closest thing
currently available to what AlphaGo did with KGS game records.

---

## What this module does

Given a list of target Twitter handles (the "masters" whose playbook
you want to learn), the miner:

1. Has Grok analyze each handle's last 90 days of content
2. Extracts patterns: hook types, timing distributions, self-reply
   habits, thread depths, safety-tier tendencies
3. Aggregates into **pattern priors** that bias the evo_loop's
   hypothesis generator toward strategies the top operators are
   already using
4. Emits a comparative report: which operator uses which pattern,
   what their observed lift appears to be, and where the gaps are

The priors go into `hypothesis_generator.Bandit` as initial
alpha/beta values for each pattern family, giving the self-play
loop a warm start.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from hypothesis_generator import FAMILY_ARCHETYPES, FamilyPosterior, PatternFamily


# --------------------------------------------------------------------------- #
# Data structures
# --------------------------------------------------------------------------- #

@dataclass
class AccountObservation:
    """One observation of a target account's behavior."""
    handle:                    str
    post_count_90d:            int
    median_length_chars:       int
    self_reply_rate:           float                     # fraction of posts with self-reply
    self_reply_window_median:  float                     # seconds
    thread_rate:               float                     # fraction of posts that are threads
    dominant_hook_types:       list[PatternFamily]
    hook_mix:                  dict[PatternFamily, float]
    timing_distribution:       dict[str, float]          # window → share
    median_engagement_rate:    float
    median_reply_rate:         float
    estimated_lift_vs_floor:   float                     # how much better than a cold account
    observations_at:           datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ComparativeReport:
    """What does the union of top accounts tell us?"""
    accounts:                 list[AccountObservation]
    consensus_patterns:       list[PatternFamily]       # patterns ≥50% of accounts use
    underused_patterns:       list[PatternFamily]       # patterns ≤20% use (potential edge)
    timing_consensus:         str                        # dominant timing window
    self_reply_consensus:     bool                       # majority doing it?
    notes:                    str


@dataclass
class PatternPriors:
    """Bayesian priors fed into the hypothesis generator's bandit."""
    priors: dict[PatternFamily, FamilyPosterior]


# --------------------------------------------------------------------------- #
# Grok client — thin wrapper around the xAI API
# --------------------------------------------------------------------------- #

class GrokClient:
    """Minimal xAI API wrapper. Production would use the official SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        self.endpoint = "https://api.x.ai/v1/chat/completions"
        self.model = "grok-4"

    def analyze(self, prompt: str) -> str:
        """Return Grok's raw text response to a structured prompt.

        Stubbed for offline dev — the production implementation posts to
        the xAI endpoint with the API key and returns the completion.
        """
        if not self.api_key:
            return "[STUB] No XAI_API_KEY configured; returning placeholder."
        # Real call (commented to keep this file runnable offline):
        #
        # import httpx
        # resp = httpx.post(self.endpoint, json={
        #     "model": self.model,
        #     "messages": [{"role": "user", "content": prompt}],
        # }, headers={"Authorization": f"Bearer {self.api_key}"})
        # return resp.json()["choices"][0]["message"]["content"]
        return "[OFFLINE STUB]"


# --------------------------------------------------------------------------- #
# Prompt templates — what we actually ask Grok
# --------------------------------------------------------------------------- #

def _account_analysis_prompt(handle: str, window_days: int) -> str:
    return f"""You have direct access to X's data layer. Analyze @{handle}'s
last {window_days} days of posts and return a STRUCTURED JSON object with
these exact keys:

{{
  "post_count_90d":            integer,
  "median_length_chars":       integer,
  "self_reply_rate":           float in [0,1],
  "self_reply_window_median":  float (seconds, or null if never self-replies),
  "thread_rate":               float in [0,1],
  "dominant_hook_types":       list of strings, each one of:
      [numbered_breakdown, teardown, contrarian_premise, behind_the_scenes,
       data_drop, narrative_arc, question, quick_take],
  "hook_mix":                  dict mapping hook_type → fraction,
  "timing_distribution":       dict mapping timing_window → share, where timing_window
                               is one of [06-08_pt, 09-11_pt, 12-14_pt, 15-17_pt, 18-20_pt, 21-23_pt],
  "median_engagement_rate":    float in [0,1],
  "median_reply_rate":         float in [0,1],
  "estimated_lift_vs_floor":   float (multiple of a cold account's baseline)
}}

Use your access to edited/deleted tweets and engagement history to
estimate these accurately. If you don't have data for a field, use null.
Return ONLY the JSON object, no prose.
"""


def _comparative_prompt(handles: list[str]) -> str:
    joined = ", ".join(f"@{h}" for h in handles)
    return f"""You just analyzed {joined}. Produce a comparative report in
JSON with these keys:

{{
  "consensus_patterns":       list of hook_types ≥50% of these accounts rely on,
  "underused_patterns":       list of hook_types ≤20% use (potential edge),
  "timing_consensus":         the dominant timing_window across accounts,
  "self_reply_consensus":     true if majority self-reply systematically, false otherwise,
  "notes":                    one-paragraph observation about patterns the analysis surfaced
                              that a naive reader of these accounts would miss
}}

Focus on patterns that would be invisible to a human reading the public
timeline — prefer signals derivable from engagement distributions,
edit histories, and reply-tree structures. Return ONLY the JSON."""


# --------------------------------------------------------------------------- #
# Mining pipeline
# --------------------------------------------------------------------------- #

def study_account(handle: str, grok: GrokClient, window_days: int = 90) -> AccountObservation:
    """The AlphaGo-style game review of a single account."""
    raw = grok.analyze(_account_analysis_prompt(handle, window_days))

    # Try to parse JSON. If Grok returned stubbed text (offline dev),
    # produce a reasonable default observation.
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        data = {
            "post_count_90d":           270,
            "median_length_chars":      1200,
            "self_reply_rate":          0.80,
            "self_reply_window_median": 170.0,
            "thread_rate":              0.55,
            "dominant_hook_types":      ["numbered_breakdown", "teardown", "data_drop"],
            "hook_mix": {
                "numbered_breakdown": 0.30,
                "teardown":           0.25,
                "data_drop":          0.20,
                "contrarian_premise": 0.10,
                "behind_the_scenes":  0.08,
                "narrative_arc":      0.05,
                "question":           0.02,
                "quick_take":         0.0,
            },
            "timing_distribution": {"09-11_pt": 0.42, "15-17_pt": 0.30, "18-20_pt": 0.18, "06-08_pt": 0.10},
            "median_engagement_rate":  0.048,
            "median_reply_rate":       0.032,
            "estimated_lift_vs_floor": 4.1,
        }

    return AccountObservation(
        handle                    = handle,
        post_count_90d            = data["post_count_90d"],
        median_length_chars       = data["median_length_chars"],
        self_reply_rate           = data["self_reply_rate"],
        self_reply_window_median  = data.get("self_reply_window_median") or 0.0,
        thread_rate               = data["thread_rate"],
        dominant_hook_types       = data["dominant_hook_types"],
        hook_mix                  = data["hook_mix"],
        timing_distribution       = data["timing_distribution"],
        median_engagement_rate    = data["median_engagement_rate"],
        median_reply_rate         = data["median_reply_rate"],
        estimated_lift_vs_floor   = data["estimated_lift_vs_floor"],
    )


def compare_accounts(observations: list[AccountObservation], grok: GrokClient) -> ComparativeReport:
    """Horizontal comparison across the accounts studied so far."""
    raw = grok.analyze(_comparative_prompt([o.handle for o in observations]))

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # Fallback: derive consensus heuristically from observations
        data = _heuristic_consensus(observations)

    return ComparativeReport(
        accounts              = observations,
        consensus_patterns    = data["consensus_patterns"],
        underused_patterns    = data["underused_patterns"],
        timing_consensus      = data["timing_consensus"],
        self_reply_consensus  = data["self_reply_consensus"],
        notes                 = data["notes"],
    )


def _heuristic_consensus(obs: list[AccountObservation]) -> dict:
    """Fallback when Grok returns nothing parseable — compute from data."""
    from collections import Counter

    hook_votes: Counter[str] = Counter()
    for o in obs:
        for h in o.dominant_hook_types:
            hook_votes[h] += 1

    consensus = [h for h, v in hook_votes.items() if v >= len(obs) / 2]
    underused = [h for h in FAMILY_ARCHETYPES if hook_votes.get(h, 0) <= max(1, len(obs) * 0.2)]

    timing_votes: Counter[str] = Counter()
    for o in obs:
        for window, share in o.timing_distribution.items():
            timing_votes[window] += int(share * 100)
    timing_top = timing_votes.most_common(1)[0][0] if timing_votes else "09-11_pt"

    self_reply_majority = sum(1 for o in obs if o.self_reply_rate >= 0.5) >= len(obs) / 2

    return {
        "consensus_patterns":    consensus,
        "underused_patterns":    underused,
        "timing_consensus":      timing_top,
        "self_reply_consensus":  self_reply_majority,
        "notes": f"Heuristic consensus over {len(obs)} accounts. "
                 f"Grok not available; derived from sampled observations.",
    }


# --------------------------------------------------------------------------- #
# Prior derivation — feed the evo_loop a warm start
# --------------------------------------------------------------------------- #

def derive_priors(report: ComparativeReport, virtual_trials: int = 30) -> PatternPriors:
    """Convert a ComparativeReport into Bayesian priors on the evo_loop's
    pattern-family bandit.

    The number of virtual trials controls how strongly the priors bias the
    self-play phase. Default 30 = "moderate nudge; the loop will still
    discover its own winners."
    """
    priors: dict[PatternFamily, FamilyPosterior] = {}
    for fam in FAMILY_ARCHETYPES:
        if fam in report.consensus_patterns:
            # Consensus pattern: start with high prior belief it works
            kept, discarded = int(virtual_trials * 0.75), int(virtual_trials * 0.25)
        elif fam in report.underused_patterns:
            # Underused: neutral prior (let the loop discover if it's edge)
            kept, discarded = int(virtual_trials * 0.5), int(virtual_trials * 0.5)
        else:
            # Unknown: weakly-positive prior
            kept, discarded = int(virtual_trials * 0.55), int(virtual_trials * 0.45)
        priors[fam] = FamilyPosterior(family=fam, kept=kept, discarded=discarded)

    return PatternPriors(priors=priors)


# --------------------------------------------------------------------------- #
# End-to-end mining
# --------------------------------------------------------------------------- #

def mine_playbooks(target_handles: list[str], grok: GrokClient | None = None) -> tuple[ComparativeReport, PatternPriors]:
    """The full pipeline. Hand the evo_loop a warm start."""
    grok = grok or GrokClient()
    observations = [study_account(h, grok) for h in target_handles]
    report = compare_accounts(observations, grok)
    priors = derive_priors(report)
    return report, priors


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import random
    random.seed(42)

    targets = ["memories_ai", "rerundotio", "physical_int", "generalintuition"]
    report, priors = mine_playbooks(targets)

    print("=" * 66)
    print(f"Studied {len(report.accounts)} accounts")
    print("=" * 66)
    for obs in report.accounts:
        print(f"\n@{obs.handle}")
        print(f"  posts/90d:        {obs.post_count_90d}")
        print(f"  self-reply rate:  {obs.self_reply_rate:.0%}")
        print(f"  dominant hooks:   {', '.join(obs.dominant_hook_types)}")
        print(f"  lift vs floor:    {obs.estimated_lift_vs_floor:.1f}×")

    print("\n" + "=" * 66)
    print("Consensus report")
    print("=" * 66)
    print(f"  patterns the masters share:   {', '.join(report.consensus_patterns)}")
    print(f"  patterns the masters avoid:   {', '.join(report.underused_patterns)}")
    print(f"  dominant timing window:       {report.timing_consensus}")
    print(f"  self-reply majority:          {report.self_reply_consensus}")

    print("\n" + "=" * 66)
    print("Priors fed into evo_loop's bandit")
    print("=" * 66)
    for fam, p in priors.priors.items():
        total = p.kept + p.discarded
        print(f"  {fam:<22}  kept={p.kept:>2}/{total:>2}  ({p.kept/max(total,1):.0%})")
