# growth-os

> **An autonomous agent that reverse-engineers distribution platforms and self-improves its own content engine. Forever.**

Most growth tools have a human in the loop. Dashboards, A/B tests, creative review. Tuesday's instinct isn't Friday's instinct; even the best operators produce non-stationary quality.

`growth-os` replaces the human with a loop. Adapted from [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) and extended from ML research to distribution engineering. The loop hypothesizes, executes, measures, verifies, keeps or discards, and logs — then repeats, forever.

It took Oyster Labs from $0 to $4M in revenue with $0 paid acquisition. The loop has been running continuously for 14 months. I haven't touched it in three.

**If you only read one file in this repo, read [`AUTORESEARCH.md`](./AUTORESEARCH.md).** Everything else is supporting infrastructure.

---

## The results (real, not projected)

| Metric | Value |
| --- | --- |
| Revenue | **$0 → $4M** |
| Devices sold | 25,000+ |
| Paid acquisition | **$0** |
| Customer acquisition cost | **$0** |
| Channels automated | 10 |
| Posts / week | 250+ |
| Humans in the loop | **0** |
| Operating cost | ~$20 / month |

No marketing team. No agency. No human scheduling posts. The content engine proposes, the verifier decides, the log remembers.

---

## The loop

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   HYPOTHESIZE ──▶ EXECUTE ──▶ MEASURE ──▶ VERIFY ──▶ DECIDE   │
│        ▲                                              │         │
│        │                                              │         │
│        └──────────────── LOG ◀─────────────────────── ┘         │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

1. **Hypothesize** — propose the next candidate post, chosen by a bandit over pattern families from the log's history
2. **Execute** — ship it through the content engine to the appropriate account
3. **Measure** — pull platform metrics 48 hours later
4. **Verify** — mechanical checklist: not-duplicate, data-fresh, sample size, score ≥ threshold, statistical significance, tier-quota compliant
5. **Decide** — kept / discarded / failed, with explicit reason
6. **Log** — append to TSV with full provenance (git hash, iteration, score, lift, z-stat)
7. **Repeat** — feed the log back into hypothesis generation

**The verifier is the part most tools get wrong.** LLMs cannot be trusted to verify their own work. They skip steps, invent results, and favor "looks reasonable" over "mechanically true." Our verifier is short, deterministic Python with no LLM calls. It is the adult in the room.

---

## Repo structure

```
growth-os/
├── AUTORESEARCH.md                  ← The protocol. The operating system.
├── METRICS.md                       ← Internal metric catalog (DADR, NSR, PC2C ...)
│
├── engine/
│   ├── autoresearch_loop.py         ← Runnable loop
│   ├── hypothesis_generator.py      ← Bandit + pattern proposer
│   ├── verifier.py                  ← Mechanical checklist (~200 LOC, no LLMs)
│   ├── results_log.py               ← Append-only TSV with atomic writes
│   ├── signal_weights.py            ← Twitter weight map, re-derivable
│   ├── content_engine.py            ← Multi-account scheduler
│   └── ab_tester.py                 ← Thompson-sampling bandit + z-test
│
├── playbook/
│   ├── 00-autoresearch-first.md     ← Read this before anything else
│   ├── 01-read-the-source.md        ← 120-hour source-read protocol
│   ├── 02-weight-mapping.md         ← Weight maps as data structures
│   ├── 03-self-reply-pattern.md     ← +75× Twitter signal (the biggest single lever)
│   ├── 04-dwell-optimization.md     ← Most durable positive signal
│   ├── 05-negative-signal-avoidance.md  ← -148× and -738× (asymmetric penalties)
│   ├── 06-author-diversity-decay.md ← Why 3 posts beats 10
│   ├── 07-multi-account-orchestration.md ← Scaling horizontally
│   └── 08-cross-platform-extension.md    ← LinkedIn / TikTok / Shopify / App Store
│
├── case-studies/
│   └── 00-zero-to-4m.md             ← Real numbers from Oyster Labs
│
├── demos/
│   └── signal-weight-explorer.html  ← Interactive — open in browser
│
└── fellowship/
    └── roadmap.md                   ← 8-week a16z Growth Engineer Fellowship plan
```

---

## Try the loop in 60 seconds

```bash
git clone https://github.com/howardleegeek/growth-os
cd growth-os/engine
python3 autoresearch_loop.py --iterations 20 --log /tmp/ar.tsv
```

Output on a cold run:

```
[iter 000001] KEPT        score= +42.8  +107.5% vs ctl, n=5327, z=+4.61
[iter 000002] discarded   score=  +3.0  failed: below_ship_threshold,lift_not_significant
[iter 000003] discarded   score=  -0.8  failed: below_ship_threshold,lift_not_significant
[iter 000004] KEPT        score= +11.6  +169.2% vs ctl, n=1633, z=+5.50
[iter 000005] discarded   score=  +3.6  failed: below_ship_threshold,lift_not_significant
[iter 000006] KEPT        score= +24.9  +266.0% vs ctl, n=4822, z=+9.04
```

Each line is one hypothesis tested against the mechanical verifier. `KEPT` means the candidate cleared all six checks. `discarded` tells you exactly which checks failed. The loop never stops.

---

## Core thesis

> **Distribution is an optimization function. Optimization functions should be attacked by autonomous agents, not by humans with spreadsheets.**

Every modern platform — Twitter, LinkedIn, TikTok, Shopify search, App Store — is a weighted scoring function. Read the weights, encode them, optimize against them with a loop that never sleeps. The only unknowns are platform-specific coefficients, which can be extracted from source (if open) or derived empirically (if closed).

This works whether your distribution target is a social feed, a search rank, an app-store position, or a product-page impression. The engine is identical; only the adapters differ.

---

## What this is NOT

- Not a content calendar tool
- Not a "better dashboard"
- Not a generator that just writes posts with an LLM
- Not a scheduler with no verification layer
- Not a growth-hacking tactics library
- Not a SaaS product with a monthly fee (it's MIT-licensed Python you run yourself)

It is **distribution infrastructure** — the missing middle layer between an LLM and a platform API.

---

## Why this hasn't been productized before

Five reasons, explained in [`AUTORESEARCH.md`](./AUTORESEARCH.md#why-this-hasnt-been-productized-by-anyone-else). The short version: the moat is operational discipline, not technology. Reading the platform source, enforcing mechanical verification, and trusting a loop over intuition — all three are unnatural for most growth teams, which is exactly why the method has outsized payoff.

---

## Who I am

**Howard Jiacheng Li** — CEO & Growth Engineer @ Oysterworld INC

- Bootstrapped Oyster Labs from $0 → $4M with zero paid acquisition
- Previously co-founded [**MPCVault**](https://mpcvault.com) (digital asset custody, $5B AUM)
- Run a 32-agent AI development factory that ships like a team of 50
- Wharton MBA, UC Berkeley Haas
- Based in SF

[github.com/howardleegeek](https://github.com/howardleegeek) · [linkedin.com/in/connecthoward](https://www.linkedin.com/in/connecthoward/) · howard.linra@gmail.com

---

## License

MIT. Take it, fork it, deploy it. If you ship something at scale, I want to hear about it.

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Highest-value contributions right now: new platform weight maps (LinkedIn, TikTok, Shopify), new platform adapters, and case studies with real numbers.
