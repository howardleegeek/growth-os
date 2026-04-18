"""Tests for engine/evo_loop.py — EvoHarness tree search smoke tests."""
from __future__ import annotations

import random
from pathlib import Path

from evo_loop import (
    Branch,
    FragilityTracker,
    propose_hook_mutation,
    propose_thread_mutation,
    propose_timing_mutation,
    run_forever,
    slot_to_sim_post,
)
from results_log import ResultsLog
from slot import Slot


def test_slot_to_sim_post_preserves_key_fields():
    slot = Slot(account_handle="@x", hook_type="teardown", contrarianness=0.6)
    sim = slot_to_sim_post(slot)
    assert sim.hook_type == "teardown"
    assert sim.contrarianness == 0.6


def test_hook_proposer_only_mutates_hook_surface():
    random.seed(1)
    parent = Slot(has_thread=True, timing_window="09-11_pt", safety_tier="A")
    child = propose_hook_mutation(parent)
    # Non-hook fields unchanged
    assert child.has_thread == parent.has_thread
    assert child.timing_window == parent.timing_window
    assert child.safety_tier == parent.safety_tier


def test_thread_proposer_enables_self_reply():
    random.seed(1)
    parent = Slot(has_thread=False, has_self_reply=False)
    child = propose_thread_mutation(parent)
    assert child.has_self_reply is True
    assert child.has_thread is True


def test_timing_proposer_picks_valid_window():
    random.seed(1)
    parent = Slot()
    child = propose_timing_mutation(parent)
    assert child.timing_window in {
        "06-08_pt", "09-11_pt", "12-14_pt",
        "15-17_pt", "18-20_pt", "21-23_pt",
    }


def test_branch_avg_lift_empty():
    b = Branch(slot=Slot(), kept_count=0, total_shipped=0)
    assert b.avg_lift() == 0.0


def test_branch_avg_lift_nonzero():
    b = Branch(slot=Slot(), kept_count=2, total_shipped=4, cumulative_lift=1.6)
    assert b.avg_lift() == 0.4


def test_fragility_tracker_updates_on_regression():
    tracker = FragilityTracker()
    initial = tracker.fragility["hook"]
    # Simulate several regressions
    for _ in range(20):
        tracker.update("hook", improved=False)
    assert tracker.fragility["hook"] > initial


def test_fragility_tracker_decreases_on_improvement():
    tracker = FragilityTracker()
    # Start with high fragility, see if improvements lower it
    tracker.fragility["hook"] = 0.8
    for _ in range(20):
        tracker.update("hook", improved=True)
    assert tracker.fragility["hook"] < 0.8


def test_run_forever_produces_log_rows(tmp_path: Path):
    """End-to-end smoke: 5 iterations should leave at least 5 rows in the TSV."""
    random.seed(42)
    log_path = tmp_path / "evo.tsv"
    run_forever(log_path, iterations=5)

    # Count non-header lines
    lines = log_path.read_text().splitlines()
    assert len(lines) >= 6  # header + at least 5 iterations


def test_run_forever_log_rows_have_valid_result(tmp_path: Path):
    random.seed(42)
    log_path = tmp_path / "evo.tsv"
    run_forever(log_path, iterations=5)

    log = ResultsLog(log_path)
    rows = log.tail(20)
    valid_results = {"kept", "discarded", "failed"}
    for r in rows:
        assert r.result in valid_results, f"Unexpected result: {r.result}"
