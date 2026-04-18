<div align="center">

# `growth-os`

### Implementation of EvoHarness engineering in Twitter algorithm automation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![No LLM in verifier](https://img.shields.io/badge/verifier-mechanical-green.svg)](./engine/verifier.py)
[![Stdlib-only core](https://img.shields.io/badge/core-stdlib--only-blue.svg)](./engine/)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](https://github.com/howardleegeek/growth-os/commits/main)

**[The Journey](./THE_JOURNEY.md)** · **[Implementation](./IMPLEMENTATION.md)** · **[Protocol](./AUTORESEARCH.md)** · **[Playbook](./playbook/)** · **[Case Studies](./case-studies/)** · **[Demo](./demos/signal-weight-explorer.html)** · **[Runtime](./clawmarketing/)**

</div>

---

> **An implementation of EvoHarness engineering applied to Twitter algorithm automation.**

Twitter's ranker is a weighted sum of predicted signal probabilities.
They open-sourced it in 2023. Nobody else has built a proper optimizer
against it. `growth-os` is that optimizer.

The system combines four ideas that haven't been combined before:

1. **Karpathy-style autoresearch** — an autonomous loop that hypothesizes, executes, measures, verifies, and logs, forever
2. **EvoHarness tree search** — parallel proposers mutate independent slot surfaces; prescreen kills 2/3 of proposals offline; only survivors ship; winning branches merge
3. **Offline Twitter simulator** — the published weight map as a scoring function, used to run thousands of mutation trials per second at zero API cost
4. **Grok opponent study** — the AlphaGo supervised-learning phase, applied to distribution: Grok mines the playbooks of master accounts (including their deleted tweets and live engagement) and seeds the evo loop with Bayesian priors from real-world top operators

The system is **Growth 2.0** — what became possible for us once vibe coding matured and Twitter's algorithm changed in late 2025.

**Growth 1.0** (pre-December 2025) was how we actually bootstrapped Oyster Labs: exclusive-membership tied to device purchase, device gifting to unlock adjacent audiences, co-branded limited editions, RT-and-comment engagement (while it still worked), a hero narrative, and months of manual reverse-engineering of the old Twitter algorithm. Human-driven, labor-intensive, effective.

When the algorithm changed and vibe coding made autonomous systems practical, I built `growth-os` to encode those lessons into an evolutionary loop that runs autonomously. **It's still being perfected.** Full history in [`THE_JOURNEY.md`](./THE_JOURNEY.md).

**If you're reading this from a16z:** [`IMPLEMENTATION.md`](./IMPLEMENTATION.md) is the deep dive written specifically for you. Start there.

**If you're a builder who wants to run this:** [`AUTORESEARCH.md`](./AUTORESEARCH.md) explains the protocol, then [`playbook/10-evolutionary-twitter-hacking.md`](./playbook/10-evolutionary-twitter-hacking.md) explains the final architecture.

---

## Design goals (what the system was built to achieve)

| Goal | Design choice |
| --- | --- |
| Zero paid acquisition | All distribution through algorithmic optimization, not spend |
| Low operator overhead | Autonomous loop with mechanical verification — no human review step |
| Low operating cost | Offline prescreen kills 2/3 of proposals before any API call |
| Reproducible decisions | Append-only TSV log with full provenance |
| Safe defaults | Safety-tier quotas prevent asymmetric negative-signal accumulation |
| Self-improving | Bandit + branch merging means outcomes compound over time |

---

## The loop

```
┌─────────────────────────── BASELINE SLOT ───────────────────────────┐
│                                                                      │
│     ┌──────────┐     ┌──────────┐     ┌──────────┐                  │
│     │Prop.hook │     │Prop.thrd │     │Prop.time │   3 proposers    │
│     │mutation  │     │mutation  │     │mutation  │   in parallel    │
│     └────┬─────┘     └────┬─────┘     └────┬─────┘                  │
│          └────────────────┼─────────────────┘                        │
│                           ▼                                           │
│                 ┌─────────────────────┐                              │
│                 │ Twitter simulator   │   Prescreen. Cheap.          │
│                 │ (offline, 0.1ms)    │   Keeps top 33%.             │
│                 └──────────┬──────────┘                              │
│                            ▼                                           │
│                  ┌─────────────────────┐                             │
│                  │ Ship to real X      │   48h measurement window     │
│                  └──────────┬──────────┘                             │
│                             ▼                                           │
│                  ┌─────────────────────┐                             │
│                  │ Mechanical verifier │   6 checks. No LLM.         │
│                  └──────────┬──────────┘                             │
│                             ▼                                           │
│                   ┌─────────┴─────────┐                              │
│                   ▼                   ▼                              │
│              ┌────────┐          ┌─────────┐                         │
│              │  KEEP  │          │ DISCARD │                         │
│              │  merge │          │  log    │                         │
│              │  log   │          │         │                         │
│              └────────┘          └─────────┘                         │
└──────────────────────────────────────────────────────────────────────┘
```

The loop never stops. Every iteration appends one row to an append-only TSV. The log is the training set and the audit trail.

---

## Repo structure

```
growth-os/
├── IMPLEMENTATION.md                 ← Deep dive for a16z (start here if reviewing)
├── AUTORESEARCH.md                   ← The protocol — Karpathy's loop, adapted
├── README.md                         ← This file
├── METRICS.md                        ← Internal metric catalog
│
├── engine/                           ← ~1,500 LOC total
│   ├── evo_loop.py                   ← EvoHarness tree search (the main loop)
│   ├── twitter_simulator.py          ← Offline weight-map oracle
│   ├── slot.py                       ← Surface-decomposed slot primitive
│   ├── verifier.py                   ← Mechanical checklist (no LLM calls)
│   ├── results_log.py                ← Append-only TSV with provenance
│   ├── autoresearch_loop.py          ← Linear autoresearch (reference impl.)
│   ├── hypothesis_generator.py       ← Bandit over pattern families
│   ├── signal_weights.py             ← Twitter weight map
│   ├── content_engine.py             ← Multi-account scheduler
│   └── ab_tester.py                  ← Thompson-sampling A/B harness
│
├── playbook/                         ← 11 chapters, each ~400–800 lines
│   ├── 00-autoresearch-first.md      ← Read before anything else
│   ├── 01-read-the-source.md         ← How I read Twitter's 10,000 lines
│   ├── 02-weight-mapping.md
│   ├── 03-self-reply-pattern.md      ← The 75× lever — single biggest lever
│   ├── 04-dwell-optimization.md
│   ├── 05-negative-signal-avoidance.md  ← Asymmetric penalties (−148× / −738×)
│   ├── 06-author-diversity-decay.md
│   ├── 07-multi-account-orchestration.md
│   ├── 08-cross-platform-extension.md
│   ├── 09-internal-specs-as-appendix.md ← 17 internal engineering specs
│   └── 10-evolutionary-twitter-hacking.md ← The final architecture
│
├── case-studies/
│   ├── 00-zero-to-4m.md              ← Real numbers from Oyster Labs
│   ├── 01-v1-postmortem.md           ← 90 drafts, 0 published (the failure that produced the design)
│   └── 02-competitor-teardown.md     ← Memories.ai / Rerun / π / General Intuition teardowns
│
├── demos/
│   └── signal-weight-explorer.html   ← Interactive — open in browser
│
└── fellowship/
    └── roadmap.md                    ← 8-week a16z Fellowship commitment
```

---

## 60-second test drive

```bash
git clone https://github.com/howardleegeek/growth-os
cd growth-os/engine

# Self-play only
python3 evo_loop.py --iterations 20 --log /tmp/evo.tsv

# Supervised + self-play (AlphaGo-style):
# First mine playbooks from master accounts via Grok, then run the loop
python3 evo_loop.py \
    --iterations 20 --log /tmp/evo.tsv \
    --warm-start memories_ai rerundotio physical_int
```

Output:

```
[iter 0005] active_branches=11  fragility={'hook': 0.10, 'thread': 0.20, 'timing': 0.36, 'safety': 0.90}
[iter 0010] active_branches=21  fragility={'hook': 0.07, 'thread': 0.18, 'timing': 0.32, 'safety': 0.90}
[iter 0015] active_branches=29  fragility={'hook': 0.05, 'thread': 0.15, 'timing': 0.29, 'safety': 0.90}
```

Every row is a slot mutation tested against the simulator, shipped (in this test, stubbed), measured, and mechanically verified. `safety` surface fragility stays near 0.9 because the loop correctly refuses to test mutations that could produce asymmetric negative signals.

---

## Production runtime is in the repo

The runtime that ships posts lives in [`clawmarketing/`](./clawmarketing/)
within this repo. ~5,000 LOC of Python (`engine/`, `publishers/`,
`adapters/`). Read it for the execution layer under the evolutionary
loop.

---

## Core thesis

> **Twitter's ranker is a ranking function. Ranking functions should be attacked by evolutionary agents, not by humans with spreadsheets.**

Every "growth tool" in 2026 has a human in the loop. Dashboards, A/B tests, creative reviews. Tuesday's instinct isn't Friday's instinct; even the best operators produce non-stationary quality.

`growth-os` replaces the human with an evolutionary loop that never sleeps, never drifts, and produces a complete audit trail. The system optimizes against the function the platform publishes. It compounds over months. It keeps its own log as training data for future iterations.

The moat is operational, not technological. Every component uses ideas that already exist in public. The willingness to read the ranker's source, encode the weight map, enforce mechanical verification, and let a loop run for an extended period — that's the unusual part.

---

## Why focused on Twitter

Three reasons `growth-os` is Twitter-first, not cross-platform:

1. **The source is public.** Twitter open-sourced their ranker in 2023. No other major platform has done this. The weight map is therefore more accurate here than anywhere else.
2. **The weights are asymmetric.** +75× self-reply, −738× report. Asymmetric functions make the optimization meaningful — on platforms with symmetric weights, the gains are smaller.
3. **The observation loop is fast.** 48 hours from ship to mature signal, vs. 7+ days on most other platforms. Faster iteration = faster learning.

Adapters for other platforms (LinkedIn, Bluesky, TikTok) are in [`playbook/08-cross-platform-extension.md`](./playbook/08-cross-platform-extension.md), but Twitter is where the core of `growth-os` runs.

---

## Maintainer

Open-sourced and maintained by an operator who built and used this system during the bootstrap phase of a consumer hardware company.

For questions, issues, or contributions: [GitHub Issues](https://github.com/howardleegeek/growth-os/issues) or [Discussions](https://github.com/howardleegeek/growth-os/discussions).

---

## License & Contributing

MIT. Take it, fork it, deploy it.

Highest-value contributions right now: new platform weight maps (LinkedIn, TikTok, Shopify search), case studies with real numbers, and extensions to the evolutionary loop. See [`CONTRIBUTING.md`](./CONTRIBUTING.md).
