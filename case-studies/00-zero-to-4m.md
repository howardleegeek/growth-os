# Case Study: $0 → $4M with zero paid acquisition

**Company:** Oyster Labs (consumer hardware — phones, glasses, health wearables)
**Operator:** Howard Li (founder, 1 FTE)
**Timeline:** Q1 2024 — present
**Stack:** `growth-os` (the system in this repo)

---

## The situation in Jan 2024

- Product was real: 5 consumer device lines, physics-verified sensor stack
- Capital: $0 raised
- Team: 1 founder, 32 AI agents I'd written myself
- Marketing budget: $0
- Problem: every conventional distribution channel required either money or people

Paid acquisition was off the table. Hiring a growth team was off the table. "Post good content and hope" was not a strategy.

The only remaining lever: **treat distribution as an engineering problem.**

---

## The hypothesis

Twitter open-sourced their ranking algorithm on 2023-03-31. 10,000+ lines of Scala,
Python, protobuf — publicly readable at [github.com/twitter/the-algorithm](https://github.com/twitter/the-algorithm).

Everyone I knew had shared the announcement on release day. Nobody had actually read it.

**Hypothesis:** the coefficients that determine distribution are published. If I read them
carefully and encode them into a content engine, I can get deterministic distribution
without paid acquisition.

---

## What I actually did

### 1. Read the source (weeks 1–4)

Spent about 120 hours reading the ranker code. Most of it was plumbing — the interesting
part is in the scoring pipeline, where a weighted sum of predicted user-action
probabilities determines which tweets surface.

Extracted the coefficients. The ones that mattered:

| Signal | Weight | Implication |
| --- | --- | --- |
| Author replies to own post | **+75×** | Every post needs a self-reply within the engagement window |
| Being replied to | **+27×** | Content needs to be reply-inducing, not like-inducing |
| Profile click | **+24×** | The bio is a landing page, not decoration |
| Deep dwell >2min | **+20×** | Threads > single tweets for any content worth distributing |
| Retweet | +2× | Not worth optimizing for |
| Like | +1× | Baseline — irrelevant to strategy |
| Negative feedback | **−148×** | One mute clusters wipes out ~148 good posts |
| Report | **−738×** | One report neutralizes ~738 good posts |

The negative weights were the revelation. I'd been optimizing like a marketer —
chase likes and virality. The algorithm punishes bad signals asymmetrically by
two orders of magnitude. **Most "growth" advice is survivorship bias from
people who happened to avoid the negative cliffs.**

### 2. Build the engine (weeks 5–12)

Wrote `content_engine.py` (the simplified version in this repo is ~200 LOC; the
production one is ~3,800). Core loop:

```
generate → classify → score → gate → schedule → post → self-reply → measure
```

Key architectural decisions:

- **Per-post safety tier (A/B/C/D):** every candidate classified before scoring.
  Tier D auto-rejected. Tier C capped at 10% of daily volume. This is what
  prevents the -738× cliffs.
- **Self-reply is a first-class primitive:** every post object carries its own
  follow-up. The scheduler fires the self-reply within the 2:45–3:00 minute
  window — long enough to look organic, short enough to catch the engagement
  surge.
- **Per-account decay tracking:** same account's 2nd post of the day is boosted
  only 62.5% as much as the 1st. The scheduler respects this — 3 high-quality
  posts beats 10 mediocre ones.
- **A/B harness (`ab_tester.py`):** Thompson-sampling bandit over content
  variations. Over 18 months I ran 2,000+ distinct experiments.

### 3. Scale to 10 channels (months 4–12)

Same engine deployed across:

- 4 Twitter accounts (brand + 3 product lines)
- 4 Bluesky accounts (parallel footprint)
- 2 LinkedIn accounts (1 personal narrative + 1 company page)

Output: ~37 posts/day, ~259 posts/week, fully automated. I haven't hand-scheduled
a post in 14 months.

---

## Results

### Distribution lift (per-post, vs. pre-engine baseline)

| Metric | Before engine | After engine | Lift |
| --- | --- | --- | --- |
| Median impressions / post | 180 | 4,100 | **+2,178%** |
| Profile click rate | 0.6% | 2.1% | **+250%** |
| Reply rate | 0.3% | 3.7% | **+1,133%** |
| Mute / report rate | 0.8% | 0.05% | **-94%** |

### Business outcomes

| Metric | Value |
| --- | --- |
| Revenue | **$4M** |
| Devices sold | 25,000+ |
| Customer acquisition cost | **$0** |
| Gross margin | 60% |
| Total capital raised | **$0** |
| Headcount | 1 founder + 0 marketers |

### The thing that compounds

The system still runs while I write this. It has been running continuously
for 14 months. Every day it generates candidates, scores them against the
published weights, ships the survivors, and logs what worked. The weight
map has been updated 4 times as Twitter has nudged the algorithm post-rename.

**CAC approaches zero because the marginal cost of the next 1,000 posts is an
LLM API call. The acquisition channel has near-zero marginal cost and
non-zero marginal conversion. That is infrastructure, not marketing.**

---

## What transfers

This case is Twitter-specific but the method is not. The same approach works wherever:

1. The platform publishes or leaks its ranking function (Twitter, most open-source platforms)
2. The platform's behavior can be reverse-engineered empirically (LinkedIn, TikTok, Shopify, Amazon)
3. Distribution quality is high-variance and under-optimized (every consumer platform)

Next extensions of `growth-os` in progress:

- **LinkedIn weight map** (dwell-dominant, different reply mechanics)
- **TikTok first-hour velocity model** (engagement-per-view in hour 1 is the load-bearing signal)
- **Shopify search ranking** (conversion-weighted relevance — the weights leak through search suggest)

---

## What I'd tell another bootstrapped founder

1. **Read the source of the platform you need.** Literally. 99% of "growth advisors" haven't.
2. **Treat negative signals as asymmetric.** Avoiding -738× matters more than hitting +75×.
3. **Encode the weights, don't internalize them.** Human intuition drifts. A scoring function doesn't.
4. **Self-reply is free.** Every platform rewards thread depth. Every founder I know ignores it.
5. **Stop calling it content strategy.** Call it distribution engineering. The reframe changes who you hire, how you measure, and what you build.
