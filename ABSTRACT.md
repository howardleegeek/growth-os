# Abstract

> A 2-minute read for people who don't have time for the full docs.

---

## What this is

`growth-os` is an **evolutionary tree search against Twitter's published
ranking algorithm**. It runs autonomously: proposes content mutations,
prescreens them against an offline simulator of the Twitter ranker,
ships the top survivors to the real platform, verifies the outcomes
mechanically, and merges winning branches into descendants. Forever.

## Why this exists

In 2023 Twitter open-sourced their ranking algorithm —
[github.com/twitter/the-algorithm](https://github.com/twitter/the-algorithm).
Most growth tools ignored this. I didn't. I read the 10,000 lines,
extracted the coefficients, encoded them as a scoring function, and
built an evolutionary loop that optimizes against it autonomously.

The system was developed and used during the bootstrap phase of a
consumer hardware company, where "no marketing budget, no marketing
team" was the starting constraint. Open-sourced here so the method
is available to anyone in the same situation.

## Why this is novel

Three ideas combined for the first time:

1. **Karpathy-style autoresearch loop** (hypothesize → verify → log → repeat)
2. **EvoHarness tree search** (parallel proposers, surface decomposition, branch merging)
3. **Offline Twitter simulator** (the weight map as a free scoring oracle)

No product I've found combines all three. The closest comparable tools
(GrowthBook, Mixpanel Experiments, Jasper) have a human in the loop and
run no tree search.

## Who should care

- **Bootstrapped founders** — this is the playbook for getting to $1M+ in
  revenue without raising capital and without hiring a growth team. Start
  with [`playbook/00-autoresearch-first.md`](./playbook/00-autoresearch-first.md).
- **Growth engineers** — this is what growth work looks like when the
  objective function is explicit and the loop is autonomous. Start with
  [`IMPLEMENTATION.md`](./IMPLEMENTATION.md).
- **ML research engineers** — this is Karpathy's autoresearch + EvoHarness
  applied to a non-ML optimization problem (distribution). If you find the
  transfer interesting, open an issue.

---

Everything that follows in this repo is a longer version of the paragraph
above.
