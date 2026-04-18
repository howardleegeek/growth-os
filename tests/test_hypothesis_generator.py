"""Tests for engine/hypothesis_generator.py — bandit over pattern families."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from hypothesis_generator import (
    FAMILY_ARCHETYPES,
    Bandit,
    FamilyPosterior,
    Hypothesis,
    explain_choice,
    propose_next,
)
from results_log import ResultsLog


@pytest.fixture()
def log_with_history(tmp_path: Path) -> ResultsLog:
    random.seed(42)
    log = ResultsLog(tmp_path / "history.tsv")
    # Seed: numbered_breakdown has good track record
    for i in range(10):
        log.append("ship_test", f"numbered_breakdown_{i:04d}", 20.0, "kept")
    for i in range(10, 15):
        log.append("ship_test", f"quick_take_{i:04d}", -3.0, "discarded")
    return log


def test_bandit_derives_posteriors_from_log(log_with_history: ResultsLog):
    b = Bandit.from_log(log_with_history)
    # numbered_breakdown should have high kept count
    assert b.posteriors["numbered_breakdown"].kept == 10
    # quick_take should have high discarded count
    assert b.posteriors["quick_take"].discarded == 5


def test_bandit_prefers_winning_families(log_with_history: ResultsLog):
    random.seed(7)
    b = Bandit.from_log(log_with_history)
    # Over many samples, numbered_breakdown should win most of the time
    wins = sum(1 for _ in range(1000) if b.pick_family() == "numbered_breakdown")
    assert wins > 500, f"numbered_breakdown won only {wins}/1000"


def test_family_posterior_sample_in_unit_interval():
    """Beta-distribution samples must live in [0, 1]."""
    p = FamilyPosterior(family="numbered_breakdown", kept=5, discarded=5)
    for _ in range(100):
        s = p.sample()
        assert 0.0 <= s <= 1.0


def test_propose_next_returns_valid_hypothesis(log_with_history: ResultsLog):
    random.seed(42)
    h = propose_next(log_with_history, iteration=100)
    assert isinstance(h, Hypothesis)
    assert h.family in FAMILY_ARCHETYPES
    assert h.target_id.startswith(h.family + "_")
    assert h.brief != ""


def test_explain_choice_covers_all_families(log_with_history: ResultsLog):
    summary = explain_choice(log_with_history)
    for fam in FAMILY_ARCHETYPES:
        assert fam in summary


def test_bandit_handles_empty_log(tmp_path: Path):
    """Cold-start case — no history means uniform priors."""
    empty = ResultsLog(tmp_path / "empty.tsv")
    b = Bandit.from_log(empty)
    for fam in FAMILY_ARCHETYPES:
        assert b.posteriors[fam].kept == 0
        assert b.posteriors[fam].discarded == 0


def test_all_pattern_families_have_archetypes():
    """Every family in the enum must have an archetype description."""
    assert len(FAMILY_ARCHETYPES) >= 8
    for fam, archetype in FAMILY_ARCHETYPES.items():
        assert archetype  # non-empty
        assert len(archetype) > 20  # meaningful description
