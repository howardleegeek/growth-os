import asyncio
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict

# Public RSS feeds without auth
RSS_FEEDS = {
    "AI": [
        "https://hnrss.org/newest?q=AI",
        "https://hnrss.org/newest?q=LLM",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
    ],
    "Web3": [
        "https://hnrss.org/newest?q=crypto",
        "https://hnrss.org/newest?q=web3",
        "https://cointelegraph.com/rss",
    ],
    "Hardware": [
        "https://hnrss.org/newest?q=hardware",
        "https://hnrss.org/newest?q=wearable",
    ],
}


async def fetch_rss(url: str, limit: int = 3) -> List[Dict[str, str]]:
    """Fetch and parse an RSS feed, returning top entries."""
    items = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            root = ET.fromstring(response.text)

            # Simple RSS parsing (channel -> item)
            for item in root.findall(".//item")[:limit]:
                title = item.findtext("title", default="").strip()
                link = item.findtext("link", default="").strip()
                desc = item.findtext("description", default="").strip()
                # Clean up html tags from description (rough)
                desc = desc.replace("<p>", "").replace("</p>", "").replace("<br>", " ")
                if len(desc) > 150:
                    desc = desc[:147] + "..."

                if title:
                    items.append({"title": title, "link": link, "description": desc})
    except Exception as e:
        print(f"⚠️ Failed to fetch RSS {url}: {e}")

    return items


async def get_daily_signals(topic: str) -> str:
    """
    Fetch trending signals for a given broad topic category.
    Returns a formatted string of recent news to inject into the LLM context.
    """
    urls = RSS_FEEDS.get(topic, RSS_FEEDS["AI"])

    all_news = []
    # Fetch feeds concurrently
    tasks = [fetch_rss(url, limit=2) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, list):
            all_news.extend(res)

    if not all_news:
        return ""

    # Format for LLM consumption
    signal_text = "TRENDING SIGNALS (incorporate into your content if relevant):\n"
    for i, item in enumerate(all_news[:5]):  # Take top 5 recent across all feeds
        signal_text += f"- {item['title']} ({item['description']})\n"

    return signal_text


if __name__ == "__main__":
    # Test script locally
    async def test():
        signals = await get_daily_signals("AI")
        print("AI Signals:")
        print(signals)
        print("\nWeb3 Signals:")
        signals_web3 = await get_daily_signals("Web3")
        print(signals_web3)

    asyncio.run(test())
