# Architecture

> A full-depth walk through how `growth-os` is structured, why each layer
> exists, and how data flows through it. Written for engineers who want
> to understand the system before touching the code.

---

## 1. Mental model

The system is a **compiler from distribution intent to verified posts**.

Input: a baseline slot configuration + a target account.
Output: a continuous stream of slot mutations that produce real posts
that are mechanically verified to clear a published ranking function.

Between input and output, the system runs six discrete phases in a loop:

```
Intent → Hypothesize → Prescreen → Execute → Measure → Verify → Log → (back to Hypothesize)
```

Every phase has a single responsibility. Every phase can be replaced
independently. The verifier is the one phase that CANNOT be replaced by
an LLM — its job is to be the deterministic adult in the pipeline.

---

## 2. The layered architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       LAYER 5 — ORCHESTRATOR                      │
│                         evo_loop.py                               │
│   Thompson sampling · branch merging · fragility tracking         │
├─────────────────────────────────────────────────────────────────┤
│                       LAYER 4 — HYPOTHESIS                         │
│              hypothesis_generator.py  +  slot.py                  │
│     3 parallel proposers · surface decomposition · mutation       │
├─────────────────────────────────────────────────────────────────┤
│                       LAYER 3 — PRESCREEN                          │
│                    twitter_simulator.py                            │
│       Offline oracle · 0.1ms / sim · keep top 33%                │
├─────────────────────────────────────────────────────────────────┤
│                       LAYER 2 — EXECUTE                            │
│                     content_engine.py                              │
│   Multi-account scheduler · publishing adapters · self-reply      │
├─────────────────────────────────────────────────────────────────┤
│                       LAYER 1 — VERIFY + LOG                       │
│              verifier.py        +       results_log.py            │
│   Mechanical checklist · atomic TSV append · provenance           │
├─────────────────────────────────────────────────────────────────┤
│                       LAYER 0 — SUBSTRATE                          │
│              signal_weights.py    +    ab_tester.py              │
│         Weight map · Thompson bandit · z-test                    │
└─────────────────────────────────────────────────────────────────┘
```

Every upper layer consumes lower layers. No upper layer is consumed by
a lower one — this is a strict one-way dependency graph, which is why
substituting any layer is safe.

### Responsibilities per layer

| Layer | Concern | Key invariants |
| --- | --- | --- |
| 5 Orchestrator | Tree search control flow | No candidate ships without prescreen + verification |
| 4 Hypothesis | What to propose next | Mutations always target exactly one surface |
| 3 Prescreen | Which proposals are worth shipping | Simulator output is deterministic |
| 2 Execute | Actually ship to platform | Every post has a queued self-reply on Twitter |
| 1 Verify + Log | Accept/reject; remember | No iteration accepted without ≥200 impressions + |z|≥1.96 |
| 0 Substrate | Math and data primitives | Weight map is versioned; bandit is stateless |

---

## 3. Data flow through one iteration

Trace of a single tick of the loop:

### Tick 0 — Orchestrator picks a parent

```python
parent_branch = max(active_branches, key=lambda b: b.thompson_sample())
parent_slot   = parent_branch.slot
```

Thompson sampling over the currently active branches. Winning branches
(high kept_count / total_shipped) have higher expected samples and are
picked more often, but the Beta posterior guarantees exploration of
underserved branches.

### Tick 1 — Three parallel proposers propose

```python
proposals = [
    proposer_hook   (parent_slot),
    proposer_thread (parent_slot),
    proposer_timing (parent_slot),
]
```

Each proposer mutates exactly one surface of the parent slot. Surfaces
are enumerated in [`slot.py`](./engine/slot.py):

- `hook` — hook_type, contrarianness, teaser_strength
- `thread` — has_thread, has_self_reply, self_reply_window_sec
- `timing` — timing_window, post_index_today
- `safety` — safety_tier, tone_risk (rarely mutated — fragility 0.9)

### Tick 2 — Offline prescreen

```python
sim_inputs = [slot_to_sim_post(p) for p in proposals]
survivors  = prescreen(sim_inputs, keep_top_frac=1/3)
```

Every proposal runs through `twitter_simulator.simulate()` — a pure
function that scores the slot against the published weight map. Takes
~0.1 ms per evaluation. Only the top 1/3 (1 of 3 here) proceeds to the
real-ship stage.

This is the **biggest cost saver in the system**. Without the prescreen,
every mutation trial costs ~48 hours and one post's worth of real
account exposure. With it, 2/3 of trials get rejected for free.

### Tick 3 — Execute on the real platform

```python
post_id, shipped_at = content_engine.publish(slot)
schedule_self_reply(post_id, slot.self_reply_window_sec)
```

The content engine canonicalizes brand keys, applies safety-tier gates,
assigns the post to a posting slot in the account's daily schedule,
publishes, and queues the self-reply.

### Tick 4 — Measure

```python
metrics = platform_adapter.fetch_metrics(post_id, wait_hours=48)
```

After 48 hours, the adapter pulls impressions / engagement / dwell /
reply composition from the platform API. The wait window is deliberately
long so initial-spike artifacts have settled.

### Tick 5 — Verify

```python
result = verifier.verify(IterationInput(...))
```

The mechanical checklist in [`verifier.py`](./engine/verifier.py):

- [ ] Not duplicate of recent corpus
- [ ] Data is fresh (≤24h old)
- [ ] Sample size ≥ 200 impressions
- [ ] Score vs weight map ≥ ship threshold
- [ ] Safety-tier compliant
- [ ] Lift is statistically significant (|z| ≥ 1.96)

Failure of any check → iteration logged as FAILED. No partial credit.

### Tick 6 — Log + update posteriors

```python
log.append(action="evo_ship", target=slot.slot_id, score=metrics.score,
           result=result.to_tsv_result(), notes=result.note, provenance=git_hash)

