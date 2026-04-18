"""Tests for engine/slot.py — surface decomposition + mutation invariants."""
from __future__ import annotations

import pytest

from slot import SURFACES, Slot, mutate


def test_baseline_slot_is_hashable():
    """Frozen dataclass invariant — slots must be usable as dict keys / set members."""
    s = Slot()
    {s: 1}  # hashable
    {s}  # hashable


def test_mutation_changes_slot_id():
    parent = Slot(slot_id="parent-xyz")
    child = mutate(parent, "hook", {"hook_type": "teardown"})
    assert child.slot_id != parent.slot_id


def test_child_references_parent():
    parent = Slot(slot_id="parent-xyz")
    child = mutate(parent, "hook", {"hook_type": "teardown"})
    assert child.parent_slot_id == "parent-xyz"


def test_mutation_only_changes_target_fields():
    parent = Slot(slot_id="p1", hook_type="numbered_breakdown",
                  has_thread=True, timing_window="09-11_pt", safety_tier="A")
    child = mutate(parent, "hook", {"hook_type": "teardown"})

    # Target surface field changed
    assert child.hook_type == "teardown"
    # Other surfaces unchanged
    assert child.has_thread == parent.has_thread
    assert child.timing_window == parent.timing_window
    assert child.safety_tier == parent.safety_tier


def test_mutation_rejects_cross_surface_field():
    """You cannot mutate `has_thread` while targeting the `hook` surface."""
    parent = Slot()
    with pytest.raises(ValueError, match="does not belong to surface"):
        mutate(parent, "hook", {"has_thread": False})


def test_mutation_rejects_unknown_surface():
    parent = Slot()
    with pytest.raises(ValueError, match="Unknown surface"):
        mutate(parent, "made_up_surface", {"hook_type": "teardown"})


def test_tier_d_mutation_is_hard_blocked():
    """Safety tier D is never acceptable — belt-and-suspenders check."""
    parent = Slot()
    with pytest.raises(ValueError, match="tier D is never"):
        mutate(parent, "safety", {"safety_tier": "D"})


def test_all_four_surfaces_defined():
    """The documented surface set must be present."""
    names = {s.name for s in SURFACES}
    assert names == {"hook", "thread", "timing", "safety"}


def test_safety_surface_has_highest_fragility():
    """Safety has the most regression risk, by design."""
    safety = next(s for s in SURFACES if s.name == "safety")
    others = [s for s in SURFACES if s.name != "safety"]
    assert all(safety.fragility > s.fragility for s in others)
    assert safety.risk_class == "HIGH"
