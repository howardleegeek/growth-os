"""Benchmark: measure how fast the Twitter simulator runs.

The IMPLEMENTATION doc claims ~0.1ms per simulate() call. This script
measures it empirically so the claim is reproducible.

Usage:
    cd growth-os
    python3 benchmarks/simulator_speed.py

Output is written to stdout AND to benchmarks/results/simulator_speed.txt
so CI can check it in.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from statistics import mean, median, stdev

# Make the engine importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from twitter_simulator import SimulatedPost, simulate  # noqa: E402

N_TRIALS      = 100_000
WARMUP_TRIALS = 1_000


def _candidate() -> SimulatedPost:
    return SimulatedPost(
        text_length=1800, has_self_reply=True, self_reply_window_sec=170,
        has_thread=True, hook_type="numbered_breakdown", safety_tier="A",
        expertise_signal=0.85, teaser_strength=0.70, contrarianness=0.30,
        tone_risk=0.05, virality_signal=0.15, general_quality=0.80,
    )


def main() -> None:
    post = _candidate()

    # Warmup
    for _ in range(WARMUP_TRIALS):
        simulate(post)

    # Timed trials
    durations_us: list[float] = []
    for _ in range(N_TRIALS):
        start = time.perf_counter_ns()
        simulate(post)
        durations_us.append((time.perf_counter_ns() - start) / 1_000)

    mean_us  = mean(durations_us)
    med_us   = median(durations_us)
    std_us   = stdev(durations_us)
    p95_us   = sorted(durations_us)[int(N_TRIALS * 0.95)]
    p99_us   = sorted(durations_us)[int(N_TRIALS * 0.99)]

    report = (
        f"Twitter simulator speed benchmark\n"
        f"==================================\n"
        f"Trials:    {N_TRIALS:,}\n"
        f"Mean:      {mean_us:>8.2f} μs per call\n"
        f"Median:    {med_us:>8.2f} μs per call\n"
        f"Stdev:     {std_us:>8.2f} μs\n"
        f"p95:       {p95_us:>8.2f} μs\n"
        f"p99:       {p99_us:>8.2f} μs\n"
        f"\n"
        f"Simulations per second (mean):   {1_000_000 / mean_us:>10,.0f}\n"
        f"Simulations per second (median): {1_000_000 / med_us:>10,.0f}\n"
    )

    print(report)

    # Persist
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "simulator_speed.txt").write_text(report)

    # Assert the claimed speed. IMPLEMENTATION.md says ~0.1ms (100μs).
    # We assert a generous 10x bound so CI doesn't flake on slow runners.
    assert mean_us < 1_000, f"Simulator is >1ms per call ({mean_us:.1f}μs) — too slow"


if __name__ == "__main__":
    main()
