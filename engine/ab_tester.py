"""
A/B tester — the harness I used to run 2,000+ content variations.

This is how I actually *discovered* which signal weights mattered in practice
vs. what the public source code implied. The source gives you the coefficients;
the A/B harness gives you the empirical lift.

Runs a Thompson-sampling bandit over variation arms so we spend traffic on
what's already winning while still exploring. Reports lift against control
with a simple z-test for significance.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# Arm — one variation being tested
# --------------------------------------------------------------------------- #

@dataclass
class Arm:
    name: str
    impressions: int = 0
    conversions: int = 0   # "conversion" = profile click (the proxy for intent)

    @property
    def rate(self) -> float:
        return self.conversions / self.impressions if self.impressions else 0.0

    # Beta(α, β) posterior with uniform prior
    def sample(self) -> float:
        alpha = 1 + self.conversions
        beta  = 1 + self.impressions - self.conversions
        return random.betavariate(alpha, beta)


# --------------------------------------------------------------------------- #
# Experiment
# --------------------------------------------------------------------------- #

@dataclass
class Experiment:
    name: str
    arms: list[Arm] = field(default_factory=list)

    def choose(self) -> Arm:
        """Thompson sampling — each arm samples from its posterior, highest wins."""
        return max(self.arms, key=lambda a: a.sample())

    def record(self, arm: Arm, converted: bool) -> None:
        arm.impressions += 1
        if converted:
            arm.conversions += 1

    # --- Reporting -------------------------------------------------------- #

    def report(self) -> str:
        control = self.arms[0]
        lines = [f"Experiment: {self.name}", "-" * 50]
        for arm in self.arms:
            lift = (arm.rate / control.rate - 1) * 100 if control.rate else 0.0
            sig  = self._z_vs(control, arm)
            lines.append(
                f"  {arm.name:<30} rate={arm.rate:.3%}  "
                f"lift={lift:+6.1f}%  z={sig:+.2f}  n={arm.impressions}"
            )
        return "\n".join(lines)

    @staticmethod
    def _z_vs(control: Arm, variant: Arm) -> float:
        """Two-proportion z-test. |z| >= 1.96 ≈ p < 0.05 two-sided."""
        if not (control.impressions and variant.impressions):
            return 0.0
        p1, n1 = control.rate, control.impressions
        p2, n2 = variant.rate, variant.impressions
        p_pool = (control.conversions + variant.conversions) / (n1 + n2)
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        return (p2 - p1) / se if se else 0.0


# --------------------------------------------------------------------------- #
# Example: the self-reply test that confirmed the 75× weight was real
# --------------------------------------------------------------------------- #

def example_self_reply_test() -> None:
    exp = Experiment(
        name="Self-reply-within-3min vs no-reply",
        arms=[
            Arm(name="no_reply (control)"),
            Arm(name="self_reply_3min"),
            Arm(name="self_reply_immediate"),
        ],
    )

    # Simulated ground truth — the 3-min self-reply is ~3× better on profile clicks
    true_rates = {
        "no_reply (control)":   0.012,
        "self_reply_3min":      0.037,   # matches what I observed in production
        "self_reply_immediate": 0.029,
    }

    for _ in range(10_000):
        arm = exp.choose()
        converted = random.random() < true_rates[arm.name]
        exp.record(arm, converted)

    print(exp.report())


if __name__ == "__main__":
    random.seed(42)
    example_self_reply_test()
