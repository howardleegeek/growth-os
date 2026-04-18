# 05 · Negative signal avoidance

> The most expensive mistake in growth engineering is treating negative signals
> symmetrically with positive ones. They are not symmetric. They are asymmetric by two
> orders of magnitude, and most "growth advice" you will read from people who don't
> know this is dangerously wrong.

---

## The math that matters

Twitter's ranker coefficients:

| Signal | Weight | Per unit impact |
| --- | --- | --- |
| Like | +1× | 1 good post = +1 |
| Retweet | +2× | 1 good post = +2 |
| Being replied to | +27× | 1 good post = +27 |
| Author replies to own post | +75× | 1 good post = +75 |
| **Negative feedback** | **−148×** | 1 bad post = **−148 good posts** |
| **Report** | **−738×** | 1 bad post = **−738 good posts** |

One post that gets reported neutralizes 738 good posts. One post that triggers
"not interested" from enough users neutralizes 148.

**This is the single most important fact in content distribution in 2026.** Nothing
else comes close. Every other playbook entry is a 2–3× multiplier. Negative signals
are 100–700× multipliers in the wrong direction.

---

## Why most growth content ignores this

Because the people producing growth content are *survivors*. They publish their wins
and forget their misfires. Nobody writes "I tried a hot take and my account got
demoted for a month and I don't know why." The survival bias means the publicly
visible growth corpus is systematically skewed toward positive-signal optimization.

The data nobody publishes is that most creators who burn out are creators whose
account crossed the negative-signal threshold once and never recovered. The ranker
doesn't forget.

---

## What triggers negative signals

### Hard triggers (auto-penalty regardless of content)

- Links to sites on the platform's internal low-quality list
- Accounts with high report history (transitive penalty on your replies)
- Posts with visible spam patterns (excessive hashtags, repeat posting, @-mention spam)
- AI-generated content below quality thresholds (more on this below)

### Soft triggers (learned from user behavior)

- Content that overclaims ("10× your revenue in 30 days")
- Content that attacks individuals by name (distinct from attacking ideas)
- Content that manufactures outrage without delivering substance
- Content that inverts social norms for shock value without payoff
- Engagement bait that the platform's classifier can identify

### The compounding trigger

When your account starts accumulating negative signals, the ranker shifts the
*thresholds* for your future posts. You go from a ~20% dwell threshold to a ~35%
threshold. Content that would have shipped normally starts getting silently
down-weighted.

**You don't get notified this has happened.** You just notice your median reach
halves and stays halved for weeks.

---

## The safety tier system

Every candidate post in our engine is classified into a safety tier before scoring:

| Tier | Risk | Share cap | Examples |
| --- | --- | --- | --- |
| **A** | Zero | 100% | Educational, data-driven, no opinions on named individuals |
| **B** | Low | 40% | Contrarian on ideas, never on people |
| **C** | Medium | 10% | Controversial-on-ideas, first-person, risk-acknowledged |
| **D** | High | **0%** | Hard block. Never ships. |

The tier caps are enforced at the scheduler layer — not at review time, not at
publish time. If you've already shipped the day's 10% tier-C quota, the 11th
tier-C candidate is rejected regardless of its score.

Implementation: [`engine/signal_weights.py`](../engine/signal_weights.py) (see
`SAFETY_TIER_MAX_SHARE`).

---

## How to train the tier classifier

The simplest working approach: hand-label ~500 posts from your corpus into A/B/C/D,
then train a small classifier (DistilBERT fine-tune works well) on the labeled set.
Recalibrate quarterly.

The labels should capture **what the ranker will penalize**, not what you personally
find tasteful. These are different categories. A post can be perfectly tasteful and
still trip the negative-signal classifier (example: a politically-adjacent take that
users in the audience disagree with and mute you for). A post can feel rough and
still be tier A (example: a technically dense thread that some users find boring but
nobody mutes).

---

## The five most common mistakes

**1. Confusing "controversial" with "tier D."**
Contrarian ideas are tier B. Attacks on named people are tier D. The difference is
whether the post generates `negative_feedback` or just disagreement. Disagreement
pays (+27×). Negative feedback costs (−148×).

**2. Running AI-generated content without human review on tier C.**
LLMs have a failure mode where they generate content that *sounds* smart but crosses
platform safety lines. If you're shipping tier C content, every post gets human review
before the gate.

**3. Treating low reach as "the algorithm is unfair."**
Low reach is almost always a lagging indicator that your account accumulated negative
signals weeks ago. The fix is not more posts; the fix is to ship tier A only for 4–6
weeks to let the negative signals decay.

**4. Deleting low-performing posts.**
Deletions read as a negative signal to the ranker. Low-reach posts should stay published.
Your best outcome is that the ranker updates its posterior on you; deleting prevents that.

**5. Not checking for transitive penalties.**
If your account replies to accounts with poor standing, you inherit some of their
reputation. Check your outbound reply graph quarterly. One bot-adjacent account in your
reply history can cost 10% of your reach.

---

## Recovery when you've already crossed the threshold

It happens. Here's the playbook:

1. **Stop shipping** for 72 hours. Let the negative-signal classifier's recent-window
   buffer age out.
2. **Ship only tier A** for the next 4 weeks. Educational, data-driven, zero named
   opposition.
3. **Track the recovery** — median reach per post week-over-week. You should see
   recovery starting around week 3.
4. **Do not attempt to re-establish "edge"** until you've clocked 4 consecutive weeks
   of recovery. The temptation to go back to tier C early is the most common way
   creators tank their account twice.

---

## The philosophy

Positive signals give you a multiplier. Negative signals give you a divisor. Multipliers
compound over time. Divisors truncate outright.

The winning long-term strategy is not "maximize positive signals." It's "minimize
divisor risk first, then maximize multipliers within the remaining surface." Most
creators get this order wrong and pay for it in opportunities they don't know they're
missing.

---

## Next

Single-account distribution has a ceiling. To scale past it: [06 · Author diversity decay](./06-author-diversity-decay.md).
