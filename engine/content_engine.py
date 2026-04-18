"""
Content engine — the scheduler that took Oyster Labs from $0 → $4M.

Architecture:
    generate → classify → score → gate → schedule → post → self-reply → measure

Runs 24/7 across 10 channels (4 Twitter accounts + 4 Bluesky + 2 LinkedIn).
Output cadence: ~37 posts/day, ~259/week.

This is the production loop. Simplified for readability; the real version has
retries, circuit breakers, observability hooks, and per-brand personas. The
architecture is identical.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from signal_weights import (
    MIN_SHIPPABLE_SCORE,
    SAFETY_TIER_MAX_SHARE,
    PostProjection,
    SIGNAL_WEIGHTS,
)


# --------------------------------------------------------------------------- #
# Types
# --------------------------------------------------------------------------- #

Platform = Literal["twitter", "bluesky", "linkedin"]
SafetyTier = Literal["A", "B", "C", "D"]


@dataclass
class Candidate:
    """A candidate post before it's been scored or gated."""
    brand: str
    platform: Platform
    text: str
    thread_continuation: str | None = None   # for the 75× self-reply lever
    hook_type: str = "question"              # question | contrarian | teardown | data
    safety_tier: SafetyTier = "A"
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScoredPost(Candidate):
    projection: PostProjection | None = None
    score: float = 0.0


# --------------------------------------------------------------------------- #
# 1. GENERATE — produce candidate posts from prompt templates + brand voice
# --------------------------------------------------------------------------- #

async def generate_candidates(brand: str, platform: Platform, n: int = 20) -> list[Candidate]:
    """Generate N candidate posts for a brand/platform pair.

    Real implementation: prompted LLM call with brand voice + topic bank +
    hook-type distribution. Stubbed here so the file is self-contained.
    """
    hooks = ["question", "contrarian", "teardown", "data"]
    return [
        Candidate(
            brand=brand,
            platform=platform,
            text=f"[{brand}] candidate #{i}",
            thread_continuation=f"[{brand}] self-reply #{i}",
            hook_type=random.choice(hooks),
            safety_tier=random.choices(["A", "B", "C", "D"], weights=[60, 30, 8, 2])[0],
        )
        for i in range(n)
    ]


# --------------------------------------------------------------------------- #
# 2. CLASSIFY + SCORE — predict signals and compute weighted score
# --------------------------------------------------------------------------- #

async def score_candidate(c: Candidate) -> ScoredPost:
    """Run the signal classifier and produce a weighted score.

    In production this calls the trained classifier. Stubbed with plausible
    distributions here — shape matches production output.
    """
    # A post with a queued self-reply projects very high on author_replies_own_post
    has_self_reply = c.thread_continuation is not None

    projection = PostProjection(
        p_author_replies_own_post = 0.97 if has_self_reply else 0.05,
        p_being_replied_to        = 0.40 if c.hook_type in ("question", "contrarian") else 0.15,
        p_profile_click           = 0.18,
        p_deep_dwell_over_2min    = 0.50 if has_self_reply else 0.10,
        p_retweet                 = 0.06,
        p_like                    = 0.55,
        p_negative_feedback       = {"A": 0.005, "B": 0.02, "C": 0.08, "D": 0.30}[c.safety_tier],
        p_report                  = {"A": 0.0, "B": 0.0005, "C": 0.005, "D": 0.05}[c.safety_tier],
    )
    return ScoredPost(
        brand=c.brand,
        platform=c.platform,
        text=c.text,
        thread_continuation=c.thread_continuation,
        hook_type=c.hook_type,
        safety_tier=c.safety_tier,
        generated_at=c.generated_at,
        projection=projection,
        score=projection.score(),
    )


# --------------------------------------------------------------------------- #
# 3. GATE — kill posts below threshold + enforce safety tier quotas
# --------------------------------------------------------------------------- #

def gate(posts: list[ScoredPost]) -> list[ScoredPost]:
    """Apply shipping threshold and tier quotas. Returns the survivors."""
    # Step 1: kill sub-threshold and all tier D
    survivors = [p for p in posts if p.score >= MIN_SHIPPABLE_SCORE and p.safety_tier != "D"]

    # Step 2: enforce tier C quota — never >10% of daily volume
    total = len(survivors)
    tier_c_cap = int(total * SAFETY_TIER_MAX_SHARE["C"])
    tier_c = [p for p in survivors if p.safety_tier == "C"][:tier_c_cap]
    others = [p for p in survivors if p.safety_tier != "C"]
    return sorted(others + tier_c, key=lambda p: p.score, reverse=True)


# --------------------------------------------------------------------------- #
# 4. SCHEDULE — stagger posts to beat author-diversity decay
# --------------------------------------------------------------------------- #

def schedule(posts: list[ScoredPost], start: datetime, window_hours: int = 16) -> list[tuple[datetime, ScoredPost]]:
    """Space posts across the active window to avoid diversity decay."""
    if not posts:
        return []
    gap = timedelta(seconds=(window_hours * 3600) // max(1, len(posts)))
    return [(start + gap * i, post) for i, post in enumerate(posts)]


# --------------------------------------------------------------------------- #
# 5. POST — actually publish (stubbed) + queue the self-reply
# --------------------------------------------------------------------------- #

async def publish(scheduled: list[tuple[datetime, ScoredPost]]) -> None:
    """Publish each post at its scheduled time, then fire the 75× self-reply."""
    for when, post in scheduled:
        # Wait until scheduled time (simplified; real impl uses a proper scheduler)
        # await asyncio.sleep(max(0, (when - datetime.utcnow()).total_seconds()))

        # 1) Post the main content
        print(f"[{when.isoformat()}] POST  {post.platform}/{post.brand}: {post.text[:60]}")

        # 2) Fire the 75× self-reply within the 3-minute optimal window.
        #    This single pattern is the largest lever in the entire system.
        if post.thread_continuation:
            reply_at = when + timedelta(minutes=2, seconds=45)
            print(f"[{reply_at.isoformat()}] REPLY {post.platform}/{post.brand}: {post.thread_continuation[:60]}")


# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #

async def run_daily_cycle(brands: list[str], platforms: list[Platform]) -> None:
    all_posts: list[ScoredPost] = []
    for brand in brands:
        for platform in platforms:
            candidates = await generate_candidates(brand, platform, n=20)
            scored     = await asyncio.gather(*(score_candidate(c) for c in candidates))
            all_posts.extend(scored)

    shipped = gate(all_posts)
    scheduled = schedule(shipped, start=datetime.utcnow().replace(hour=6, minute=0, second=0))
    await publish(scheduled)

    print()
    print(f"Generated:  {len(brands) * len(platforms) * 20}")
    print(f"Shipped:    {len(shipped)}")
    print(f"Top score:  {shipped[0].score:.2f}" if shipped else "nothing shipped")


if __name__ == "__main__":
    asyncio.run(run_daily_cycle(
        brands=["oyster", "puffy_ai", "claw_glasses", "claw_phones"],
        platforms=["twitter", "bluesky", "linkedin"],
    ))
