# Case Study: why v1 of the content engine shipped zero posts

**Period:** 2026-02-24 → 2026-02-25
**Outcome:** 90 drafts generated, **0 published, 100% wasted**
**Response:** Deleted everything. Rebuilt around mechanical verification.

This is the most important document in this repo. `growth-os` exists because a
previous version of the same system failed so completely and so mechanically
that the only honest response was to tear it down and start over. The
postmortem below is the direct ancestor of every design decision in the
autoresearch loop.

Published here as a commitment to the operator discipline that the rest of the
playbook depends on: **if the data says you failed, the data is right, and
the tool is wrong.**

---

## Data summary

| Metric | Value |
| --- | --- |
| Drafts generated | 90 |
| Drafts published | **0** |
| Hours of operator time to review | ~12 |
| Waste rate | **100%** |
| Immediate action | All 90 drafts deleted |

Every single draft was rejected for at least one of the seven mechanical
problems enumerated below. None of the rejections were "I didn't like the
vibe." All of them were pattern-level failures I could point to in the data.

---

## Error #1 — Brand identity collapse

**The data:**

| Display name | Posts | Problem |
| --- | --- | --- |
| Bruno Moreira | 20 | Bruno is a *persona*, not a brand. LinkedIn-only by design — was shipping to Twitter. |
| ClawGlasses | 12 | Correct |
| Clawglasses | 11 | Case-inconsistent — system thought this was a different brand |
| Oyster Republic (emoji variant) | 11 | Emoji in account name broke string matching |
| Clawphones: Universal... | 10 | Correct |
| Puffy - Solana x OPL... | 9 | Old brand name, not "Puffy AI" |
| Puffy AI | 6 | Correct |
| clawphones | 6 | All-lowercase; different from official |
| Oyster Republic | 5 | No emoji; inconsistent with the other 11 |

**Root cause:** Integration ID → brand-key mapping was not canonicalized. The
same physical brand had 2–3 different string representations in the account
database. The content generator didn't know which brand it was writing for,
so it wrote for a fuzzy union of all of them.

**Lesson encoded in growth-os:** Every publishing adapter must canonicalize
`integration_id → brand_key` at the boundary. Content generation accepts
only canonical brand keys. See [`engine/content_engine.py`](../engine/content_engine.py) `Candidate.brand`.

---

## Error #2 — Topic monoculture

**The data:**

| Topic | Share | Problem |
| --- | --- | --- |
| "on-device vs cloud" | **53%** | More than half the output was the same talking point |
| "Silicon Valley takedown" | 32% | Attacking, no product substance |
| Samsung upcycling | 20% | One news story, used 18 times |
| moonshine/whisper comparison | 10% | One model comparison, used 9 times |

Note the column sums to >100% because posts hit multiple topics — but even
accounting for overlap, the entire output cluster was 3–4 topics on loop.

**Root cause:** The memory system deduped adjacent posts but didn't enforce
*pillar rotation*. Trending signals (HN + RSS) returned same-topic AI news,
and the LLM had no counterweight forcing it to draw from other pillars.

**Lesson encoded in growth-os:** Content pillars are a mandatory input with
enforced percentages. The hypothesis generator's bandit runs over **pattern
families** precisely because a bandit that has been reading "numbered
breakdown got kept 7 times this week" will actively propose teardowns,
contrarians, and behind-the-scenes posts to diversify. See
[`engine/hypothesis_generator.py`](../engine/hypothesis_generator.py).

---

## Error #3 — Voice drift into degen register

**The data:**

| Phrase | Occurrences in 90 drafts |
| --- | --- |
| "larp" | 5 |
| "cope" | 3 |
| "rugged" | 3 |
| "midwit" | 2 |
| "brain rot" | 2 |
| "cooked" | 1 |

**Root cause:** The brand voice description used adjectives like "cynical,"
"degen-flavored," and "terse." The LLM over-interpreted these as permission
to write in the register of Crypto-Twitter-at-3am. That register is a
tier-C to tier-D safety risk depending on the audience — on LinkedIn it's
tier-D full-stop, which is why Bruno's 20 drafts were categorically
unpublishable.

**Lesson encoded in growth-os:** Voice profiles carry **sample voice
examples** in addition to adjectives. LLMs learn voice from 3 concrete
examples faster than from 10 adjectives. The style-transfer pass that runs
after generation enforces the voice using the samples, not the description.

---

## Error #4 — Zero engagement hooks

**The data:**

| Feature | Share | Implication |
| --- | --- | --- |
| No question mark | 66% | Twitter rewards `being_replied_to` at +27×, but 2/3 of drafts didn't invite replies |
| No links | **100%** | Not one draft had a destination |
| No hashtags | **100%** | Not one draft had a platform-retrieval hook |

**Root cause:** The generator prompt had no hard constraint requiring each
post to carry at least one engagement hook. The brand frameworks listed
"voice" extensively and "platform mechanics" not at all.