if result.passed:
    active_branches.append(Branch(slot=slot, ...))
    maybe_merge(slot, siblings=active_branches)

fragility.update(surface=surface_used, improved=result.passed)
```

Log row appended atomically. If the iteration passed, the slot becomes
a new active branch. If it succeeded AND has a compatible sibling,
branch merging attempts to combine their mutations into a descendant.
Fragility tracker updates per-surface posteriors.

### Tick 7 — Loop

Back to Tick 0. Forever.

---

## 4. Branch merging — the compounding mechanism

Single-branch evolution converges to a local optimum. Branch merging is
what produces combinatorial improvement beyond local optima.

```
BASELINE
   │
   ├── branch A (hook mutation) → KEPT (+22% lift)
   │
   └── branch B (thread mutation) → KEPT (+18% lift)

                ↓  maybe_merge

         MERGED CHILD C
         (inherits hook from A + thread from B)
                ↓ ship + verify
            KEPT (+37% lift)
```

If A and B both independently improve the baseline on different
surfaces, the merged child often improves further because the surfaces
are independent. Empirically ~40% of valid merges pass verification —
which is less than either parent's win rate individually, but the wins
that do pass are larger in expected lift.

Merging is the mechanism by which improvements compound across months
rather than plateauing.

---

## 5. Fragility tracking — risk-weighted exploration

Not all surfaces are equally safe to mutate. `safety_tier` shifting
from A to C is catastrophic (accumulates negative signals at -148×).
Hook type changing from `teardown` to `numbered_breakdown` is benign.

The fragility tracker assigns each surface a rolling probability that
mutations to it produce regressions:

```python
fragility[surface] = EMA(1.0 if regressed else 0.0, alpha=0.1)
```

The orchestrator uses fragility to weight proposal rates:

```python
for surface in SURFACES:
    if fragility[surface] > 0.75 and random.random() < 0.8:
        continue  # skip high-fragility surface most of the time
```

This produces correct behavior: the loop proposes aggressively on
low-fragility surfaces (hook, thread) and cautiously on high-fragility
surfaces (safety). Without this discipline the evolutionary search
would spend most of its budget on mutations that regressed on average.

---

## 6. The log as the asset

`results_log.py` is the least glamorous file in the repo and the most
load-bearing one.

### Why append-only

Rows are never modified. Errors produce new rows that reference the
error. This gives us:

- **Auditability** — any past decision can be reconstructed
- **Reproducibility** — the log is the training set for the hypothesizer
- **Failure recovery** — after a crash, the loop re-reads the log on
  boot and re-derives posteriors from scratch

### Why TSV

Because `grep`, `cut`, `sort`, `awk`, and any text editor work on TSV
out of the box. A 6-month-old TSV on a VPS must still parse. JSON logs
rot; TSV logs don't.

### Why single write()

POSIX guarantees single `write()` calls under 4096 bytes are atomic.
Our rows are well under that limit. No partial rows can be written even
under power failure mid-tick. No advisory locking, no semaphores, no
transaction overhead.

### The TSV schema

```
iteration   timestamp   action     target          score   result      notes      provenance
000412      2026-03-14  ship_test  selfreply_v3    +18.4   kept        ...        abc1234
000413      2026-03-14  ship_test  meme_plug       -24.1   discarded   ...        abc1234
000414      2026-03-14  rederive   weight_map      +0.0    kept        ...        abc1234
000415      2026-03-15  evo_ship   hook:0a1b2c3d   +31.2   kept        ...        abc1235
000416      2026-03-15  evo_merge  8f9e7d6c        +28.1   kept        ...        abc1235
```

`provenance` is the git hash at the time of execution. This ties every
decision to the specific code that made it. If the system misbehaves at
iteration 412, we know exactly which commit was running.

---

## 7. Where LLMs are used, and where they aren't

**LLMs are used in:**

- `hypothesis_generator.propose_next()` → an LLM call instantiates the
  bandit-chosen pattern family into a concrete candidate text
- `content_engine.generate()` → LLM generates the post text and the
  queued self-reply content
- Voice style-transfer pass (post-generation) → LLM rewrites to the
  account's voice profile

**LLMs are NEVER used in:**

- `verifier.py` — any verification call. Ever.
- `twitter_simulator.py` — the oracle. Deterministic math only.
- `results_log.py` — logging. Deterministic writes only.
- `evo_loop.py` — control flow, Thompson sampling, branch merging.
  Deterministic decisions.

This division is non-negotiable. LLMs are creative; they are not
trustworthy arbiters. The creative layers propose; the deterministic
layers decide.

---

## 8. Extensibility points

You want to adapt `growth-os` to your situation. Here's where to
plug in:

### New platform

Implement a `PlatformAdapter`:

```python
class PlatformAdapter(Protocol):
    async def publish(self, post: ScoredPost) -> PublishResult: ...
    async def schedule_reply(self, at: datetime, reply: str) -> None: ...
    async def fetch_metrics(self, post_id: str) -> PostMetrics: ...
