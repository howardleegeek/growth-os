# 8-week Fellowship Roadmap

> If accepted into the a16z Growth Engineer Fellowship, here's what I'd ship for the
> cohort and the portfolio companies. Not speculative — this is a concrete commitment.

---

## The thesis

a16z has a portfolio of ~500 companies. A non-trivial fraction of them have serious
distribution problems. Most of them have marketing teams where they should have
autonomous distribution loops. The difference is exactly what `growth-os` encodes.

A "growth engineer" in 2026 isn't a person who runs A/B tests. It's a person who
deploys autonomous agents that run A/B tests at a cadence and verification-rigor
no human team can match. The fellowship is the right environment to operationalize
this at scale: I get access to portfolio founders who have real distribution
problems, real data, and the ability to tell me in 30 minutes whether the loop
transfers to their situation or doesn't.

---

## Deliverables (committed)

By end of week 8, I ship three things:

1. **`growth-os` v1.0** — polished, documented, deployed. This repo, but production-ready
   for adoption by a portfolio company today.
2. **Five portfolio case studies** — the method applied to 5 a16z portfolio companies,
   with before/after distribution metrics where the companies let me publish them.
3. **The Platform Algorithm Reverse-Engineering Toolkit (PARE)** — a companion OSS
   project that lets any founder build their own weight map for any platform in <40 hours.

---

## Week-by-week plan

### Weeks 1–2 · Intake & Portfolio Diagnostic

**Goal:** Understand the distribution state of the portfolio.

- Interview 10 a16z portfolio founders about their distribution bottleneck
- For each: classify the problem (platform-specific vs. audience vs. content vs. ops)
- Synthesize: what are the top 3 categories of distribution pain in the portfolio?
- Deliverable: `portfolio-diagnostic.md` — pattern summary, available to all fellows

Concrete commitments:
- 10 interviews booked by end of week 1
- 10 interviews completed by end of week 2
- Pattern synthesis shared with cohort by end of week 2

### Weeks 3–4 · `growth-os` Hardening

**Goal:** Take `growth-os` from working-at-Oyster-Labs to deployable-anywhere.

- Extract our internal platform adapters into clean OSS adapters
  (Twitter, LinkedIn, Bluesky, TikTok, Reddit)
- Ship a `growth-os init` CLI that scaffolds a new deployment in <5 minutes
- Write the adapter-SDK so a founder can add a new platform in an afternoon
- Open test coverage to 90%+ on the core engine
- Deliverable: `v1.0` release, public npm/PyPI packages, one-command install

### Weeks 5–6 · Deploy to Portfolio Partners

**Goal:** Get `growth-os` actually running inside at least 3 portfolio companies.

- Partner with 3 portfolio companies from weeks 1–2 that have distribution bottlenecks
  `growth-os` is well-suited to solve
- For each, customize the weight map + safety tiers to their platform/audience
- Deploy and run for 2 weeks with weekly check-ins
- Measure before/after: DADR, NSR, PC2C (see [METRICS.md](../METRICS.md))
- Deliverable: 3 deployment case studies with real metrics

### Weeks 7–8 · PARE Toolkit + Cohort Playbook

**Goal:** Turn the one-off approach into something any founder can run on their own.

- Ship **PARE** (Platform Algorithm Reverse-Engineering Toolkit):
  - Step-by-step Jupyter notebook template for reading a new platform's source
  - Weight-extraction helpers (regex patterns, config parsing, coefficient tables)
  - A/B harness templates pre-wired for common platforms
  - Empirical weight-discovery protocols for closed-source platforms
- Ship the **Growth Engineering Cohort Playbook** — everything in this repo's
  `playbook/` directory, refined with feedback from the 10 founder interviews and 3
  portfolio deployments
- Deliverable: PARE repo + polished Cohort Playbook, both MIT-licensed, publicly
  shipped by end of week 8

---

## Why me

Three reasons, in ascending order of relevance:

### I've already done it

The method in this repo isn't speculative. It took my company from $0 to bootstrap-phase revenue
with $0 CAC. The engine is live. The metrics are real. Every claim in this repo is
reproducible from my own production data.

### I can write the code myself

The fellowship's value compounds when the fellow can actually ship. I've shipped 14
products and run a 32-agent AI dev factory that turns decisions into production code in
hours, not weeks. The 8-week timeline is achievable because the bottleneck will not be
implementation speed.

### I'm genuinely trying to open-source this

I don't have a distribution moat I'm protecting. Oyster Labs' moat is our hardware and
our physics-verified sensor data. The content engine is the support infrastructure,
not the product. Putting it in public makes the method available to every founder who
needs it — and that's the right outcome regardless of whether I get the fellowship.

This is a commitment, not a pitch: the contents of this repo will be public whether or
not I'm accepted. The fellowship is the environment that lets me 10× the blast radius.

---

## The honest constraints

- I'm running Oyster Labs full-time. I can commit ~30 hours/week to fellowship work.
  If that's not enough, let's discuss — I'd rather scope to fit than over-promise.
- I'm based in SF. In-person is fine; I'd prefer hybrid if it's an option.
- I will not attach Oyster Labs' name to the fellowship without explicit invitation.
  The work here is personal; the case study numbers are from Oyster but the method
  is independent of the company.

---

## Contact

For fellowship-related questions: [GitHub Issues](https://github.com/howardleegeek/growth-os/issues) or [Discussions](https://github.com/howardleegeek/growth-os/discussions).
