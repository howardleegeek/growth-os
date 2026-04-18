# clawmarketing

> **The production content engine that ran Oyster Labs from bootstrap phase in revenue with $0 paid acquisition.**
>
> This is the actual Python that ships posts. For the methodology and
> evolutionary architecture on top of it, see
> **[github.com/howardleegeek/growth-os](https://github.com/howardleegeek/growth-os)**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Revenue bootstrapped](https://img.shields.io/badge/bootstrapped-%240%20%E2%86%92%20%244M-success.svg)](https://github.com/howardleegeek/growth-os/blob/main/case-studies/00-zero-to-4m.md)
[![No paid ads](https://img.shields.io/badge/paid%20acquisition-%240-blue.svg)](https://github.com/howardleegeek/growth-os/blob/main/case-studies/00-zero-to-4m.md)

---

## What this is

The runtime that reads brand briefs, generates algorithm-optimized
content, scores it against the published Twitter ranking weights, and
publishes to multiple channels (X, Bluesky, LinkedIn).

This is the production code. Not a demo. Not a tutorial. Not a
simplified teaching version.

---

## What it produced

- **bootstrap phase** in revenue at Oyster Labs
- **$0** paid acquisition, 100% organic
- **25,000+** devices sold
- **10 channels** automated (4 X + 4 Bluesky + 2 LinkedIn)
- **~37 posts/day**, ~259/week
- **extended continuous operation** of continuous operation
- **~$20/mo** operating cost (LLM API + VPS)

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                                                              │
│  SIGNALS ──▶ IDEATOR ──▶ SCORER ──▶ STRUCTURER ──▶ ADAPTER │
│     │           │           │           │            │      │
│     │           ▼           ▼           ▼            ▼      │
│  trending.py  ideator.py  content_   post_       platform_ │
│  signal_      campaign_   scorer.py  structures  adapters  │
│  ingestor.py  generator.py                                  │
│                                                              │
│                                         ▼                    │
│                                     PUBLISHERS               │
│                                         │                    │
│                                   ┌─────┼─────┬───────┐     │
│                                   ▼     ▼     ▼       ▼     │
│                                  x_api postiz linkedin n8n  │
│                                                              │
│                               ANALYTICS ◀─── MEMORY          │
│                               analytics.py   memory.py       │
│                                     │           ▲            │
│                                     └─── REFLECTION ─────────┘
│                                          reflection_agent.py │
│                                          reflections.py      │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

Every module has one responsibility. Total: ~5,000 LOC of Python.

---

## Layout

```
clawmarketing/
├── engine/                     ← Core generation + scoring (~3,700 LOC)
│   ├── ideator.py              ← Proposes seed ideas conditioned on brand + signals
│   ├── content_scorer.py       ← Scores candidates against Twitter weight map
│   ├── post_structures.py      ← Templates: numbered, teardown, contrarian, ...
│   ├── llm.py                  ← Multi-provider router (Z.AI, Grok, MiniMax, OpenAI)
│   ├── analytics.py            ← Daily metrics pipeline
│   ├── memory.py               ← Narrative memory — dedup + pillar rotation
│   ├── reflection_agent.py     ← Post-campaign reflection loop
│   ├── reflections.py          ← Reflection-driven strategy updates
│   ├── signal_ingestor.py      ← HN / RSS / trending signal intake
│   ├── trending.py             ← Trending topic scoring
│   ├── campaign_generator.py   ← Multi-post campaign orchestration
│   ├── context_loader.py       ← Brand context + recent-post context assembly
│   ├── mcp_client.py           ← MCP tool integration
│   └── brand_dna.py            ← Brand-voice canonical representation
│
├── publishers/                 ← Platform publishing adapters (~600 LOC)
│   ├── base_publisher.py       ← Common interface
│   ├── x_api.py                ← X (Twitter) — tweepy wrapper
│   ├── postiz_publisher.py     ← Postiz multi-platform publisher
│   ├── linkedin_mcp.py         ← LinkedIn via MCP
│   └── n8n_webhook.py          ← n8n workflow trigger
│
├── adapters/                   ← Platform-specific content shaping (~320 LOC)
│   └── platform_adapters.py    ← XAdapter, LinkedInAdapter, BlueskyAdapter
│
├── requirements.txt
└── .env.example                ← Environment variables (no secrets)
```

---

## Key files worth reading

| File | Why |
| --- | --- |
| `engine/ideator.py` (~390 LOC) | Where algorithmic-optimized seed ideas get generated |
| `engine/content_scorer.py` (~430 LOC) | Twitter weight map scoring applied to candidates |
| `engine/post_structures.py` (~410 LOC) | The pattern families ported into [growth-os](https://github.com/howardleegeek/growth-os/blob/main/engine/hypothesis_generator.py) |
| `engine/llm.py` (~490 LOC) | Cost-aware LLM router across 4 providers |
| `publishers/postiz_publisher.py` (~400 LOC) | Multi-platform scheduled publishing |
| `adapters/platform_adapters.py` (~320 LOC) | Per-platform content transformation |

---

## Running it

### 1. Install

```bash
git clone https://github.com/howardleegeek/clawmarketing
cd clawmarketing
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

Copy `.env.example` → `.env` and fill in your API keys. The engine will
gracefully skip any provider you don't configure.

### 3. Point it at your own brand

Create a directory `engine/brands/<your_brand>/` with:

- `brand.md` — brand voice, pillars, sample voice examples
- `persona.md` — who the brand account is

Examples of the format are in the [growth-os playbook chapter 07](https://github.com/howardleegeek/growth-os/blob/main/playbook/07-multi-account-orchestration.md).

### 4. Ship a campaign

```python
from engine.campaign_generator import generate_campaign
from engine.ideator import Ideator
from publishers.postiz_publisher import PostizPublisher

campaign = generate_campaign(brand="your_brand", posts=10)
for post in campaign:
    PostizPublisher().publish(post)
```

---

## What's been REMOVED from the public version

Everything in this repo is the real production code, with the following
redactions:

- **API keys** — all references go through `os.getenv()` / env-var
  lookups. No hardcoded secrets. Never were any.
- **Postiz integration IDs** — replaced with `"REDACTED_INTEGRATION_ID"`.
  These map to specific Postiz accounts; they're account-specific.
- **Brand persona markdown files** — the specific persona descriptions
  for Oyster Labs brands (`oysterecosystem`, `clawglasses`, `ubsphone`)
  are proprietary to those brands and not published here. The format
  and approach are covered in the growth-os playbook.
- **Database dumps / logs / drafts** — not published.
- **Frontend code** — separate stack, not relevant to the content engine.

Everything else is the actual Python that ran in production.

---

## Relationship to growth-os

This repo (`clawmarketing`) is **the runtime**. It ships posts.

[`growth-os`](https://github.com/howardleegeek/growth-os) is **the
evolutionary layer on top**. It proposes slot mutations, prescreens them
with an offline simulator, runs them through this engine, verifies
outcomes mechanically, logs, and merges winning branches.

Reading order:

1. Read the [`growth-os` README](https://github.com/howardleegeek/growth-os) for the method
2. Read this repo for the actual runtime
3. Read the [`growth-os` case studies](https://github.com/howardleegeek/growth-os/tree/main/case-studies) for what it produced

---

## License

MIT. See [`LICENSE`](./LICENSE).

---

## Contributing

Open a [GitHub Issue](https://github.com/howardleegeek/clawmarketing/issues)
or a [Discussion](https://github.com/howardleegeek/clawmarketing/discussions).
See [`growth-os/CONTRIBUTING.md`](https://github.com/howardleegeek/growth-os/blob/main/CONTRIBUTING.md)
for the contribution philosophy.

Highest-value contributions:

- Platform adapters for platforms not yet covered (TikTok, Farcaster, etc.)
- LLM provider additions to `engine/llm.py`
- Real-world case studies (with brand details sanitized if needed)
