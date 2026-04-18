"""
Post Structure Templates — 6 narrative structures for content generation.

Based on intern research (March 2026). Each structure defines the narrative
shape of a post, independent of platform formatting. The ideator selects
a structure before generating content, ensuring variety and intentional
post architecture instead of random generation.

Usage:
    from engine.post_structures import select_structure, get_structure_prompt

    structure = select_structure(weekday=0)  # Monday
    prompt_block = get_structure_prompt(structure, platform="twitter")
"""

import random
from typing import Optional

# ── Structure Definitions ──────────────────────────────────────────

STRUCTURES = {
    "ai_insights": {
        "name": "AI Insights",
        "purpose": "Thought leadership — interpret an AI trend and explain why it matters",
        "sections": ["Hook", "Insight", "Key Points (3-4)", "Brand Perspective", "Closing Thought"],
        "prompts": {
            "twitter": (
                "POST STRUCTURE: AI Insights (thought leadership)\n"
                "1. HOOK: Bold claim or surprising observation about an AI trend. Under 280 chars.\n"
                "2. EVIDENCE: 2-3 specific implications of this trend — real data, concrete examples. Under 280 chars.\n"
                "3. QUESTION: Connect the trend to real-world AI perception. End with a direct question that invites debate. Under 280 chars.\n"
                "Separate parts with --- on its own line.\n"
            ),
            "bluesky": (
                "POST STRUCTURE: AI Insights\n"
                "One sharp observation about an AI trend + why it matters for real-world AI.\n"
                "Be specific — name the trend, give one concrete implication.\n"
                "Under 300 chars. Single post.\n"
            ),
            "linkedin": (
                "POST STRUCTURE: AI Insights (thought leadership)\n"
                "1. HOOK: One-line insight about an AI trend. Hard line break after.\n"
                "2. CONTEXT: Why this trend matters — 2-3 choppy paragraphs with specific examples.\n"
                "3. KEY POINTS: 3-4 implications, each 1 sentence. Use bullet style if natural.\n"
                "4. BRAND LENS: How real-world AI perception fits into this shift. 1-2 sentences.\n"
                "5. CLOSE: Reflection or question. No generic CTAs.\n"
                "800-1200 chars total.\n"
            ),
            "linkedin_bruno": (
                "POST STRUCTURE: AI Insights (founder perspective)\n"
                "1. HOOK: Personal observation about an AI trend you're seeing firsthand.\n"
                "2. ANALYSIS: What this means for builders — share your engineering perspective.\n"
                "3. KEY POINTS: 3-4 implications with technical specifics.\n"
                "4. REFLECTION: How this connects to what you're building. Use 'I' statements.\n"
                "800-1200 chars total.\n"
            ),
        },
        "example_topics": [
            "agentic AI", "multimodal systems", "on-device AI",
            "AI development workflows", "wearable AI", "edge inference",
            "vision-language models", "AI agent orchestration",
        ],
    },

    "educational": {
        "name": "Educational",
        "purpose": "Teach something useful to developers or builders",
        "sections": ["Problem", "Explanation", "Best Practices (3-5)", "Brand Context", "Discussion Question"],
        "prompts": {
            "twitter": (
                "POST STRUCTURE: Educational (teach something)\n"
                "1. PROBLEM: Name a specific challenge when building real-world AI systems. Under 280 chars.\n"
                "2. INSIGHT: One key lesson or approach that addresses it — be concrete, cite specifics. Under 280 chars.\n"
                "3. QUESTION: Ask how others approach this challenge. Under 280 chars.\n"
                "Separate parts with --- on its own line.\n"
            ),
            "bluesky": (
                "POST STRUCTURE: Educational\n"
                "State a real challenge in building AI systems + the key insight that addresses it.\n"
                "Practical and specific. Under 300 chars.\n"
            ),
            "linkedin": (
                "POST STRUCTURE: Educational\n"
                "1. PROBLEM: Describe a challenge when building AI systems that interact with the physical world. 1-2 sentences.\n"
                "2. EXPLANATION: Explain the concept that addresses it. Choppy paragraphs.\n"
                "3. BEST PRACTICES: 3-5 practical tips or lessons. Use bullets naturally.\n"
                "4. CONTEXT: Briefly connect to real-world perception and wearable AI. 1-2 sentences.\n"
                "5. QUESTION: Ask readers how they approach this challenge.\n"
                "800-1200 chars total.\n"
            ),
            "linkedin_bruno": (
                "POST STRUCTURE: Educational (builder's lesson)\n"
                "1. PROBLEM: A challenge you hit while building. Personal experience.\n"
                "2. WHAT I LEARNED: The insight, with technical details.\n"
                "3. TIPS: 3-5 practical takeaways for other builders.\n"
                "4. CONNECT: How this applies to vision AI / on-device systems.\n"
                "5. QUESTION: What's your experience with this?\n"
                "800-1200 chars total.\n"
            ),
        },
        "example_topics": [
            "structuring AI projects", "prompt engineering workflows",
            "evaluation pipelines", "AI cost optimization",
            "agent orchestration", "on-device inference tradeoffs",
            "vision pipeline latency", "edge AI deployment",
        ],
    },

    "product_update": {
        "name": "Product Update",
        "purpose": "Announce improvements — show progress without hype",
        "sections": ["Hook", "Update Explanation", "Key Improvements (3-4)", "User Benefit", "Closing Vision"],
        "prompts": {
            "twitter": (
                "POST STRUCTURE: Product Update\n"
                "1. HOOK: What shipped or improved — be specific (version, feature name, metric). Under 280 chars.\n"
                "2. DETAILS: What changed and why it matters — concrete numbers (latency, accuracy, etc). Under 280 chars.\n"
                "3. QUESTION: Ask what users want next, or if they've hit the problem this solves. Under 280 chars.\n"
                "Separate parts with --- on its own line.\n"
            ),
            "bluesky": (
                "POST STRUCTURE: Product Update\n"
                "What shipped + one concrete improvement with a number.\n"
                "Builder tone, not press release. Under 300 chars.\n"
            ),
            "linkedin": (
                "POST STRUCTURE: Product Update\n"
                "1. HOOK: Announce the update. One line, hard break.\n"
                "2. EXPLANATION: What improved and why. Choppy paragraphs.\n"
                "3. IMPROVEMENTS: 3-4 specific capabilities or metrics. Bullet style.\n"
                "4. USER BENEFIT: How this makes real-world AI interaction better.\n"
                "5. VISION: One line — how this moves AI closer to the physical world.\n"
                "800-1200 chars. Not overly promotional.\n"
            ),
            "linkedin_bruno": (
                "POST STRUCTURE: Product Update (founder's perspective)\n"
                "1. HOOK: What we just shipped. Direct.\n"
                "2. WHY: The engineering decision behind this update.\n"
                "3. DETAILS: 3-4 improvements with technical specifics.\n"
                "4. WHAT'S NEXT: Where this takes us. Honest about what's still missing.\n"
                "800-1200 chars.\n"
            ),
        },
        "example_topics": [
            "better AI response quality", "improved latency",
            "new interaction capabilities", "OTA update",
            "developer SDK improvements", "battery optimization",
            "new language support", "vision model upgrade",
        ],
    },

    "product_launch": {
        "name": "Product Launch",
        "purpose": "Major announcement — confident and visionary",
        "sections": ["Announcement", "Product Description", "Key Features", "Vision", "Availability"],
        "prompts": {
            "twitter": (
                "POST STRUCTURE: Product Launch\n"
                "1. ANNOUNCEMENT: What launched — product name, one-line what it does. Bold and clear. Under 280 chars.\n"
                "2. KEY FACTS: 2-3 concrete specs or capabilities. Numbers matter. Under 280 chars.\n"
                "3. AVAILABILITY: Where to get it + a question about what people will build with it. Under 280 chars.\n"
                "Separate parts with --- on its own line.\n"
            ),
            "bluesky": (
                "POST STRUCTURE: Product Launch\n"
                "Announce what launched + the one fact that matters most (price, capability, availability).\n"
                "Confident but not hype. Under 300 chars.\n"
            ),
            "linkedin": (
                "POST STRUCTURE: Product Launch\n"
                "1. ANNOUNCEMENT: Clear launch statement. One line, hard break.\n"
                "2. DESCRIPTION: What the product enables. 2-3 choppy paragraphs.\n"
                "3. FEATURES: Key capabilities. Concrete specs.\n"
                "4. VISION: Why real-world AI perception matters.\n"
                "5. AVAILABILITY: Where to learn more or get it.\n"
                "800-1200 chars. Confident, visionary, builder-oriented.\n"
            ),
            "linkedin_bruno": (
                "POST STRUCTURE: Product Launch (founder's announcement)\n"
                "1. ANNOUNCEMENT: What we're launching and why it matters to me personally.\n"
                "2. BACKSTORY: The engineering journey — what it took to build this.\n"
                "3. FEATURES: Key capabilities with technical depth.\n"
                "4. VISION: What this means for the future of AI in the physical world.\n"
                "5. LINK: Where to check it out.\n"
                "800-1200 chars.\n"
            ),
        },
        "example_topics": [
            "new product version", "hardware revision",
            "SDK release", "platform launch",
            "partnership announcement", "new market entry",
        ],
    },

    "use_case_story": {
        "name": "Use Case / Story",
        "purpose": "Show real value through scenario-based storytelling",
        "sections": ["Scenario", "Problem", "Solution", "Result", "Takeaway"],
        "prompts": {
            "twitter": (
                "POST STRUCTURE: Use Case Story\n"
                "1. SCENARIO: Set the scene — a specific person, place, or situation where AI perception matters. Under 280 chars.\n"
                "2. RESULT: What happened when AI could actually see — concrete outcome with specifics. Under 280 chars.\n"
                "3. TAKEAWAY: Why this matters broadly. End with a question. Under 280 chars.\n"
                "Separate parts with --- on its own line.\n"
            ),
            "bluesky": (
                "POST STRUCTURE: Use Case Story\n"
                "A specific scenario where AI with vision made a real difference.\n"
                "Scene + outcome in one tight post. Under 300 chars.\n"
            ),
            "linkedin": (
                "POST STRUCTURE: Use Case / Story\n"
                "1. SCENARIO: Describe a real-world situation. Set the scene with specific details.\n"
                "2. PROBLEM: What challenge existed in that environment.\n"
                "3. SOLUTION: How AI with visual perception addressed it.\n"
                "4. RESULT: The concrete outcome — numbers, time saved, impact.\n"
                "5. TAKEAWAY: Why perception-enabled AI matters for the future.\n"
                "End with a discussion question.\n"
                "800-1200 chars. Story format, not a case study.\n"
            ),
            "linkedin_bruno": (
                "POST STRUCTURE: Use Case / Story (founder's experience)\n"
                "1. SCENE: A moment that changed how I think about this product.\n"
                "2. PROBLEM: What the person was struggling with.\n"
                "3. WHAT HAPPENED: The moment it clicked — specific, visceral.\n"
                "4. IMPACT: What it meant. Real numbers or real emotion.\n"
                "5. REFLECTION: Why this is the future. Be honest.\n"
                "800-1200 chars.\n"
            ),
        },
        "example_topics": [
            "warehouse inventory", "real-time translation",
            "accessibility — low vision", "field inspection",
            "healthcare rounds", "retail analytics",
            "education — lab assistance", "navigation for visually impaired",
        ],
    },

    "builder_philosophy": {
        "name": "Builder Philosophy / Narrative",
        "purpose": "Express engineering beliefs and product philosophy",
        "sections": ["Vision", "Builder Philosophy", "Engineering Approach", "Implication", "Closing Reflection"],
        "prompts": {
            "twitter": (
                "POST STRUCTURE: Builder Philosophy\n"
                "1. VISION: A bold statement about where AI is headed. Opinionated. Under 280 chars.\n"
                "2. WHY: The engineering philosophy behind your approach — why you build the way you do. Under 280 chars.\n"
                "3. QUESTION: A thought-provoking question about the future of AI. Under 280 chars.\n"
                "Separate parts with --- on its own line.\n"
            ),
            "bluesky": (
                "POST STRUCTURE: Builder Philosophy\n"
                "One strong opinion about how AI should work in the real world.\n"
                "Engineering conviction, not marketing. Under 300 chars.\n"
            ),
            "linkedin": (
                "POST STRUCTURE: Builder Philosophy / Narrative\n"
                "1. VISION: Bold statement about the future of AI. One line, hard break.\n"
                "2. PHILOSOPHY: How the team approaches building — what you believe and why.\n"
                "3. ENGINEERING: Why real-world testing and iteration matter. Specific examples.\n"
                "4. IMPLICATION: Why perception-based AI represents a major shift.\n"
                "5. REFLECTION: End with a thought-provoking question.\n"
                "800-1200 chars. Thoughtful, forward-looking.\n"
            ),
            "linkedin_bruno": (
                "POST STRUCTURE: Builder Philosophy (founder's beliefs)\n"
                "1. CONVICTION: Something I believe about AI that most people don't.\n"
                "2. WHY: The experience that shaped this belief.\n"
                "3. HOW WE BUILD: Our engineering approach, with specifics.\n"
                "4. WHERE THIS GOES: The implication for the industry.\n"
                "5. QUESTION: Challenge the reader to think differently.\n"
                "800-1200 chars.\n"
            ),
        },
        "example_topics": [
            "AI needs real senses, not just text", "on-device vs cloud tradeoffs",
            "why $99 matters", "open source AI hardware",
            "building for accessibility from day one", "the case against cloud-only AI",
            "why AI agents need eyes", "hardware iteration vs software iteration",
        ],
    },
}