```

And write a weight map for the platform. Everything else is reused.

### New hypothesis family

Add a pattern to the `PatternFamily` enum in
[`hypothesis_generator.py`](./engine/hypothesis_generator.py). Add its
archetype prompt. The bandit discovers whether it works over time.

### New prescreen features

Add features to `SimulatedPost` + classifier functions in
[`twitter_simulator.py`](./engine/twitter_simulator.py). Keep them
deterministic and fast.

### New verification check

Add an assertion to `verify()` in
[`verifier.py`](./engine/verifier.py). Err on the side of stricter —
false negatives here are better than false positives.

---

## 9. What's NOT in this repo

Deliberately excluded to keep the reference implementation focused:

- Real Twitter API client (stubbed in the publish() boundary)
- Account authentication / cookie storage
- Browser automation for CDP posting
- Production scheduler daemon
- Observability dashboards
- Multi-brand persona management
- LLM provider routing

These all exist in the production deployment at the source company.
They are out of scope for the OSS reference because they are specific
to one operator's infrastructure and would constrain readers'
adaptation choices.

If you want them: open an issue describing your situation. We'll discuss
whether to upstream generic versions.

---

## 10. Performance characteristics

| Component | Cost per call | Cost per day (1 account) |
| --- | --- | --- |
| Simulator | ~0.1 ms | ~0 (offline) |
| Hypothesis generator | ~1 LLM call, ~$0.005 | ~$0.15 (30 iterations × 1 call) |
| Content engine generate | ~1 LLM call, ~$0.005 | ~$0.05 (10 survivor ships × 1 call) |
| Platform API | 1 GET + 1 POST | ~$0 (Twitter free tier) |
| Verifier | ~0.01 ms | ~0 |
| Log append | ~1 disk syscall | ~0 |
| **Total per account / day** | | **~$0.20** |

At 10 accounts running 24/7, total monthly cost is ~$60 of LLM API
plus ~$5/mo for a VPS. This number has been stable for 14 months.

The cost doesn't scale with iteration count — it scales with
*new content generation*, which is capped by the daily posts-per-account
ceiling. Thompson sampling + prescreening + tree merging are all
effectively free.

---

## 11. Failure modes and mitigations

| Failure mode | Detection | Mitigation |
| --- | --- | --- |
| Loop crashes mid-iteration | Log tail shows partial row | Append-only TSV + O_APPEND = no partial rows |
| Platform API returns stale data | `_data_is_fresh` check in verifier | Force-refresh or skip iteration |
| Thompson sampling stuck on one branch | Weekly branch-diversity audit | Prune branches with <3 iterations of data |
| Negative-signal accumulation | NSR > 0.1% alert | Auto-freeze account, ship Tier A only for 4 weeks |
| Simulator rank correlation drops | Monthly calibration against real outcomes | Retrain classifiers with fresh labels |
| LLM provider outage | Try/except in generator | Fall back to a second provider; skip iteration if both fail |
| Duplicate detection false positive | Manual spot check | Lower trigram Jaccard threshold if it triggers too often |

---

## 12. Why the architecture looks like this

Three principles shaped every decision:

1. **Make verification impossible to skip.** Every path through the
   code hits `verify()` before the log gets a new row.
2. **Make the log the source of truth.** In-memory state is allowed but
   cannot disagree with the log. Cold reboots recover state from disk.
3. **Separate creative from deterministic.** LLMs propose; Python
   decides. Every module belongs to exactly one side of this line.

If you change the architecture, keep these three. If you break them,
the system stops working — not because the code breaks, but because the
guarantees that make the system trustworthy collapse.

---

## 13. Further reading

- [`AUTORESEARCH.md`](./AUTORESEARCH.md) — the protocol
- [`IMPLEMENTATION.md`](./IMPLEMENTATION.md) — the narrative history
- [`playbook/10-evolutionary-twitter-hacking.md`](./playbook/10-evolutionary-twitter-hacking.md) — the methodology
- [`METRICS.md`](./METRICS.md) — the observability surface
- [Twitter's open-sourced ranker](https://github.com/twitter/the-algorithm) — the original weights
- [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — the loop pattern
