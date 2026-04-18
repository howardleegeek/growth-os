<div align="center">

# `growth-os`

### Evolutionary tree search that hacks Twitter's ranking algorithm

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![No LLM in verifier](https://img.shields.io/badge/verifier-mechanical-green.svg)](./engine/verifier.py)
[![Uptime](https://img.shields.io/badge/uptime-14%20months-brightgreen.svg)](./case-studies/00-zero-to-4m.md)
[![Revenue generated](https://img.shields.io/badge/bootstrapped-%240%20%E2%86%92%20%244M-success.svg)](./case-studies/00-zero-to-4m.md)
[![Paid acquisition](https://img.shields.io/badge/paid%20acquisition-%240-blue.svg)](./case-studies/00-zero-to-4m.md)
[![Operating cost](https://img.shields.io/badge/running%20cost-~%2420%2Fmo-lightgrey.svg)](./IMPLEMENTATION.md)

**[Implementation](./IMPLEMENTATION.md)** · **[Protocol](./AUTORESEARCH.md)** · **[Playbook](./playbook/)** · **[Case Studies](./case-studies/)** · **[Demo](./demos/signal-weight-explorer.html)**

</div>

---

> **An evolutionary tree search that hacks Twitter's ranking algorithm. Forever.**

Twitter's ranker is a weighted sum of predicted signal probabilities.
They open-sourced it in 2023. Nobody else has built a proper optimizer
against it. `growth-os` is that optimizer.

The system combines three ideas that haven't been combined before:

1. **Karpathy-style autoresearch** — an autonomous loop that hypothesizes, executes, measures, verifies, and logs, forever
2. **EvoHarness tree search** — parallel proposers mutate independent slot surfaces; prescreen kills 2/3 of proposals offline; only survivors ship; winning branches merge
3. **Offline Twitter simulator** — the published weight map as a scoring function, used to run thousands of mutation trials per second at zero API cost

It ran Oyster Labs from $0 → $4M in revenue with $0 paid acquisition. The loop has been running continuously for 14+ months. I haven't touched it in three.

**If you're reading this from a16z:** [`IMPLEMENTATION.md`](./IMPLEMENTATION.md) is the deep dive written specifically for you. Start there.

**If you're a builder who wants to run this:** [`AUTORESEARCH.md`](./AUTORESEARCH.md) explains the protocol, then [`playbook/10-evolutionary-twitter-hacking.md`](./playbook/10-evolutionary-twitter-hacking.md) explains the final architecture.

---

## The results (real, not projected)

| Metric | Value |
| --- | --- |
| Revenue | **$0 → $4M** |
| Devices sold | 25,000+ |
| Paid acquisition | **$0** |
| Customer acquisition cost | **$0** |
| Humans in the loop | **0** |
| Operating cost | ~$20 / month |
| Median impressions / post | 180 → 4,100 (**+2,178%**) |
| Continuous uptime | 14+ months |

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
python3 evo_loop.py --iterations 20 --log /tmp/evo.tsv
```

Output:

```
[iter 0005] active_branches=11  fragility={'hook': 0.10, 'thread': 0.20, 'timing': 0.36, 'safety': 0.90}
[iter 0010] active_branches=21  fragility={'hook': 0.07, 'thread': 0.18, 'timing': 0.32, 'safety': 0.90}
[iter 0015] active_branches=29  fragility={'hook': 0.05, 'thread': 0.15, 'timing': 0.29, 'safety': 0.90}
```

Every row is a slot mutation tested against the simulator, shipped (in this test, stubbed), measured, and mechanically verified. `safety` surface fragility stays near 0.9 because the loop correctly refuses to test mutations that could produce asymmetric negative signals.

---

## Core thesis

> **Twitter's ranker is a ranking function. Ranking functions should be attacked by evolutionary agents, not by humans with spreadsheets.**

Every "growth tool" in 2026 has a human in the loop. Dashboards, A/B tests, creative reviews. Tuesday's instinct isn't Friday's instinct; even the best operators produce non-stationary quality.

`growth-os` replaces the human with an evolutionary loop that never sleeps, never drifts, and produces a complete audit trail. The system optimizes against the function the platform publishes. It compounds over months. It keeps its own log as training data for future iterations.

The moat is operational, not technological. Every component uses ideas that already exist in public. The willingness to read the ranker's source, encode the weight map, enforce mechanical verification, and let a loop run for 14 months — that's the unusual part.

---

## Why focused on Twitter

Three reasons `growth-os` is Twitter-first, not cross-platform:

1. **The source is public.** Twitter open-sourced their ranker in 2023. No other major platform has done this. The weight map is therefore more accurate here than anywhere else.
2. **The weights are asymmetric.** +75× self-reply, −738× report. Asymmetric functions make the optimization meaningful — on platforms with symmetric weights, the gains are smaller.
3. **The observation loop is fast.** 48 hours from ship to mature signal, vs. 7+ days on most other platforms. Faster iteration = faster learning.

Adapters for other platforms (LinkedIn, Bluesky, TikTok) are in [`playbook/08-cross-platform-extension.md`](./playbook/08-cross-platform-extension.md), but Twitter is where the core of `growth-os` runs.

---

## Who I am

**Howard Jiacheng Li** — CEO & Growth Engineer @ Oysterworld INC

- Bootstrapped Oyster Labs from $0 → $4M with zero paid acquisition, zero capital raised
- Previously co-founded [**MPCVault**](https://mpcvault.com) — digital asset custody, $5B AUM at peak
- Wharton MBA, UC Berkeley Haas
- SF-based, running a 32-agent AI development factory that ships like a team of 50

[github.com/howardleegeek](https://github.com/howardleegeek) · [linkedin.com/in/connecthoward](https://www.linkedin.com/in/connecthoward/) · howard.linra@gmail.com

---

## License & Contributing

MIT. Take it, fork it, deploy it. If you ship something meaningful, I want to hear about it.

Highest-value contributions right now: new platform weight maps (LinkedIn, TikTok, Shopify search), case studies with real numbers, and extensions to the evolutionary loop. See [`CONTRIBUTING.md`](./CONTRIBUTING.md).

---

## For a16z — the ask

If you're evaluating for the Growth Engineer Fellowship: read [`IMPLEMENTATION.md`](./IMPLEMENTATION.md), then [`fellowship/roadmap.md`](./fellowship/roadmap.md). I'd like 30 minutes on a call. Agenda is in the implementation doc. Thanks for looking.
