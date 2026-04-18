"""
Brand DNA Analyzer — Forked from Open-Pomelli (MIT License)
Uses our stack: Minimax LLM + Playwright + Postiz CDN

Replaces:
  - MUAPI GPT-5-Nano → Minimax (engine/llm.py)
  - FAL upload → Postiz CDN (postiz upload)
  - Playwright → kept as-is

Usage:
    python -m engine.brand_dna https://clawglasses.com
    python -m engine.brand_dna --all   # Analyze all 4 brands
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Our LLM
from engine.llm import generate_text


# --- Brand website registry ---
BRAND_SITES = {
    "clawglasses": "https://clawglasses.com",
    "ubsphone": "https://ubsphone.com",
    "oysterecosystem": "https://oysterrepublic.xyz",
}


async def _llm_analyze(system_prompt: str, user_message: str) -> str:
    """Thin wrapper around our LLM stack."""
    result = await generate_text(
        system_prompt=system_prompt,
        user_message=user_message,
    )
    return result or ""


async def _llm_json(system_prompt: str, user_message: str) -> dict:
    """Call LLM and parse JSON from response."""
    raw = await _llm_analyze(system_prompt, user_message)
    # Strip markdown fences
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM JSON, returning raw text")
        return {"raw": raw}


class BrandDNAAnalyzer:
    """
    Comprehensive brand DNA extraction using Playwright + Minimax LLM.

    Pipeline:
      1. Playwright fetches website → HTML, text, computed styles, images, meta
      2. Playwright captures screenshot → saved locally
      3. Minimax LLM analyzes text content → brand messaging, tone, personality
      4. Minimax synthesizes all data → structured Brand DNA JSON
    """

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )

    async def analyze(self, url: str, brand_key: str = "") -> Dict[str, Any]:
        """Full Brand DNA extraction pipeline."""
        logger.info(f"[BrandDNA] Analyzing {url} ...")

        # Step 1: Playwright fetch
        web_data = await self._fetch_with_playwright(url)
        if web_data.get("error"):
            logger.error(f"[BrandDNA] Fetch failed: {web_data['error']}")
            return {"error": web_data["error"], "source_url": url}

        # Step 2: Screenshot (optional — stored locally)
        screenshot_path = web_data.get("screenshot_path")

        # Step 3: LLM text analysis
        text_analysis = await self._analyze_text(web_data)

        # Step 4: Extract assets
        assets = web_data.get("assets", {})
        brand_images = self._extract_top_images(assets)
        logo_data = self._extract_logo(assets)
        guidelines = self._extract_guidelines(assets)

        # Step 5: Synthesize Brand DNA
        brand_dna = self._synthesize(
            url=url,
            brand_key=brand_key,
            text_analysis=text_analysis,
            web_data=web_data,
            assets=assets,
            brand_images=brand_images,
            logo_data=logo_data,
            guidelines=guidelines,
            screenshot_path=screenshot_path,
        )

        logger.info(
            f"[BrandDNA] ✅ Extracted DNA for {brand_dna.get('brand_name', 'Unknown')}"
        )
        return brand_dna

    # ── Playwright fetch ──────────────────────────────────────

    async def _fetch_with_playwright(self, url: str) -> Dict[str, Any]:
        """Fetch website content + computed styles using Playwright."""
        try:
            from playwright.async_api import async_playwright
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error(
                "playwright / beautifulsoup4 not installed. "
                "Run: pip install playwright beautifulsoup4 && playwright install"
            )
            return {"error": "Missing deps: playwright, beautifulsoup4"}

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    user_agent=self.user_agent,
                    viewport={"width": 1280, "height": 900},
                )
                page = await ctx.new_page()

                resp = await page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                status = resp.status if resp else 0
                await page.wait_for_timeout(3000)  # let JS render

                html = await page.content()
                title = await page.title()

                # DOM evaluation for styles + assets
                assets = await page.evaluate(
                    """() => {
                    const gs = (el, p) => getComputedStyle(el).getPropertyValue(p);
                    const colors = new Set(), fonts = new Set();
                    document.querySelectorAll('body,h1,h2,h3,p,a,button,.btn,header,footer,div,span,nav')
                        .forEach(el => {
                            const s = getComputedStyle(el);
                            if (s.color && s.color !== 'rgba(0, 0, 0, 0)') colors.add(s.color);
                            if (s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)') colors.add(s.backgroundColor);
                            if (s.fontFamily) fonts.add(s.fontFamily);
                        });
                    const images = Array.from(document.images)
                        .filter(i => i.naturalWidth > 50 && i.naturalHeight > 50)
                        .map(i => ({src: i.src, width: i.naturalWidth, height: i.naturalHeight, alt: i.alt || ''}));
                    const links = Array.from(document.links).map(a => ({text: a.innerText.trim().slice(0,80), href: a.href}));
                    const icons = Array.from(document.querySelectorAll('link[rel*="icon"], link[rel="apple-touch-icon"]')).map(l => l.href);
                    const og = document.querySelector('meta[property="og:image"]');
                    return {
                        colors: Array.from(colors).slice(0, 40),
                        fonts: Array.from(fonts).slice(0, 10),
                        images: images.slice(0, 30),
                        links: links.slice(0, 50),
                        icons,
                        og_image: og ? og.content : null
                    };
                }"""
                )

                # Screenshot
                ss_dir = Path("/tmp/brand_dna_screenshots")
                ss_dir.mkdir(exist_ok=True)
                ss_path = str(ss_dir / f"{url.replace('https://','').replace('/','_')}_{int(time.time())}.png")
                await page.screenshot(path=ss_path, full_page=False)

                await browser.close()

                # Parse text with BS4
                soup = BeautifulSoup(html, "html.parser")
                meta = {}
                desc = soup.find("meta", attrs={"name": "description"})
                if desc:
                    meta["description"] = desc.get("content", "")
                kw = soup.find("meta", attrs={"name": "keywords"})
                if kw:
                    meta["keywords"] = kw.get("content", "")
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                text = soup.get_text(separator=" ", strip=True)

                logger.info(f"[BrandDNA] Fetched {len(text)} chars, {len(assets.get('images',[]))} images")
                return {
                    "url": url,
                    "status": status,
                    "title": title,
                    "text": text,
                    "metadata": meta,
                    "assets": assets,
                    "screenshot_path": ss_path,
                }
        except Exception as e:
            logger.error(f"[BrandDNA] Playwright error: {e}")
            return {"error": str(e)}

    # ── LLM Text Analysis ─────────────────────────────────────

    async def _analyze_text(self, web_data: Dict) -> Dict[str, Any]:
        """Use Minimax to extract brand messaging from website text."""
        text = web_data.get("text", "")[:4000]
        title = web_data.get("title", "")
        meta = web_data.get("metadata", {})

        user_msg = f"""Analyze this website content and extract brand messaging elements.

