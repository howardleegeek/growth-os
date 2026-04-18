# The journey — how Oyster actually grew, in plain English

> Growth 1.0 and Growth 2.0. Two different eras, two different
> playbooks. No mythology. No exaggeration. Just what we did, what
> worked, what didn't, and what we learned.

---

## Growth 1.0 — the traditional phase (pre-December 2025)

This was the bootstrap phase. No vibe coding existed yet. We were a
solo operator with manual tooling and a lot of willingness to show
up every day.

### The core bootstrap mechanic

> **Buy a device, earn an exclusive membership.**

Every device purchase unlocked access to a real, members-only
community of early builders and adjacent founders. The device was
$160. The membership was genuinely useful. Exclusivity was real —
you couldn't join without a device. That single mechanic produced
most of the early revenue and most of the early word-of-mouth.

Customer acquisition cost collapsed toward zero because every
member was, functionally, a sales channel — not because we asked
them to be, but because the community was worth telling their
friends about.

### The tactical work — honest list

These are what "doing growth" actually looked like day-to-day.
Most of them are considered outdated now. They worked at the time.

**RT + Comment tactics.** Typical pre-2025 engagement farming —
retweet, reply, quote-post on adjacent accounts. Basic, not clever,
but when done consistently by a human it produced a surprising
amount of reach. This kind of simple tactic is mostly dead now —
the post-December-2025 algorithm penalizes the pattern more
aggressively. We used it while it was still effective.

**Gifting devices to unlock other people's audiences.** We sent
free devices to people whose audience overlap with ours was high.
They weren't obligated to post about it. Most did anyway because
the device was interesting. A single device to the right person
produced more reach than a month of cold outreach.

**Co-branded editions (联名款).** Limited-edition collaborations
with adjacent brands and personalities. Each collab gave us access
to the partner's audience in a way that felt native, not
promotional. Exclusivity lived in the product again — you couldn't
buy the collab edition after the drop closed.

**Hero narrative.** A protagonist, a mission, a villain, stakes.
Posts contributed to the arc. Followers came back for the next
chapter, not for the algorithm.

**Grok-assisted trend discovery.** We used Grok to scan live X
data and find what was hot in adjacent spaces before the crowd
caught on. Being early on a signal was worth ten being late.

**Manual reverse-engineering of the old algorithm.** Before
December 2025, Twitter's ranker had more exploitable signals than
it does now. We spent months testing by hand, writing weights
down in a spreadsheet, building a manual playbook off it.

**Leverage-point hunting.** Not every engagement is equal. We
looked for network nodes whose amplification was unusually high
relative to follower count — respected-in-the-niche experts
rather than mass-market personalities. Showing up in front of
their audiences as a peer was worth more than most paid
placements.

### What it cost

Growth 1.0 was labor-intensive. Every day. Every piece. No
autonomous layer — the loop ran through a human. It produced
customers. It didn't produce a system someone else could run.

---

## The break — late 2025

Two things happened in roughly the same window:

**Twitter changed its algorithm.** The ranker got rewritten.
Coefficients shifted. Some of the Growth 1.0 techniques degraded
or stopped working. The spreadsheet went stale.

**Vibe coding matured.** The kind of software a solo operator
could ship with AI assistance jumped a notch. What used to require
a small engineering team became buildable in a few weeks by one
person with imagination.

Growth 1.0 stopped being optimal the same quarter that Growth 2.0
became possible.

---

## Growth 2.0 — vibe-coded, ambitious (post-December 2025, ongoing)

Growth 2.0 is what happens when you stop asking "what manual
tactic should I do today" and start asking "what system could I
build that does the tactic continuously, better than I can do it
by hand."

Vibe coding is the enabler. Before it, I would have said no — "I
don't have the engineering bandwidth to build an evolutionary
loop, a simulator, a verifier, a log." After it, a solo operator
can ship that system in weeks. The imagination-to-code gap
collapsed.

