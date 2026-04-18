# Internal metrics — the ones that actually matter

> This is the metric catalog we use internally at Oyster Labs to run our content engine.
> Publishing it because most teams I talk to track the wrong things — likes, follower
> count, "engagement" — and none of them correlate tightly with the business outcomes
> we actually care about.

---

## Why these metrics

The metrics that get published in "growth dashboards" are mostly vanity. Followers go
up while revenue stays flat. Engagement rate spikes during a viral moment and then
the account converts nothing.

The metrics below were selected by one principle: **they must predict downstream
business outcomes** (devices sold, enterprise pilots, inbound founder DMs, waitlist
signups). If a metric couldn't defend itself in a regression against revenue, it's
not here.

---

## The canonical table

Every account reports these daily into our shared analytics store. The schema matches
`backend/schemas/analytics.py` in our internal codebase:

```python
class AnalyticsResponse(BaseModel):
    date: date
    posts_count: int
    impressions: int
    engagements: int
    followers_gained: int
    engagement_rate: float
```

Extended to the full internal catalog below.

---

## Tier 1 — the four metrics that run the business

These four are on the wall. Everyone on the team can recite them.

### 1. Decay-adjusted daily reach (DADR)

The sum of `effective_score × impressions` across all posts shipped by an account
that day, normalized by the account's 30-day trailing median. This is the number that
captures "did we distribute well today, controlling for author diversity decay and
platform-level variance."

```
DADR(account, day) = Σ [ effective_score(post) × impressions(post) ]
                     / median_30d(decay_adjusted_reach, account)
```

A DADR of 1.0 means we had a normal day. 1.5 is excellent. 0.5 is a warning.

This is the single metric that best predicts 30-day-forward revenue in our historical
data (r² ≈ 0.58 against device orders).

### 2. Profile-click-to-conversion rate (PC2C)

The share of profile clicks that result in a downstream conversion event (product-page
visit, email signup, waitlist, or direct DM) within 7 days. This measures whether the
audience we're attracting is the audience that buys.

```
PC2C = conversions / profile_clicks    (7-day rolling window)
```

Industry benchmark: ~1–2% is normal. Our target: >4%. Our 2025 median: 4.7%.

This is the metric that distinguishes "viral content" from "profitable content." A
meme post can generate 50× profile clicks at 0.1% PC2C — net zero. A technical thread
can generate 5× profile clicks at 8% PC2C — net positive.

### 3. Negative signal rate (NSR)

Total negative signals (mute, block, hide, "not interested", report) divided by total
impressions. The most important number on the dashboard, because negative signals are
asymmetric.

```
NSR = (mutes + hides + not_interesteds + blocks + reports × 5) / impressions
```

Note the `× 5` on reports — that's a rough internal calibration for how much weight
to give reports over other negative signals when tracking the overall health of an
account.

Target: <0.05%. We investigate anything above 0.1%. Above 0.5% triggers a "ship only
tier A for 4 weeks" protocol.

### 4. Dwell-positive content share (DPCS)

The share of shipped posts that achieve ≥2-minute median dwell time.

```
DPCS = posts_with_median_dwell_over_2min / total_posts_shipped
```

Target: >60%. Current median across our accounts: 72%.

This is our leading indicator. Dwell-positive content takes 3–7 days to convert into
DADR gains but predicts them reliably.

---

## Tier 2 — the diagnostic metrics

These don't go on the wall but they're what you look at when Tier 1 moves in an
unexpected direction.

### Reply-rate-from-strangers (RRFS)

Replies from accounts that have never interacted with this account before, divided by
impressions. This is the *genuine* reply rate — it excludes engagement pods, cross-brand
cross-talk, and repeat-commenter noise.

```
RRFS = (replies - replies_from_known_accounts) / impressions
```

Why it matters: a healthy growth account has RRFS ≥ 0.3% steady-state. An engagement-
farmed account has RRFS near zero even while its total reply count looks healthy.

### Thread-continuation rate (TCR)