Title: {title}
Description: {meta.get('description', '')}
Keywords: {meta.get('keywords', '')}
Content: {text}

Return ONLY valid JSON (no markdown fences):
{{
  "brand_name": "string",
  "tagline": "string or empty",
  "value_proposition": "1-2 sentence summary",
  "tone_of_voice": ["trait1", "trait2", "trait3"],
  "brand_personality": ["trait1", "trait2", "trait3"],
  "target_audience": "description",
  "key_messages": ["msg1", "msg2", "msg3"],
  "industry": "string",
  "brand_language": "e.g. Professional English / Casual Web3"
}}"""

        result = await _llm_json(
            system_prompt="You are a senior brand strategist. Extract structured brand DNA from website content. Return ONLY valid JSON.",
            user_message=user_msg,
        )

        # Fallback
        if "raw" in result and len(result) == 1:
            return {
                "brand_name": title,
                "tone_of_voice": ["professional"],
                "brand_personality": ["trustworthy"],
                "industry": "technology",
            }
        return result

    # ── Asset extraction helpers ──────────────────────────────

    def _extract_top_images(self, assets: Dict) -> List[Dict]:
        """Top 10 largest images from scraped assets."""
        imgs = assets.get("images", [])
        sorted_imgs = sorted(
            imgs, key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True
        )
        return sorted_imgs[:10]

    def _extract_logo(self, assets: Dict) -> Dict[str, Any]:
        """Find best logo candidate."""
        logo_imgs = [
            img["src"]
            for img in assets.get("images", [])
            if "logo" in img.get("src", "").lower() or "logo" in img.get("alt", "").lower()
        ]
        og = assets.get("og_image")
        icons = assets.get("icons", [])

        url = logo_imgs[0] if logo_imgs else (og or (icons[0] if icons else None))
        return {"url": url, "candidates": logo_imgs + icons}

    def _extract_guidelines(self, assets: Dict) -> List[Dict]:
        """Find links to brand guidelines / media kits."""
        keywords = ["brand", "media kit", "press", "style guide", "logo", "assets"]
        found = []
        for link in assets.get("links", []):
            t = link.get("text", "").lower()
            h = link.get("href", "").lower()
            if any(k in t or k in h for k in keywords):
                found.append(link)
        return found[:5]

    # ── Synthesis ─────────────────────────────────────────────

    def _synthesize(
        self,
        url: str,
        brand_key: str,
        text_analysis: Dict,
        web_data: Dict,
        assets: Dict,
        brand_images: List,
        logo_data: Dict,
        guidelines: List,
        screenshot_path: Optional[str],
    ) -> Dict[str, Any]:
        """Combine all analyses into comprehensive Brand DNA."""

        scraped_colors = assets.get("colors", [])
        scraped_fonts = assets.get("fonts", [])

        # Convert rgb() to hex for colors
        hex_colors = []
        for c in scraped_colors[:20]:
            if c.startswith("rgb"):
                try:
                    nums = [int(x.strip()) for x in c.replace("rgb(", "").replace("rgba(", "").replace(")", "").split(",")[:3]]
                    hex_colors.append(f"#{nums[0]:02x}{nums[1]:02x}{nums[2]:02x}")
                except:
                    hex_colors.append(c)
            else:
                hex_colors.append(c)
        # Deduplicate
        unique_colors = list(dict.fromkeys(hex_colors))[:10]

        return {
            "brand_key": brand_key,
            "brand_name": text_analysis.get("brand_name", web_data.get("title", "")),
            "industry": text_analysis.get("industry", "technology"),
            "tagline": text_analysis.get("tagline", ""),
            "value_proposition": text_analysis.get("value_proposition", ""),
            "tone_of_voice": text_analysis.get("tone_of_voice", ["professional"]),
            "brand_personality": text_analysis.get("brand_personality", ["trustworthy"]),
            "brand_language": text_analysis.get("brand_language", "English"),
            "target_audience": text_analysis.get("target_audience", "General"),
            "key_messages": text_analysis.get("key_messages", []),
            "visual_style": {
                "colors": unique_colors,
                "primary_colors": unique_colors[:3],
                "secondary_colors": unique_colors[3:6],
                "fonts": scraped_fonts,
                "logo": logo_data,
                "imagery_style": "modern product photography",
                "layout_style": "modern minimalist",
            },
            "assets": {
                "logo_url": logo_data.get("url"),
                "top_images": [img.get("src", "") for img in brand_images],
                "guidelines_links": guidelines,
                "screenshot_path": screenshot_path,
            },
            "source_url": url,
            "extracted_from": "brand_dna_v1_minimax",
        }


# ── CLI entry point ───────────────────────────────────────────

async def analyze_brand(brand_key: str) -> Dict[str, Any]:
    """Analyze a single brand by key."""
    url = BRAND_SITES.get(brand_key)
    if not url:
        raise ValueError(f"Unknown brand: {brand_key}. Available: {list(BRAND_SITES.keys())}")

    analyzer = BrandDNAAnalyzer()
    dna = await analyzer.analyze(url, brand_key=brand_key)

    # Save to engine/brands/<brand_key>_dna.json
    out_dir = Path(__file__).parent / "brands"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{brand_key}_dna.json"
    with open(out_path, "w") as f:
        json.dump(dna, f, indent=2, ensure_ascii=False)
    logger.info(f"[BrandDNA] Saved → {out_path}")

    return dna


async def analyze_all_brands() -> Dict[str, Dict]:
    """Analyze all 4 brand websites."""
    results = {}
    for brand_key in BRAND_SITES:
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing brand: {brand_key}")
        logger.info(f"{'='*60}")
        try:
            dna = await analyze_brand(brand_key)
            results[brand_key] = dna
        except Exception as e:
            logger.error(f"Failed to analyze {brand_key}: {e}")
            results[brand_key] = {"error": str(e)}
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--all":
            asyncio.run(analyze_all_brands())
        elif arg.startswith("http"):
            # Raw URL
            analyzer = BrandDNAAnalyzer()
            dna = asyncio.run(analyzer.analyze(arg))
            print(json.dumps(dna, indent=2, ensure_ascii=False))
        else:
            # Brand key
            asyncio.run(analyze_brand(arg))
    else:
        print("Usage:")
        print("  python -m engine.brand_dna clawglasses")
        print("  python -m engine.brand_dna --all")
        print("  python -m engine.brand_dna https://example.com")
