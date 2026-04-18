"""Tests for engine/signal_weights.py — weight map integrity + scoring math."""
from __future__ import annotations

import pytest

from signal_weights import (
    AUTHOR_DIVERSITY_DECAY,
    MIN_SHIPPABLE_SCORE,
    PostProjection,
    SAFETY_TIER_MAX_SHARE,
    SIGNAL_WEIGHTS,
    effective_weight,
)


# --------------------------------------------------------------------------- #
# Weight map integrity
# --------------------------------------------------------------------------- #

def test_weight_map_has_expected_signals():
    """The 8 published Twitter signals must be present."""
    expected = {
        "author_replies_own_post",
        "being_replied_to",
        "profile_click",
        "deep_dwell_over_2min",
        "retweet",
        "like",
        "negative_feedback",
        "report",
    }
    assert set(SIGNAL_WEIGHTS) == expected


def test_self_reply_is_the_largest_positive_weight():
    """The +75x self-reply signal should be the largest positive coefficient."""
    positives = {k: v for k, v in SIGNAL_WEIGHTS.items() if v > 0}
    assert max(positives, key=positives.get) == "author_replies_own_post"


def test_report_is_the_largest_negative_weight():
    """Report penalty should dwarf all other negatives."""
    negatives = {k: v for k, v in SIGNAL_WEIGHTS.items() if v < 0}
    assert min(negatives, key=negatives.get) == "report"


def test_negative_weights_are_asymmetric():
    """Report penalty dwarfs all positives — one report kills hundreds of good posts."""
    max_positive = max(SIGNAL_WEIGHTS.values())      # author_replies_own_post = 75
    max_neg_magnitude = abs(min(SIGNAL_WEIGHTS.values()))  # report = 738
    # Asymmetric means report >= 5x the biggest positive signal
    assert max_neg_magnitude >= 5 * max_positive


def test_like_is_the_baseline():
    """Like is documented as the +1 baseline unit."""
    assert SIGNAL_WEIGHTS["like"] == 1.0


# --------------------------------------------------------------------------- #
# Decay
# --------------------------------------------------------------------------- #

def test_decay_factor_is_documented_value():
    """Diversity decay is the 0.625 value from the documented ranker behavior."""
    assert AUTHOR_DIVERSITY_DECAY == pytest.approx(0.625)


def test_effective_weight_reduces_with_post_index():
    base = 100.0
    assert effective_weight(base, post_index_today=1) == pytest.approx(100.0)
    assert effective_weight(base, post_index_today=2) == pytest.approx(62.5)
    assert effective_weight(base, post_index_today=3) == pytest.approx(39.0625)


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #

def _high_quality_projection() -> PostProjection:
    return PostProjection(
        p_author_replies_own_post=0.95,
        p_being_replied_to=0.35,
        p_profile_click=0.15,
        p_deep_dwell_over_2min=0.45,
        p_retweet=0.05,
        p_like=0.60,
        p_negative_feedback=0.01,
        p_report=0.0001,
    )


def test_high_quality_post_clears_ship_threshold():
    score = _high_quality_projection().score()
    assert score >= MIN_SHIPPABLE_SCORE


def test_scoring_is_deterministic():
    """Same projection must produce same score every time."""
    p = _high_quality_projection()
    assert p.score() == p.score()
    assert p.score() == p.score()


def test_post_index_affects_score_via_decay():
    p = _high_quality_projection()
    assert p.score(post_index_today=1) > p.score(post_index_today=2)
    assert p.score(post_index_today=2) > p.score(post_index_today=3)


# --------------------------------------------------------------------------- #
# Safety tiers
# --------------------------------------------------------------------------- #

def test_tier_d_has_zero_max_share():
    """Tier D must be hard-blocked."""
    assert SAFETY_TIER_MAX_SHARE["D"] == 0.0


def test_tier_c_capped_at_ten_percent():
    """Tier C should max at 10% of daily volume."""
    assert SAFETY_TIER_MAX_SHARE["C"] <= 0.10


def test_tier_a_is_unrestricted():
    assert SAFETY_TIER_MAX_SHARE["A"] == 1.00
