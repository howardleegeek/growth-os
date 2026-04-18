"""
Analytics Feedback Loop — Pulls Postiz analytics, generates LLM feedback, stores in NarrativeMemory.

Flow:
  1. posts:list → get recent published posts for brand/platform
  2. analytics:post <id> → get per-post engagement data
  3. LLM → generate actionable feedback rules from data
  4. NarrativeMemory.save_performance_feedback() → store for ideator

The ideator reads performance_history from memory state and adjusts content angles accordingly.
"""

import asyncio
import json
import logging
import os
import subprocess
import shutil
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def _get_postiz_bin() -> str:
    path = shutil.which("postiz")
    if path:
        return path
    for candidate in ["/opt/homebrew/bin/postiz", "/usr/local/bin/postiz"]:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("postiz CLI not found")


def _get_api_key() -> str:
    key = os.environ.get("POSTIZ_API_KEY", "")
    if key:
        return key
    env_path = os.path.expanduser("~/.oyster-keys/postiz.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[7:]
                if line.startswith("POSTIZ_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _run_postiz_cmd(args: List[str], timeout: int = 30) -> Optional[str]:
    """Run a postiz CLI command and return stdout, or None on failure."""
    postiz_bin = _get_postiz_bin()
    env = os.environ.copy()
    api_key = _get_api_key()
    if api_key:
        env["POSTIZ_API_KEY"] = api_key

    try:
        result = subprocess.run(
            [postiz_bin] + args,
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        if result.returncode == 0:
            return result.stdout
        logger.warning(f"postiz {' '.join(args[:2])} failed: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        logger.warning(f"postiz {' '.join(args[:2])} timed out ({timeout}s)")
    except Exception as e:
        logger.error(f"postiz {' '.join(args[:2])} error: {e}")
    return None


def _parse_json_from_output(output: str) -> Any:
    """Extract JSON from postiz CLI output (skips emoji header lines)."""
    if not output:
        return None
    # Find the first [ or { in the output
    for i, ch in enumerate(output):
        if ch in ("[", "{"):
            try:
                return json.loads(output[i:])
            except json.JSONDecodeError:
                pass
    # Try parsing the whole thing
    try:
        return json.loads(output.strip())
    except json.JSONDecodeError:
        return None


# ── CLI Wrappers ──────────────────────────────────────────────────

def list_recent_posts(
    integration_id: Optional[str] = None,
    days_back: int = 7,
    days_forward: int = 7,
) -> List[Dict[str, Any]]:
    """List recent posts from Postiz. Optionally filter by integration."""
    start = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    end = (datetime.now(timezone.utc) + timedelta(days=days_forward)).strftime("%Y-%m-%dT23:59:59Z")

    output = _run_postiz_cmd(["posts:list", "--startDate", start, "--endDate", end])
    data = _parse_json_from_output(output)
    if not data:
        return []

    posts = data.get("posts", data) if isinstance(data, dict) else data
    if not isinstance(posts, list):
        return []

    # Filter by integration if specified
    if integration_id:
        posts = [
            p for p in posts
            if p.get("integration", {}).get("id") == integration_id
        ]

    return posts


def get_post_analytics(post_id: str) -> Optional[Dict[str, Any]]:
    """Get analytics for a specific post."""
    output = _run_postiz_cmd(["analytics:post", post_id])
    return _parse_json_from_output(output)


def get_platform_analytics(integration_id: str) -> Optional[Any]:
    """Get platform-level analytics for an integration."""
    output = _run_postiz_cmd(["analytics:platform", integration_id])
    return _parse_json_from_output(output)


# ── Analytics Aggregation ─────────────────────────────────────────

def aggregate_post_metrics(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pull analytics for each published post and aggregate metrics.
    Returns summary stats for LLM feedback generation.
    """
    published = [p for p in posts if p.get("state") == "PUBLISHED" and p.get("releaseId")]

    if not published:
        logger.info("No published posts with analytics data yet")
        return {"total_posts": len(posts), "published": 0, "metrics": []}

    metrics = []
    for post in published[:10]:  # Cap at 10 to avoid CLI spam
        post_id = post["id"]
        analytics = get_post_analytics(post_id)
        if analytics:
            # Extract content preview for context
            content_raw = post.get("content", "")
            # Strip HTML tags for preview
            import re
            content_clean = re.sub(r"<[^>]+>", "", content_raw)[:100]

            metrics.append({
                "post_id": post_id,
                "content_preview": content_clean,
                "publish_date": post.get("publishDate", ""),
                "analytics": analytics,
            })

    return {
        "total_posts": len(posts),
        "published": len(published),
        "with_analytics": len(metrics),
        "metrics": metrics,
    }


# ── LLM Feedback Generation ──────────────────────────────────────

async def generate_performance_feedback(
    aggregated: Dict[str, Any],
    brand_key: str,
    platform: str,
) -> Optional[str]:
    """
    Use LLM to analyze post performance and generate actionable feedback rules.
    Returns a 1-2 sentence rule the ideator should follow.
    """
    if not aggregated.get("metrics"):
        # No analytics data yet — generate a bootstrap rule
        total = aggregated.get("total_posts", 0)
        published = aggregated.get("published", 0)
        if total > 0 and published == 0:
            return f"All {total} posts are still in DRAFT state. Prioritize publishing scheduled content before generating more."
        return None

    # Format metrics for LLM
    metrics_text = []
    for m in aggregated["metrics"][:5]:
        metrics_text.append(
            f"- Post: \"{m['content_preview']}...\"\n"
            f"  Date: {m['publish_date']}\n"
            f"  Analytics: {json.dumps(m['analytics'], default=str)[:300]}"
        )
    metrics_block = "\n".join(metrics_text)

    from .llm import generate_text

    prompt = f"""Analyze these {platform} posts for brand "{brand_key}":

{metrics_block}

Based on engagement data, generate exactly ONE actionable rule (1-2 sentences) that the content ideator should follow tomorrow.
Focus on: what topic/angle/format got the most engagement vs least.
Example: "Posts with specific numbers/stats got 3x more replies than vague claims. Lead with concrete data points."
Example: "Thread-style posts outperformed single tweets by 2x. Use the self-reply for a data point or counterargument."

Your rule:"""

    feedback = await generate_text(
        system_prompt="You are a social media analytics strategist. Generate brief, actionable content rules from performance data.",
        user_message=prompt,
    )
    return feedback


# ── Main Loop ─────────────────────────────────────────────────────

async def run_analytics_feedback_loop(
    brand_key: str,
    platform: str,
    integration_id: str,
    memory: Any,  # NarrativeMemory instance
) -> Optional[str]:
    """
    Full analytics feedback loop for one brand/platform:
    1. List recent posts
    2. Pull per-post analytics
    3. Generate LLM feedback
    4. Store in NarrativeMemory

    Returns the feedback string, or None if no data.
    """
    campaign_name = f"{brand_key}_{platform}"

    logger.info(f"[Analytics] Pulling data for {campaign_name} (integration: {integration_id[:12]}...)")

    # 1. List recent posts for this integration
    posts = list_recent_posts(integration_id=integration_id, days_back=7, days_forward=7)
    logger.info(f"[Analytics] Found {len(posts)} posts for {campaign_name}")

    if not posts:
        return None

    # 2. Aggregate metrics
    aggregated = aggregate_post_metrics(posts)
    logger.info(
        f"[Analytics] {campaign_name}: {aggregated['published']} published, "
        f"{aggregated.get('with_analytics', 0)} with analytics"
    )

    # 3. Generate feedback via LLM
    feedback = await generate_performance_feedback(aggregated, brand_key, platform)
    if not feedback:
        return None

    logger.info(f"[Analytics] Feedback for {campaign_name}: {feedback[:100]}...")

    # 4. Store in memory
    memory.save_performance_feedback(campaign_name, feedback)

    return feedback
