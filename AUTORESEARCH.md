# Autoresearch — the operating system of growth-os

> Every component in this repo is a child of one idea: **distribution is an
> optimization function, and optimization functions should be attacked by
> autonomous agents, not by humans with spreadsheets.**
>
> This document describes the autonomous loop that runs underneath everything
> else. If you only read one file in this repo, read this one.

---

## The one-paragraph version

`growth-os` is not a content tool. It is an autonomous agent that continuously
reverse-engineers the ranking function of a distribution platform, proposes
experiments against that function, verifies outcomes mechanically, keeps what
works, discards what doesn't, and repeats forever. The "content engine" people
see is the surface output. The autoresearch loop underneath is what actually
produces the results.

This is adapted from [Karpathy's autoresearch](https://github.com/karpathy/autoresearch),
which proposed the same loop for ML research. I extended it to distribution
because the underlying shape is identical: a high-dimensional objective
function, an exploration space, and mechanical verification. The only thing
that changes is the domain.

---

## Why this architecture exists

Every growth tool I'd seen in 2024 had the same failure mode: a human in the
loop, making decisions from dashboards, reading anecdotes, and drifting toward
whatever felt good that week. Even the best operators produce non-stationary
quality — Tuesday's instinct isn't Friday's instinct.

A loop with a mechanical scoring function doesn't drift. It doesn't get tired.
It doesn't optimize for what looks good on Twitter; it optimizes for the
scoring function I give it. If the scoring function is the platform's published
ranking weights (or an empirically derived approximation), the loop is
literally optimizing against the same objective the platform is ranking you
against.

Most growth teams fight the algorithm. An autoresearch loop **aligns** with it.

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

1. **HYPOTHESIZE** — given the current weight map and what's worked before,
   propose the next N candidate posts (or content patterns, or timing windows,
   or whatever the experiment is over).
2. **EXECUTE** — ship the candidates through the normal content engine.
3. **MEASURE** — 48 hours later, pull platform metrics for each.
4. **VERIFY** — check mechanically:
   - Data is fresh (not cached)
   - Post actually shipped
   - Metrics exceed minimum sample size
   - Score computed against the weight map
   - Lift vs. control is statistically distinguishable (z-test)
5. **DECIDE** — keep if lift is positive and significant; discard otherwise;
   update the posterior on the classifier used to pick it.
6. **LOG** — append to TSV with full provenance. Every decision is traceable.
7. **REPEAT** — feed the updated posterior back into HYPOTHESIZE.

The loop never stops. Mine has been running for 14+ months.

---

## What "mechanical verification" means

> "Every finding requires code evidence. No theoretical fluff."
> — from the autoresearch protocol

Verification is not "the post did well." Verification is a checklist:

- [ ] **Not duplicate** — candidate is semantically distinct from the last 7 days of shipped content
- [ ] **Fresh** — metrics pulled from platform API within the last 24 hours
- [ ] **Score passes** — computed score vs. weight map exceeds the ship threshold
- [ ] **Lift is real** — z-statistic against control crosses the significance line
- [ ] **Safety-tier compliant** — tier-C/D quotas respected
- [ ] **Provenance complete** — TSV row populated with all fields

If any check fails, the iteration is logged as FAILED and the loop moves on.
No vibes. No "looks good to me."

This is the single most important discipline in the entire repo. Everything
else is elaboration.

---

## TSV logs — the provenance layer

Every loop iteration appends one row to a TSV file:

```
iteration   timestamp   action     target          score   result      notes
000412      2026-03-14  ship_test  selfreply_v3    +18.4   kept        +203% vs ctl, n=412, z=2.84
000413      2026-03-14  ship_test  meme_plug       -24.1   discarded   triggered tier-C gate
000414      2026-03-14  rederive   weight_map                           LinkedIn: dwell 48→52, reshare 18→22
000415      2026-03-15  ship_test  contrarian_v7   +31.2   kept        +412% vs ctl, n=387, z=3.91
```

Two properties that matter:

1. **Every decision is traceable.** Six months later, if I want to know why
   the `selfreply_v3` pattern is the current best, I can grep the TSV and
   find the iteration where it was promoted. Intuition forgets. TSVs don't.

2. **The log is the training set.** The hypothesis generator reads the TSV
   every iteration and uses the history to bias its next proposal. Kept
   patterns get reinforced; discarded patterns get explored-against. This
   is the compounding mechanism — the loop gets better at proposing good
   experiments the longer it runs.

Every domain has its own TSV: content, weight-map re-derivation, safety-tier
calibration, A/B experiments, negative-signal monitoring.

---

## What runs on what hardware

The operating architecture I use at Oyster Labs:

- **Claude Opus** (expensive, human-adjacent) — architecture decisions,
  approvals, occasional review. Touches the loop rarely.
- **OpenCode / Kimi K2.5 Turbo** (free, effectively unlimited) — runs the
  actual loop. Generates candidates, computes scores, fires the publisher,
  appends to TSV. Runs 24/7.
- **Python mechanical layer** — the verifier. Short, deterministic, no LLM
  calls. Enforces the checklist above. No LLM can bypass it.

This split is important. **LLMs cannot be trusted to verify their own work.**
They skip steps, invent results, and favor "looks reasonable" over
"mechanically true." The verifier is Python because the verifier's job is to
be the adult in the room.

Approximate cost per month at my scale: <$10 (LLM API), plus a $5/mo VPS.
The loop runs on a refrigerator-sized hardware footprint and outproduces a
team.

---

## Domain extensions

The protocol generalizes. I run autoresearch loops for:

| Domain | Goal | Verification |
| --- | --- | --- |
| **Content generation** (this repo) | Ship posts that score high on platform weights | Scored against weight map + measured lift |
| **Weight-map re-derivation** | Keep weight maps in sync as platforms evolve | Empirical coefficient drift vs. last release |
| **Competitive BD** | Discover and qualify investor/partner targets | Verified profile, not-recent-duplicate, relevance score |
| **Technical reconnaissance** | Track new research/tech in target domain | Source-verified, freshness window, relevance threshold |
| **Security auditing** | STRIDE threat model across the stack | Code-evidence requirement (file:line) |

All share the same shape: **hypothesize → execute → measure → verify → decide →
log → repeat**. Domain-specific code is minimal; the loop itself is the asset.

---

## Why this hasn't been productized by anyone else

Five reasons I've thought through:

1. **It only works if you trust mechanical verification over intuition.** Most
   product and growth teams are anchored on intuition. Surrendering it to a
   loop feels like losing agency. In practice, the loop makes fewer mistakes
   than intuition — but this realization takes months of running it to
   arrive at.

2. **The bar is "can't be faked."** Most content tools cut corners on
   verification because cut-corner verification is easier to ship and
   superficially similar. Autoresearch is binary: if the verifier is a vibe
   check, the system doesn't work.

3. **It requires reading the platform source.** Most growth teams don't and
   won't. The weight map is the forcing function that keeps the loop
   grounded; without a real weight map, the loop optimizes against noise.

4. **The value compounds on time horizon, not on user count.** A typical SaaS
   product's value is proportional to user × time. An autoresearch loop's
   value is proportional to iterations × quality-of-verification. A single
   user running it for a year generates more compounding value than 1,000
   users running it for a week.

5. **Karpathy's autoresearch framing is 2023-era and most founders haven't
   internalized it.** The pattern is mature in ML research circles, nascent
   everywhere else.

Any one of these would explain why no one has shipped this. All five
explain why no one will ship a *better* version of this in the near term.
The moat is operational discipline, not technology.

---

## How this changes the narrative

A content tool says: "here are better posts."

An autoresearch system says: **"here is a process that makes posts strictly
better every week, forever, without a human in the loop."**

The difference is the difference between "a tool" and "an operator." Every
a16z portfolio company has 20 tools and 0 operators. The right framing of
this repo is: the operator you always wanted, open-source.

---

## If you want to run one yourself

The rest of this repo is the reference implementation:

- `engine/autoresearch_loop.py` — the runnable loop
- `engine/hypothesis_generator.py` — proposes next experiments
- `engine/verifier.py` — the mechanical checklist
- `engine/results_log.py` — TSV append + provenance

Read them in that order. Then fork, configure your weight map, and point
the loop at your accounts. On a $5/mo VPS with Kimi K2.5 Turbo via OpenRouter,
the monthly operating cost is under $20.

---

## Credits

- [Andrej Karpathy / autoresearch](https://github.com/karpathy/autoresearch) —
  the original framing, which I extended from ML research to distribution
  engineering.
- [Twitter / the-algorithm](https://github.com/twitter/the-algorithm) — the
  reference weight map.
- Every founder who told me growth couldn't be engineered — you were the
  forcing function for building this.
