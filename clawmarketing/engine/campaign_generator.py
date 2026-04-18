"""
Campaign Generator — Forked from Open-Pomelli (MIT License)
Adapted for Oyster Labs: Postiz MCP image gen + Brand DNA + multi-channel export.

Capabilities:
  1. Campaign Generator — Brand DNA → multi-channel marketing images + copy
  2. Reference-Based Image Gen — brand logo as reference for consistent style
  3. Multi-channel Asset Export — Twitter/LinkedIn/Bluesky/Instagram sized outputs

Usage:
    from engine.campaign_generator import CampaignEngine
    engine = CampaignEngine()
    results = await engine.generate_campaign("clawglasses", "social_media")
    results = await engine.generate_images_for_batch("/tmp/content_batch.json")
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Platform asset dimensions
PLATFORM_DIMENSIONS = {
    "twitter_post": (1200, 675),
    "twitter_header": (1500, 500),
    "linkedin_post": (1200, 628),
    "linkedin_banner": (1584, 396),
    "bluesky_post": (1200, 675),
    "instagram_post": (1080, 1080),
    "instagram_story": (1080, 1920),
    "hero_image": (1920, 1080),
    "product_mockup": (1024, 1024),
    "social_square": (1080, 1080),
    "banner": (1920, 600),
    "og_image": (1200, 630),
}

# Campaign types with deliverables
CAMPAIGN_TYPES = {
    "social_media": {
        "deliverables": ["twitter_post", "linkedin_post", "bluesky_post", "instagram_post"],
        "description": "Multi-platform social media campaign",
    },
    "product_launch": {
        "deliverables": ["hero_image", "product_mockup", "twitter_post", "linkedin_post", "og_image"],
        "description": "Product launch campaign with hero + social",
    },
    "brand_awareness": {
        "deliverables": ["social_square", "twitter_header", "linkedin_banner", "banner"],
        "description": "Brand awareness assets across platforms",
    },
    "event": {
        "deliverables": ["banner", "social_square", "instagram_story", "twitter_post"],
        "description": "Event marketing campaign",
    },
}


def _load_brand_dna(brand_key: str) -> Dict[str, Any]:
    """Load Brand DNA JSON for a brand."""
    dna_path = Path(__file__).parent / "brands" / f"{brand_key}_dna.json"
    if not dna_path.exists():
        raise FileNotFoundError(f"Brand DNA not found: {dna_path}")
    with open(dna_path) as f:
        return json.load(f)


def _build_image_prompt(
    brand_dna: Dict[str, Any],
    deliverable_type: str,
    campaign_brief: str = "",
    post_content: str = "",
) -> str:
    """Build a brand-consistent image generation prompt."""
    brand_name = brand_dna.get("brand_name", "")
    industry = brand_dna.get("industry", "technology")
    tagline = brand_dna.get("tagline", "")
    tone = ", ".join(brand_dna.get("tone_of_voice", ["professional"]))
    personality = ", ".join(brand_dna.get("brand_personality", ["modern"]))

    visual = brand_dna.get("visual_style", {})
    primary_colors = visual.get("primary_colors", [])
    color_str = ", ".join(primary_colors[:3]) if primary_colors else "dark navy, white"
    imagery_style = visual.get("imagery_style", "modern product photography")

    # Deliverable-specific context
    type_context = {
        "twitter_post": "Social media post image for Twitter/X. Eye-catching, bold, scroll-stopping.",
        "linkedin_post": "Professional LinkedIn post image. Clean, authoritative, thought-leadership style.",
        "bluesky_post": "Social media post image for Bluesky. Tech-forward, developer-friendly aesthetic.",
        "instagram_post": "Instagram square post. Visually striking, high contrast, mobile-optimized.",
        "instagram_story": "Instagram story format (vertical 9:16). Immersive, full-screen impact.",
        "hero_image": "Website hero banner. Premium, wide format, strong visual hierarchy.",
        "product_mockup": "Product photography. Clean background, studio lighting, premium feel.",
        "social_square": "Universal social media square image. Works across all platforms.",
        "banner": "Wide banner image. Cinematic composition, brand colors prominent.",
        "og_image": "Open Graph preview image. Clear text area, brand identity prominent.",
        "twitter_header": "Twitter profile header banner. Wide, brand colors, clean.",
        "linkedin_banner": "LinkedIn company page banner. Professional, brand-forward.",
    }

    context = type_context.get(deliverable_type, "Marketing image.")

    # Build the prompt
    content_hint = ""
    if post_content:
        # Extract the core idea (first 80 chars) to guide image
        content_hint = f"Visual concept: {post_content[:80]}."
    elif campaign_brief:
        content_hint = f"Campaign: {campaign_brief[:80]}."

    prompt = (
        f"{context} "
        f"Brand: {brand_name} — {industry}. "
        f"{content_hint} "
        f"Style: {imagery_style}, {tone}. "
        f"Color palette: {color_str}. "
        f"Mood: {personality}. "
        f"No text overlays. Professional quality. High resolution."
    )

    return prompt.strip()


def _size_to_aspect_ratio(size: tuple) -> str:
    """Convert size tuple to aspect ratio string."""
    w, h = size
    if w == h:
        return "1:1"
    ratio = w / h
    if 1.7 <= ratio <= 1.8:
        return "16:9"
    elif 2.5 <= ratio <= 4.5:
        return "4:1"  # banners
    elif 1.85 <= ratio <= 2.0:
        return "16:9"
    elif 0.5 <= ratio <= 0.6:
        return "9:16"
    elif w > h:
        return "16:9"
    else:
        return "9:16"


class CampaignEngine:
    """
    Generates complete, multi-asset campaigns with brand consistency.
    Uses Postiz MCP for AI image generation (300/month) and VEO3 video (30/month).
    """

    def __init__(self):
        self._mcp = None

    async def _get_mcp(self):
        """Lazy-load Postiz MCP client."""
        if self._mcp is None:
            from .mcp_client import PostizMCP
            self._mcp = PostizMCP()
            await self._mcp.initialize()
        return self._mcp

    async def generate_campaign(
        self,
        brand_key: str,
        campaign_type: str = "social_media",
        campaign_brief: str = "",
        custom_deliverables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete campaign with multiple coordinated assets.

        Args:
            brand_key: Brand identifier (clawglasses, ubsphone, oysterecosystem)
            campaign_type: Type of campaign (social_media, product_launch, etc.)
            campaign_brief: Description of the campaign
            custom_deliverables: Optional custom list of deliverable types
        """
        logger.info(f"[Campaign] Starting {campaign_type} for {brand_key}")

        brand_dna = _load_brand_dna(brand_key)

        # Determine deliverables
        if custom_deliverables:
            deliverables = custom_deliverables
        elif campaign_type in CAMPAIGN_TYPES:
            deliverables = CAMPAIGN_TYPES[campaign_type]["deliverables"]
        else:
            deliverables = ["twitter_post", "linkedin_post"]

        results = {
            "brand_key": brand_key,
            "campaign_type": campaign_type,
            "campaign_brief": campaign_brief,
            "deliverables": deliverables,
            "assets": [],
            "started_at": datetime.utcnow().isoformat(),
        }

        mcp = await self._get_mcp()

        for i, deliverable in enumerate(deliverables, 1):
            logger.info(f"[Campaign] Generating {deliverable} ({i}/{len(deliverables)})")

            prompt = _build_image_prompt(
                brand_dna=brand_dna,
                deliverable_type=deliverable,
                campaign_brief=campaign_brief,
            )

            try:
                image_result = await mcp.generate_image(prompt)
                asset = {
                    "type": deliverable,
                    "dimensions": PLATFORM_DIMENSIONS.get(deliverable, (1024, 1024)),
                    "prompt": prompt,
                    "image_url": image_result.get("path", ""),
                    "image_id": image_result.get("id", ""),
                    "status": "success" if image_result.get("path") else "failed",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                results["assets"].append(asset)
                logger.info(f"[Campaign] {deliverable} → {asset['image_url'][:60]}...")
            except Exception as e:
                logger.error(f"[Campaign] {deliverable} failed: {e}")
                results["assets"].append({
                    "type": deliverable,
                    "status": "failed",
                    "error": str(e),
                })

        results["completed_at"] = datetime.utcnow().isoformat()
        results["success_count"] = len([a for a in results["assets"] if a.get("status") == "success"])
        logger.info(f"[Campaign] Done: {results['success_count']}/{len(deliverables)} assets")
        return results

    async def generate_image_for_post(
        self,
        brand_key: str,
        platform: str,
        post_content: str = "",
    ) -> Dict[str, Any]:
        """Generate a single image for a specific post."""
        brand_dna = _load_brand_dna(brand_key)

        # Map platform to deliverable type
        platform_map = {
            "twitter": "twitter_post",
            "x": "twitter_post",
            "linkedin": "linkedin_post",
            "bluesky": "bluesky_post",
            "instagram": "instagram_post",
        }
        deliverable = platform_map.get(platform.lower(), "social_square")

        prompt = _build_image_prompt(
            brand_dna=brand_dna,
            deliverable_type=deliverable,
            post_content=post_content,
        )

        mcp = await self._get_mcp()
        image_result = await mcp.generate_image(prompt)

        return {
            "type": deliverable,
            "dimensions": PLATFORM_DIMENSIONS.get(deliverable, (1024, 1024)),
            "prompt": prompt,
            "image_url": image_result.get("path", ""),
            "image_id": image_result.get("id", ""),
        }

    async def generate_images_for_batch(
        self,
        batch_path: str,
        max_images: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Generate AI images for a batch of posts from JSON file.

        Args:
            batch_path: Path to content batch JSON
            max_images: Max images to generate (quota protection)
        """
        with open(batch_path) as f:
            posts = json.load(f)

        results = []
        count = 0

        for post in posts:
            if count >= max_images:
                logger.warning(f"[Campaign] Reached max_images={max_images}, stopping")
                break

            brand = post.get("brand", "")
            platform = post.get("platform", "twitter")
            content = post.get("content", "")

            if not brand:
                continue

            try:
                result = await self.generate_image_for_post(
                    brand_key=brand,
                    platform=platform,
                    post_content=content,
                )
                result["post_index"] = posts.index(post)
                result["brand"] = brand
                result["platform"] = platform
                results.append(result)
                count += 1
                logger.info(f"[Batch] {count}/{max_images}: {brand}/{platform} → {result.get('image_url', '')[:50]}")

                # Rate limit protection
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"[Batch] Failed {brand}/{platform}: {e}")
                results.append({
                    "post_index": posts.index(post),
                    "brand": brand,
                    "platform": platform,
                    "status": "failed",
                    "error": str(e),
                })

        return results

    async def generate_video(
        self,
        brand_key: str,
        brief: str = "",
        orientation: str = "horizontal",
        prefer_slides: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a video for a brand.

        Priority: VEO3 (paid plan, 30/mo) → image-text-slides (trial OK, unlimited).
        VEO3 is higher quality but requires paid Postiz plan.

        Args:
            brand_key: Brand identifier
            brief: Video concept brief
            orientation: "horizontal" or "vertical"
            prefer_slides: Force image-text-slides instead of VEO3
        """
        brand_dna = _load_brand_dna(brand_key)
        brand_name = brand_dna.get("brand_name", brand_key)
        industry = brand_dna.get("industry", "technology")
        tone = ", ".join(brand_dna.get("tone_of_voice", ["professional"]))

        if brief:
            video_brief = brief
        else:
            tagline = brand_dna.get("tagline", "")
            video_brief = (
                f"A short promotional video for {brand_name}, a {industry} brand. "
                f"Tagline: {tagline}. Tone: {tone}. "
                f"Premium quality, cinematic feel."
            )

        mcp = await self._get_mcp()

        # Try VEO3 first (paid plan only), fall back to image-text-slides
        if not prefer_slides:
            try:
                # VEO3 needs reference images — generate one first
                image_prompt = _build_image_prompt(brand_dna, "product_mockup", brief)
                ref_image = await mcp.generate_image(image_prompt)
                if ref_image and ref_image.get("id"):
                    result = await mcp.generate_video(
                        identifier="veo3",
                        orientation=orientation,
                        custom_params=[
                            {"key": "prompt", "value": video_brief},
                            {"key": "images", "value": [
                                {"id": ref_image["id"], "path": ref_image.get("path", "")}
                            ]},
                        ],
                    )
                    video_url = result.get("url") or result.get("path", "")
                    if video_url:
                        return {
                            "brand_key": brand_key,
                            "prompt": video_brief,
                            "identifier": "veo3",
                            "orientation": orientation,
                            "video_url": video_url,
                            "ref_image": ref_image.get("path", ""),
                            "status": "success",
                        }
            except Exception as e:
                logger.info(f"[Video] VEO3 unavailable ({e}), falling back to slides")

        # Fallback: image-text-slides (works on trial plan)
        logger.info(f"[Video] Using image-text-slides for {brand_key}")
        import httpx
        api_key = os.environ.get("POSTIZ_API_KEY", "")
        if not api_key:
            env_path = os.path.expanduser("~/.oyster-keys/postiz.env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("export "):
                            line = line[7:]
                        if line.startswith("POSTIZ_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                "https://api.postiz.com/public/v1/generate-video",
                json={
                    "type": "image-text-slides",
                    "output": orientation,
                    "customParams": {
                        "prompt": video_brief,
                        "voice": "default",
                    },
                },
                headers={"Authorization": api_key, "Content-Type": "application/json"},
            )

        if resp.status_code >= 400:
            return {
                "brand_key": brand_key,
                "prompt": video_brief,
                "identifier": "image-text-slides",
                "status": "failed",
                "error": resp.text[:200],
            }

        data = resp.json()
        return {
            "brand_key": brand_key,
            "prompt": video_brief,
            "identifier": "image-text-slides",
            "orientation": orientation,
            "video_url": data.get("path", ""),
            "video_id": data.get("id", ""),
            "status": "success",
        }


# ── CLI entry point ──────────────────────────────────────────

async def _main():
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if len(sys.argv) < 3:
        print("Usage:")
        print("  python -m engine.campaign_generator <brand_key> <campaign_type>")
        print("  python -m engine.campaign_generator clawglasses social_media")
        print("  python -m engine.campaign_generator --batch /tmp/content_batch.json [max_images]")
        print("  python -m engine.campaign_generator --video <brand_key> [brief]")
        return

    engine = CampaignEngine()

    if sys.argv[1] == "--batch":
        batch_path = sys.argv[2]
        max_images = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        results = await engine.generate_images_for_batch(batch_path, max_images)
        out_path = "/tmp/campaign_images.json"
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {out_path}")
    elif sys.argv[1] == "--video":
        brand_key = sys.argv[2]
        brief = sys.argv[3] if len(sys.argv) > 3 else ""
        result = await engine.generate_video(brand_key, brief)
        print(json.dumps(result, indent=2))
    else:
        brand_key = sys.argv[1]
        campaign_type = sys.argv[2]
        brief = sys.argv[3] if len(sys.argv) > 3 else ""
        results = await engine.generate_campaign(brand_key, campaign_type, brief)
        out_path = f"/tmp/campaign_{brand_key}_{campaign_type}.json"
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {out_path}")
        print(f"Success: {results['success_count']}/{len(results['deliverables'])}")


if __name__ == "__main__":
    asyncio.run(_main())
