"""Tests for engine/grok_playbook_miner.py — AlphaGo supervised phase.

Runs fully offline — Grok API calls are stubbed when XAI_API_KEY isn't set,
and all tests in this file must work with no key.
"""
from __future__ import annotations

from grok_playbook_miner import (
    AccountObservation,
    GrokClient,
    compare_accounts,
    derive_priors,
    mine_playbooks,
    study_account,
)
from hypothesis_generator import FAMILY_ARCHETYPES


def test_grok_client_initializes_without_key(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    client = GrokClient()
    # Must degrade gracefully to offline stub
    response = client.analyze("test")
    assert "STUB" in response.upper() or "OFFLINE" in response.upper()


def test_study_account_returns_observation(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    obs = study_account("example_handle", GrokClient())
    assert isinstance(obs, AccountObservation)
    assert obs.handle == "example_handle"
    assert 0.0 <= obs.self_reply_rate <= 1.0
    assert 0.0 <= obs.thread_rate <= 1.0
    assert obs.post_count_90d > 0


def test_compare_accounts_produces_consensus(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    client = GrokClient()
    observations = [
        study_account("a", client),
        study_account("b", client),
        study_account("c", client),
    ]
    report = compare_accounts(observations, client)
    # consensus_patterns is a list
    assert isinstance(report.consensus_patterns, list)
    assert len(report.accounts) == 3


def test_derive_priors_produces_all_families():
    # Build a minimal report to derive priors from
    from grok_playbook_miner import ComparativeReport
    report = ComparativeReport(
        accounts=[],
        consensus_patterns=["numbered_breakdown", "teardown"],
        underused_patterns=["quick_take"],
        timing_consensus="09-11_pt",
        self_reply_consensus=True,
        notes="test",
    )
    priors = derive_priors(report, virtual_trials=20)
    for fam in FAMILY_ARCHETYPES:
        assert fam in priors.priors
        p = priors.priors[fam]
        assert p.kept + p.discarded > 0


def test_consensus_families_get_higher_priors():
    from grok_playbook_miner import ComparativeReport
    report = ComparativeReport(
        accounts=[],
        consensus_patterns=["numbered_breakdown"],
        underused_patterns=["quick_take"],
        timing_consensus="09-11_pt",
        self_reply_consensus=True,
        notes="test",
    )
    priors = derive_priors(report, virtual_trials=40)
    consensus_rate = priors.priors["numbered_breakdown"].kept / (
        priors.priors["numbered_breakdown"].kept + priors.priors["numbered_breakdown"].discarded
    )
    neutral_rate = priors.priors["quick_take"].kept / (
        priors.priors["quick_take"].kept + priors.priors["quick_take"].discarded
    )
    # Consensus patterns should be favored relative to underused/neutral
    assert consensus_rate > neutral_rate


def test_mine_playbooks_end_to_end(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    report, priors = mine_playbooks(["a", "b", "c"])
    assert len(report.accounts) == 3
    assert len(priors.priors) == len(FAMILY_ARCHETYPES)
