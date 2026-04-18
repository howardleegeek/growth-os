# Case Study: teardown of 4 Physical AI funding announcements

> One of the most valuable outputs of the autoresearch loop is **competitor
> teardown** — running the same mechanical analysis on other companies'
> distribution playbooks that we run on our own. This file documents the
> teardown of 4 physical-AI companies' funding-announcement distribution
> strategies. Patterns identified here directly informed the weight
> map and pattern families in `growth-os`.

---

## 1. Memories.ai — $16M, August 2025

### The distribution stack

| Layer | What they did |
| --- | --- |
| **Founder account primary** | Shawn Shen (@shawnshenjx) posted the launch tweet from his personal account |
| **Company account amplifies** | @memories_ai reposted + extended with product shots |
| **Third-party endorsement** | Law firm (Wilson Sonsini), angel investors, AI media bloggers all independently retweeted |
| **Tagline** | "Unlimited visual recall is here, and it fits in your pocket." |
| **Mechanic** | "World's first LVMM" (Large Visual Memory Model) — rarity claim |
| **Secondary PR** | TechCrunch same day + Seedcamp blog + NVIDIA partnership at GTC 2026 |
| **Self-propagating PR** | Bounty program announcement ($2M) — *hiring as PR* |

### What the algorithm rewards about this

- **Founder-first = +75× self-reply multiplier on founder's account** (founder's personal engagement gets rewarded more than company-account engagement)
- **"World's first X"** framing maximizes `being_replied_to` (+27×) because it invites challenge
- **Visible endorsement chain** raises TweepCred on the root post — PageRank effect
- **Hiring bounty** produces content that competitors' own fans must engage with (extending reach outside the founder's first-degree network)

### Pattern imported into growth-os

A pattern family named `rarity_claim` was added to the hypothesis generator
after this teardown. Archetype: "Concrete claim of being first at something
specific, supported by credential from authoritative source." The family's
early-iteration kept-rate was 52%, well above the engine-average.

---

## 2. Rerun — $20.2M, March 2025

### The distribution stack

| Layer | What they did |
| --- | --- |
| **Technical-depth blog same-day as funding** | Not a PR piece — an actual technical analysis |
| **Framing** | "The Missing Data Infrastructure for Physical AI" |
| **Evidence stack** | Visible user list: Meta, Google, Hugging Face LeRobot, Unitree |
| **Angel network** | Guillermo Rauch (Vercel), Wes McKinney (pandas), Eric Jang (robotics) — each brings built-in KOL reach |
| **Open-source first** | The commercial wrapper was secondary; the OSS product was the leader |

### What the algorithm rewards about this

- **Deep-dwell content** (technical blog) clears the +20× dwell weight for everyone who clicks through from the announcement tweet
- **Angel investor profiles** have pre-existing high TweepCred — their retweets propagate through networks the Rerun team doesn't reach directly
- **OSS-first** sidesteps the `negative_feedback` penalty that promotional PR-heavy announcements incur

### Pattern imported into growth-os

A pattern family named `technical_teardown` was added — "here is the
specific technical gap and here is the specific technical analysis of our
approach." This family's kept-rate is lower than rarity_claim (38%) but
its PC2C (profile-click-to-conversion) is 3.1× higher because it attracts
engineers who convert to users.

---

## 3. Physical Intelligence (π) — $1.1B, ongoing rounds

### The distribution stack

| Layer | What they did |
| --- | --- |
| **Minimalism** | Website is one sentence of mission + research list + team + investors. No marketing fluff. |
| **Research as PR** | Every major update is a paper drop with demo video — not a press release |
| **Investor logo wall** | Bond, Bezos, Khosla, Lux, OpenAI, Sequoia, CapitalG, Thrive — logos alone are the credential |
| **Team as credential** | 65+ people, all listed with photos. "Look at who we convinced to join." |
| **Release cadence** | π0.5 → π0.6 → Multi-Scale Embodied Memory, spaced ~4 months apart |

### What the algorithm rewards about this