### What Growth 2.0 looks like

`growth-os` is Growth 2.0 made concrete. Every component in this
repo exists because Growth 1.0 taught us it mattered, and vibe
coding made it possible to build.

- **The Twitter simulator** exists because we spent months doing
  what it simulates — scoring candidates against the weight map
  by hand. Now it does thousands of trials per second, offline,
  for free.
- **The evolutionary tree search** exists because we learned that
  hill climbing (one-at-a-time) is too slow. Three parallel
  proposers + prescreen + branch merging gives us a hunger game
  where strategies compete and the fittest survive.
- **The mechanical verifier** exists because we learned that
  "looks good to me" is how accounts accumulate silent negative
  signals. A deterministic checklist catches what a tired human
  operator misses.
- **The append-only TSV log** exists because we used to live in
  spreadsheets and they went stale. A log is a durable training
  set and a durable audit trail.
- **The Grok playbook miner** exists because we used to pick
  master accounts to study by intuition, and intuition is noisy.
  Grok scans the live data layer and proposes priors we'd have
  spent weeks deriving.

### The hunger-games framing

The single clearest way to describe Growth 2.0:

> **We built a simulation arena where content strategies play a
> hunger game against each other. The fittest strategy wins —
> and when the algorithm shifts next, a new fittest emerges
> without us needing to notice.**

That's what `growth-os` is, in one sentence.

---

## The honest current state

**What growth-os does today:**

- Encodes the post-December-2025 Twitter weight map
- Runs an evolutionary tree search over content slot mutations
- Prescreens offline via a simulator (cheap, no real ships)
- Verifies real outcomes mechanically (no LLM in the judgment path)
- Logs every decision to an append-only TSV
- Warm-starts from master-account analysis via Grok

**What Growth 1.0 taught it:**

- The weight map shape (we learned it empirically before we encoded it)
- The safety-tier system (we got burned on asymmetric penalties)
- The self-reply window (measured by hand, automated now)
- The pattern families in the hypothesis generator (we knew which
  content shapes worked before we named them)

**What it doesn't yet do as well as Growth 1.0:**

- Hero-narrative continuity across autonomously-generated posts
  (we don't yet have a great representation of a multi-month arc)
- Replicating the exclusive-membership social mechanic (that's
  product + community, not software)
- Peer-to-peer relationship building (deliberately still manual —
  coordination signals get penalized if you automate this)
- Co-branded-drop-level partnerships (these are deal work, not
  algorithmic)

**What's left to perfect:**

- Narrative layer
- Cross-platform evolutionary search (currently Twitter-first)
- Improved Grok-miner accuracy over longer windows
- A clean portfolio-company deployment path

---

## Why I'm open-sourcing Growth 2.0

Three reasons:

1. **The lessons are more valuable than the code.** Reading the
   playbook will teach you the method whether or not you run the
   code.
2. **The code gets better with more eyes on it.** Being public
   catches my blind spots faster.
3. **I don't think distribution infrastructure should be private.**
   Oyster Labs' moat is hardware + sensor data. The content
   infrastructure is support. Keeping it private just slows
   everyone down.

---

## The one-paragraph truth

Growth 1.0 was traditional: we bootstrapped Oyster Labs by building
a useful device, tying its purchase to exclusive-community
membership, gifting it to accounts whose audiences mattered to us,
running co-branded limited editions to unlock partner reach, using
RT-and-comment tactics while they still worked, writing a hero
narrative, and reverse-engineering the pre-December-2025 algorithm
by hand. When Twitter changed its algorithm and vibe coding matured
in late 2025, I built `growth-os` — Growth 2.0 — to encode the
lessons and run them as an evolutionary hunger game inside an
offline simulator. Growth 1.0 was human-driven. Growth 2.0 is
system-driven. They're the same discipline, at different scales,
with different tools.

The journey is the lesson. The code is the attempt to preserve the
lesson through the next algorithm change.
