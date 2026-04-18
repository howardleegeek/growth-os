"""
Slot — the primitive the evolutionary loop mutates.

A "slot" in growth-os is one specific (account, time, hook, tier, voice,
depth) configuration. It's the thing EvoHarness calls a "surface." The
evo loop doesn't mutate posts directly — it mutates slots, then generates
a post that fills the mutated slot.

The separation matters. Posts are ephemeral (ship, measure, forget). Slots
are persistent (they describe the CONFIGURATION that produced a post). When
a branch wins, we save the slot config, not the post text — because what
generalizes is the configuration, not the specific words.

---

Surface decomposition — the EvoHarness pattern applied to Twitter:

A slot has 4 independently-mutable surfaces. Each has its own risk class
and fragility score. The evo loop can propose mutations to any one surface
at a time, which makes the search space finite and tractable.

                ┌───────────────────────────────┐
                │           SLOT                 │
                │                                │
                │  surface 1: hook_text          │  <- risk LOW, fragility 0.15
                │  surface 2: thread_continuation│  <- risk LOW, fragility 0.20
                │  surface 3: timing_window      │  <- risk MEDIUM, fragility 0.40
                │  surface 4: safety_tier        │  <- risk HIGH, fragility 0.90
                │                                │
                └───────────────────────────────┘

Fragility tracks how often mutations to this surface regress vs. improve.
High-fragility surfaces (like safety_tier) require more cautious mutations
and more validation before promotion.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timezone
from typing import Literal


# --------------------------------------------------------------------------- #
# Enumerated surface values
# --------------------------------------------------------------------------- #

HookType = Literal[
    "numbered_breakdown", "teardown", "contrarian_premise",
    "behind_the_scenes",  "data_drop", "narrative_arc",
    "question",           "quick_take",
]

SafetyTier = Literal["A", "B", "C", "D"]

TimingWindow = Literal[
    "06-08_pt",   # early morning PT — low competition, indexing window
    "09-11_pt",   # late morning — peak US engagement
    "12-14_pt",   # midday — lunch scroll
    "15-17_pt",   # late afternoon — secondary peak
    "18-20_pt",   # evening — EU crossover
    "21-23_pt",   # late night — low competition
]


# --------------------------------------------------------------------------- #
# The Slot
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Slot:
    """One (account × time × hook × tier × voice × depth) configuration.

    Frozen because the evo loop needs slots to be hashable and comparable
    as identity. Mutations produce new Slot instances via dataclass.replace.
    """

    # --- identity --------------------------------------------------------- #
    slot_id:          str                = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_slot_id:   str | None         = None

    # --- surface 1: hook --------------------------------------------------- #
    hook_type:        HookType           = "numbered_breakdown"
    contrarianness:   float              = 0.30     # 0..1
    teaser_strength:  float              = 0.50     # 0..1

    # --- surface 2: thread ------------------------------------------------- #
    has_thread:              bool        = True
    has_self_reply:          bool        = True
    self_reply_window_sec:   int         = 170      # optimal 165–180

    # --- surface 3: timing ------------------------------------------------- #
    timing_window:    TimingWindow       = "09-11_pt"
    post_index_today: int                = 1        # 1st, 2nd, or 3rd post of the day

    # --- surface 4: safety ------------------------------------------------- #
    safety_tier:      SafetyTier         = "A"
    tone_risk:        float              = 0.05     # 0..1, tracked independently

    # --- account bindings (not mutable by the evo loop) ------------------- #
    account_handle:   str                = "unknown"

    # --- non-surface features (derived from the generated text) ----------- #
    text_length:      int                = 1200
    expertise_signal: float              = 0.70
    virality_signal:  float              = 0.10
    general_quality:  float              = 0.70


# --------------------------------------------------------------------------- #
# Surface metadata — used by the evo loop for risk-weighted mutation
# --------------------------------------------------------------------------- #

@dataclass
class SurfaceMeta:
    name:        str
    risk_class:  Literal["LOW", "MEDIUM", "HIGH"]
    fragility:   float                       # 0..1, higher = more regression risk
    fields:      list[str]                   # which Slot fields belong to this surface


SURFACES: list[SurfaceMeta] = [
    SurfaceMeta(
        name       = "hook",
        risk_class = "LOW",
        fragility  = 0.15,
        fields     = ["hook_type", "contrarianness", "teaser_strength"],
    ),
    SurfaceMeta(
        name       = "thread",
        risk_class = "LOW",
        fragility  = 0.20,
        fields     = ["has_thread", "has_self_reply", "self_reply_window_sec"],
    ),
    SurfaceMeta(
        name       = "timing",
        risk_class = "MEDIUM",
        fragility  = 0.40,
        fields     = ["timing_window", "post_index_today"],
    ),
    SurfaceMeta(
        name       = "safety",
        risk_class = "HIGH",
        fragility  = 0.90,    # mutations here carry big downside — safety_tier C or D is catastrophic
        fields     = ["safety_tier", "tone_risk"],
    ),
]


# --------------------------------------------------------------------------- #
# Mutation — produces a child slot with one surface modified
# --------------------------------------------------------------------------- #

def mutate(slot: Slot, surface_name: str, mutations: dict) -> Slot:
    """Apply a mutation to ONE surface of a slot, returning a new child slot.

    The evo loop's proposers generate mutations like:
        {"hook_type": "teardown", "contrarianness": 0.6}
    which get passed here along with the surface name.

    Constraints enforced:
      - Only fields belonging to the named surface may be mutated
      - safety_tier "D" is never accepted — hard block at this layer
      - Child slot's parent_slot_id points back to the parent
    """
    surface = next((s for s in SURFACES if s.name == surface_name), None)
    if surface is None:
        raise ValueError(f"Unknown surface: {surface_name}")

    for field_name in mutations:
        if field_name not in surface.fields:
            raise ValueError(
                f"Field '{field_name}' does not belong to surface '{surface_name}'. "
                f"Valid fields: {surface.fields}"
            )

    # Hard block tier D at the mutation layer — belt and suspenders
    if mutations.get("safety_tier") == "D":
        raise ValueError("safety_tier D is never a valid mutation")

    new_slot = replace(
        slot,
        slot_id        = uuid.uuid4().hex[:12],
        parent_slot_id = slot.slot_id,
        **mutations,
    )
    return new_slot


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    baseline = Slot(account_handle="@oysterecosystem")
    child = mutate(baseline, "hook", {"hook_type": "teardown", "contrarianness": 0.55})

    print(f"Parent slot: {baseline.slot_id}  hook={baseline.hook_type}  contrarianness={baseline.contrarianness}")
    print(f"Child slot:  {child.slot_id}  hook={child.hook_type}  contrarianness={child.contrarianness}")
    print(f"Child's parent: {child.parent_slot_id}  (matches parent = {child.parent_slot_id == baseline.slot_id})")

    print()
    print("Surface table:")
    for s in SURFACES:
        print(f"  {s.name:<8}  risk={s.risk_class:<6}  fragility={s.fragility:.2f}  fields={s.fields}")
