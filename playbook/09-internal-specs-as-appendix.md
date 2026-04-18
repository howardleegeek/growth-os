# 09 · Internal specs — how we actually build each component

> Appendix. The previous eight chapters describe the method. This chapter
> documents the internal engineering specs we used to build the system at
> Oyster Labs — what got broken down into tickets, what the acceptance
> criteria were, and in what order the work shipped. Published for anyone
> who wants to see how the method translates into actual engineering work.

---

## Why these specs are in the repo

Most "playbooks" online stop at the methodology and let readers figure out
the engineering. That gap is where 80% of failed implementations die — not
because the method is wrong, but because the engineering under the method
is harder than it looks.

The specs below are the real ones. They shipped. They produced the
infrastructure that ran Oyster Labs from $0 → $4M. Published in condensed
form (acceptance criteria only) so you can use them as a checklist when
you build your own version.

---

## Spec summary (17 internal tickets)

| ID | Spec | What it ships | Priority |
| --- | --- | --- | --- |
| S01 | Postiz publisher | Multi-platform publishing adapter | P0 |
| S02 | Trending signals | HN / RSS / Twitter trend ingestion | P0 |
| S03 | A/B hook variants | Bandit over hook patterns | P0 |
| S04 | Analytics feedback | Closed feedback loop to generator | P0 |
| S05 | Bluesky connector | AT-protocol adapter | P1 |
| S06 | Engagement-farmer reform | Reply-bot within ToS limits | P1 |
| S07 | Twitter algorithm optimization | Weight map integration | **P0 — core** |
| S08 | STP (segmentation/targeting/positioning) engine | Per-audience content | P1 |
| S09 | Daily content pipeline | End-to-end daily loop | P0 |
| S10 | Multi-brand ideation | Per-brand seed-idea isolation | P0 |
| S11 | LLM router | Cost-aware model selection | P1 |
| S12 | Cross-account synergy | Coordination-signal avoidance | P1 |
| S13 | Self-thread expansion | 75× self-reply automation | **P0 — core** |
| S14 | Content quality polish | Style-transfer pass | P1 |
| S15 | LinkedIn volume boost | LinkedIn-specific optimization | P1 |
| S16 | Farcaster integration | New-platform expansion | P2 |
| S18 | Analytics agent control | Agent-driven metric monitoring | P1 |

The starred specs (S07, S13) are the ones most directly load-bearing to
the $4M outcome. Everything else is supporting infrastructure.

---

## Spec template we use

Every ticket follows this shape:

```markdown
---
task_id: SXX-short-slug
project: content-engine
priority: 1
estimated_minutes: 45
depends_on: [S01, S02]
modifies: ["path/to/file.py", "path/to/other.py"]
executor: glm | minimax | codex | claude
---

## Goal
[One sentence — what this ships]

## Background
[Context, including references to playbook chapters and external sources]

## Changes
### 1. FileName.py: subsection name
- Add ...
- Modify ...

### 2. OtherFile.py: subsection name
- Add ...

## Acceptance criteria
- [ ] Specific measurable outcome 1
- [ ] Specific measurable outcome 2
- [ ] pytest path/to/test.py passes

## Do not
- [Explicit list of what NOT to change]
```

This template matters because it forces every change to pre-commit to a
**measurable acceptance criterion**. No "I'll know it when I see it."
Combined with mechanical verification in the runtime, this is what keeps
the system self-correcting.

---

## S07 — Twitter algorithm optimization (the most important spec)

