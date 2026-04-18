# How growth-os was built

> A technical deep-dive written in plain-English narrative form. Covers
> what's actually running under the hood, how the pieces fit together,
> and the timeline of how the system evolved from a failed v1 into the
> current evolutionary loop.
>
> Read this if you want to understand the system at engineering depth.
> Read [`README.md`](./README.md) or [`ABSTRACT.md`](./ABSTRACT.md) first
> for context.

---

## TL;DR — the one-paragraph engineering summary

`growth-os` is a **Twitter-algorithm-hacking toolkit** that combines three
ideas that have not been combined before:

1. **Karpathy-style autoresearch** — an autonomous loop that hypothesizes,
   executes, measures, verifies, and logs, forever.
2. **EvoHarness tree search** — parallel proposers mutate independent
   surfaces of a "slot" configuration, the cheap simulator prescreens
   survivors, Thompson sampling picks the next parent branch, winning
   mutations merge into descendants.
3. **Offline Twitter simulator** — the published open-source Twitter
   ranking weights, encoded as a scoring function, used to run thousands
   of mutation trials per second at zero API cost before anything ships.

The system was built because a solo operator with no marketing budget
had to treat distribution as an engineering problem. It ran the
originating company from bootstrap-phase go-to-market.
The framework itself is what's open-sourced here.

---

## Why this is novel

I have read every open-source growth / content tool I can find. None of
them combine these three ideas. Specifically:

| Pattern | Who has it | Who doesn't |
| --- | --- | --- |
| Autoresearch loop (Karpathy, 2023) | ML research labs | Every growth tool |
| EvoHarness tree search (2026) | AI harness research | Every growth tool |
| Offline Twitter algorithm simulator | Nobody I've found | Everyone |
| All three combined | Only this repo | — |

The closest comparable is "programmatic SEO" — tools that automate content
against Google's ranking. Those tools cheat on mechanical verification
(they ship and pray) and none of them run tree search. This is what that
class of tool looks like when you take engineering discipline seriously.

---

## The four load-bearing components

The implementation is ~1,500 lines of Python across 7 modules. Small on
purpose. Every file is under 400 lines. Every function has one job. If it
takes you longer than 10 minutes to read a module, I'm doing it wrong.

### 1. `engine/twitter_simulator.py` — the oracle

**Purpose:** score a candidate post against Twitter's published weight
map without actually shipping it.

**How it works:** Twitter's ranker is a weighted sum of predicted signal
probabilities. We have the weights (open-sourced by Twitter in 2023) and
we have feature extractors for each signal (fit on 2,000+ labeled
historical posts). The simulator combines them:

```
simulated_score(post) = sum over signals of:
                        P(signal fires for this post)  ×  WEIGHT[signal]
```

**Engineering details:**

- Deterministic. Same input produces same output. No RNG.
- Fast. ~0.1ms per simulation. We run 10,000 simulations in a second.
- Stateless. No DB calls. No network. No LLM calls.
- Ranking-correlation, not absolute-truth. The simulator is trusted to
  rank candidate mutations, not to predict specific impression counts.
  Empirical rank correlation vs. real Twitter outcomes: r ≈ 0.72.

**Why this matters:** Every EvoHarness-style workflow is bottlenecked on
evaluation cost. Real shipping takes 48 hours and costs one post's worth
of account exposure. Simulation takes a microsecond and costs nothing.
If we filter to the top 10% via simulation before shipping, we get a 10×
effective iteration rate at 1/10 the account risk.

### 2. `engine/slot.py` — the surface decomposition

**Purpose:** represent "one specific posting configuration" as a
four-surface object the evo loop can mutate independently.

A **slot** is `(account, time, hook, tier, voice, depth, ...)` — a fully
specified configuration for a single post. Frozen, hashable, immutable.
Mutations produce new child slots linked to their parents.

The **4 surfaces** are:

| Surface | Risk class | Fragility | Fields |
| --- | --- | --- | --- |
| `hook` | LOW | 0.15 | hook_type, contrarianness, teaser_strength |
| `thread` | LOW | 0.20 | has_thread, has_self_reply, self_reply_window_sec |
| `timing` | MEDIUM | 0.40 | timing_window, post_index_today |
| `safety` | HIGH | 0.90 | safety_tier, tone_risk |

**Fragility** is the historical probability that a mutation to this
surface regresses performance. Computed from the log — every regression
increments fragility; every improvement decrements it. The evo loop uses
fragility to weight mutation proposals: high-fragility surfaces require
more validation before promotion.

**Why this matters:** without surface decomposition, mutations become
combinatorially infeasible. With it, the evo loop can make one small
change at a time and isolate which change produced which outcome.

### 3. `engine/evo_loop.py` — the tree search

**Purpose:** the main loop. Spawns three parallel mutation proposers per
iteration, prescreens via the simulator, full-evaluates the survivors on
the real platform, merges winning branches, and repeats forever.

Pseudocode:

```
while True:
    parent = thompson_sample(active_branches, weight_by="historical_lift")

    proposals = parallel([
        proposer_A(parent),  # mutates surface "hook"
        proposer_B(parent),  # mutates surface "thread" or "timing"
        proposer_C(parent),  # mutates surface with lowest fragility
    ])

    survivors = prescreen(proposals, via=twitter_simulator, keep_top_frac=0.33)

    for slot in survivors:
        real_metrics = ship_and_measure(slot, wait_hours=48)
        verdict = mechanical_verifier(real_metrics)
        log.append(slot, proposals, real_metrics, verdict)
        if verdict.kept:
            active_branches.add(slot)
            maybe_merge(slot, siblings=active_branches)

    fragility.update(from_log=log.tail())
```

**Engineering details:**

- Three proposers per iteration, not one. Tree search beats hill climbing.
- Prescreen via simulator kills 67% of proposals before they ever hit
  Twitter — saves account risk and iteration time.
- Thompson sampling over the branch tree, weighted by lift. Exploits
  known-good parents while still exploring.
- Branch merging: if two sibling branches both win (different surfaces),
  a merged child inherits both mutations and is re-evaluated. This is
  the mechanism by which compounding improvements actually compound.
- The log is the source of truth. Restarting the loop re-derives all
  state from the log. No hidden in-memory state.

### 4. `engine/verifier.py` — the adult in the room

**Purpose:** the mechanical checklist that every iteration passes through
before its result is accepted as real.

This is the single most important file in the repo. LLMs cannot be trusted
to verify their own work — they skip steps, invent results, and favor
"looks reasonable" over "mechanically true." The verifier is deterministic
Python, no LLM calls, and if it says the iteration failed, the iteration
failed.

Checks enforced:

- [ ] **Not duplicate** — trigram Jaccard vs. last 200 posts < 0.88
- [ ] **Data is fresh** — platform metrics pulled within last 24h
- [ ] **Sample size** — ≥200 impressions before the iteration counts
- [ ] **Score passes threshold** — against the weight map
- [ ] **Safety-tier compliant** — C ≤ 10% daily, D blocked
- [ ] **Lift is statistically significant** — two-proportion z-test, |z| ≥ 1.96

Any failure → iteration logged as `discarded` with the failed check list.
No partial credit. No "probably okay."

---

## How I actually built this — the timeline

**Weeks 1–2: reading.** Read the Twitter source. ~120 hours. Produced the
weight map in [`engine/signal_weights.py`](./engine/signal_weights.py).
Commit messages from this period mostly say things like "map HeavyRanker
coefficients."

**Weeks 3–6: v1 content engine (failed).** Built a straightforward content
pipeline with no evolutionary loop and only vibe-level verification.
Produced 90 drafts in 48 hours; zero were publishable. Postmortem is in
[`case-studies/01-v1-postmortem.md`](./case-studies/01-v1-postmortem.md).
This failure directly produced the design of every component in the
current repo — each of the seven failure modes became a mechanical check
or a design constraint.

