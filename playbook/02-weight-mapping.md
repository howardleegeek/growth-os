# 02 · Weight mapping

> Once you've read the source, the next job is to turn the weights into something a
> program can reason about. The output of this step is a scoring function your content
> engine can call before every post ships.

---

## The core data structure

A weight map is just `dict[SignalName, float]`. Keep it flat. Keep it boring.
Keep it readable by someone who has never touched your codebase.

```python
SIGNAL_WEIGHTS = {
    "author_replies_own_post":   75.0,
    "being_replied_to":          27.0,
    "profile_click":             24.0,
    "deep_dwell_over_2min":      20.0,
    "retweet":                    2.0,
    "like":                       1.0,
    "negative_feedback":       -148.0,
    "report":                  -738.0,
}
```

The full reference implementation is in [`engine/signal_weights.py`](../engine/signal_weights.py).

---

## Three properties your weight map must have

### 1. Machine-readable

You will call this dict from the scoring step of every candidate post. Any format that
requires humans in the loop (spreadsheets, Notion, Linear tickets) will rot. A Python
module checked into the repo is the floor — YAML if you need config reload, database
table if you need to hot-update without a deploy.

### 2. Versioned

Platforms change their weights. You will update the map. You need to know, 6 months later,
what the weights were on 2026-02-14 when that campaign performed unexpectedly well.

The simplest pattern: put the weights in git. Commit each change with the source of the
update ("Twitter released v2.3 of the ranker, dwell weight moved from 20 → 22").

If you need to run historical backtests, store each version's weight map as a separate
file (`weights/2026-02-14.py`, `weights/2026-04-10.py`) and reference the one in force
at the time each post shipped.

### 3. Interpretable

Anyone on the team should be able to look at the map and understand *why* a post scored
where it did. That means:

- Name each weight after the thing it measures, not after an internal code ID
- Put the sign of the weight where you can see it (positive = boost, negative = penalty)
- Comment each weight with the source it came from and the last time you verified it

The cost of an interpretable map is ~5 extra minutes when you write it. The benefit is
every future engineer who uses it doesn't have to reverse-engineer your reverse-engineering.

---

## Per-post scoring

The scoring function is a weighted sum of predicted signal probabilities:

```
score(post) = sum over signals of:
              P(signal fires for this post)  ×  WEIGHT[signal]
```

The probabilities come from a classifier. Mine is small: logistic regression on top
of embedding features + a few handcrafted ones (has_image, thread_depth, hook_type).
Sophistication is not the goal. The goal is to replace vibes with numbers.

Full implementation: [`engine/signal_weights.py`](../engine/signal_weights.py) (see
`PostProjection.score()`).

---

## Threshold calibration

Once you can score a post, you need a ship/kill threshold. Mine is `MIN_SHIPPABLE_SCORE = 5.0`.

How I set it:

1. Score every historical post I'd ever published through the new function
2. Bucket by score decile
3. Plot actual impressions vs. score per bucket
4. Find the point where impressions collapse below a usable floor
5. That's the threshold

The threshold is platform-specific and will drift. Recalibrate monthly at minimum.

---

## What to do when the classifier is wrong

You will miss badly at first. The signal probabilities from your classifier will not match
reality for months. That's fine — the scoring function is still useful even with a
biased classifier, because you're comparing *candidates against each other under the
same bias*, not against absolute truth.

Two practical habits:

- **Weekly calibration check:** compare predicted vs. observed rates for each signal.
  If observed is systematically lower/higher, retrain with the delta.
- **Quarterly re-baseline:** re-label a fresh sample of ~500 posts by hand and retrain
  end-to-end. Small classifiers drift fast.

---

## Why this beats intuition-driven content

Three reasons:

**Compositionality.** When the objective is a scoring function, you can reason about
*why* a post scored where it did. Intuition-driven feedback ("this didn't feel right")
isn't debuggable.

**Scale invariance.** The function scales. Intuition doesn't — once you're at 250 posts/week
across 10 accounts you can't personally taste every one.

**Asymmetric penalties surface.** Intuition under-weights negative signals because we
remember our wins more than our flops. A scoring function with −148× in it will kill a
post your gut wanted to ship.

---

## Next

Now we ship: [03 · Self-reply pattern](./03-self-reply-pattern.md).
