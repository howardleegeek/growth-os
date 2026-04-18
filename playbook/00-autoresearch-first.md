# 00 · Autoresearch first

> **Read this before anything else in the playbook.** The subsequent chapters
> describe individual patterns, platform-specific weights, and operational
> techniques. This chapter describes the loop those patterns run inside.
> If you skip it, everything else will read as a collection of tactics —
> which is the misreading that produced every failed growth program I've
> ever seen.

---

## The point

`growth-os` is not a tool you use. It is a loop you deploy.

The loop:

```
hypothesize → execute → measure → verify → decide → log → repeat
```

Every single idea in this playbook — self-reply patterns, dwell optimization,
safety tiers, multi-account orchestration, cross-platform extension — exists to
be *fed into that loop*. The patterns are not the product. The loop is the
product. The patterns are what the loop consumes.

If you implement the patterns without the loop, you get a short burst of
results followed by decay. The patterns drift because the platform drifts,
your instincts drift, and without mechanical verification you can't tell
the difference between a real shift and a hallucination of one.

If you implement the loop without the patterns, you get an agent that tests
random variations and slowly discovers the patterns yourself. That works
too — the loop will converge given enough iterations — but you're paying
the opportunity cost of not starting from a weight map that's already
known.

Both together: you get a system that starts smart and gets smarter.
Indefinitely.

---

## The shape of the loop, in more detail

**Hypothesize.** A bandit samples from pattern families (numbered breakdown,
teardown, contrarian, behind-the-scenes, etc.) based on the log's kept/discarded
ratio for each. An LLM call instantiates the sampled family into a concrete
candidate, conditioned on the account's voice profile and a "not duplicate of
last 7 days" constraint.

**Execute.** The candidate runs through the content engine: safety-tier
classification, score computation against the weight map, schedule assignment,
publish, and queued self-reply. Real version across 10 accounts; reference
implementation in [`engine/content_engine.py`](../engine/content_engine.py).

**Measure.** After a fixed wait window (48 hours for Twitter; varies per
platform), the loop pulls metrics: impressions, engagement rate, profile
clicks, dwell, reply composition. The measurement window is chosen to be
long enough that initial-spike artifacts have settled.

**Verify.** The checklist — deterministic Python with no LLM calls:

- Not duplicate of recent corpus (trigram Jaccard < 0.88)
- Metrics fetched within last 24h (data fresh)
- Sample size ≥ 200 impressions
- Score vs. weight map ≥ ship threshold
- Safety-tier quota compliant
- Lift vs. control is statistically distinguishable (|z| ≥ 1.96)

Any failure and the iteration is logged as FAILED. No partial credit. No
"looks promising." The verifier is [`engine/verifier.py`](../engine/verifier.py).

**Decide.** Kept, discarded, or failed. If kept, the candidate's family gets
a success bump in the bandit; future iterations see more candidates of that
family. If discarded, the family gets a failure bump; future iterations see
fewer. The decision rule is a Bayesian update, not a vote.

**Log.** One row appended to an append-only TSV with full provenance: git
hash at time of execution, iteration number, family, score, lift, z-stat,
and reason. Reference: [`engine/results_log.py`](../engine/results_log.py).

**Repeat.** The log is the training set. The next iteration's hypothesizer
reads the log on startup and re-derives posteriors from scratch. Stateless
across process restarts — the log is the truth.

---

## What "mechanical" really means

A verifier is mechanical if it produces the same output for the same input,
deterministically, without any LLM call or human judgment in the path. That
definition excludes almost every "growth analytics" product on the market,
because they all include at least one step where a human or an LLM is
expected to eyeball the result.

The practical consequence: mechanical verification is *binary*. Either a
candidate passes the checklist or it doesn't. There is no "it's probably
okay." Probably-okay posts are the ones that cost you -148× and -738×
negative signals weeks later.

If you only internalize one sentence from this playbook, make it this:
**"probably okay" is the failure mode.**

---

## Why the log is the asset

The log compounds two things:

1. **It's the training set.** Every iteration's outcome feeds back into the
   hypothesizer's posterior. Good families get reinforced; bad families
   get explored around. Over months, the system gets strictly better at
   proposing candidates that will pass the verifier.

2. **It's the audit trail.** Six months from now, when a metric regresses,
   you can grep the log and find the iteration where the regression
   started. You can see exactly which pattern got promoted, under what
   weight map, with what lift, against which control. Intuition can't
   remember that. Logs can.

If you take one implementation shortcut in this entire repo, don't let it
be the log. Everything else is replaceable. The log is the compounding
asset.

---

## Why almost no one runs this

Five reasons, explored more fully in [`AUTORESEARCH.md`](../AUTORESEARCH.md):

1. Surrendering intuition to a loop feels like losing agency, until you
   watch the loop make fewer mistakes than you do.
2. Mechanical verification is binary — most tools cut corners and ship
   vibe checks that look like verification but aren't.
3. The loop needs a real weight map, which requires reading the platform
   source. Most teams don't.
4. Value compounds on time horizon, not user count. Wrong shape for most
   SaaS.
5. Karpathy's framing is 2023-era and hasn't percolated out of ML research
   yet.

The sum of these is why the method is open for anyone willing to do the
operational work. The moat is discipline, not insight.

---

## If you implement only one thing

Start with the verifier. [`engine/verifier.py`](../engine/verifier.py) is
~200 lines. Run it against your last 30 days of shipped content — treat
each post as if it had gone through the loop. See how many would have
passed the checklist. For most teams, the answer is somewhere between 15%
and 40%, which is a direct measure of how much waste is in the current
process.

Then build the log. Then the hypothesizer. Then hand off scheduling to
the loop. In that order. Each step compounds the previous.

---

## How this chapter relates to the rest

The remaining chapters describe specific high-leverage patterns the loop
should know about:

- Chapter 1: how to read the source to build the initial weight map
- Chapter 2: the weight map as a data structure your engine can reason about
- Chapter 3: the self-reply pattern (+75× on Twitter — the biggest single lever)
- Chapter 4: dwell as the most durable positive signal
- Chapter 5: negative-signal avoidance (−148× and −738× asymmetric penalties)
- Chapter 6: author-diversity decay (why 3 posts outperforms 10)
- Chapter 7: scaling horizontally through multiple accounts
- Chapter 8: extending the same engine to other platforms

All of these feed the loop. None of them replace it.

---

## Next

Now that the loop is clear, the first concrete input it needs is a weight
map: [01 · Read the source](./01-read-the-source.md).
