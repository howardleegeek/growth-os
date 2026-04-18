# Contributing to growth-os

Thanks for considering a contribution. This project is young, ambitious, and deliberately
opinionated. The guidance below explains what kinds of changes are most welcome and
what the bar is.

---

## What this project is

`growth-os` is an open-source toolkit for **engineering distribution against published
platform ranking functions**. It encodes the method I used to bootstrap Oyster Labs
from $0 to bootstrap-phase revenue with zero paid acquisition.

The project has three layers:

- `engine/` — runnable Python that scores and schedules content under a weight map
- `playbook/` — the methodology, written down
- `case-studies/` — real deployments with real numbers

Contributions that extend any of these three layers are welcome. Contributions that
expand the scope into unrelated territory (generic social media automation, email
marketing, etc.) will be politely declined — this is not that project.

---

## Highest-value contributions

Ordered by how much they help the community:

### 1. New platform weight maps

The Twitter weight map is here because I read the source. Every other platform needs
the same treatment. If you've done the 40–120 hour read for LinkedIn / Bluesky /
TikTok / Shopify search / anywhere else, and you have a weight map to share:
**please open a PR**. The more platforms we cover, the more useful this project
becomes to everyone.

The bar: your weight map needs to cite sources for every coefficient. Either "this
is in their public source at X" or "I derived this empirically through Y experiment."
Hand-wavy coefficients will be asked for evidence.

### 2. New platform adapters

Adding a new publishing adapter (so the engine can publish to a new platform) is a
self-contained, well-scoped contribution. The adapter interface is documented in
`engine/content_engine.py`. Good adapters come with:
- A real working publish path (not a stub)
- Unit tests against a mock server
- Documentation of any platform-specific quirks (rate limits, content restrictions,
  timing windows)

### 3. Case studies

If you deploy `growth-os` in your own operation and have before/after metrics, a case
study contribution is welcome. Template in `case-studies/00-zero-to-4m.md`.
Publishing your numbers publicly helps every future reader calibrate their expectations.

### 4. Playbook extensions

New patterns, corrections to existing patterns, counter-evidence that disproves a
pattern — all welcome. The playbook is opinionated but not dogmatic; if the data
says something I wrote is wrong, I'd rather update it than be wrong in public.

---

## What doesn't fit

- Generic "AI content generation" frameworks. There are dozens. This isn't one.
- Scheduled-posting tools with no scoring/gating layer. Not in scope.
- Growth-hacking tactics that rely on bot networks, engagement pods, or ToS violations.
  Hard no. This project is about engineering with the platform, not against it.
- Proprietary SaaS integrations that aren't replaceable with an OSS equivalent.
  `growth-os` must remain runnable without paying for third-party services.

---

## Code style

Python:
- Type hints on all public functions
- No external dependencies unless genuinely necessary; current core is stdlib-only
- Modules under 500 LOC; if you need more, split
- Tests for anything in `engine/`; prose changes in `playbook/` don't need tests

Markdown:
- One sentence per line in source files (easier diffs)
- Tables over prose when comparing things
- Link to primary sources whenever possible
- No AI-generated filler

---

## Review philosophy

Reviews optimize for three things in this order:

1. **Correctness.** The method only works if the claims are true. If a PR makes a
   claim I can't verify, I'll ask how you verified it.
2. **Clarity.** This project is read more than it's run. PRs that are hard to read
   will be asked to simplify.
3. **Scope.** Small, well-scoped PRs merge fast. Sprawling refactors take longer
   and require discussion up front.

---

## Governance

Right now: benevolent dictator for life (me). This will change as contributor volume
justifies it. If you're contributing consistently, I'll give you commit rights and
we'll move to a less centralized model.

---

## Contact

Use [GitHub Issues](https://github.com/howardleegeek/growth-os/issues) for bugs, feature requests, or questions. Use [Discussions](https://github.com/howardleegeek/growth-os/discussions) for open-ended conversations.
