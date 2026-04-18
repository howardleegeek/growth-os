"""
Trending Signals — Feeds real-world ammo into the Ideator.

Multi-source signal fetcher with graceful fallback chain:
  1. ClawFeed (local news aggregator at :8767)
  2. Hacker News Top Stories API (free, no key)
  3. RSS feeds (TechCrunch AI, The Verge)

Usage:
    from engine.trending import fetch_signals, format_signals_for_prompt
    signals = await fetch_signals(limit=5)
    prompt_block = format_signals_for_prompt(signals)
"""

import logging
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List

import httpx

logger = logging.getLogger(__name__)

CLAWFEED_URL = os.getenv("CLAWFEED_URL", "http://127.0.0.1:8767")
TIMEOUT = 12.0

# RSS sources — free, no auth, always available
RSS_FEEDS = [
    ("https://hnrss.org/newest?points=100&count=10", "Hacker News"),
    ("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch AI"),
    ("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "The Verge AI"),
    ("https://9to5google.com/guides/google-ai/feed/", "9to5 AI"),
    ("https://www.wired.com/feed/tag/ai/latest/rss", "Wired AI"),
    ("https://decrypt.co/feed", "Decrypt Crypto"),
    ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
]

# Keywords for relevance filtering — signals must match at least one
RELEVANCE_KEYWORDS = {
    "ai", "agent", "llm", "vision", "glasses", "wearable", "ar ", "vr ",
    "hardware", "chip", "inference", "on-device", "edge", "mobile",
    "privacy", "sovereign", "decentraliz", "web3", "crypto", "depin",
    "apple", "meta", "openai", "google", "anthropic", "nvidia",
    "phone", "wallet", "security", "encrypt", "open source", "opensource",
    "robot", "autonomo", "sensor", "camera", "neural", "transformer",
    "regulation", "ban", "sideload", "antitrust",
}


@dataclass
class TrendingSignal:
    topic: str
    summary: str
    source: str
    url: str = ""
    relevance: float = 0.5


# ── Source 1: ClawFeed ──────────────────────────────────────────────

async def _fetch_clawfeed(client: httpx.AsyncClient, limit: int) -> List[TrendingSignal]:
    """Try ClawFeed local aggregator."""
    try:
        resp = await client.get(f"{CLAWFEED_URL}/api/articles", params={"limit": limit})
        if resp.status_code != 200:
            return []
        data = resp.json()
        articles = data.get("articles", data if isinstance(data, list) else [])
        return [
            TrendingSignal(
                topic=a.get("title", "")[:120],
                summary=a.get("summary", a.get("description", ""))[:200],
                source="ClawFeed",
                url=a.get("url", ""),
            )
            for a in articles[:limit]
            if a.get("title")
        ]
    except Exception as e:
        logger.debug(f"ClawFeed unavailable: {e}")
        return []


# ── Source 2: Hacker News ───────────────────────────────────────────

async def _fetch_hackernews(client: httpx.AsyncClient, limit: int) -> List[TrendingSignal]:
    """Fetch top HN stories via official API (free, no key)."""
    try:
        resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        if resp.status_code != 200:
            return []
        story_ids = resp.json()[:limit]

        signals = []
        for sid in story_ids:
            item_resp = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
            if item_resp.status_code != 200:
                continue
            item = item_resp.json()
            if not item or not item.get("title"):
                continue
            signals.append(TrendingSignal(
                topic=item["title"][:120],
                summary=f"{item.get('score', 0)} points | {item.get('descendants', 0)} comments",
                source="Hacker News",
                url=item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                relevance=min(item.get("score", 0) / 500, 1.0),
            ))
        return signals
    except Exception as e:
        logger.debug(f"HN fetch failed: {e}")
        return []


# ── Source 3: RSS Feeds ─────────────────────────────────────────────

async def _fetch_rss(client: httpx.AsyncClient, limit: int) -> List[TrendingSignal]:
    """Parse RSS feeds as last-resort signal source."""
    signals = []
    for feed_url, source_name in RSS_FEEDS:
        try:
            resp = await client.get(feed_url)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.text)
            # Handle both RSS 2.0 (<item>) and Atom (<entry>)
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items[:3]:  # 3 per feed
                title = (
                    item.findtext("title")
                    or item.findtext("{http://www.w3.org/2005/Atom}title")
                    or ""
                )
                desc = (
                    item.findtext("description")
                    or item.findtext("{http://www.w3.org/2005/Atom}summary")
                    or ""
                )
                link = (
                    item.findtext("link")
                    or (item.find("{http://www.w3.org/2005/Atom}link") or {}).get("href", "")
                    or ""
                )
                if title:
                    # Strip HTML tags from description
                    import re
                    clean_desc = re.sub(r"<[^>]+>", "", desc)[:200]
                    signals.append(TrendingSignal(
                        topic=title[:120],
                        summary=clean_desc,
                        source=source_name,
                        url=link,
                    ))
        except Exception as e:
            logger.debug(f"RSS {source_name} failed: {e}")
            continue
    return signals[:limit]


# ── Public API ──────────────────────────────────────────────────────

def _is_relevant(signal: TrendingSignal) -> bool:
    """Check if a signal is relevant to our brands based on keywords."""
    text = f"{signal.topic} {signal.summary}".lower()
    return any(kw in text for kw in RELEVANCE_KEYWORDS)


async def fetch_signals(limit: int = 5) -> List[TrendingSignal]:
    """
    Fetch trending signals from available sources.
    Tries ClawFeed first, then combines HN + RSS for broader coverage.
    Filters for relevance to our brands.
    Returns at most `limit` signals.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        # Try ClawFeed first (already curated)
        signals = await _fetch_clawfeed(client, limit * 2)
        if signals:
            relevant = [s for s in signals if _is_relevant(s)]
            if relevant:
                logger.info(f"Got {len(relevant)} relevant signals from ClawFeed")
                return relevant[:limit]

        # Combine HN + RSS for broader coverage, then filter
        all_signals = []
        hn_signals = await _fetch_hackernews(client, limit * 3)
        all_signals.extend(hn_signals)

        rss_signals = await _fetch_rss(client, limit * 3)
        all_signals.extend(rss_signals)

        # Filter for relevance
        relevant = [s for s in all_signals if _is_relevant(s)]
        if relevant:
            logger.info(f"Got {len(relevant)} relevant signals from HN+RSS (filtered from {len(all_signals)})")
            return relevant[:limit]

        # If nothing relevant, return top HN stories anyway (better than nothing)
        if all_signals:
            logger.info(f"No relevant signals found, using top {limit} from {len(all_signals)} total")
            return all_signals[:limit]

    logger.warning("All signal sources failed — ideator will run without trending context")
    return []


def format_signals_for_prompt(signals: List[TrendingSignal]) -> str:
    """Format signals into a prompt block the ideator can digest."""
    if not signals:
        return ""

    lines = [
        "--- REAL-WORLD SIGNALS (past 24h — use these as ammo) ---",
    ]
    for i, s in enumerate(signals[:5], 1):
        lines.append(f"{i}. [{s.source}] {s.topic}")
        if s.summary:
            lines.append(f"   → {s.summary[:150]}")
    lines.append("--- END SIGNALS ---")
    return "\n".join(lines)
