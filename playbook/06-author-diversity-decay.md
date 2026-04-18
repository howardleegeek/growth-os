# 06 · Author diversity decay

> The single biggest mistake creators make at scale is not understanding that their
> second post of the day gets 62.5% of the distribution their first post got, and
> their third gets 43.75%. If you're posting 10 times a day, you're giving away most
> of your distribution to the algorithm's own diversity function.

---

## What the function does

Every ranker with a "For You" style surface runs a post-ranking diversity pass. The pass
prevents a single author from monopolizing a user's feed — good for user experience, bad
for accounts that don't account for it.

The mechanism is a multiplier applied to each subsequent candidate from the same author:

```
effective_score(post) = raw_score(post) × diversity_decay ^ (post_index_today - 1)
```

For Twitter the empirical decay factor is `~0.625`:

| Post index | Effective multiplier | Cumulative reach if raw score is constant |
| --- | --- | --- |
| 1st post  | 1.000× | 100% |
| 2nd post  | 0.625× | 162.5% |
| 3rd post  | 0.391× | 201.6% |
| 4th post  | 0.244× | 226.0% |
| 5th post  | 0.153× | 241.3% |
| 10th post | 0.015× | 257.7% |

Look at the cumulative column. By your fifth post, you've spent five posts' worth of
effort to get 2.4× the reach of your first post. By your tenth, you're getting 2.57×
for 10× the effort. Marginal return per additional post collapses.

---

## The implication

**Three high-quality posts out-perform ten mediocre posts.** The marginal post after
~3 per day per account is nearly free reach for the platform and nearly zero return
for you.

This is the opposite of what "post 5–10 times a day for consistency" advice prescribes.
That advice was correct in 2018 when reverse-chronological feeds dominated. It is
actively harmful in 2026.

---

## What to do about it

### Move 1: cap posts-per-account-per-day at 3

Any additional post adds friction to your operations without adding distribution. Our
engine hard-caps at 3 high-quality posts per account per day. Slot 4+ is simply not
scheduled.

Exception: pure reply work doesn't count against the cap. The diversity decay applies
to standalone posts appearing in For You surfaces. Replies in other people's threads
live under different ranking logic.

### Move 2: use multiple accounts to scale throughput

If you need more than 3 posts/day of distribution, you need more than 1 account. Each
account has its own diversity budget — the first post from account B is a fresh 1.000×.

This is why our production footprint is 4 Twitter + 4 Bluesky + 2 LinkedIn = 10 accounts.
Not because we need that many brands (we have 5). Because each brand needs both a
corporate and a founder-persona account to hit the daily distribution ceiling.

### Move 3: stagger posts across the active window

If you're going to ship 3 posts, don't ship them in a one-hour block. Distribute them
across the 16-hour active window. Even though the decay is per-author-per-day, there's
a secondary recency boost in the first 90 minutes after each post. Stagger to maximize
overlap between your recency windows.

Our scheduler: posts spaced evenly across a 6am–10pm window, approximately 5.3 hours
apart, randomized by ±25 minutes.

### Move 4: alternate post types

The diversity classifier is more forgiving of diverse post types from the same author.
Don't ship 3 numbered-breakdown posts in a day. Ship a numbered-breakdown, a teardown,
and a contrarian. Same author, but the ranker's feature embedding sees them as different
content, which softens the decay by ~8–12% empirically.

---

## What the math actually looks like in our engine

From [`engine/signal_weights.py`](../engine/signal_weights.py):

```python
AUTHOR_DIVERSITY_DECAY = 0.625

def effective_weight(base_score: float, post_index_today: int) -> float:
    return base_score * (AUTHOR_DIVERSITY_DECAY ** (post_index_today - 1))
```

And from [`engine/content_engine.py`](../engine/content_engine.py)'s scheduler, each
scheduled post carries its daily-index so the scoring function can re-evaluate whether
the post still clears the ship threshold given its decayed score.

The non-obvious consequence: **a post that scored 6.0 on its own might score 3.75 as
the second post of the day, which is below our 5.0 threshold and gets killed.** The
scheduler respects this — marginal posts that would have been net-negative after decay
never ship.

---

## The counterintuitive optimization

Because the decay is multiplicative, the optimization isn't "ship more posts." It's
"ship posts with higher pre-decay scores, and ship them earlier in your daily slot
sequence."

This inverts the intuition most growth teams operate on. They treat volume as the
independent variable. The engine treats **slot-quality-weighted volume** as the
independent variable.

Practically: if you have 4 candidate posts and only 3 slots, you don't queue the 4th
for tomorrow. You re-rank all 4 for tomorrow's slots 1–3 and drop the weakest. Today's
slots 2 and 3 already get the top two candidates.

---

## Cross-platform note

The decay factor varies:

| Platform | Estimated decay | Soft daily cap |
| --- | --- | --- |
| Twitter / X | 0.625 | 3 posts |
| LinkedIn | 0.55 | 2 posts |
| Bluesky | 0.70 | 4 posts |
| Reddit | per-subreddit | 1/subreddit/day |
| TikTok | no meaningful decay | 5+ posts |
| YouTube | no meaningful decay | unlimited |

For cross-platform production, respect each platform's cap independently. Don't
coordinate caps across platforms — the decay functions are independent.

---

## Next

Now that you understand decay, you need to scale beyond one account:
[07 · Multi-account orchestration](./07-multi-account-orchestration.md).