# ── Weekly Distribution ────────────────────────────────────────────
# Suggested distribution weights per day of week (Mon=0, Sun=6)
# Based on intern's recommended weekly cadence

WEEKLY_WEIGHTS = {
    0: {"ai_insights": 0.4, "educational": 0.3, "builder_philosophy": 0.3},           # Monday
    1: {"educational": 0.4, "use_case_story": 0.3, "ai_insights": 0.3},               # Tuesday
    2: {"product_update": 0.4, "ai_insights": 0.3, "builder_philosophy": 0.3},         # Wednesday
    3: {"ai_insights": 0.3, "use_case_story": 0.4, "educational": 0.3},               # Thursday
    4: {"builder_philosophy": 0.4, "ai_insights": 0.3, "use_case_story": 0.3},         # Friday
    5: {"ai_insights": 0.5, "builder_philosophy": 0.3, "educational": 0.2},            # Saturday
    6: {"use_case_story": 0.4, "builder_philosophy": 0.3, "ai_insights": 0.3},         # Sunday
}

# Product launches/updates are event-driven, not scheduled — use them when there's real news


# ── Hook Library ───────────────────────────────────────────────────

HOOK_PATTERNS = {
    "insight": [
        "Most AI products fail for one simple reason.",
        "AI tools are getting smarter — but the workflows around them are still broken.",
        "The gap between AI demos and AI in production keeps growing.",
        "Everyone talks about AI agents. Almost nobody talks about what they can actually see.",
        "The biggest unlock for AI isn't a better model. It's better input.",
    ],
    "builder": [
        "Building AI products in 2026 looks very different from 2023.",
        "Every AI team eventually runs into this problem.",
        "We broke our inference pipeline three times before we got it right.",
        "The hardest part of shipping AI hardware isn't the hardware.",
        "We spent months optimizing latency. Here's what actually moved the needle.",
    ],
    "contrarian": [
        "Most AI marketing advice is wrong.",
        "The biggest AI adoption barrier isn't technology.",
        "Cloud AI is a crutch. On-device is the future.",
        "AI agents don't need better language models. They need eyes.",
        "Everyone's building AI chatbots. Almost nobody's building AI that can see.",
    ],
}


