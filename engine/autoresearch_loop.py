"""
Autoresearch loop — the runnable core of growth-os.

Reads like prose because the shape matters more than any single line:

    while True:
        hypothesis = propose_next(log, iteration)
        outcome    = execute(hypothesis)
        metrics    = measure(outcome)
        result     = verify(...)
        log.append(action, target, score, result)
        iteration += 1

Everything else in this repo is supporting infrastructure for this loop.

Production note: this reference implementation runs synchronously and stubs
the `execute` and `measure` boundaries because those cross network, platform
APIs, and persistence layers that are environment-specific. In production at
Oyster Labs, `execute` calls the multi-account content engine and `measure`
pulls from the analytics store 48 hours later.

The verifier and the log are the non-negotiable pieces — those work
unchanged in every deployment.
"""

from __future__ import annotations

import argparse
import random
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hypothesis_generator import Hypothesis, explain_choice, propose_next
from results_log import ResultsLog
from verifier import IterationInput, VerificationResult, verify


# --------------------------------------------------------------------------- #
# Execute + measure (boundary stubs — replace with real platform clients)
# --------------------------------------------------------------------------- #

@dataclass
class ExecutionResult:
    post_id:         str
    shipped_at:      datetime
    candidate_text:  str


def execute(hypothesis: Hypothesis) -> ExecutionResult:
    """Ship the candidate through the content engine.

    Real implementation:
      1. Run the generator (LLM) conditioned on hypothesis.archetype + brief
      2. Score it, run it through safety-tier gate
      3. Queue it in the scheduler; it will publish at its assigned slot
      4. Return the post_id and shipped timestamp

    Stubbed here — returns a synthetic post_id.
    """
    return ExecutionResult(
        post_id        = f"ps_{hypothesis.target_id}",
        shipped_at     = datetime.now(timezone.utc),
        candidate_text = hypothesis.brief,
    )


@dataclass
class Metrics:
    impressions:          int
    engagement_rate:      float
    score_vs_weight_map:  float
    tier:                 str


def measure(post: ExecutionResult, wait_hours: int = 48) -> Metrics:
    """Pull platform metrics after the measurement window.

    Real implementation:
      1. Sleep until shipped_at + wait_hours (or schedule a callback)
      2. Hit platform API for impressions / clicks / replies / dwell
      3. Compute score against the current weight map
      4. Return

    Stubbed here — simulates a noisy outcome.
    """
    # Simulate some posts being winners, some being losers
    is_winner = random.random() < 0.42
    return Metrics(
        impressions         = random.randint(500, 8000) if is_winner else random.randint(50, 2500),
        engagement_rate     = random.uniform(0.02, 0.06) if is_winner else random.uniform(0.001, 0.02),
        score_vs_weight_map = random.uniform(8.0, 48.0)  if is_winner else random.uniform(-4.0, 6.0),
        tier                = random.choices(["A", "B", "C"], weights=[65, 30, 5])[0],
    )


# --------------------------------------------------------------------------- #
# Control baseline — rolling 30-day median for this account
# --------------------------------------------------------------------------- #

@dataclass
class Baseline:
    """Synthesized from the last 30 days of shipped posts on this account."""
    rate: float = 0.015
    n:    int = 3200


def current_baseline(_log: ResultsLog) -> Baseline:
    """Compute the rolling control baseline.

    Real implementation reads platform metrics for the rolling window and
    computes the median engagement rate + cumulative impressions. Stubbed
    here with a plausible static value.
    """
    return Baseline()


# --------------------------------------------------------------------------- #
# The loop
# --------------------------------------------------------------------------- #

def run_once(log: ResultsLog, iteration: int, recent_corpus: list[str],
             tier_c_shipped_today: int, total_shipped_today: int,
             provenance: str) -> VerificationResult:
    """One full iteration — hypothesize, execute, measure, verify, log."""

    hypothesis = propose_next(log, iteration=iteration)
    execution  = execute(hypothesis)
    metrics    = measure(execution)
    baseline   = current_baseline(log)

    inp = IterationInput(
        candidate_text          = execution.candidate_text,
        candidate_tier          = metrics.tier,
        recent_shipped_corpus   = recent_corpus,
        metrics_fetched_at      = datetime.now(timezone.utc),
        impressions             = metrics.impressions,
        engagement_rate         = metrics.engagement_rate,
        score_vs_weight_map     = metrics.score_vs_weight_map,
        ship_threshold          = 5.0,
        control_rate            = baseline.rate,
        control_n               = baseline.n,
        tier_c_shipped_today    = tier_c_shipped_today,
        total_shipped_today     = total_shipped_today,
    )
    vr = verify(inp)

    log.append(
        action     = "ship_test",
        target     = hypothesis.target_id,
        score      = metrics.score_vs_weight_map,
        result     = vr.to_tsv_result() if vr.passed else "discarded",
        notes      = vr.note,
        provenance = provenance,
    )
    return vr


def run_forever(log_path: Path, max_iterations: int | None = None, sleep_seconds: float = 0.0) -> None:
    """Run the loop. Pass max_iterations=None for true forever-run.

    Most production deployments use max_iterations=None plus a systemd/launchd
    wrapper that restarts the process on crash.
    """
    log = ResultsLog(log_path)
    provenance = _git_hash()

    iteration = 0
    recent_corpus: list[str] = []
    shipped_today = 0
    tier_c_shipped_today = 0
    day_of_last_reset = datetime.now(timezone.utc).date()

    while max_iterations is None or iteration < max_iterations:
        # Daily counter reset
        today = datetime.now(timezone.utc).date()
        if today != day_of_last_reset:
            shipped_today = 0
            tier_c_shipped_today = 0
            day_of_last_reset = today

        iteration += 1
        vr = run_once(
            log                   = log,
            iteration             = iteration,
            recent_corpus         = recent_corpus[-200:],
            tier_c_shipped_today  = tier_c_shipped_today,
            total_shipped_today   = shipped_today,
            provenance            = provenance,
        )
        shipped_today += 1

        print(f"[iter {iteration:06d}] {'KEPT    ' if vr.passed else 'discarded'}  "
              f"score={vr.score:+6.1f}  {vr.note}")

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #

def _git_hash() -> str:
    """Short git hash at the time of execution. Logged as provenance."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).parent,
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return "nogit"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(description="growth-os autoresearch loop")
    parser.add_argument("--log", default="./autoresearch.tsv",
                        help="Path to append-only TSV log")
    parser.add_argument("--iterations", type=int, default=20,
                        help="Max iterations this run (None = forever)")
    parser.add_argument("--sleep", type=float, default=0.0,
                        help="Seconds to sleep between iterations")
    args = parser.parse_args()

    run_forever(
        log_path       = Path(args.log),
        max_iterations = args.iterations,
        sleep_seconds  = args.sleep,
    )


if __name__ == "__main__":
    random.seed(42)
    main()
