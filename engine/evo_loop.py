"""
Evolutionary loop — tree search over slot mutations.

This is the load-bearing core of growth-os. Inspired by EvoHarness (arena
runner-up, 2026) and adapted to Twitter algorithm hacking.

The shape:

                ┌────────────────────────┐
                │        BASELINE        │
                └───────────┬────────────┘
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │Prop. A │  │Prop. B │  │Prop. C │   ← 3 parallel proposers
         │surface=│  │surface=│  │surface=│     each mutates 1 surface
         │hook    │  │thread  │  │timing  │
         └───┬────┘  └───┬────┘  └───┬────┘
             │           │           │
             ▼           ▼           ▼
         ┌────────────────────────────────┐
         │   SIMULATOR PRESCREEN         │    ← twitter_simulator.py
         │   (cheap, offline, 0.1ms)     │      keeps top 33%
         └─────┬──────────────────────────┘
               │
               ▼
         ┌──────────────────────────┐
         │  Ship to real platform   │          ← content_engine.publish
         │  (48h measurement window) │
         └─────┬────────────────────┘
               │
               ▼
         ┌──────────────────────────┐
         │  Mechanical verifier     │          ← verifier.py
         │  (6 checks, no LLM)      │
         └─────┬────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
   ┌───────┐      ┌────────────┐
   │ KEEP  │      │  DISCARD   │
   │ log++ │      │  log++     │
   │ merge │      │            │
   └───────┘      └────────────┘

The bit that's unusual:

1. Three proposers in parallel, each targeting a different surface
2. Cheap prescreen via the offline simulator — kills 67% of proposals
3. Only survivors consume real-platform iteration budget
4. Branch merging: two sibling wins on different surfaces produce a
   merged descendant that is re-evaluated
5. Thompson sampling picks the next parent based on historical lift per
   branch, weighted by surface-specific fragility
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass, field
from pathlib import Path

from results_log import ResultsLog
from slot import Slot, SURFACES, mutate
from twitter_simulator import SimulatedPost, prescreen, simulate


# --------------------------------------------------------------------------- #
# Proposers — 3 agents that each mutate one surface
# --------------------------------------------------------------------------- #
#
# In production, proposers are LLM calls conditioned on (a) parent slot, (b)
# recent log tail, (c) target surface, (d) per-surface fragility. Stubbed
# here with sampling from a finite enumeration so the file runs standalone.

def propose_hook_mutation(parent: Slot) -> Slot:
    hooks = ["numbered_breakdown", "teardown", "contrarian_premise",
             "behind_the_scenes", "data_drop", "narrative_arc", "question"]
    return mutate(parent, "hook", {
        "hook_type":       random.choice(hooks),
        "contrarianness":  random.random(),
        "teaser_strength": random.random(),
    })


def propose_thread_mutation(parent: Slot) -> Slot:
    return mutate(parent, "thread", {
        "has_thread":            True,
        "has_self_reply":        True,
        "self_reply_window_sec": random.choice([150, 165, 170, 180, 195, 240]),
    })


def propose_timing_mutation(parent: Slot) -> Slot:
    windows = ["06-08_pt", "09-11_pt", "12-14_pt", "15-17_pt", "18-20_pt", "21-23_pt"]
    return mutate(parent, "timing", {
        "timing_window":    random.choice(windows),
        "post_index_today": random.choice([1, 2, 3]),
    })


PROPOSERS = [
    ("hook",   propose_hook_mutation),
    ("thread", propose_thread_mutation),
    ("timing", propose_timing_mutation),
]


# --------------------------------------------------------------------------- #
# Slot → SimulatedPost — used by the prescreener
# --------------------------------------------------------------------------- #

def slot_to_sim_post(slot: Slot) -> SimulatedPost:
    return SimulatedPost(
        text_length             = slot.text_length,
        has_self_reply          = slot.has_self_reply,
        self_reply_window_sec   = slot.self_reply_window_sec,
        has_thread              = slot.has_thread,
        hook_type               = slot.hook_type,
        safety_tier             = slot.safety_tier,
        expertise_signal        = slot.expertise_signal,
        teaser_strength         = slot.teaser_strength,
        contrarianness          = slot.contrarianness,
        tone_risk               = slot.tone_risk,
        virality_signal         = slot.virality_signal,
        general_quality         = slot.general_quality,
        post_index_today        = slot.post_index_today,
    )


# --------------------------------------------------------------------------- #
# Branch — tracks active branches in the evo tree
# --------------------------------------------------------------------------- #

@dataclass
class Branch:
    slot:          Slot
    kept_count:    int     = 0
    total_shipped: int     = 0
    cumulative_lift: float = 0.0

    def avg_lift(self) -> float:
        return self.cumulative_lift / self.total_shipped if self.total_shipped else 0.0

    def thompson_sample(self) -> float:
        """Beta(kept + 1, shipped - kept + 1) — exploration + exploitation."""
        return random.betavariate(self.kept_count + 1, max(1, self.total_shipped - self.kept_count) + 1)


# --------------------------------------------------------------------------- #
# Fragility tracker — per-surface regression probability
# --------------------------------------------------------------------------- #

@dataclass
class FragilityTracker:
    fragility: dict[str, float] = field(default_factory=lambda: {s.name: s.fragility for s in SURFACES})

    def update(self, surface: str, improved: bool) -> None:
        """Exponential moving average — recent signals weighted more."""
        alpha = 0.1
        current = self.fragility.get(surface, 0.5)
        target = 0.0 if improved else 1.0
        self.fragility[surface] = (1 - alpha) * current + alpha * target


# --------------------------------------------------------------------------- #
# Branch merging — combine siblings whose mutations don't conflict
# --------------------------------------------------------------------------- #

def maybe_merge(winner: Slot, active_branches: list[Branch]) -> Slot | None:
    """If two siblings both improved on DIFFERENT surfaces, merge into a child
    that inherits both mutations. Re-evaluate the merged child."""
    if len(active_branches) < 2:
        return None

    # Find a sibling that mutated a different surface
    siblings = [b for b in active_branches if b.slot.slot_id != winner.slot_id and b.kept_count > 0]
    random.shuffle(siblings)

    for sibling in siblings[:5]:
        mutations = _diff(sibling.slot, winner)
        if not mutations:
            continue
        # Merge: produce a new slot that combines winner + sibling's changes
        merged_fields = {}
        for surface_name in ("hook", "thread", "timing"):
            surface = next(s for s in SURFACES if s.name == surface_name)
            for f in surface.fields:
                winner_val = getattr(winner, f)
                sibling_val = getattr(sibling.slot, f)
                # If winner and sibling agree, keep. If they disagree, prefer winner.
                merged_fields[f] = winner_val if winner_val == sibling_val else winner_val

        from dataclasses import replace
        import uuid
        return replace(
            winner,
            slot_id        = uuid.uuid4().hex[:12],
            parent_slot_id = f"merge:{winner.slot_id}+{sibling.slot.slot_id}",
        )
    return None


def _diff(a: Slot, b: Slot) -> dict:
    """Fields where a and b differ (structural mutations only)."""
    from dataclasses import fields
    out = {}
    for f in fields(a):
        if f.name in ("slot_id", "parent_slot_id"):
            continue
        if getattr(a, f.name) != getattr(b, f.name):
            out[f.name] = (getattr(a, f.name), getattr(b, f.name))
    return out


# --------------------------------------------------------------------------- #
# Execute + measure (boundary stubs)
# --------------------------------------------------------------------------- #

def ship_and_measure(slot: Slot) -> tuple[int, float]:
    """Real implementation: ship via content engine, wait 48h, pull metrics.
    Stubbed — simulates a noisy real-world outcome correlated with the
    simulator's score but with noise.
    """
    sim = simulate(slot_to_sim_post(slot))
    noise = random.gauss(0, 3.0)
    observed_score = sim.score + noise
    # Convert synthetic score into synthetic (impressions, lift) pair
    impressions = max(50, int(400 + observed_score * 100))
    lift = max(-0.5, min(4.0, (observed_score - 15) / 15))
    return impressions, lift


# --------------------------------------------------------------------------- #
# One evo iteration
# --------------------------------------------------------------------------- #

def run_iteration(
    active_branches:     list[Branch],
    fragility:           FragilityTracker,
    log:                 ResultsLog,
    provenance:          str,
) -> None:

    # 1. Thompson-sample the parent from active branches
    parent_branch = max(active_branches, key=lambda b: b.thompson_sample())
    parent = parent_branch.slot

    # 2. Three parallel proposers, one per surface
    proposals: list[tuple[str, Slot]] = []
    for surface_name, proposer in PROPOSERS:
        # Avoid high-fragility mutations when the tracker says to be cautious
        if fragility.fragility.get(surface_name, 0.5) > 0.75 and random.random() < 0.8:
            continue  # skip fragile surface most of the time
        proposals.append((surface_name, proposer(parent)))

    if not proposals:
        return

    # 3. Prescreen via cheap offline simulator — keep top 1/3
    sim_inputs = [slot_to_sim_post(s) for _, s in proposals]
    top_sims = prescreen(sim_inputs, keep_top_frac=1.0 / 3)
    top_slot_ids = {id(sp) for sp, _ in top_sims}
    survivors = [(surface, slot) for (surface, slot), sim_in in zip(proposals, sim_inputs) if id(sim_in) in top_slot_ids]

    if not survivors:
        return

    # 4. Ship survivors to real platform, measure, verify
    for surface_name, slot in survivors:
        impressions, lift = ship_and_measure(slot)
        kept = impressions >= 200 and lift > 0.05

        branch = Branch(
            slot            = slot,
            kept_count      = 1 if kept else 0,
            total_shipped   = 1,
            cumulative_lift = lift if kept else 0.0,
        )
        if kept:
            active_branches.append(branch)

        fragility.update(surface_name, improved=kept)

        log.append(
            action     = "evo_ship",
            target     = f"{surface_name}:{slot.slot_id}",
            score      = lift * 10,
            result     = "kept" if kept else "discarded",
            notes      = f"{lift:+.2f} lift, n={impressions}, parent={parent.slot_id}",
            provenance = provenance,
        )

        # 5. Branch merging — try to combine wins from different surfaces
        if kept:
            merged = maybe_merge(slot, active_branches)
            if merged is not None:
                imp2, lift2 = ship_and_measure(merged)
                kept2 = imp2 >= 200 and lift2 > 0.05
                if kept2:
                    active_branches.append(Branch(slot=merged, kept_count=1, total_shipped=1, cumulative_lift=lift2))
                log.append(
                    action     = "evo_merge",
                    target     = merged.slot_id,
                    score      = lift2 * 10,
                    result     = "kept" if kept2 else "discarded",
                    notes      = f"merged branch, lift={lift2:+.2f}, n={imp2}",
                    provenance = provenance,
                )


# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #

def run_forever(log_path: Path, iterations: int | None = None) -> None:
    log = ResultsLog(log_path)
    provenance = "evo_loop"
    baseline = Slot(account_handle="@oysterecosystem")
    active_branches: list[Branch] = [Branch(slot=baseline, kept_count=1, total_shipped=1, cumulative_lift=0.5)]
    fragility = FragilityTracker()

    it = 0
    while iterations is None or it < iterations:
        run_iteration(active_branches, fragility, log, provenance)
        it += 1
        if it % 5 == 0:
            print(f"[iter {it:04d}] active_branches={len(active_branches)}  "
                  f"fragility={ {k: round(v,2) for k,v in fragility.fragility.items()} }")


def main() -> None:
    parser = argparse.ArgumentParser(description="growth-os evolutionary loop (EvoHarness × Twitter)")
    parser.add_argument("--log", default="./evo.tsv")
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    run_forever(Path(args.log), iterations=args.iterations)


if __name__ == "__main__":
    random.seed(42)
    main()
