# 01 · Read the source

> The single highest-leverage thing a growth engineer can do in 2026 is read the ranking
> source code of the platforms they're trying to distribute on. Almost nobody does.

---

## Why this works

Modern distribution platforms are ranking functions. A ranking function is a weighted sum
of feature scores. If you know the weights, you know the function. If you know the function,
you can optimize against it.

Most "growth work" is done by people who don't know the function exists, so they approximate
it through taste, folklore, and survivorship bias. Those approximations are expensive and
wrong in predictable directions — usually biased toward chasing positive signals while
ignoring asymmetric negative ones.

Reading the source is a 40–120 hour investment that collapses the approximation gap.

---

## What's actually public (as of 2026)

| Platform | Source status | Where to start |
| --- | --- | --- |
| Twitter / X | **Fully open** since 2023-03-31 | [github.com/twitter/the-algorithm](https://github.com/twitter/the-algorithm) · focus on `src/scala/com/twitter/home_mixer/.../HeavyRankerScoringPipeline.scala` |
| Mastodon | Fully open (reference server) | [github.com/mastodon/mastodon](https://github.com/mastodon/mastodon) · timelines are reverse-chronological; virality lives in trending + follow graph |
| Bluesky (AT Protocol) | Fully open | [github.com/bluesky-social/social-app](https://github.com/bluesky-social/social-app) · algorithm feeds are user-pluggable, which means you can *ship your own* |
| Reddit | Partially public (search + ranking papers) | The [hot ranking algorithm](https://medium.com/hacking-and-gonzo/how-reddit-ranking-algorithms-work-ef111e33d0d9) is a known formula; subreddit variance dominates |
| LinkedIn | Leaked + reverse-engineered | [Hootsuite algorithm teardown](https://blog.hootsuite.com/linkedin-algorithm/) + observed behavior |
| TikTok | Leaked guidance + empirical | NYT [leaked internal deck](https://www.nytimes.com/2021/12/05/business/media/tiktok-algorithm.html) · first-hour velocity dominates |
| YouTube | Research papers | [Deep Neural Networks for YouTube Recommendations (2016)](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45530.pdf) · still directionally valid |
| Instagram | Periodic creator disclosures | Adam Mosseri's "[How Instagram works](https://creators.instagram.com/blog/instagram-ranking-explained)" is updated ~yearly |

The rule: **read the primary source before you read the takes.** Medium posts about
algorithms are compressed through a game-of-telephone by the time they reach you.

---

## How I read the Twitter source (120-hour breakdown)

This is the exact process I used. It generalizes.

**Hours 0–8: map the codebase.**
Don't read anything. Just traverse the top-level directory structure and note what's where.
For Twitter: `src/scala` is the ranker, `src/python/twitter/deepbird` is the ML, `navi` is the serving layer, `representation-scorer` is the embedding scorer. Most of the code is plumbing; only ~10% is the thing you care about.

**Hours 8–24: find the scoring function.**
Search for `objective`, `loss`, `reward`, `weight`, `coefficient`, `score`, and the canonical model names (`HeavyRanker`, `LightRanker`). You're looking for the place where per-candidate scores become a single number. In Twitter's case this is `HeavyRankerScoringPipeline.scala` and the config sitting next to it.

**Hours 24–56: extract the coefficients.**
Read the scoring function line by line. Note every multiplier, every threshold, every
conditional branch. Translate into a weight table (like the one in [`engine/signal_weights.py`](../engine/signal_weights.py)).

**Hours 56–88: find the classifiers.**
Each coefficient multiplies a predicted probability. Follow the probabilities back to their
classifiers. What features do they consume? How often are they retrained? What's the
implicit prior when evidence is missing?

**Hours 88–120: map the negative-space assumptions.**
The most important reading happens when you realize what the code *doesn't* do. Twitter's
ranker uses no user-LLM alignment signal, so verbose LLM-generated content doesn't get
boosted. It does use dwell — so a thread that keeps users scrolling wins regardless of
how it reads. That asymmetry is where the alpha is.

---

## Deliverable

At the end of 120 hours you should have:

1. A weight table (machine-readable: dict/YAML/JSON) — see [`engine/signal_weights.py`](../engine/signal_weights.py)
2. A list of signals the ranker consumes AND a list of signals you expected it to consume but it doesn't
3. A list of asymmetric penalties (negative weights that dominate equivalent positive wins)
4. A "what to ignore" list — signals whose coefficients are too small to matter

---

## Common objections (and why they're wrong)

**"The public source is out of date."**
Usually true by 6–18 months. Also usually doesn't matter. Coefficients get tuned; the
architecture doesn't. The 75× self-reply weight on Twitter has shifted between releases
but has never dropped to parity with +1× like. The shape of the function is stable even
when the exact values aren't.

**"This only works for open-source platforms."**
No — it works wherever you can establish the function empirically. If TikTok rewards
first-hour engagement velocity, you can measure that yourself and build the same scoring
discipline without source code.

**"My product isn't content-based."**
Every product has distribution. Shopify product search, Amazon buy-box, App Store ranking,
Google Play featured, Product Hunt hot — all are ranking functions. Same method applies.

**"I don't have 120 hours."**
Then you will lose to someone who does. This is the most asymmetric skill investment in
growth engineering right now.

---

## Next

When the weight table is in hand, start encoding it: [02 · Weight mapping](./02-weight-mapping.md).