# ── Selection Logic ────────────────────────────────────────────────

def select_structure(
    weekday: int = 0,
    force_structure: Optional[str] = None,
    exclude: Optional[list] = None,
) -> str:
    """
    Select a post structure based on day-of-week weights.

    Args:
        weekday: Day of week (0=Monday, 6=Sunday)
        force_structure: Override with a specific structure key
        exclude: List of structure keys to exclude (e.g., recently used)

    Returns:
        Structure key (e.g., "ai_insights", "educational")
    """
    if force_structure and force_structure in STRUCTURES:
        return force_structure

    weights = WEEKLY_WEIGHTS.get(weekday, WEEKLY_WEIGHTS[0])

    if exclude:
        weights = {k: v for k, v in weights.items() if k not in exclude}

    if not weights:
        # Fallback if all excluded
        weights = {"ai_insights": 0.5, "builder_philosophy": 0.5}

    keys = list(weights.keys())
    probs = list(weights.values())
    total = sum(probs)
    probs = [p / total for p in probs]

    return random.choices(keys, weights=probs, k=1)[0]


def get_structure_prompt(structure_key: str, platform: str = "twitter") -> str:
    """
    Get the structure-specific prompt block for a given platform.

    Args:
        structure_key: Key from STRUCTURES dict
        platform: Platform identifier (twitter, bluesky, linkedin, linkedin_bruno)

    Returns:
        Prompt string to inject into the ideator's Step 2
    """
    structure = STRUCTURES.get(structure_key)
    if not structure:
        return ""

    prompt = structure["prompts"].get(platform, structure["prompts"].get("twitter", ""))
    return prompt


def get_random_hook(hook_type: Optional[str] = None) -> str:
    """
    Get a random hook from the hook library.

    Args:
        hook_type: "insight", "builder", or "contrarian". Random if None.

    Returns:
        A hook string to use as inspiration (not to copy verbatim)
    """
    if hook_type and hook_type in HOOK_PATTERNS:
        hooks = HOOK_PATTERNS[hook_type]
    else:
        hook_type = random.choice(list(HOOK_PATTERNS.keys()))
        hooks = HOOK_PATTERNS[hook_type]

    return random.choice(hooks)


def get_structure_info(structure_key: str) -> dict:
    """Get metadata about a structure for logging/analytics."""
    structure = STRUCTURES.get(structure_key, {})
    return {
        "key": structure_key,
        "name": structure.get("name", "Unknown"),
        "purpose": structure.get("purpose", ""),
        "sections": structure.get("sections", []),
    }
