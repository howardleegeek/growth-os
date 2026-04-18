"""Tests for engine/twitter_simulator.py — offline oracle correctness + determinism."""
from __future__ import annotations

from twitter_simulator import SimulatedPost, prescreen, simulate


def _good() -> SimulatedPost:
    return SimulatedPost(
        text_length=1800, has_self_reply=True, self_reply_window_sec=170,
        has_thread=True, hook_type="numbered_breakdown", safety_tier="A",
        expertise_signal=0.85, teaser_strength=0.70, contrarianness=0.30,
        tone_risk=0.05, virality_signal=0.15, general_quality=0.80,
    )


def _bad() -> SimulatedPost:
    return SimulatedPost(
        text_length=90, has_self_reply=False, self_reply_window_sec=0,
        has_thread=False, hook_type="quick_take", safety_tier="C",
        expertise_signal=0.20, teaser_strength=0.10, contrarianness=0.80,
        tone_risk=0.60, virality_signal=0.05, general_quality=0.30,
    )


def test_simulator_ranks_good_above_bad():
    assert simulate(_good()).score > simulate(_bad()).score


def test_simulator_is_deterministic():
    """No RNG in the oracle — same input produces same output."""
    post = _good()
    assert simulate(post).score == simulate(post).score


def test_high_quality_biggest_contributor_is_self_reply():
    """The 75x lever should dominate for a post with self_reply."""
    assert simulate(_good()).biggest_contributor == "author_replies_own_post"


def test_low_quality_biggest_penalty_is_negative_feedback_or_report():
    result = simulate(_bad())
    assert result.biggest_penalty in {"negative_feedback", "report"}


def test_self_reply_window_affects_score():
    """Out-of-optimal window should score lower."""
    optimal = SimulatedPost(**{**_good().__dict__, "self_reply_window_sec": 170})
    bad_timing = SimulatedPost(**{**_good().__dict__, "self_reply_window_sec": 500})
    assert simulate(optimal).score > simulate(bad_timing).score


def test_tier_d_never_wins_simulation():
    """A tier-D post should always score worse than the corresponding tier-A."""
    post_a = _good()
    post_d = SimulatedPost(**{**post_a.__dict__, "safety_tier": "D", "tone_risk": 0.9})
    assert simulate(post_a).score > simulate(post_d).score


def test_prescreen_keeps_top_fraction():
    posts = [_good(), _bad(), _good(), _bad()]
    survivors = prescreen(posts, keep_top_frac=0.5)
    assert len(survivors) == 2
    # Survivors should be the good ones
    assert all(s[1].score > 0 for s in survivors)


def test_prescreen_returns_scored_pairs_in_descending_order():
    posts = [_bad(), _good(), _bad(), _good()]
    survivors = prescreen(posts, keep_top_frac=1.0)
    scores = [s[1].score for s in survivors]
    assert scores == sorted(scores, reverse=True)


def test_simulator_is_fast_enough_for_prescreening():
    """Sanity check: 1000 simulations should complete in under 1 second."""
    import time
    post = _good()
    start = time.perf_counter()
    for _ in range(1000):
        simulate(post)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"1000 simulations took {elapsed:.3f}s, too slow"
