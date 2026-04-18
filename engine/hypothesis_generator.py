"""
Hypothesis generator — proposes the next experiment.

Reads the results log, looks at what's been tried, and proposes the next
candidate to ship. The key insight: **the generator learns from the log.**
Patterns that have been kept get reinforced (more variations proposed);
patterns that have been discarded get explored around (similar but
deliberately distinct candidates).

This is the compounding mechanism in the autoresearch loop. Each iteration
makes the next iteration smarter about what to propose.

The generator itself is simple — a bandit over pattern families plus a
small LLM call to instantiate the chosen pattern. The intelligence lives
in the log, not in the generator.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

from results_log import ResultsLog


# --------------------------------------------------------------------------- #
# Pattern families — what we know how to propose
# --------------------------------------------------------------------------- #
#
# Each family is a high-level content shape. The hypothesis generator picks a
# family via Thompson sampling on the kept/discarded history, then hands off
# to an LLM call (stubbed here) to produce the actual text.

PatternFamily = Literal[
    "numbered_breakdown",   # "7 ways X" — scroll-depth optimizer
    "teardown",             # "I read X so you don't have to" — profile-click driver
    "contrarian_premise",   # "Everyone says X, data says Y" — reply-rate driver
    "behind_the_scenes",    # "Here's the actual mechanism behind X" — dwell driver
    "data_drop",            # "We A/B'd X. Here are the results" — credibility driver
    "narrative_arc",        # First-person story — thread-depth driver
    "question_hook",        # Opens with a genuine question — engagement driver
    "quick_take",           # 1–2 sentence observation — filler, rarely wins
]


FAMILY_ARCHETYPES: dict[PatternFamily, str] = {
    "numbered_breakdown":  "List of N items, each a sentence, structured as a thread.",
    "teardown":            "Claim + 3–5 surprising findings from reading something rare.",
    "contrarian_premise":  "Consensus statement + data that contradicts it + resolution.",
    "behind_the_scenes":   "Technical explanation of a mechanism most readers can't see.",
    "data_drop":           "Experimental result table with methodology footnote.",
    "narrative_arc":       "First-person walk through a decision, ending on a takeaway.",
    "question_hook":       "Genuine question, followed by the author's working answer.",
    "quick_take":          "One-liner observation. Use sparingly.",
}


# --------------------------------------------------------------------------- #
# Bandit state — posterior beliefs about each family's success rate
# --------------------------------------------------------------------------- #

@dataclass
class FamilyPosterior:
    family:      PatternFamily
    kept:        int = 0
    discarded:   int = 0

    def sample(self) -> float:
        """Thompson sample from Beta(1+kept, 1+discarded)."""
        return random.betavariate(1 + self.kept, 1 + self.discarded)


@dataclass
class Bandit:
    posteriors: dict[PatternFamily, FamilyPosterior] = field(default_factory=dict)

    @classmethod
    def from_log(cls, log: ResultsLog) -> "Bandit":
        """Re-derive posteriors from the entire log on every boot. Stateless
        across process restarts — the log is the source of truth."""
        b = cls(posteriors={f: FamilyPosterior(family=f) for f in FAMILY_ARCHETYPES})
        for row in log.tail(n=10**9):
            # Target column holds family name when it's a ship_test iteration
            if row.action != "ship_test":
                continue
            fam = row.target.split("_")[0] if "_" in row.target else row.target
            # Normalize — target IDs look like "numbered_breakdown_012"
            # so we take up to the last underscore segment
            segs = row.target.rsplit("_", 1)
            fam_key = segs[0] if len(segs) == 2 and segs[1].isdigit() else row.target
            if fam_key in b.posteriors:
                if row.result == "kept":
                    b.posteriors[fam_key].kept += 1
                elif row.result == "discarded":
                    b.posteriors[fam_key].discarded += 1
        return b

    def pick_family(self) -> PatternFamily:
        return max(self.posteriors.values(), key=lambda p: p.sample()).family


# --------------------------------------------------------------------------- #
# Candidate proposal
# --------------------------------------------------------------------------- #

@dataclass
class Hypothesis:
    target_id:  str              # "numbered_breakdown_0412"
    family:     PatternFamily
    archetype:  str              # the prompt guidance
    brief:      str              # one-sentence description of the specific candidate


def propose_next(log: ResultsLog, iteration: int) -> Hypothesis:
    """Read the log, sample a family, propose one candidate from it.

    In production the `brief` field is generated by an LLM call conditioned on
    (a) the archetype prompt, (b) the account's voice profile, (c) the topic
    bank, and (d) a constraint that this brief is semantically distinct from
    the last 7 days of shipped content. Stubbed here so the file stands alone.
    """
    bandit = Bandit.from_log(log)
    family = bandit.pick_family()
    archetype = FAMILY_ARCHETYPES[family]

    # Stubbed brief — real version calls the LLM with the above context
    brief = f"[{family}] candidate #{iteration} under archetype: {archetype}"

    return Hypothesis(
        target_id = f"{family}_{iteration:04d}",
        family    = family,
        archetype = archetype,
        brief     = brief,
    )


# --------------------------------------------------------------------------- #
# Explain — why did we pick this family?
# --------------------------------------------------------------------------- #

def explain_choice(log: ResultsLog) -> str:
    """Produce a one-line audit summary of the current bandit state.

    Makes the autoresearch loop's reasoning traceable. The explanation is
    appended to every log row as provenance.
    """
    bandit = Bandit.from_log(log)
    parts = []
    for fam in FAMILY_ARCHETYPES:
        p = bandit.posteriors[fam]
        rate = p.kept / (p.kept + p.discarded) if (p.kept + p.discarded) else 0
        parts.append(f"{fam}:{p.kept}/{p.kept+p.discarded}({rate:.1%})")
    return " | ".join(parts)


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    random.seed(42)
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tf:
        path = Path(tf.name)

    log = ResultsLog(path)

    # Simulate 30 iterations of shipping
    for i in range(30):
        h = propose_next(log, iteration=i)
        # Simulate outcome — numbered_breakdown and teardown tend to win
        if h.family in ("numbered_breakdown", "teardown"):
            outcome = "kept" if random.random() < 0.7 else "discarded"
        elif h.family == "quick_take":
            outcome = "kept" if random.random() < 0.15 else "discarded"
        else:
            outcome = "kept" if random.random() < 0.45 else "discarded"
        log.append("ship_test", h.target_id, random.uniform(-5, 40), outcome)

    print("After 30 iterations:")
    print(explain_choice(log))
    print("\nNext proposal:")
    h = propose_next(log, iteration=31)
    print(f"  family: {h.family}")
    print(f"  brief:  {h.brief}")

    path.unlink(missing_ok=True)
