"""
OmniIdeator v2 — Report-Then-Generate pattern.

Flow:
  1. Generate a marketing research report (factual, analytical)
  2. From the report, generate a platform-agnostic seed idea (creative)
  3. Condense loop if needed (max 3 retries)

This two-step approach produces much better content than single-shot generation
because the LLM first reasons about the topic (report) then creates (idea).
Inspired by LangChain Social Media Agent's research-then-create pattern.
"""

import asyncio
import logging
from typing import Dict, Any

from .memory import NarrativeMemory
from .post_structures import select_structure, get_structure_prompt, get_random_hook

logger = logging.getLogger(__name__)


# Platform-specific output format instructions (injected into Step 2)
PLATFORM_OUTPUT_RULES = {
    "twitter": (
        "OUTPUT FORMAT: Write a 2-3 part X (Twitter) thread.\n"
        "- Part 1: Hook — bold claim, hot take, or provocative question. MUST be under 280 chars.\n"
        "- Part 2: Evidence — specific numbers, real data, engineering details, comparisons. MUST be under 280 chars.\n"
        "- Part 3: MANDATORY — end with a direct question that invites debate ('Would you...?', 'What's your...?', 'Is X really...?'). MUST be under 280 chars.\n"
        "Separate parts with --- on its own line. No hashtags. No prefixes. No 'Part 1:'. Raw text only.\n"
        "ZERO emojis. ZERO hashtags. Proper grammar but casual tone.\n"
        "\n"
        "ALGORITHM OPTIMIZATION (follow these to maximize reach):\n"
        "- Part 3 MUST end with a question mark — replies = 27x algorithm weight.\n"
        "- Include concrete data (numbers, %, comparisons) — bookmarks = save value.\n"
        "- Be contrarian or surprising — retweets come from 'I need people to see this'.\n"
        "- Thread format = 20x dwell time weight (reader stays >2min).\n"
    ),
    "bluesky": (
        "OUTPUT FORMAT: Write a single Bluesky post, MUST be under 300 characters.\n"
        "Conversational, like sharing a thought. Be concise but specific.\n"
        "ZERO emojis. ZERO hashtags. Raw text only.\n"
    ),
    "linkedin": (
        "OUTPUT FORMAT: Write a LinkedIn post, 800-1200 characters.\n"
        "Start with a compelling hook line, then hard line break.\n"
        "Use choppy paragraphs (1-2 sentences max). Let moments breathe.\n"
        "Tell a story. Use 'I' or 'We'. Authentic and grounded.\n"
        "NO corporate fluff. NO hashtags. NO CTAs like 'What do you think?'\n"
        "NO slang (tbh, ngl, larp, lmao, fr, af, imo, rn, lowkey, highkey, based, cope, bruh, fam).\n"
    ),
    "linkedin_bruno": (
        "OUTPUT FORMAT: Write a LinkedIn post from a hardware founder's personal account, 800-1200 characters.\n"
        "Start with a compelling hook line, then hard line break.\n"
        "Use choppy paragraphs (1-2 sentences max). Personal and reflective.\n"
        "Use 'I' statements. Share real experiences and technical details.\n"
        "NO corporate fluff. NO hashtags. NO CTAs like 'What do you think?'\n"
        "NO slang (tbh, ngl, larp, lmao, fr, af, imo, rn, lowkey, highkey, based, cope, bruh, fam).\n"
    ),
}

# Shared anti-pattern rules injected into every platform
_SHARED_RULES = (
    "NO AI TROPES: Never use leverage, delve, crucial, testament, landscape, realm, "
    "tapestry, navigate, innovative, unlock, dive, paradigm, game-changer, revolutionize, "
    "ecosystem, synergy, holistic, robust, cutting-edge, groundbreaking, seamless, empower.\n"
    "NEVER break character. NEVER mention you are an AI.\n"
    "NEVER mention any sibling brands.\n"
)


