"""Tests for engine/ab_tester.py — Thompson-sampling bandit + z-test stats."""
from __future__ import annotations

import random

from ab_tester import Arm, Experiment


def test_arm_rate_zero_when_empty():
    assert Arm(name="a").rate == 0.0


def test_arm_rate_computes_correctly():
    arm = Arm(name="a", impressions=100, conversions=25)
    assert arm.rate == 0.25


def test_arm_sample_in_unit_interval():
    arm = Arm(name="a", impressions=100, conversions=50)
    for _ in range(50):
        s = arm.sample()
        assert 0.0 <= s <= 1.0


def test_experiment_choose_returns_an_arm():
    exp = Experiment(name="test", arms=[Arm(name="a"), Arm(name="b")])
    chosen = exp.choose()
    assert chosen in exp.arms


def test_thompson_sampling_converges_to_better_arm():
    """Over 10k trials, Thompson sampling should favor the higher true rate."""
    random.seed(42)
    exp = Experiment(
        name="convergence",
        arms=[Arm(name="control"), Arm(name="variant")],
    )
    true_rates = {"control": 0.02, "variant": 0.08}  # 4x difference

    for _ in range(10_000):
        arm = exp.choose()
        converted = random.random() < true_rates[arm.name]
        exp.record(arm, converted)

    # Variant should get most of the impressions due to Thompson exploitation
    variant = next(a for a in exp.arms if a.name == "variant")
    control = next(a for a in exp.arms if a.name == "control")
    assert variant.impressions > control.impressions
    # Observed rates should roughly reflect truth
    assert abs(variant.rate - 0.08) < 0.02
    assert abs(control.rate - 0.02) < 0.02


def test_z_test_returns_zero_with_empty_arms():
    exp = Experiment(name="t", arms=[Arm(name="a"), Arm(name="b")])
    z = exp._z_vs(exp.arms[0], exp.arms[1])
    assert z == 0.0


def test_z_test_positive_for_winning_variant():
    exp = Experiment(
        name="t",
        arms=[
            Arm(name="control", impressions=1000, conversions=10),  # 1%
            Arm(name="variant", impressions=1000, conversions=40),  # 4%
        ],
    )
    z = exp._z_vs(exp.arms[0], exp.arms[1])
    assert z > 1.96, f"variant should show significant positive lift, got z={z}"


def test_z_test_negative_for_regression():
    exp = Experiment(
        name="t",
        arms=[
            Arm(name="control", impressions=1000, conversions=40),  # 4%
            Arm(name="variant", impressions=1000, conversions=10),  # 1% — worse
        ],
    )
    z = exp._z_vs(exp.arms[0], exp.arms[1])
    assert z < -1.96, f"variant should show significant regression, got z={z}"


def test_report_format_contains_all_arms():
    exp = Experiment(name="t", arms=[
        Arm(name="control", impressions=100, conversions=5),
        Arm(name="v1", impressions=100, conversions=10),
    ])
    report = exp.report()
    assert "control" in report
    assert "v1" in report
    assert "Experiment: t" in report