The core spec that encoded the weight map from
[github.com/twitter/the-algorithm](https://github.com/twitter/the-algorithm)
into the content engine. Condensed:

**Goal:** write Twitter's open-source ranking weights into the content
generator, so every candidate post is scored against the published
objective function before shipping.

**Core weight table shipped in this spec:**

| Interaction | Weight (absolute) | Weight (relative to like) |
| --- | --- | --- |
| Author reply to own post | **+75.0** | **150×** |
| Being replied to | +13.5 | 27× |
| Profile click | +12.0 | 24× |
| Good click (conversation + save/reply) | +11.0 | 22× |
| Good click v2 (conversation + dwell >2min) | +10.0 | 20× |
| Retweet | +1.0 | 2× |
| Like | +0.5 | 1× |
| Negative feedback | **−74.0** | **−148×** |
| Report | **−369.0** | **−738×** |

**Author diversity decay:** 2nd post of the day = 62.5% weight, 3rd = 43.75%,
floor = 25%. Implication: 3 high-quality posts > 10 mediocre. (See
[playbook chapter 6](./06-author-diversity-decay.md).)

**TweepCred:** PageRank-based author reputation score, 0–100. High-following /
low-followers ratio is penalized. Interactions with high-TweepCred accounts
boost your score.

**Changes shipped:**
1. `ideator.py` — added `ALGORITHM_WEIGHTS` constant and
   `generate_seed_idea(optimize_for_algorithm=True)` parameter
2. `ideator.py` — added `optimal_posting_schedule()` with enforced 3-hour
   minimum gap and mandatory self-reply queuing within 30 minutes
3. `platform_adapters.py` — XAdapter `adapt()` accepts `algorithm_hooks`
   parameter, enforces self-reply + dwell hook + reply-inducing hook

**Acceptance criteria:**
- [ ] Every generated post scored against weight map before publish
- [ ] Self-reply automatically queued for every main post
- [ ] Posts per account per day capped at 3
- [ ] `pytest tests/test_algorithm_scoring.py` passes
- [ ] Empirical median reach per post increases ≥50% within 14 days

The full spec file and its companions live in our internal repo. The
pieces generalizable beyond Oyster Labs have been ported into
[`engine/signal_weights.py`](../engine/signal_weights.py) in this repo.

---

## S13 — Self-thread expansion (the second most important spec)

**Goal:** make self-reply a first-class primitive in the content engine so
it cannot be accidentally skipped.

**Background:** Self-reply at +75× is the largest single lever in the
entire Twitter weight map. Manual implementation drifts — operators forget,
vacations happen, accounts go silent. The only way to realize the +75×
consistently is to make the engine incapable of shipping a main post
without a queued self-reply.

**Changes shipped:**
1. `Candidate` dataclass — added `thread_continuation: str | None` field;
   ideator is *required* to produce this alongside every main post
2. Scheduler — fires `publish_reply(reply_to=main_post_id, text=continuation)`
   at `main_post.shipped_at + timedelta(minutes=2, seconds=45)`
3. Verifier — rejects any candidate with `thread_continuation is None` on
   Twitter platform
4. Analytics — explicit column `self_reply_landed: bool`; alerts if <95% of
   daily posts have landed self-replies

**Acceptance criteria:**
- [ ] 100% of Twitter posts from the engine have a self-reply queued
- [ ] ≥95% of queued self-replies actually land within 2:45–3:15 min window
- [ ] Analytics dashboard shows median post impressions ≥ +150% after full
      rollout

The reference implementation of this pattern in this repo is in
[`engine/content_engine.py`](../engine/content_engine.py) — see the `publish()`
function.

---

## The specs we haven't published

Specs S01–S06 and S08–S16 are either:
- Tightly coupled to Oyster-specific infrastructure (Postiz, our DB schema,
  our auth) — not portable; or
- Operational rather than methodological (LLM router cost accounting,
  Bluesky rate-limit handling) — useful but specific

The universal parts of each have been ported into the relevant code
modules and playbook chapters. The full specs exist in our internal repo.
If you're a serious adopter, reach out — happy to share the specs that
would be most useful to your implementation.

---

## What to do with this as a reader

Three options:

1. **Use the template** — adapt the spec structure to your own engineering
   process. The "acceptance criteria with mechanical test" section is the
   most important part.
2. **Copy the acceptance patterns** — especially for S07 and S13, which are
   load-bearing for Twitter.
3. **Build your own S07-equivalent for your platform** — the most
   important application of this chapter is: don't skip the step where
   you encode the platform's weight map into a spec with testable
   acceptance criteria.

The specs aren't philosophy. They're the engineering under the philosophy.
If you skip this layer, the philosophy won't compile.
