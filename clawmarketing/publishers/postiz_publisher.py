"""
Postiz Publisher — Routes content through Postiz MCP endpoint.

MECE boundary:
  - Postiz handles: scheduling, publishing, analytics, media CDN
  - Self-built handles: engagement farming, signals, brand DNA generation

Primary: MCP endpoint (reliable, no CLI rate limits)

Supports:
  - Multi-platform posting via integration IDs
  - Media attachments (URLs from Postiz CDN)
  - Draft / schedule / now modes
  - Platform-specific settings (e.g. who_can_reply for Twitter)
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import shutil
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from .base_publisher import BasePublisher
from engine.content_scorer import ContentScorer

logger = logging.getLogger(__name__)

# Quality gate — reject content below this score
_scorer = ContentScorer(threshold=55)

# Default platform settings — optimize for algorithm engagement
# Twitter: "everyone" maximizes 27x reply weight
PLATFORM_DEFAULT_SETTINGS = {
    "twitter": [{"key": "who_can_reply_post", "value": "everyone"}],
    # Bluesky and LinkedIn have no additional settings
}

# Postiz Integration ID mapping
INTEGRATION_IDS = {
    # X (Twitter)
    "x_oysterecosystem": "REDACTED_INTEGRATION_ID",
    "x_clawglasses": "REDACTED_INTEGRATION_ID",
    "x_ubsphone": "REDACTED_INTEGRATION_ID",
    # Bluesky
    "bsky_oysterecosystem": "REDACTED_INTEGRATION_ID",
    "bsky_clawglasses": "REDACTED_INTEGRATION_ID",
    "bsky_clawphones": "REDACTED_INTEGRATION_ID",
    # LinkedIn
    "linkedin_bruno": "REDACTED_INTEGRATION_ID",
    "linkedin_clawglasses_page": "REDACTED_INTEGRATION_ID",
    "linkedin_clawphones_page": "REDACTED_INTEGRATION_ID",
    "linkedin_oysterrepublic_page": "REDACTED_INTEGRATION_ID",
    # Farcaster (Warpcast) — connect accounts in Postiz UI, then add IDs here
    # "fc_oysterecosystem": "",
    # "fc_clawglasses": "",
    # Threads — connect Meta/Instagram Business accounts in Postiz UI
    # "threads_oysterecosystem": "",
    # "threads_clawglasses": "",
}

# Brand → integration ID mapping for routing
BRAND_PLATFORM_MAP = {
    "clawglasses": {
        "twitter": "x_clawglasses",
        "bluesky": "bsky_clawglasses",
        "linkedin": "linkedin_clawglasses_page",
        "linkedin_bruno": "linkedin_bruno",
        # "farcaster": "fc_clawglasses",    # Uncomment after connecting in Postiz
        # "threads": "threads_clawglasses",  # Uncomment after connecting in Postiz
    },
    "oysterecosystem": {
        "twitter": "x_oysterecosystem",
        "bluesky": "bsky_oysterecosystem",
        "linkedin": "linkedin_oysterrepublic_page",
        # "farcaster": "fc_oysterecosystem",
        # "threads": "threads_oysterecosystem",
    },
    "ubsphone": {
        "twitter": "x_ubsphone",
        "bluesky": "bsky_clawphones",  # UBSPhone uses clawphones Bluesky (shared account)
        "linkedin": "linkedin_clawphones_page",
    },
}

# Canonical display names for each brand
CANONICAL_BRAND_NAMES = {
    "clawglasses": "ClawGlasses",
    "ubsphone": "ClawPhones",
    "oysterecosystem": "Oyster Republic",
}

# Reverse mapping: Postiz integration ID → canonical brand_key
# Auto-built at module load from BRAND_PLATFORM_MAP + INTEGRATION_IDS
INTEGRATION_TO_BRAND = {}
for _brand_key, _platforms in BRAND_PLATFORM_MAP.items():
    for _platform, _id_key in _platforms.items():
        _integration_id = INTEGRATION_IDS.get(_id_key, "")
        if _integration_id:
            INTEGRATION_TO_BRAND[_integration_id] = _brand_key


def resolve_brand_from_integration(integration_id: str) -> str:
    """Reverse lookup: Postiz integration ID -> canonical brand_key."""
    return INTEGRATION_TO_BRAND.get(integration_id, "")


def resolve_integration_id(brand_key: str, platform: str) -> str:
    """Resolve brand + platform to a Postiz integration ID."""
    brand_map = BRAND_PLATFORM_MAP.get(brand_key.lower(), {})
    id_key = brand_map.get(platform.lower(), "")
    if id_key:
        return INTEGRATION_IDS.get(id_key, id_key)
    return ""


# ── Shared MCP singleton (thread-safe) ────────────────────────

_mcp_instance = None
_mcp_lock = asyncio.Lock()


async def _get_mcp():
    """Get or create the shared PostizMCP instance (race-condition safe)."""
    global _mcp_instance
    if _mcp_instance is not None:
        return _mcp_instance
    async with _mcp_lock:
        # Double-check after acquiring lock
        if _mcp_instance is not None:
            return _mcp_instance
        from engine.mcp_client import PostizMCP
        _mcp_instance = PostizMCP()
        await _mcp_instance.initialize()
        logger.info("[Postiz] MCP session initialized")
        return _mcp_instance


async def _reset_mcp():
    """Force-reset MCP singleton (for session recovery)."""
    global _mcp_instance
    if _mcp_instance and hasattr(_mcp_instance, '_client'):
        try:
            if _mcp_instance._client and not _mcp_instance._client.is_closed:
                await _mcp_instance._client.aclose()
        except Exception:
            pass
    _mcp_instance = None


def _text_to_html(text: str) -> str:
    """Convert plain text to Postiz HTML format."""
    lines = text.strip().split("\n")
    html_parts = []
    for line in lines:
        line = line.strip()
        if not line:
            html_parts.append("<p></p>")
        else:
            html_parts.append(f"<p>{line}</p>")
    return "".join(html_parts)


class PostizPublisher(BasePublisher):
    """Publish content via Postiz MCP (primary) or CLI (fallback)."""

    def __init__(self, brand_key: str = "", **kwargs):
        super().__init__(platform_name="postiz", **kwargs)
        self.brand_key = brand_key

    async def publish(
        self,
        text: str,
        media_paths: Optional[List[str]] = None,
        platform: str = "twitter",
        thread_replies: Optional[List[str]] = None,
        schedule_minutes: int = 0,
        mode: str = "schedule",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Publish a post via Postiz MCP endpoint.

        Args:
            text: The main post content
            media_paths: List of media URLs (already on Postiz CDN)
            platform: Target platform (twitter, bluesky, linkedin)
            thread_replies: Optional list of thread reply texts (for long threads)
            schedule_minutes: Minutes from now to schedule (0 = 5min default)
            mode: "schedule", "now", or "draft"
        """
        # === SANITIZE: strip reasoning model artifacts before quality gate ===
        # MiniMax M1, DeepSeek, etc. emit <think>...</think> blocks
        text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()
        # Strip common LLM preambles
        text = re.sub(
            r"^(?:Here(?:'s| is).*?:\s*|Sure[,!]?\s*|Certainly[,!]?\s*)+",
            "", text, flags=re.IGNORECASE
        ).strip()

        if not text or len(text) < 20:
            logger.warning("[Postiz] Content empty after sanitization")
            return {
                "status": "blocked",
                "reason": "empty_after_sanitization",
                "platform": platform,
                "brand": self.brand_key,
            }

        # === QUALITY GATE: reject low-quality content before publishing ===
        score_result = _scorer.score(text, platform=platform, brand=self.brand_key)
        if not score_result.passed:
            logger.warning(
                f"[Postiz] QUALITY GATE BLOCKED — score={score_result.score} "
                f"grade={score_result.grade} issues={score_result.issues}"
            )
            return {
                "status": "blocked",
                "reason": "quality_gate",
                "score": score_result.score,
                "grade": score_result.grade,
                "issues": score_result.issues,
                "suggestions": score_result.suggestions,
                "platform": platform,
                "brand": self.brand_key,
            }
        logger.info(
            f"[Postiz] Quality gate PASSED — score={score_result.score} grade={score_result.grade}"
        )

        integration_id = kwargs.get("integration_id") or resolve_integration_id(
            self.brand_key, platform
        )

        if not integration_id:
            return {
                "status": "failed",
                "reason": f"No integration ID for brand={self.brand_key} platform={platform}",
            }

        # Schedule time — always set (minimum 5 min from now)
        schedule_time = datetime.now(timezone.utc) + timedelta(
            minutes=max(schedule_minutes, 5)
        )
        date_utc = schedule_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Convert to HTML
        content_html = _text_to_html(text)

        # Thread replies → comments (each reply becomes a thread post)
        comments = []
        if thread_replies:
            comments = [_text_to_html(reply) for reply in thread_replies]
            logger.info(f"[Postiz] Thread: {len(thread_replies)+1} parts")

        # Platform settings
        settings = kwargs.get("settings") or PLATFORM_DEFAULT_SETTINGS.get(platform.lower(), [])

        logger.info(f"[Postiz] Publishing to {platform} for {self.brand_key} via MCP")

        try:
            mcp = await _get_mcp()
            result = await mcp.schedule_post(
                integration_id=integration_id,
                content_html=content_html,
                date_utc=date_utc,
                attachments=media_paths or [],
                comments=comments,
                settings=settings,
                post_type=mode,
            )

            # Parse MCP response
            if isinstance(result, dict) and "output" in result:
                posts = result["output"]
                post_id = posts[0]["postId"] if posts else ""
                logger.info(f"[Postiz] MCP success: postId={post_id}")
                return {
                    "status": "success",
                    "platform": platform,
                    "brand": self.brand_key,
                    "mode": mode,
                    "post_id": post_id,
                    "thread_parts": (len(comments) + 1) if comments else 1,
                    "via": "mcp",
                }
            elif isinstance(result, dict) and result.get("error"):
                raise RuntimeError(result["error"])
            else:
                logger.info(f"[Postiz] MCP result: {str(result)[:200]}")
                return {
                    "status": "success",
                    "platform": platform,
                    "brand": self.brand_key,
                    "mode": mode,
                    "thread_parts": (len(comments) + 1) if comments else 1,
                    "via": "mcp",
                    "raw": str(result)[:200],
                }

        except Exception as e:
            logger.error(f"[Postiz] MCP failed: {e}")
            # Last-resort retry: reset singleton and try once more
            if "session" in str(e).lower():
                try:
                    import asyncio as _aio
                    await _reset_mcp()
                    await _aio.sleep(1)
                    mcp = await _get_mcp()
                    result = await mcp.schedule_post(
                        integration_id=integration_id,
                        content_html=content_html,
                        date_utc=date_utc,
                        attachments=media_paths or [],
                        comments=comments,
                        settings=settings,
                        post_type=mode,
                    )
                    if isinstance(result, dict) and "output" in result:
                        posts = result["output"]
                        post_id = posts[0]["postId"] if posts else ""
                        logger.info(f"[Postiz] MCP retry success: postId={post_id}")
                        return {
                            "status": "success",
                            "platform": platform,
                            "brand": self.brand_key,
                            "mode": mode,
                            "post_id": post_id,
                            "thread_parts": (len(comments) + 1) if comments else 1,
                            "via": "mcp_retry",
                        }
                except Exception as retry_e:
                    logger.error(f"[Postiz] MCP retry also failed: {retry_e}")

            return {
                "status": "failed",
                "platform": platform,
                "brand": self.brand_key,
                "error": str(e),
                "via": "mcp",
            }

    async def publish_batch(
        self,
        posts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Publish multiple posts via MCP batch endpoint.

        Each post dict should have:
            - content: str
            - platform: str
            - self_reply: str (optional)
            - media: list[str] (optional)
            - schedule_minutes: int (optional, offset from now)
        """
        mcp = await _get_mcp()
        base_time = datetime.now(timezone.utc) + timedelta(minutes=5)

        batch_entries = []
        for i, post in enumerate(posts):
            integration_id = post.get("integration_id") or resolve_integration_id(
                self.brand_key, post.get("platform", "twitter")
            )

            schedule_offset = post.get("schedule_minutes", i * 60)
            schedule_time = base_time + timedelta(minutes=schedule_offset)
            platform = post.get("platform", "twitter")
            settings = post.get("settings") or PLATFORM_DEFAULT_SETTINGS.get(platform.lower(), [])

            entry = {
                "integration_id": integration_id,
                "content_html": _text_to_html(post["content"]),
                "date_utc": schedule_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "attachments": post.get("media", []),
                "comments": [_text_to_html(post["self_reply"])] if post.get("self_reply") else [],
                "settings": settings,
                "type": post.get("mode", "schedule"),
            }
            batch_entries.append(entry)

        logger.info(f"[Postiz] Batch publishing {len(batch_entries)} posts via MCP")

        try:
            result = await mcp.schedule_batch(batch_entries)
            return {
                "status": "success",
                "total": len(batch_entries),
                "result": result,
                "via": "mcp",
            }
        except Exception as e:
            logger.error(f"[Postiz] Batch MCP failed: {e}")
            return {"status": "failed", "reason": str(e), "via": "mcp"}