**Lesson encoded in growth-os:** Every pattern family in the hypothesis
generator includes a minimum-engagement-hook clause as part of its
archetype. The verifier additionally checks that shipped content hits the
hook — a post without a hook scores low on the weight map and fails the
ship threshold. See [`engine/verifier.py`](../engine/verifier.py).

---

## Error #5 — Near-duplicate content across accounts

**The data:** 5 clusters of near-identical posts, where the same seed idea
was sent to different brand accounts with only cosmetic variation.

**Root cause:** The generator shared a single seed-idea pool across all
brands, then "branded" each output with cosmetic changes (different @-handle,
minor wording). The algorithm's coordination-signal classifier picks this up
instantly, and it flags the accounts as a coordinated cluster — which is a
slow-burn penalty the content team can't see until reach silently halves
weeks later.

**Lesson encoded in growth-os:** Each brand account must generate its own
candidates from its own topic bank. No seed sharing. The verifier runs a
deduplication check against the last 200 posts on the account (trigram
Jaccard at 0.88 threshold). See
[`engine/verifier.py#_not_duplicate`](../engine/verifier.py).

---

## Error #6 — Analytics feedback never actually fed back

**The data:** The analytics pipeline ran daily and wrote performance data to
memory via `memory.save_performance_feedback()`. The generator never called
`memory.get_performance_feedback()`. The loop was open. 14 days of feedback
data sat there untouched.

**Root cause:** A code bug nobody caught because nothing broke visibly.
`save` worked; nothing read. The system produced a convincing dashboard of
"feedback captured" while the generator continued generating blind.

**Lesson encoded in growth-os:** **Every save must have a corresponding read.**
If you store data the loop never consumes, the data is dead weight and the
loop is blind. The autoresearch loop's TSV log is deliberately the
single-source-of-truth — the hypothesis generator *always* reads it on
boot, re-derives posteriors from the entire history, and uses them to
propose the next iteration. No way for feedback to silently stop feeding
back.

---

## Error #7 — Capability audit was last done never

**The data:**

| Tool built | Capability | Actual usage |
| --- | --- | --- |
| Cross-brand shoutout | Implemented | **Never called** |
| AI image gen (300/mo quota) | Available | 4/day, low quality |
| Video gen via Postiz MCP (30/mo) | Available | **0%** |
| Engagement farmer | Complete interaction system | Disabled |
| Postiz Agent structured multi-step | Available | Not integrated |

**Root cause:** Features got shipped and then forgotten. The team treated
"the feature exists" as "the feature is being used," which it wasn't. Some
of the unused tools would have moved the needle immediately.

**Lesson encoded in growth-os:** Every sprint includes a 10-minute
**capability audit** — list tools built in the last 90 days, check
call-count from the log. Zero-call-count tools are either deleted or
explicitly flagged as deprecated. The goal is to never ship dead code into
the content path, because dead code is the longest-running tax in any
growth system.

---

## Ironclad rules that emerged

These six rules came out of the postmortem. They are load-bearing to every
piece of code in this repo:

1. **Brand frameworks are the foundation of content quality.** Incomplete
   framework → LLM invents → 100% waste. Section 7 ("Platform Rules") of
   the brand framework is non-optional.
2. **Sample voice beats adjective voice.** 3 concrete examples > 10 lines
   of descriptive prose.
3. **Every post must carry at least one engagement hook.** No question, no
   link, no hashtag = dead post. Verifier enforces.
4. **Content pillars have enforced percentages.** Otherwise one topic
   swallows the calendar (see 53% on-device-vs-cloud).
5. **Every save must have a read.** Closed-loop check. Dead data is a
   silent killer.
6. **Capability audit every sprint.** Tool existing ≠ tool used.

---

## Why this postmortem matters for the design of growth-os

Read this page from end to beginning and you'll see the autoresearch loop
emerge by necessity:

- "Every save must have a read" → **the log is the only source of truth**
- "Content pillars have enforced percentages" → **the bandit over pattern families**
- "Every post must carry an engagement hook" → **the scoring gate**
- "Capability audit every sprint" → **the tail-of-log check**
- "Sample voice beats adjective voice" → **voice profile samples, not descriptions**
- "Brand frameworks are the foundation" → **canonical brand keys at the API boundary**

None of these are inventions. All of them are corrections of specific
mechanical failures that produced 90 unpublished drafts in 48 hours. The
architecture exists because the alternative — vibes — was measured, quantified,
and found catastrophic.

---

## The honest operator discipline

When a growth system fails, there are two postures:

- **Apology posture.** "The AI misbehaved. We'll fine-tune the prompt."
  Outcome: same failure in a slightly different shape next month.
- **Postmortem posture.** "The loop had these seven mechanical defects.
  Here's what we enforce now so each one is structurally impossible."
  Outcome: a system that gets strictly better each iteration.

Autoresearch only works if you commit to postmortem posture. Apology
posture is why most growth teams plateau — the errors keep happening
because the team keeps pardoning them rather than logging them.

This case study is the evidence that I do postmortem posture. The ongoing
TSV log is the evidence that the system does too.
