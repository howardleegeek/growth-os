# 04 · Dwell optimization

> Dwell time is the only engagement signal that can't be faked by a single click. Every
> serious ranking algorithm weights it. Optimizing for dwell is the cleanest path to
> distribution that survives algorithm changes.

---

## Why dwell matters

Twitter's ranker assigns **+20×** to `deep_dwell_over_2min`. LinkedIn, TikTok, and YouTube
all weight dwell more heavily than any single click-based signal — often 3–10× more.

The reason is asymmetric: clicks can be manufactured (bots, engagement pods, ragebait).
Dwell cannot — no automated actor will spend 2 real minutes on a post that doesn't hold
its attention. Platforms know this, and they weight accordingly.

This has a useful property: **dwell-optimized content doesn't degrade when the algorithm
updates.** The coefficients on click signals shift every quarter. The coefficient on
dwell never drops meaningfully because the signal it captures is fundamental to the
ranking objective.

Optimizing for dwell is therefore the most *durable* positive signal play.

---

## The components of dwell

Dwell time on a post is decomposed by the classifier into four components, each
observable:

1. **Initial hook latency** — how long before the user leaves within the first 3 seconds
2. **Scroll depth** — how far down the post they travel
3. **Thread continuation rate** — whether they click into replies
4. **Return visits** — whether they come back to the post within 24 hours

Different content maximizes different components. The best-performing posts in our
corpus optimize at least three of four.

---

## Content patterns that hold dwell

### Pattern A: the numbered breakdown

Single-tweet format: "There are 7 ways most founders waste their first $100K. Here's the list."

Followed by a thread of 7 items. Dwell is earned by completion bias — users who start
will finish. Scroll depth is maximized by structure.

Production data (our corpus, n=212 posts):
- Median dwell: 94 seconds (vs. 31s baseline)
- Thread continuation rate: 58% (vs. 19% baseline)

### Pattern B: the teardown

"I read [thing nobody else read]. Here are the 4 things that surprised me."

This pattern combines a rare-information hook (rewards profile clicks, +24×) with a thread
that holds dwell. Pairs naturally with the self-reply pattern from [chapter 3](./03-self-reply-pattern.md).

### Pattern C: the contrarian premise

"Everyone says [consensus]. The actual data says [contrarian]."

Reply-inducing by construction (+27× from `being_replied_to`). Dwell is earned because
readers stick around to evaluate whether the contrarian claim holds up. Requires
substance; manufactured contrarianism trips negative-signal classifiers.

### Pattern D: the behind-the-scenes mechanic

"Here's the actual technical mechanism behind [common phenomenon]."

Works especially well for founders: you have privileged access to mechanisms most
audiences don't see. Dwell is earned through genuine novelty. Scroll depth is naturally
long because explanations require paragraphs.

---

## Anti-patterns that destroy dwell

### The one-liner hot take

Single sentence, no follow-on. Even if it gets likes, dwell is ~8 seconds. The +1× like
boost doesn't offset the opportunity cost of not shipping a dwell-positive post in the
same slot.

### The plug

"Check out [product link]." Users scroll past plugs in under 2 seconds, and the ranker
classifies the post as promotional. Dwell is near-zero and promotional content gets
down-weighted across the account over time.

### The meme without commentary

Memes travel on retweets (+2×), which is the worst-rewarded positive signal in the
Twitter ranker. They produce impressions but not downstream engagement — followers
acquired from memes don't convert.

### The cliffhanger that doesn't pay off

"You won't believe what happened next..." Dwell spikes, then the post fails to deliver,
and the `negative_feedback` classifier picks up the disappointment signal. One of these
costs ~148 normal posts worth of distribution.

---

## Implementation note

The scoring function in [`engine/signal_weights.py`](../engine/signal_weights.py) uses
`p_deep_dwell_over_2min` as one of its inputs. That probability comes from a small
classifier trained on features like:

- Post length in characters
- Presence of thread continuation
- Hook type classification (numbered / teardown / contrarian / plug / meme / cliffhanger)
- Post structure (list / narrative / declarative / interrogative)

We retrain monthly on fresh labeled data. The classifier is ~15KB of coefficients; the
work is in labeling, not modeling.

---

## The asymmetry one more time

Ten posts optimized for dwell will out-distribute fifty posts optimized for likes. Every
week that you're shipping at scale, this gap compounds. By month six the dwell-optimized
account is a different species of distribution asset than a like-optimized account.

---

## Next

Dwell maximizes upside. Now we need to avoid the asymmetric downside:
[05 · Negative signal avoidance](./05-negative-signal-avoidance.md).