On posts that ship with a self-reply, the share of users who scroll from the parent
into the continuation.

```
TCR = (users_viewed_reply) / (users_viewed_parent)
```

Good: >30%. Great: >50%. Our 2025 median: 44%.

TCR is our proxy for whether the self-reply actually delivers the dwell it claims to.

### Safety-tier share (STS)

Percentage breakdown of shipped posts across A/B/C/D tiers. Always monitor; rarely
intervene unless drift is large.

```
STS = {"A": 0.62, "B": 0.28, "C": 0.09, "D": 0.01}  # example from a recent week
```

Alerts:
- Tier A below 50% → we're over-indexing on edge, risk of accumulated negative signals
- Tier C above 12% → we're over the safety cap
- Tier D above 0% → hard bug in the gate, investigate immediately

### Hook-type distribution (HTD)

For each shipped post, its classified hook type. Tracks whether the engine is producing
a healthy variety or collapsing into one pattern (usually contrarian, which is where
classifiers drift).

```
HTD = {
  "numbered":    0.22,
  "teardown":    0.19,
  "contrarian":  0.15,
  "data":        0.24,
  "narrative":   0.12,
  "question":    0.08,
}
```

Alert: any single hook type above 35% triggers diversification.

### Cross-account engagement leakage (CAEL)

How often users who engage with account A also engage with account B within 24 hours.
This is how we catch the ranker's coordination-signal classifier getting suspicious
of our multi-account footprint.

```
CAEL(A→B) = |engagers(A, t) ∩ engagers(B, t+24h)| / |engagers(A, t)|
```

Target: <8% per account pair. If CAEL climbs above 15%, we're cross-pollinating too
much and the accounts need topic separation.

---

## Tier 3 — the business metrics

These are the numbers the board sees. They lag Tier 1 by 14–30 days.

### Organic CAC

Total content ops spend (LLM API, infra, labor) divided by new paying customers in the
period. For us, this number is consistently under $1 per customer because the engine
cost is near-fixed while acquisition scales with content output.

### Revenue per 1,000 impressions

Total revenue in the period divided by total impressions × 1,000. This is the closest
single number to "content ROI."

Industry benchmark for consumer hardware: $0.20–$0.80. Our median: $2.10.

### Waitlist signup velocity

New waitlist signups per week. Tracked separately from conversions because waitlist is
where our pre-launch distribution shows up; product pages are where our current-product
distribution shows up.

### Inbound founder-DM rate

DMs from identifiable founders (LinkedIn check-out against their profile) per week.
This is the metric that predicts BD pipeline, because founders who DM us first convert
at ~18× the rate of founders we cold-outreach.

---

## Metrics we deliberately don't track

Because they actively mislead.

- **Total followers.** Vanity. Correlates weakly with revenue once past ~5K.
- **Engagement rate** (as usually defined). Too loose — includes reply-pods, cross-brand
  cross-talk, and low-quality likes. We use RRFS and DPCS instead.
- **Click-through rate** to product pages. Over-indexed by bots and bookmarkers. PC2C
  captures the real signal.
- **Trending topic participation.** Almost always tier-C or worse, and the conversion is
  poor because trend-driven traffic isn't intent-driven.

---

## Implementation note

The metric pipeline is in our internal codebase; it mirrors the public schema shown at
the top. It reads from each platform's API (or scraping fallback when the API doesn't
expose the signal), writes to a PostgreSQL `analytics_daily` table, and the dashboards
read from there.

The pieces of the pipeline that are platform-agnostic — the metric definitions, the
Tier-A-B-C alerting logic, the aggregation math — are worth open-sourcing and will be
in a future release of this repo. The pieces that are platform-specific (API clients,
scraper fallbacks) are not portable.

---

## If you track only three

You won't track all of these. Nobody does. If you can only afford three metrics:

1. **DADR** — are we distributing
2. **NSR** — are we safe
3. **PC2C** — is the audience we're attracting the audience that buys

Everything else is diagnostics for when one of those three moves.
