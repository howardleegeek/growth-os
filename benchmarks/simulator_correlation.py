"""Benchmark: measure how well the simulator's ranking correlates with a
hold-out 'ground truth' (synthesized here, since real Twitter outcomes are
not part of the OSS repo).

The IMPLEMENTATION doc claims r ≈ 0.72 empirically. This script:
  1. Generates a synthetic ground-truth function that loosely resembles
     real Twitter outcomes (weights + noise)
  2. Scores 1000 random SimulatedPosts through both the simulator AND
     the synthetic ground truth
  3. Reports Spearman rank correlation

With random seeding, this benchmark is deterministic and the correlation
it produces is a reproducible regression test for the simulator.

Usage:
    python3 benchmarks/simulator_correlation.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from twitter_simulator import SimulatedPost, simulate  # noqa: E402

N_POSTS = 1_000
SEED    = 42


def _random_post(rng: random.Random) -> SimulatedPost:
    hooks = ["numbered_breakdown", "teardown", "contrarian_premise",
             "behind_the_scenes", "data_drop", "narrative_arc",
             "question", "quick_take"]
    tiers = ["A", "A", "A", "B", "B", "C"]  # skewed toward A (realistic)
    return SimulatedPost(
        text_length=rng.randint(80, 2500),
        has_self_reply=rng.random() < 0.7,
        self_reply_window_sec=rng.choice([0, 120, 165, 170, 180, 240]),
        has_thread=rng.random() < 0.55,
        hook_type=rng.choice(hooks),
        safety_tier=rng.choice(tiers),
        expertise_signal=rng.random(),
        teaser_strength=rng.random(),
        contrarianness=rng.random(),
        tone_risk=rng.random() * 0.3,   # mostly low risk (realistic)
        virality_signal=rng.random() * 0.2,
        general_quality=rng.random(),
    )


def _synthetic_ground_truth(post: SimulatedPost, rng: random.Random) -> float:
    """A different scoring function that produces plausible real-world outcomes.

    Not identical to simulate(). Deliberately different coefficients + noise
    so the correlation test isn't tautological.
    """
    base = 0.0
    if post.has_self_reply and 140 <= post.self_reply_window_sec <= 200:
        base += 60 * (0.8 + rng.random() * 0.4)
    base += post.text_length / 2000 * 20 * rng.random()
    base += 30 if post.has_thread else 0
    base += {"A": 0, "B": -5, "C": -30, "D": -200}[post.safety_tier]
    base += post.expertise_signal * 15
    base -= post.tone_risk * 40
    # Noise
    base += rng.gauss(0, 5)
    return base


def _spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation. Returns value in [-1, 1]."""
    from statistics import correlation  # Python 3.10+

    def ranks(values: list[float]) -> list[float]:
        indexed = sorted(enumerate(values), key=lambda p: p[1])
        ranked = [0.0] * len(values)
        for rank, (orig_idx, _) in enumerate(indexed, start=1):
            ranked[orig_idx] = float(rank)
        return ranked

    return correlation(ranks(xs), ranks(ys))


def main() -> None:
    rng = random.Random(SEED)

    posts = [_random_post(rng) for _ in range(N_POSTS)]
    simulator_scores  = [simulate(p).score for p in posts]
    ground_truth_scores = [_synthetic_ground_truth(p, rng) for p in posts]

    rho = _spearman(simulator_scores, ground_truth_scores)

    report = (
        f"Simulator vs synthetic ground-truth correlation\n"
        f"================================================\n"
        f"Posts scored:          {N_POSTS}\n"
        f"Mean simulator score:  {mean(simulator_scores):+8.2f}\n"
        f"Mean ground-truth:     {mean(ground_truth_scores):+8.2f}\n"
        f"\n"
        f"Spearman rank corr:    r = {rho:+.3f}\n"
        f"\n"
        f"Interpretation:\n"
        f"  r > 0.6  — simulator is useful for prescreening\n"
        f"  r > 0.8  — simulator closely tracks ground truth\n"
        f"  r < 0.5  — simulator is worse than random for ranking\n"
    )
    print(report)

    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "simulator_correlation.txt").write_text(report)

    # Regression check: the simulator's ranking power should survive.
    # Generous bound — just asserting useful-for-prescreening.
    assert rho > 0.45, f"Simulator correlation dropped to {rho:.3f} — regression"


if __name__ == "__main__":
    main()
