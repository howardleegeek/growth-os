# 07 · Multi-account orchestration

> Once you've hit the diversity-decay ceiling on a single account, the next move is
> horizontal: multiple accounts, one engine. This chapter covers the architecture
> that makes that safe and productive.

---

## Why multiple accounts

Two reasons:

1. **Throughput ceiling.** A single Twitter account clears ~3 high-quality posts per
   day before diversity decay eats the marginal reach. If you need more distribution
   volume than that, you need more accounts.

2. **Persona segmentation.** Different audience segments respond to different framings
   of the same underlying message. Separate accounts let you A/B personas at the account
   level without brand contamination.

Our production footprint: 4 Twitter + 4 Bluesky + 2 LinkedIn = 10 accounts orchestrated
from a single engine.

---

## The four account archetypes

Our accounts fall into four stable archetypes. This isn't the only way to segment, but
it's the one that consistently works:

| Archetype | Voice | Posts | Example handle |
| --- | --- | --- | --- |
| **Corporate** | Neutral, factual, product-led | Announcements, feature drops, customer wins | `@oysterecosystem` |
| **Founder** | First-person, opinion-forward, narrative | Thesis, contrarian takes, build-in-public | (personal account) |
| **Product-specific** | Scoped to one product line's audience | Tutorials, use cases, community calls | `@ClawGlasses`, `@puffy_ai` |
| **Technical** | Deeply technical, engineer-to-engineer | Architecture posts, benchmarks, open-source | `@UBSPHONE` |

Same company, same engine, four voices. The engine routes candidate posts to the
right archetype based on content-type classification, not manual assignment.

---

## Architecture

The engine is one process with per-account state. Each account has:

- A voice profile (system prompt, style guidance, banned terms)
- A topic bank (subjects this account is allowed to post about)
- A daily schedule (3 posts/day for Twitter, 2/day for LinkedIn, etc.)
- A safety tier quota (A/B/C share caps)
- An analytics scope (this account's historical performance — classifier inputs)

The orchestration loop:

```
for each account in accounts:
    candidates = generate(account.voice_profile, account.topic_bank)
    scored     = score(candidates, using global classifier + account's history)
    survivors  = gate(scored, account.tier_quota)
    schedule(survivors, account.posting_window)
```

The classifier is global — trained on the union of all accounts' histories. The voice
profiles are local. This is the correct split: classifiers benefit from more data;
personas benefit from strict separation.

---

## Keeping accounts properly independent

If multiple accounts appear to be coordinated, the ranker will penalize them. The
penalty is smaller than a direct negative signal but it compounds — accounts flagged
as coordinated lose ~15% of their reach per month until the flag clears.

Rules we enforce in code:

**Never cross-mention between accounts.** The `@` mention is the clearest coordination
signal available to the ranker. Our content engine treats cross-brand mentions as a
tier-D violation; any generated post that includes another brand's handle is rejected
at the gate.

**Never post identical content across accounts.** Even paraphrasing is risky —
duplicate-detection runs on embedding similarity, and paraphrased content frequently
fails the threshold. Each account generates fresh candidates from its own topic bank.

**Never coordinate reply threads.** If account A posts and accounts B/C/D all reply within
a short window, the reply-graph classifier picks up the coordination signal. We enforce
minimum reply delays of 4+ hours between accounts replying to the same parent, with
strict limits on how often any two accounts appear in the same thread.

**Never overlap posting windows at account-pair level.** Account A posts at 9am; account B
posts at 9:05am with a semantically adjacent topic. This is a coordination signal. Our
scheduler staggers topic-adjacent posts across accounts by at least 90 minutes.

---

## Per-account voice discipline

The single hardest problem in multi-account operation is voice drift. Over 6–12 months,
if the same engine generates content for all accounts, the accounts' voices start to
converge. Readers notice. The ranker notices.

Three mechanisms we use to prevent drift:

### Archetype-locked prompting

Each account has a frozen archetype prompt. It's versioned in git, and changes require
a deliberate review. Prompt drift is the main cause of voice drift; preventing prompt
drift prevents most voice drift.

### Per-account style transfer layer

After generation, each candidate runs through a style-transfer pass specific to that
account — an LLM call with few-shot examples from the account's own best-performing
historical posts. The style-transfer pass enforces the voice.

### Quarterly voice audits

Every quarter, we sample 20 recent posts from each account and ask: "would a long-time
follower of this account recognize this as on-voice?" Posts that fail are logged. If an
account accumulates >2 failures in a quarter, we freeze its topic bank and retrain the
archetype prompt.

---

## Account-level metrics

Each account reports its own metrics into a shared analytics store. At the account
level we track:

- **Followers gained / lost per day**
- **Median impressions per post (rolling 30-day)**
- **Engagement rate (engagements / impressions)**
- **Reply rate from strangers (not own-engine cross-talk)**
- **Profile click rate** — the direct proxy for audience-growth intent
- **Safety-tier share** (A/B/C breakdown of shipped posts)
- **Diversity-decay-adjusted daily reach**

See [METRICS.md](../METRICS.md) for the full internal metric catalog.

---

## Brand isolation: a hard constraint

For our operation (5 consumer brands under one parent company), brand isolation is an
iron rule: **no brand's content ever mentions another brand's name, handle, or
association.** Violation is a tier-D block.

This seems obvious but is hard to enforce at scale. The content engine includes a
pre-publish classifier specifically for cross-brand mention detection. Any candidate
that trips it is rejected without review.

The reason: the ranker treats inter-brand coordination as commercial spam. Our revenue
depends on each brand's independent credibility. We pay a small content-quality cost
(can't leverage one brand's audience to boost another) in exchange for a large
distribution-credibility gain.

---

## When to add a new account

Rules of thumb:

- **Don't add an account until the existing accounts are at the diversity-decay ceiling.**
  An under-utilized account is worse than no account — it trains the ranker that your
  accounts have low engagement.

- **Don't add an account you can't feed with 3+ unique posts per day.** A ghost account
  accumulates negative signals (unfollows, "not interested") faster than it accumulates
  reach.

- **Do add accounts when you discover a new audience segment with distinct vocabulary.**
  If the same message framed for engineers vs. framed for designers has 3× different
  reply rates, that's two audiences, and probably two accounts.

---

## Next

[08 · Cross-platform extension](./08-cross-platform-extension.md).