**Weeks 7–10: autoresearch loop.** Built the single-threaded loop
described in [`AUTORESEARCH.md`](./AUTORESEARCH.md). Mechanical verifier,
append-only TSV log, hypothesis generator with a bandit over 8 pattern
families. This is when the engine started producing consistently
publishable content.

**Weeks 11–14: the offline simulator.** The breakthrough insight: the
weight map is the scoring function, and the scoring function is free to
evaluate. Encoded the feature extractors, fit them against labeled
historical posts, measured rank correlation with real outcomes. This is
what made prescreening cheap and therefore made evolutionary search
feasible.

**Weeks 15–18: evo loop.** Rewrote the core loop as tree search with
parallel proposers, prescreen via simulator, branch merging. Performance
numbers went from "consistently publishable" to "consistently
outperforming our historical best." The 75× self-reply window
optimization from 165s–180s was discovered here — the tree search found
it by accident while optimizing the `thread` surface.

**Weeks 19+: scale to 10 accounts.** Added multi-account orchestration
layer, cross-account coordination signal avoidance, per-brand voice
isolation. The loop has been running continuously across 10 accounts
since week 19. continuous operation.

---

## What it actually produced

| Metric | Before growth-os | After deployment |
| --- | --- | --- |
| Revenue | $0 | **$4M** |
| Devices sold | 0 | **25,000+** |
| Paid acquisition cost | — | **$0** |
| Customer acquisition cost | — | **$0** |
| Monthly operating cost of the loop | — | **<$20** |
| Humans in the content pipeline | 1 (me, part-time) | **0** |
| Median impressions per post | 180 | **4,100** (+2,178%) |
| Profile click rate | 0.6% | **2.1%** (+250%) |
| Reply rate | 0.3% | **3.7%** (+1,133%) |

The loop is still running. While I'm writing this document, it's
proposing mutations, prescreening them, and shipping survivors. The last
iteration logged was ~4 minutes ago.

Full metrics catalog in [`METRICS.md`](./METRICS.md), full case study in
[`case-studies/00-zero-to-4m.md`](./case-studies/00-zero-to-4m.md).

---

## What this is NOT

Addressing the objections I expect:

**"This is just content automation."**
Content automation doesn't reverse-engineer platform weights, doesn't run
mechanical verification, doesn't do tree search, and doesn't produce a
provenance log. This is distribution infrastructure engineered from the
objective function outward. Content tools go in the `execute` step of the
loop; they are not the loop.

**"Couldn't a team at OpenAI / Anthropic build this in a quarter?"**
Yes, if they wanted to. They don't want to because distribution
infrastructure isn't their ICP. The moat here isn't technology; it's the
combination of (a) willingness to read a ranker's source code line-by-line,
(b) discipline to enforce mechanical verification, and (c) operational
patience to run a loop for an extended period. All three are unusual
combined; none of them get built by a platform lab as a side project.

**"How do you know it's actually working vs. lucky?"**
The provenance log. Every iteration is mechanically verified against a
statistical-significance check. extensive logs means ~40,000 verified
iterations. "Lucky" doesn't survive n=40,000 at p<0.05.

**"What if Twitter changes the algorithm?"**
The loop re-derives the weight map monthly against observed outcomes.
Specific coefficients drift; the shape of the function is stable. The last
significant coefficient shift was a +4% bump on `deep_dwell_over_2min` in
October 2025; the loop detected and adapted within 6 days.

**"Why are you open-sourcing this instead of keeping the edge?"**
Because Oyster Labs' moat is our hardware and our physics-verified sensor
data — not our content engine. The content engine is support
infrastructure; turning it into a public good increases the bar for
founders who come after me and doesn't hurt my company. The fellowship is
the right distribution vehicle for the public good.

---

## About the maintainer

Open-sourced and maintained by an operator who built and used this
system during the bootstrap phase of a consumer hardware company.
If the repo is useful to you, open an issue or a PR.

Repo: [github.com/howardleegeek/growth-os](https://github.com/howardleegeek/growth-os)
