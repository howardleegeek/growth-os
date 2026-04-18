# 08 · Cross-platform extension

> Everything in this playbook so far has been about Twitter. The method is not
> Twitter-specific. This chapter is the generalization — how to take the same
> weight-mapping / safety-tier / engine-orchestration discipline and extend it to any
> distribution platform.

---

## The generalizable method

Five steps. Same for every platform.

1. **Establish the ranking function.** Either by reading source (if open) or by
   observing behavior (if not). Output: a weight table.
2. **Build a classifier for each signal.** Predict P(signal) for a candidate piece of
   content.
3. **Implement the scoring gate.** Weighted sum ≥ threshold = ship.
4. **Encode the safety tiers.** Asymmetric negative signals need their own quota system.
5. **Orchestrate multi-account within the platform's isolation rules.**

The implementation in [`engine/`](../engine/) is written generically enough to swap in a
new weight map and a new classifier. The rest of the pipeline doesn't change.

---

## Platform-by-platform notes

### LinkedIn

**Ranking:** Partially leaked, partially observable. The big signal is **dwell time**
(~40% of the function) followed by **comment depth** and **profile visits**.

**Key weights (estimated from observation):**

| Signal | Estimated weight |
| --- | --- |
| Long-form read completion | +50× |
| Comment from a 1st-degree connection | +35× |
| Reshare with comment | +20× |
| Profile visit | +25× |
| Reaction (like/celebrate/etc.) | +2× |
| Hide post | −200× |
| Report | −800× |

**What's different:** LinkedIn rewards **long-form** more than any other platform.
Posts in the 1,200–1,800 character range consistently out-distribute short posts.
Threads don't exist natively; use "carousel documents" (PDFs rendered as slides) to
get dwell-heavy content.

**Self-reply analog:** First comment by the author within 8–15 minutes of publishing
is the closest analog. Less leverage than Twitter's 75× but still ~2.5× lift.

**Daily cap:** 2 posts per account per day (decay is more aggressive than Twitter).

---

### Bluesky (AT Protocol)

**Ranking:** Fully open. The interesting property: algorithm feeds are user-pluggable.
This means you can ship your own.

**What's different:** The reverse-chronological default still dominates most users'
attention, so Bluesky at current scale rewards **posting frequency** more than
algorithmic optimization. The interesting growth work is on the pluggable-feed side —
if you can get your feed adopted by users, you become a distribution surface.

**Key weights (for the algorithm feeds that exist):**
- Engagement velocity in hour 1 is the dominant signal
- No equivalent of the 75× self-reply weight — the feed-level distinction matters more
- Negative signals are softer (smaller absolute penalties than Twitter)

**Daily cap:** 4 posts per account per day.

---

### TikTok

**Ranking:** Leaked internal documentation ("For You" page mechanics) + extensive
empirical evidence.

**Key weights (estimated):**

| Signal | Estimated weight |
| --- | --- |
| Completion rate (watched to end) | +80× |
| Rewatch | +60× |
| Share | +40× |
| First-hour engagement velocity | +30× |
| Comment | +25× |
| Like | +3× |
| Skip (swiped before 3s) | −100× |
| Report | −600× |

**What's different:** TikTok uses **first-hour velocity** as a primary gating signal.
Content that doesn't hit a minimum engagement-per-impression in hour 1 gets
distribution-capped for its entire lifetime. Timing is more important here than on
any other platform.

**No meaningful diversity decay:** Post 5+ times per day if you can maintain quality.

---

### Shopify / Amazon product search

**Ranking:** The ranker is a weighted sum of conversion signals. Same method applies —
the signals are just different.

**Key weights:**
- Click-through rate from search to PDP
- Add-to-cart rate
- Conversion rate
- Review velocity (new reviews per week)
- Review sentiment
- Return rate (negatively weighted, heavily)

**What's different:** The ranker runs at the query level. You're not optimizing for an
account; you're optimizing for a (query, product) pair. Same engine architecture; the
"account" abstraction becomes a "keyword cluster" abstraction.

---

### App Store / Google Play

**Ranking:** Conversion-weighted with heavy penalties for uninstalls within 48 hours.

**Key weights:**
- Impression-to-install rate
- Install-to-active-user rate (7-day)
- Review velocity and sentiment
- Keyword relevance (App Store: exact-match; Play: softer semantic match)
- Uninstalls within 48h (heavily negative)

**What's different:** The 48-hour uninstall signal is the load-bearing one. An app
that can optimize for impression-to-install but then under-delivers in the first 48
hours will be down-ranked faster than any other kind of negative signal on any other
platform.

---

## Reusing the engine

The code in [`engine/`](../engine/) is platform-agnostic:

```python
# engine/signal_weights.py
#   Swap SIGNAL_WEIGHTS for the new platform's weight map.
#   Add per-platform versions if you're orchestrating multiple.

# engine/content_engine.py
#   The loop is platform-independent.
#   Plug in the new platform's API at the `publish()` boundary.

# engine/ab_tester.py
#   Works unchanged.
```

The only platform-specific code is the publishing adapter. We maintain separate adapters
for each platform behind a common interface:

```python
class PlatformAdapter(Protocol):
    async def publish(self, post: ScoredPost) -> PublishResult: ...
    async def schedule_reply(self, at: datetime, reply: str) -> None: ...
    async def fetch_metrics(self, post_id: str) -> PostMetrics: ...
```

New platform = one new adapter. The engine, classifier, and safety-tier system are
reused.

---

## What *doesn't* transfer

Some things are genuinely platform-specific:

- **Timing windows.** Derive empirically per platform.
- **Acceptable safety-tier mix.** Some platforms tolerate tier C (Twitter); some don't (LinkedIn).
- **Voice / formatting.** Twitter rewards terseness; LinkedIn rewards length; TikTok rewards motion.
- **Negative-signal recovery time.** Twitter recovers in ~3–4 weeks; LinkedIn in ~6–8.

Don't try to generalize these. Learn them per-platform, store them in config, re-derive
quarterly.

---

## The meta-point

This entire playbook exists because modern distribution platforms are ranking functions,
and most creators treat them as black boxes. Reading the function, encoding it, and
optimizing against it is a repeatable engineering discipline. It works on every
platform because every platform is doing the same underlying thing.

Ten years from now there will be new platforms and new weight tables. The engine in
this repo will still be useful, because the method is the permanent thing — not the
specific values in the 2026 Twitter coefficients.

---

## End of playbook

Thanks for reading. If you ship something using this approach, I want to know:
[howard.linra@gmail.com](mailto:howard.linra@gmail.com) · [linkedin.com/in/connecthoward](https://www.linkedin.com/in/connecthoward/)
