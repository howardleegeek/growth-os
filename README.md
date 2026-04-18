# growth-os

> **Most founders pay for distribution. I read the source code of it.**

Twitter open-sourced their ranking algorithm in 2023. 10,000+ lines of Scala, Python, and protobuf. I'm probably one of 50 people on earth who actually read all of it.

Then I built a system around it.

---

## The result

| Metric | Value |
| --- | --- |
| Revenue | **$0 → $4M** |
| Devices sold | 25,000+ |
| Paid acquisition | **$0** |
| CAC | **$0** |
| Channels | 10 automated |
| Posts / week | 250+ |
| Founders | 1 (me) |
| Marketers | 0 |

No growth hacking. No agencies. No SEO tricks. Just engineering against an objective function the platform publishes for free — and nobody reads.

---

## What this repo is

`growth-os` is the open-source toolkit I use to reverse-engineer distribution platforms and turn them into programmatic channels.

It's not a content calendar. It's not a CRM. It's **distribution infrastructure**.

```
growth-os/
├── engine/            # The Python system that ran my $4M GTM
│   ├── signal_weights.py      # Twitter algorithm weight map
│   ├── content_engine.py      # Core scheduling + posting loop
│   ├── ab_tester.py           # Variation harness (2,000+ tests)
│   └── metrics.py             # Attribution + ROAS tracking
├── playbook/          # The methodology, written down
│   ├── 01-read-the-source.md
│   ├── 02-weight-mapping.md
│   ├── 03-self-reply-pattern.md
│   ├── 04-dwell-optimization.md
│   └── 05-negative-signal-avoidance.md
├── case-studies/      # How I used it
│   └── 00-zero-to-4m.md
├── demos/             # Interactive — open in browser
│   └── signal-weight-explorer.html
└── fellowship/        # What I'd build in 8 weeks at a16z
    └── roadmap.md
```

---

## Core thesis

> **Distribution is an engineering problem, not a marketing one.**

Most "growth" work treats platforms as black boxes. Test copy. A/B headlines. Pray for the algorithm.

That's witchcraft, not engineering.

Every modern platform — Twitter, LinkedIn, TikTok, Shopify search, Amazon, YouTube — is an **optimization function with known or discoverable weights**. Read the weights, align with them, and distribution becomes deterministic.

This repo is what that looks like when you take it seriously.

---

## The 4 signal weights that changed everything

From Twitter's open-source algorithm ([github.com/twitter/the-algorithm](https://github.com/twitter/the-algorithm)):

| Signal | Weight | What I did |
| --- | --- | --- |
| Author replies to own post | **75×** | Every post gets an auto self-reply in <3min |
| Being replied to | **27×** | Optimized for reply-inducing hooks (questions, contrarian) |
| Profile click | **24×** | Teaser language, bio as landing page |
| Deep dwell (>2min) | **20×** | Long-form threads, never single tweets for key content |
| Retweet | 2× | Not optimized for |
| Like | 1× | Baseline |
| Negative feedback | **−148×** | Content safety tier system, never risk >5% surface |
| Report | **−738×** | Hard block list of pattern classes |

**One post with a "report" signal = -738 good posts neutralized.** That asymmetry is the thing 99% of growth marketers never account for.

---

## Why this matters for a16z

This playbook isn't Twitter-specific. It's a **method**:

1. Find platforms whose algorithms are either open-source or discoverable via observation
2. Map the weights through systematic A/B testing
3. Encode the weights into a content engine
4. Optimize against the objective function, not against your taste

Platforms this is being extended to next:
- **LinkedIn** (dwell-time dominant, different reply mechanics)
- **TikTok** (engagement velocity, first-hour signals)
- **Shopify / Amazon** (conversion-weighted search)
- **App Store** (review velocity, uninstall penalties)

Every a16z portfolio company with distribution is leaving money on the table because they have a marketing team where they should have a growth engineering team.

---

## Applying to a16z Growth Engineer Fellowship

I'm applying to this fellowship to:

1. Open-source `growth-os` with the cohort
2. Interview 5 a16z portfolio founders about their distribution bottlenecks
3. Build a "Platform Algorithm Reverse-Engineering Toolkit" as the cohort artifact
4. Deploy it to 1 portfolio company and measure lift

See [`fellowship/roadmap.md`](./fellowship/roadmap.md) for the 8-week plan.

---

## About the operator

**Howard Jiacheng Li** — CEO & Growth Engineer @ Oysterworld INC

- Bootstrapped Oyster Labs from $0 → $4M revenue / 25K devices / zero paid ads
- Previously co-founded **MPCVault** (digital asset custody, $5B AUM)
- Wharton MBA, UC Berkeley Haas
- SF-based, running a 32-agent AI factory that ships like a team of 50

[github.com/howardleegeek](https://github.com/howardleegeek) · [linkedin.com/in/connecthoward](https://www.linkedin.com/in/connecthoward/) · howard.linra@gmail.com

---

## License

MIT — take it, extend it, deploy it. If you ship it at scale, DM me.
