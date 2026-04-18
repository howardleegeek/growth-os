"""Tests for engine/verifier.py — the mechanical adult in the room."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from verifier import IterationInput, verify


def _good_input() -> IterationInput:
    return IterationInput(
        candidate_text="A substantive thread about reverse-engineering ranking functions",
        candidate_tier="A",
        recent_shipped_corpus=["unrelated_post_1", "unrelated_post_2"],
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


def test_good_input_passes():
    result = verify(_good_input())
    assert result.passed
    assert result.failed_checks == []


def test_stale_data_fails():
    stale = IterationInput(**{**_good_input().__dict__,
                               "metrics_fetched_at": datetime.now(timezone.utc) - timedelta(days=2)})
    result = verify(stale)
    assert not result.passed
    assert "metrics_stale" in result.failed_checks


def test_tiny_sample_fails():
    tiny = IterationInput(**{**_good_input().__dict__, "impressions": 42})
    result = verify(tiny)
    assert not result.passed
    assert "insufficient_sample_size" in result.failed_checks


def test_sub_threshold_score_fails():
    low = IterationInput(**{**_good_input().__dict__, "score_vs_weight_map": 1.2})
    result = verify(low)
    assert not result.passed
    assert "below_ship_threshold" in result.failed_checks


def test_tier_d_hard_blocked():
    d_tier = IterationInput(**{**_good_input().__dict__, "candidate_tier": "D"})
    result = verify(d_tier)
    assert not result.passed
    assert "tier_quota_violation" in result.failed_checks


def test_tier_c_over_quota_fails():
    """If 3 tier-C already shipped out of 5 today (60%), adding another should fail."""
    over = IterationInput(**{**_good_input().__dict__,
                              "candidate_tier": "C",
                              "tier_c_shipped_today": 3,
                              "total_shipped_today": 5})
    result = verify(over)
    assert not result.passed
    assert "tier_quota_violation" in result.failed_checks


def test_insignificant_lift_fails():
    """Positive lift but |z| < 1.96 should be rejected as noise."""
    marginal = IterationInput(**{**_good_input().__dict__,
                                  "engagement_rate": 0.016,  # barely above 0.015 control
                                  "impressions": 220})
    result = verify(marginal)
    assert not result.passed
    assert "lift_not_significant" in result.failed_checks


def test_duplicate_is_caught():
    """If candidate repeats recent content verbatim, should be flagged."""
    original_text = "A substantive thread about reverse-engineering ranking functions"
    dup = IterationInput(**{**_good_input().__dict__,
                             "recent_shipped_corpus": [original_text, "other"]})
    result = verify(dup)
    assert not result.passed
    assert "duplicate_of_recent_post" in result.failed_checks


def test_no_llm_calls_in_verifier():
    """Static sanity: verifier module must not import any LLM client."""
    import verifier as v
    src = open(v.__file__).read()
    # Accept comments/docstrings mentioning LLMs (that's intentional)
    # But forbid actual imports of LLM clients
    for forbidden in ["import openai", "import anthropic", "from openai", "from anthropic"]:
        assert forbidden not in src, f"Verifier imports {forbidden} — must be LLM-free"


def test_verifier_is_deterministic():
    """Same input → same output. No randomness in decisions."""
    inp = _good_input()
    r1 = verify(inp)
    r2 = verify(inp)
    assert r1.passed == r2.passed
    assert r1.failed_checks == r2.failed_checks
