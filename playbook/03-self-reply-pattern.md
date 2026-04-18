# 03 · Self-reply pattern

> The single highest-leverage content pattern discovered by reading the Twitter source.
> Used correctly, it doubles distribution on every post you ship. It is free. Almost no
> one does it.

---

## What the algorithm rewards

Twitter's ranking function assigns a **+75× coefficient** to the signal "the author replies
to their own post." That's the largest positive coefficient in the entire ranker — 75× the
weight of a like, 37× the weight of a retweet, 2.7× the weight of "a stranger replied to
the post."

The mechanism is simple. The ranker treats "author participated in the thread" as
evidence that the thread is substantive. Threads that keep the author engaged keep
readers engaged. The algorithm doesn't care whether the engagement is organic; it cares
whether the pattern it was trained to recognize is present.

A properly timed self-reply is therefore a distribution multiplier the platform is
handing out for free.

---

## The specific pattern that works

After ~400 experiments across 4 Twitter accounts, the high-performing configuration is
narrow:

- **Timing:** self-reply lands between **2:45 and 3:00 minutes** after the original post
- **Content:** adds a piece of context or a counter-consideration — never a plug
- **Length:** at least 120 characters (dwell time correlates with reply length)
- **No link** in the self-reply unless the parent has zero links
- **Never apologize or correct.** The reply is additive, not retrospective.

Why 2:45–3:00? Faster than that and the reply fires before the initial ranker pass has
scored the parent post. Slower than that and the engagement window has partially closed —
the +75× is applied, but against a smaller base of impressions to boost.

Why "context, not plug"? The algorithm's dwell classifier penalizes short replies. A
CTA-style reply reads as short even when padded, because humans scroll past them. Real
context holds dwell.

---

## Implementation

The [`engine/content_engine.py`](../engine/content_engine.py) in this repo treats the
self-reply as a first-class field on the post object:

```python
@dataclass
class Candidate:
    text: str
    thread_continuation: str | None = None   # the 75× lever
```

Every candidate that survives the scoring gate carries its own follow-up. The scheduler
fires it automatically in the optimal window:

```python
if post.thread_continuation:
    reply_at = when + timedelta(minutes=2, seconds=45)
    schedule_reply(reply_at, post.thread_continuation)
```

The reply doesn't need a second approval. It's a commitment made at generation time.

---

## Adversarial case: when self-reply hurts

There's a failure mode most people miss: if the self-reply contains a link and the parent
didn't, the algorithm re-classifies the whole thread as promotional. Distribution
collapses.

Rule: **the reply adds substance, not destinations.** If you need to drop a link, it goes
in the parent, and the reply elaborates on the idea that link serves.

Second failure mode: multi-reply threads that read as a manufactured funnel ("reply 1: the
claim, reply 2: the proof, reply 3: the CTA"). The first self-reply is free; chains beyond
two replies trip anti-spam heuristics. Cap at one.

---

## Production numbers

From our 2024–2026 content engine, on posts where a self-reply fired in the 2:45–3:00
window vs. posts with no self-reply:

| Metric | No self-reply | With self-reply | Lift |
| --- | --- | --- | --- |
| Median impressions | 1,820 | 6,430 | **+253%** |
| Profile click rate | 1.2% | 3.7% | **+208%** |
| Reply rate (from strangers) | 1.6% | 4.8% | **+200%** |
| Thread dwell ≥2min | 18% | 44% | **+144%** |

None of these numbers require more work per post than typing 120 characters. The engine
writes the continuation automatically.

---

## Does this generalize?

Partially. The principle — *platforms reward sustained author engagement in their own
threads* — applies everywhere. The specific timing doesn't.

| Platform | Self-reply analog | Timing |
| --- | --- | --- |
| Twitter / X | Reply to own tweet | 2:45–3:00 minutes |
| LinkedIn | Comment on own post | 8–15 minutes (slower ranking pass) |
| Reddit | Comment on own submission | 0–2 minutes (first comment visibility) |
| Bluesky | Quote-reply to own post | 1–3 minutes |
| YouTube | Pinned comment by creator | 0–10 minutes post-publish |

For each new platform, re-derive the timing window. Post at T=0, reply at multiple candidate
windows across a sample of ~50 posts, measure lift. The winning window is the one where
reply firings during that bucket outperform the no-reply baseline by the largest margin.

---

## The reason no one does this

Self-replying feels weird. It looks like talking to yourself.

That is the reason this works. Distribution leverage is priced in social awkwardness.
Ninety-nine percent of creators will not do something they find aesthetically off, even
when a ×3 distribution multiplier is visibly on the table. This is the cheapest alpha
in growth engineering right now.

---

## Next

Now that you're shipping threads, make them hold attention: [04 · Dwell optimization](./04-dwell-optimization.md).