- **Research drops are deeply dwell-positive** — papers are inherently >2min content
- **The release cadence creates a Schelling point** — every 4 months the ecosystem knows to expect π news, which means engagement velocity is pre-loaded
- **Investor logo wall operates as a trust classifier** — users' implicit filter for "should I take this seriously" is shortcut

### Pattern imported into growth-os

A **cadence primitive** was added to the scheduler. Instead of posting
uniformly, the engine now supports predictable cadence patterns (e.g.,
"every Tuesday at 9am PT, a technical deep-dive"). Cadence-delivered
content has shown +18% higher dwell than uniform-scheduled content.

---

## 4. General Intuition — $134M seed, October 2025

### The distribution stack

| Layer | What they did |
| --- | --- |
| **Contrarian thesis** | "True AGI requires something LLMs fundamentally lack" — directly challenges the dominant paradigm |
| **Data-moat narrative** | "2 billion videos/year from 10 million MAU across tens of thousands of games" — specific numbers as evidence |
| **Gaming-to-real-world path** | Low-risk, data-rich starting domain → general agent |
| **Dual-lead VC** | Khosla + General Catalyst — the investor combination itself is a narrative beat |

### What the algorithm rewards about this

- **Contrarian premises** are the highest reply-inducing content class — direct multiplier on +27× weight
- **Specific numeric moats** beat vague claims on engagement and profile-click
- **Multi-investor narratives** trigger coverage across VC Twitter, which is a distinct audience cluster

### Pattern imported into growth-os

A pattern family named `contrarian_premise` already existed (from our own
postmortem analysis), but the numeric-moat element was added as a
sub-pattern: every contrarian post must carry at least one concrete number
with a citation. Posts of this shape have a kept-rate of 61% — the highest
of any family.

---

## The meta-lesson

These four companies didn't hire better growth agencies. They ran better
loops:

- Memories.ai ran a **founder-first amplification loop** with mechanical
  cadence tied to VC relationships
- Rerun ran a **technical-dwell-as-distribution loop** with pre-placed
  angel endorsement
- Physical Intelligence runs a **research-as-distribution loop** with
  4-month rhythm
- General Intuition ran a **contrarian-claim-with-specific-moat loop**
  timed to funding events

Each is a different application of the same underlying pattern: **encode
the distribution function, optimize the content to hit it, and make the
cadence predictable enough that the platform's recency classifier treats
you as a known entity.**

The teardowns above are what an autoresearch loop looks like when you point
it at *someone else's* distribution instead of your own. The same method.
The same scoring gate. The same log. Just a different target account.

---

## Recommended adaptation for teams reading this

If you're applying `growth-os` at your own company, run this exact
teardown on 3–5 of your competitors before you point the loop at yourself.
Treat their distribution as ground-truth examples and use them to
calibrate your weight map.

Specifically:
1. Pick 3 competitors whose distribution is clearly outperforming yours
2. For each, catalog the last 6 months of major announcements
3. For each announcement, tag the pattern family (rarity_claim, technical_teardown, contrarian_premise, etc.)
4. Measure the observed lift vs. their baseline
5. Weight your hypothesis generator's bandit priors based on what's worked for them

This gives the loop a warm start instead of 2–3 months of random
exploration.

---

## Citation trail

Original teardowns were generated by the autoresearch loop on 2026-03-18
with a competitor-analysis preset. Source links preserved for reproducibility:

- [Memories.ai homepage](https://memories.ai)
- [Memories.ai Seedcamp announcement](https://seedcamp.com/views/memories-ai-raises-8m-to-build-human-like-memory-for-ai/)
- [Rerun physical-AI data blog](https://rerun.io/blog/physical-ai-data)
- [Rerun TechCrunch coverage](https://techcrunch.com/2025/03/20/reruns-open-source-ai-platform-for-robots-drones-and-cars-revs-up-with-17m-seed/)
- [Physical Intelligence website](https://www.pi.website/)
- [General Intuition TechCrunch coverage](https://techcrunch.com/2025/10/16/general-intuition-lands-134m-seed-to-teach-agents-spatial-reasoning-using-video-game-clips/)