class OmniIdeator:
    """Core Brain: Generates platform-ready content via Report-Then-Generate."""

    def __init__(self, cdp_port: int = 9222):
        self.cdp_port = cdp_port

    async def generate_seed_idea(
        self,
        campaign_name: str,
        objective: str,
        memory_state: Dict[str, Any],
        brand_context: str,
        trending_signals: str = "",
        reflection_rules: str = "",
        content_pillar: str = "",
        platform: str = "twitter",
        structure: str = "",
    ) -> str:
        """
        Two-step generation:
          Step 1: Generate a marketing research report (factual analysis)
          Step 2: From the report, generate PLATFORM-READY content directly

        The output from Step 2 is the final post — no second LLM call needed.
        """
        history = "\n".join(memory_state.get("history", [])[:5])
        current_arc = memory_state.get("current_arc", "Initial rollout.")

        # Load brand-specific reflection rules if available
        brand_reflections = self._load_brand_reflections(brand_context)

        # Platform-specific max_tokens
        report_tokens = 800
        if platform in ("linkedin", "linkedin_bruno"):
            content_tokens = 1200
        else:
            content_tokens = 600

        # ── Step 1: Marketing Research Report ──

        report = await self._generate_report(
            objective=objective,
            current_arc=current_arc,
            brand_context=brand_context,
            trending_signals=trending_signals,
            reflection_rules=reflection_rules,
            content_pillar=content_pillar,
            brand_reflections=brand_reflections,
            history=history,
            max_tokens=report_tokens,
        )

        # ── Structure Selection (if not provided) ──
        if not structure:
            import datetime
            weekday = datetime.datetime.now().weekday()
            recently_used = [h.split("|")[0].strip() for h in memory_state.get("history", [])[:3]
                           if "|" in h]
            structure = select_structure(weekday=weekday, exclude=recently_used)
            logger.info(f"[Structure] Selected: {structure} (weekday={weekday})")

        structure_prompt = get_structure_prompt(structure, platform)
        hook_inspiration = get_random_hook()

        # ── Step 2: Platform-ready content from Report ──

        content = await self._generate_from_report(
            report=report,
            brand_context=brand_context,
            reflection_rules=reflection_rules,
            brand_reflections=brand_reflections,
            history=history,
            platform=platform,
            max_tokens=content_tokens,
            structure_prompt=structure_prompt,
            hook_inspiration=hook_inspiration,
        )

        if not content:
            # Fallback
            import uuid
            content = (
                f"Focus on building great products rather than playing zero-sum games. "
                f"True innovation comes from solving real problems. ({uuid.uuid4().hex[:4]})"
            )

        logger.info(f"[Content Generated for {platform}]: {content[:100]}...")
        return content

    # ──────────────────────────────────────────────────────────

    async def _generate_report(
        self,
        *,
        objective: str,
        current_arc: str,
        brand_context: str,
        trending_signals: str,
        reflection_rules: str,
        content_pillar: str,
        brand_reflections: str,
        history: str,
        max_tokens: int = 800,
    ) -> str:
        """Step 1: Generate a factual marketing research report."""
        from .llm import generate_text

        trending_block = ""
        if trending_signals:
            trending_block = f"""
REAL-WORLD SIGNALS (MANDATORY — your report MUST reference at least one):
{trending_signals}

REQUIREMENT: Pick the most relevant signal above and build your report around it. Connect it to the brand's perspective. Do NOT ignore these signals — content that reacts to real events gets 3-5x more engagement than generic posts.
"""

        pillar_block = ""
        if content_pillar:
            pillar_block = f"""
CONTENT FOCUS (mandatory topic area): {content_pillar}
Your report MUST center on this topic.
"""

        reflection_block = ""
        if reflection_rules:
            reflection_block = f"""
ANALYTICS FEEDBACK (strict rules from past performance):
{reflection_rules}
"""

        brand_reflection_block = ""
        if brand_reflections:
            brand_reflection_block = f"""
BRAND STYLE RULES (learned from human edits — follow these exactly):
{brand_reflections}
"""

        prompt = f"""You are a marketing analyst. Write a brief research report (3-5 bullet points) about the current state of the topic below. Be factual, specific, and cite real trends/data where possible.

BRAND & PERSONA CONTEXT:
{brand_context}

OBJECTIVE: {objective}
NARRATIVE ARC: {current_arc}

{pillar_block}
{trending_block}
{reflection_block}
{brand_reflection_block}

DO NOT repeat these past angles:
{history}

Your report should cover:
1. What's happening in this space RIGHT NOW (trends, news, shifts)
2. What the audience cares about (pain points, aspirations)
3. A contrarian or surprising angle the brand can own
4. One specific fact, stat, or example to anchor the argument

Write the report as bullet points. Be analytical, not creative. Facts first.

MARKETING REPORT:"""

        logger.info(f"[Ideator] Step 1: Generating marketing report...")

        report = await generate_text(
            system_prompt=(
                "You are a marketing research analyst. Write factual, analytical reports "
                "about brand topics. Use real trends, data points, and industry knowledge. "
                "Be specific and evidence-based. Never use marketing fluff. "
                "Never mention you are an AI."
            ),
            user_message=prompt,
            prefer_grok=False,
            max_tokens=max_tokens,
        )

        if not report:
            report = (
                f"Topic: {content_pillar or objective}\n"
                f"- Market is shifting toward decentralized, user-owned infrastructure\n"
                f"- Privacy and sovereignty are emerging consumer priorities\n"
                f"- Hardware+AI convergence is underpriced by the market"
            )

        logger.info(f"[Report]: {report[:120]}...")
        return report

    async def _generate_from_report(
        self,
        *,
        report: str,
        brand_context: str,
        reflection_rules: str,
        brand_reflections: str,
        history: str,
        platform: str = "twitter",
        max_tokens: int = 600,
        structure_prompt: str = "",
        hook_inspiration: str = "",
    ) -> str:
        """Step 2: Generate PLATFORM-READY content from the research report.

        This is the FINAL output — no second LLM call needed.
        Platform formatting rules are baked directly into the prompt.
        """
        from .llm import generate_text

        reflection_block = ""
        if reflection_rules:
            reflection_block = f"""
STRICT DO'S AND DON'TS:
{reflection_rules}
"""

        brand_reflection_block = ""
        if brand_reflections:
            brand_reflection_block = f"""
BRAND VOICE RULES (learned from human edits):
{brand_reflections}
"""

        # Get platform-specific output rules
        platform_rules = PLATFORM_OUTPUT_RULES.get(platform, PLATFORM_OUTPUT_RULES["twitter"])

        # Structure-specific prompt (narrative shape)
        structure_block = ""
        if structure_prompt:
            structure_block = f"\n{structure_prompt}\n"

        hook_block = ""
        if hook_inspiration:
            hook_block = f"\nHOOK INSPIRATION (use as style reference, do NOT copy verbatim): \"{hook_inspiration}\"\n"

        prompt = f"""Based on the marketing research report below, write the FINAL post for {platform.upper().replace('_BRUNO', ' (personal account)')}.

RESEARCH REPORT:
{report}

BRAND & PERSONA:
{brand_context}

{reflection_block}
{brand_reflection_block}

DO NOT repeat these past angles:
{history}

{structure_block}
{hook_block}
{platform_rules}
{_SHARED_RULES}

REQUIREMENTS:
1. Ground it in something SPECIFIC from the report (a real event, news, stat, or trend)
2. Must sound like a HUMAN founder thinking out loud, not a marketer
3. Include concrete details — numbers, specs, real comparisons. Generic claims are banned.
4. MUST include a QUESTION that invites replies (27x algorithm weight). Examples:
   - "Would you trade X for Y?"
   - "What's stopping [audience] from doing X?"
   - "Is X actually better than Y, or are we fooling ourselves?"
   People who reply to your post = 27x boost. Make them WANT to answer.
5. PRESERVE all specific numbers, technical details, and engineering specifics. Do NOT compress or summarize away the good stuff.
6. Make it BOOKMARK-WORTHY: include a surprising fact, a useful comparison, or a concrete takeaway people want to save. Posts with high bookmark rates get recommended to new audiences.
7. Be CONTRARIAN — agree-bait gets likes, disagree-bait gets retweets and replies. Pick a side.

BAD: "AI is revolutionizing the tech landscape"
GOOD: "Apple just killed sideloading in the EU. If you can't install your own apps on hardware you paid for, you don't own that device. We built ClawPhones specifically because this was inevitable — full root access, no gatekeepers."

Your post (raw text only, no prefixes):"""

        logger.info(f"[Ideator] Step 2: Generating {platform} content from report...")

        content = await generate_text(
            system_prompt=(
                "You are a founder/builder writing a social media post. "
                "Stay STRICTLY in character based on the brand context. "
                "Be bold, specific, and human. Never sound like a marketer. "
                "Never break character. Never mention you are an AI. "
                "Output ONLY the post text — no prefixes, no quotes, no explanations."
            ),
            user_message=prompt,
            prefer_grok=True,
            max_tokens=max_tokens,
        )

        if content:
            logger.info(f"[Content for {platform}]: {content[:100]}...")

        return content

    # ──────────────────────────────────────────────────────────

    def _load_brand_reflections(self, brand_context: str) -> str:
        """Load brand-specific reflection rules learned from human edits."""
        import os
        from pathlib import Path

        # Extract brand name from context (heuristic)
        brand_key = ""
        for bk in ("clawglasses", "oysterecosystem", "ubsphone"):
            if bk in brand_context.lower():
                brand_key = bk
                break

        if not brand_key:
            return ""

        reflections_dir = Path(__file__).parent / "reflections"
        rules_file = reflections_dir / f"{brand_key}_rules.md"

        if rules_file.exists():
            rules = rules_file.read_text().strip()
            if rules:
                logger.info(f"[Reflections] Loaded {len(rules)} chars of brand rules for {brand_key}")
                return rules

        return ""
