"""
Reflections — Self-improving brand voice learning from human edits.

When a human edits content via review.py, we:
1. Store the original → edited diff in {brand}_edits.jsonl
2. Periodically analyze diffs to extract brand voice rules
3. Save rules to {brand}_rules.md (injected into ideator prompts)

This creates a feedback loop: human edits → learned rules → better generation → fewer edits needed.
Inspired by LangChain Social Media Agent's reflection pattern.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REFLECTIONS_DIR = Path(__file__).parent / "reflections"


def ensure_dir():
    REFLECTIONS_DIR.mkdir(parents=True, exist_ok=True)


def get_edit_history(brand: str, limit: int = 20) -> list[dict]:
    """Load recent edit history for a brand."""
    ensure_dir()
    edits_file = REFLECTIONS_DIR / f"{brand}_edits.jsonl"
    if not edits_file.exists():
        return []

    entries = []
    with open(edits_file) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Return most recent entries
    return entries[-limit:]


def get_brand_rules(brand: str) -> str:
    """Load current brand rules."""
    ensure_dir()
    rules_file = REFLECTIONS_DIR / f"{brand}_rules.md"
    if rules_file.exists():
        return rules_file.read_text().strip()
    return ""


def save_brand_rules(brand: str, rules: str):
    """Save brand rules."""
    ensure_dir()
    rules_file = REFLECTIONS_DIR / f"{brand}_rules.md"
    rules_file.write_text(rules.strip() + "\n")
    logger.info(f"[Reflections] Saved {len(rules)} chars of rules for {brand}")


async def analyze_edits(brand: str, min_edits: int = 3) -> Optional[str]:
    """
    Analyze edit history and generate/update brand rules.
    Requires at least min_edits entries to have enough signal.
    Returns the new rules string, or None if not enough data.
    """
    edits = get_edit_history(brand, limit=30)
    if len(edits) < min_edits:
        logger.info(
            f"[Reflections] {brand}: only {len(edits)} edits, need {min_edits} to analyze"
        )
        return None

    # Build analysis prompt
    edit_examples = []
    for e in edits[-15:]:  # Last 15 edits
        edit_examples.append(
            f"ORIGINAL: {e.get('original', '')[:200]}\n"
            f"EDITED TO: {e.get('edited', '')[:200]}\n"
            f"PLATFORM: {e.get('platform', 'unknown')}"
        )

    existing_rules = get_brand_rules(brand)
    existing_block = ""
    if existing_rules:
        existing_block = f"""
EXISTING RULES (update/refine these based on new edits):
{existing_rules}
"""

    prompt = f"""Analyze these human edits to content for the brand "{brand}".
The human edited the AI-generated originals into the edited versions.

EDIT HISTORY:
{'---'.join(edit_examples)}

{existing_block}

Based on these edits, identify the PATTERNS of what the human changed.
Generate a concise set of BRAND VOICE RULES that would prevent these edits in the future.

FORMAT — Write rules as a bulleted markdown list:
- DO: [specific instruction]
- DON'T: [specific anti-pattern]
- VOICE: [tone/style guidance]
- LENGTH: [character/word preferences]

Be extremely specific. Not "be more casual" but "use sentence fragments, drop periods at end of sentences, never use exclamation marks".

Max 15 rules. Most important rules first.

BRAND RULES:"""

    from .llm import generate_text

    logger.info(f"[Reflections] Analyzing {len(edits)} edits for {brand}...")

    rules = await generate_text(
        system_prompt=(
            "You are a brand voice analyst. Analyze human edits to AI-generated content "
            "and extract specific, actionable style rules. Be precise and pattern-focused. "
            "Focus on what changed and WHY. Output rules only, no commentary."
        ),
        user_message=prompt,
        prefer_grok=False,  # Use Claude/Gemini for analysis
    )

    if rules:
        save_brand_rules(brand, rules)
        logger.info(f"[Reflections] Generated {len(rules)} chars of rules for {brand}")
        return rules

    return None


async def refresh_all_brands():
    """Refresh reflection rules for all brands with enough edit data."""
    ensure_dir()
    brands = set()
    for f in REFLECTIONS_DIR.glob("*_edits.jsonl"):
        brand = f.stem.replace("_edits", "")
        brands.add(brand)

    results = {}
    for brand in brands:
        try:
            rules = await analyze_edits(brand)
            results[brand] = "updated" if rules else "not enough data"
        except Exception as e:
            results[brand] = f"error: {e}"
            logger.error(f"[Reflections] Error analyzing {brand}: {e}")

    return results


# ── CLI ──────────────────────────────────────────────────────

async def _cli_main():
    import argparse

    parser = argparse.ArgumentParser(description="Brand Voice Reflections")
    sub = parser.add_subparsers(dest="cmd")

    # show
    p_show = sub.add_parser("show", help="Show brand rules")
    p_show.add_argument("brand", help="Brand key (e.g., clawglasses)")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze edits and generate rules")
    p_analyze.add_argument("brand", help="Brand key")
    p_analyze.add_argument("--min-edits", type=int, default=3)

    # refresh
    sub.add_parser("refresh", help="Refresh all brand rules")

    # history
    p_hist = sub.add_parser("history", help="Show edit history")
    p_hist.add_argument("brand", help="Brand key")
    p_hist.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()

    if args.cmd == "show":
        rules = get_brand_rules(args.brand)
        if rules:
            print(f"\n📋 Brand Rules for {args.brand}:\n")
            print(rules)
        else:
            print(f"📭 No rules found for {args.brand}")

    elif args.cmd == "analyze":
        rules = await analyze_edits(args.brand, min_edits=args.min_edits)
        if rules:
            print(f"\n✅ Generated rules for {args.brand}:\n")
            print(rules)
        else:
            print(f"📭 Not enough edit data for {args.brand}")

    elif args.cmd == "refresh":
        results = await refresh_all_brands()
        print("\n📊 Refresh Results:")
        for brand, status in results.items():
            print(f"  {brand}: {status}")

    elif args.cmd == "history":
        edits = get_edit_history(args.brand, limit=args.limit)
        if edits:
            print(f"\n📜 Last {len(edits)} edits for {args.brand}:\n")
            for e in edits:
                print(f"  [{e.get('timestamp', '?')[:10]}] {e.get('platform', '?')}")
                print(f"    Original: {e.get('original', '')[:80]}...")
                print(f"    Edited:   {e.get('edited', '')[:80]}...")
                print()
        else:
            print(f"📭 No edit history for {args.brand}")

    else:
        parser.print_help()


if __name__ == "__main__":
    import asyncio
    asyncio.run(_cli_main())
