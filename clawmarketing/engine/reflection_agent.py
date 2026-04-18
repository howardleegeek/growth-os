#!/usr/bin/env python3
import os
import sys
import json
from typing import Dict, Any

# Ensure PYTHONPATH is active
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.memory import NarrativeMemory
from engine.llm import generate_text


class ReflectionAgent:
    """Agent that analyzes post performance and provides dos and don'ts."""

    def __init__(self):
        self.memory = NarrativeMemory()

    async def reflect_on_campaign(self, campaign_name: str) -> str:
        """
        Analyze recent analytics for a campaign and return a summary of
        what worked, what didn't, and specific dos/don'ts for the Ideator.
        """
        state = self.memory.get_campaign_state(campaign_name)
        analytics = state.get("analytics", [])

        if not analytics:
            return "No analytics data available yet. Continue exploring varied content angles."

        # Sort by engagement (likes + replies + retweets)
        def get_engagement(m):
            return m.get("likes", 0) + m.get("replies", 0) + m.get("retweets", 0)

        sorted_analytics = sorted(analytics, key=get_engagement, reverse=True)

        # Take the top 3 and bottom 3 to compare
        top_posts = sorted_analytics[:3]

        # Only consider bottom posts if we have enough
        bottom_posts = sorted_analytics[-3:] if len(sorted_analytics) >= 6 else []

        if get_engagement(top_posts[0]) == 0:
            return "No engagement data available yet on existing posts. Continue exploring varied content angles."

        prompt_data = {
            "top_performing_posts": [
                {
                    "text": p.get("text"),
                    "engagement": get_engagement(p),
                    "impressions": p.get("impressions", 0),
                }
                for p in top_posts
            ],
            "low_performing_posts": [
                {
                    "text": p.get("text"),
                    "engagement": get_engagement(p),
                    "impressions": p.get("impressions", 0),
                }
                for p in bottom_posts
            ],
        }

        system_prompt = (
            "You are an expert Social Media Strategist analyzing content performance. "
            "Your job is to read the performance data of recent posts and deduce what resonates with the audience vs what fails.\n\n"
            "Produce a highly concise 'Do's and Don'ts' guide for future content generation. "
            "Focus on tone, structure, topic, and formatting. "
            "Output ONLY the rules in a bulleted format, nothing else."
        )

        user_message = f"Here is the recent performance data. Provide strictly the Do's and Don'ts.\n\n{json.dumps(prompt_data, indent=2)}"

        try:
            print(
                f"🧠 [Reflection Agent] Analyzing {len(analytics)} posts for {campaign_name}..."
            )
            reflection_result = await generate_text(
                system_prompt, user_message, prefer_grok=False
            )
            if reflection_result:
                # Cache the reflection in memory
                state["latest_reflection"] = reflection_result
                db_file = self.memory._get_file_path(campaign_name)
                with open(db_file, "w") as f:
                    json.dump(state, f, indent=2)
                return reflection_result
        except Exception as e:
            print(f"⚠️ [Reflection Agent] Error reflecting: {e}")

        # Fallback if we already have a cached reflection
        return state.get(
            "latest_reflection",
            "No analytics data available yet. Continue exploring varied content angles.",
        )


async def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--campaign",
        required=True,
        help="Campaign mapping key (e.g. clawglasses_bruno_daily)",
    )
    args = parser.parse_args()

    agent = ReflectionAgent()
    rules = await agent.reflect_on_campaign(args.campaign)
    print("=== PERFORMANCE REFLECTION ===")
    print(rules)
    print("==============================")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
