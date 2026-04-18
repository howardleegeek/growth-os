import json
import os
import sys
from abc import ABC, abstractmethod
from typing import Optional

from engine.llm import generate_text

# n8n Webhook URL - set this in your environment or ~/.openclaw/.env
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")


class BasePlatformAdapter(ABC):
    """
    Spokes: Adapts a 'Seed Idea' into a platform-native post.
    """

    @abstractmethod
    def __init__(self, platform: str):
        self.platform = platform

    @abstractmethod
    async def format_content(self, seed_idea: str, persona_profile: dict) -> str:
        """Takes a seed idea and formats it into natural platform context."""
        pass

    @abstractmethod
    async def publish(self, content: str, handle: str, dry_run: bool = False) -> dict:
        """Publishes the content via API or CDP to the respective platform."""
        pass


class XAdapter(BasePlatformAdapter):
    def __init__(self):
        super().__init__("X/Twitter")
        self.preamble = (
            "CRITICAL RULES FOR AUTHENTIC X (TWITTER) POSTS:\n"
            "0. LANGUAGE: ALL OUTPUT MUST BE IN ENGLISH. Never write in Chinese, Spanish, or any other language.\n"
            "1. THREAD FORMAT: Write a 2-3 part thread. Each part under 280 chars. Separate parts with ---. Part 1 = hook (bold claim or question). Part 2 = evidence/depth (specifics, numbers, experience). Part 3 = takeaway or next step (optional, only if it adds value). Each part must stand alone AND build on the previous.\n"
            "2. NO AI TROPES: DO NOT use: leverage, delve, crucial, testament, landscape, realm, tapestry, navigate, innovative, unlock, dive, game-changer, revolutionize.\n"
            "3. NO SYCOPHANCY: Stop agreeing. Just make your point directly.\n"
            "4. GRAMMAR: Proper sentence capitalization (first word capitalized). Casual but correct. Missing articles or run-ons are OK for voice, but not sloppy.\n"
            "5. TAKE A STAND: Have a clear, blunt opinion. No wishy-washy hedging. Say something specific, not generic marketing.\n"
            "6. EMOJIS: Zero emojis. Never.\n"
            "7. ZERO HASHTAGS: NEVER include hashtags. Twitter algorithm penalizes hashtags with reduced reach. Not even one.\n"
            "8. VARIETY: Do NOT repeat the same talking points across posts. Each post should cover a DIFFERENT angle, topic, or insight. Avoid repeating product stats verbatim.\n"
            "9. MATCH PERSONA: Follow the persona's voice EXACTLY. A hardware founder sounds different from a crypto builder.\n"
            "10. BRAND ISOLATION: NEVER mention any sibling brands. Each brand is 100% independent.\n"
            "11. SPECIFICITY: Reference concrete details — numbers, technical specs, real comparisons, specific use cases. Generic claims like 'we're the best' are banned.\n"
            "12. OUTPUT: Return ONLY the thread text with --- separators. No prefixes, no quotes, no 'Part 1:', no numbering. Just raw text separated by ---."
        )
        # Import isolated Publisher module based on MECE architecture
        from publishers.x_api import XApiPublisher

        self.publisher = XApiPublisher()

    @staticmethod
    def _load_reflection_rules(brand_key: str) -> str:
        """Load learned brand rules from reflection files."""
        reflections_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "engine", "reflections"
        )
        # Try exact match, then common aliases
        aliases = [brand_key, brand_key.lower(), brand_key.replace("-", "_")]
        for alias in aliases:
            path = os.path.join(reflections_dir, f"{alias}_rules.md")
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        return f.read().strip()
                except Exception:
                    pass
        return ""

    async def format_content(self, seed_idea: str, persona_profile: dict) -> str:
        print(f"✍️ [Adapter: {self.platform}] Formatting seed idea...")

        # Load brand reflection rules if available
        brand_name = persona_profile.get("brand_key", persona_profile.get("handle", ""))
        rules = self._load_reflection_rules(brand_name)
        rules_section = f"\n\nLEARNED BRAND RULES (MUST FOLLOW):\n{rules}" if rules else ""

        system_prompt = f"{self.preamble}{rules_section}\n\nPersona constraints:\n{json.dumps(persona_profile, indent=2)}"
        prompt = (
            f"Write a 2-3 part X (Twitter) thread based on this idea. Match the persona's voice exactly.\n"
            f"Part 1: Hook — bold claim, hot take, or surprising fact (under 280 chars)\n"
            f"Part 2: Depth — evidence, specific numbers, technical detail, or real experience (under 280 chars)\n"
            f"Part 3 (optional): Takeaway — what you learned, what's next, or a question that invites replies (under 280 chars)\n\n"
            f"Separate parts with --- on its own line. No hashtags. No prefixes. Raw text only.\n\n"
            f"Seed Idea:\n{seed_idea}"
        )

        formatted = await generate_text(
            system_prompt=system_prompt, user_message=prompt
        )
        return formatted or "Error generating text"

    @staticmethod
    def split_thread(text: str) -> list[str]:
        """Split LLM output into thread parts (separated by ---).

        Returns list of parts, each truncated to 280 chars.
        Minimum 1 part (main tweet), typically 2-3 parts.
        """
        # Split by --- delimiter
        parts = [p.strip() for p in text.split("---") if p.strip()]
        if not parts:
            parts = [text.strip()]
        # Truncate each part to 280 chars
        result = []
        for part in parts:
            if len(part) > 280:
                part = part[:277].rsplit(" ", 1)[0] + "..."
            result.append(part)
        return result

    async def publish(self, content: str, handle: str, dry_run: bool = False) -> dict:
        print(f"🚀 [Publish: {self.platform}] Posting as {handle}")
        if dry_run:
            print(f"[DRY RUN] {content}")
            return {"status": "success", "url": "dry_run"}

        return await self.publisher.publish(text=content, handle=handle)


class BlueskyAdapter(BasePlatformAdapter):
    def __init__(self):
        super().__init__("Bluesky")
        self.max_length = 300  # Bluesky hard limit
        self.preamble = (
            "CRITICAL RULES FOR AUTHENTIC BLUESKY POSTS:\n"
            "0. LANGUAGE: ALL OUTPUT MUST BE IN ENGLISH. Never write in Chinese, Spanish, or any other language.\n"
            "1. HARD LIMIT: Your output MUST be under 300 characters. Be extremely concise.\n"
            "2. CONVERSATIONAL: Write like a real person sharing a thought with their community.\n"
            "3. NO AI TROPES: DO NOT use: leverage, delve, crucial, testament, landscape, realm, tapestry, navigate, game-changer.\n"
            "4. GRAMMAR: Proper sentence capitalization. Casual but correct.\n"
            "5. THOUGHT PROCESS: Frame as a genuine observation or insight. Natural, not forced.\n"
            "6. EMOJIS: Never.\n"
            "7. ZERO HASHTAGS: NEVER include any hashtags.\n"
            "8. MATCH PERSONA: Follow the persona's voice EXACTLY. Each brand has its own tone.\n"
            "9. OUTPUT RAW TEXT ONLY: No prefixes, no quotes, no explanations.\n"
            "10. BRAND ISOLATION: NEVER mention any sibling brands.\n"
            "11. SPECIFICITY: Mention concrete details, not generic marketing claims."
        )

    async def format_content(self, seed_idea: str, persona_profile: dict) -> str:
        print(f"✍️ [Adapter: {self.platform}] Formatting seed idea...")
        system_prompt = f"{self.preamble}\n\nPersona constraints:\n{json.dumps(persona_profile, indent=2)}"
        prompt = f"Write an authentic Bluesky post about this. Match the persona's voice and brand positioning exactly. MUST be under 300 characters. RAW TEXT ONLY.\n\nSeed Idea:\n{seed_idea}"

        formatted = await generate_text(
            system_prompt=system_prompt, user_message=prompt
        )
        text = formatted or "Error generating text"
        # Hard truncation safety net — Bluesky maxLength=300
        if len(text) > self.max_length:
            text = text[: self.max_length - 3].rsplit(" ", 1)[0] + "..."
            print(f"⚠️ [Adapter: {self.platform}] Truncated to {len(text)} chars (limit: {self.max_length})")
        return text

    async def publish(self, content: str, handle: str, dry_run: bool = False) -> dict:
        print(f"🚀 [Publish: {self.platform}] Posting as {handle}")
        if dry_run:
            print(f"[DRY RUN] {content}")
            return {"status": "success", "url": "dry_run"}
        # Primary: Postiz publisher (if available)
        try:
            from publishers.postiz_publisher import PostizPublisher

            publisher = PostizPublisher(brand_key="")
            return await publisher.publish(text=content, platform="bluesky")
        except (ImportError, FileNotFoundError):
            pass
        # Fallback: bluesky-poster wrapper or atproto
        return {"status": "skipped", "reason": "No Bluesky publisher configured"}


class FarcasterAdapter(BasePlatformAdapter):
    def __init__(self):
        super().__init__("Farcaster")
        self.max_length = 800  # Farcaster/Warpcast limit
        self.preamble = (
            "CRITICAL RULES FOR FARCASTER (WARPCAST) — WEB3 NATIVE SOCIAL:\n"
            "0. LANGUAGE: ALL OUTPUT MUST BE IN ENGLISH. Never write in Chinese or any other language.\n"
            "1. MAX 780 CHARACTERS. Farcaster has an 800 char limit. Be concise but can go deeper than Twitter.\n"
            "2. CRYPTO-NATIVE VOICE: You live onchain. Speak like a builder, not a marketer. Use terms like: onchain, permissionless, composable, trustless, based, wagmi, gm.\n"
            "3. NO CORPORATE FLUFF: Zero marketing-speak. No 'leverage', 'ecosystem', 'innovative'. Just builder talk.\n"
            "4. TECHNICAL DEPTH OK: Unlike Twitter, Farcaster rewards technical takes. Mention specific protocols, chains, standards.\n"
            "5. FORMATTING: Lowercase mostly. Can use line breaks for emphasis. No hashtags.\n"
            "6. CHANNEL-AWARE: Posts often go to channels (/crypto, /dev, /wearables). Write like you're posting in a focused community.\n"
            "7. IMPERFECTION: Fragments, run-ons, casual abbreviations all good.\n"
            "8. EMOJIS: Sparingly. One max, only crypto-culture ones (🔥, ⚡, 🫡).\n"
            "9. OUTPUT RAW TEXT ONLY: No prefixes, no quotes, no explanations.\n"
            "10. BRAND ISOLATION: NEVER mention any sibling brands. Each brand is 100% independent. Only mention the brand specified in the persona context."
        )

    async def format_content(self, seed_idea: str, persona_profile: dict) -> str:
        print(f"✍️ [Adapter: {self.platform}] Formatting seed idea...")
        system_prompt = f"{self.preamble}\n\nPersona constraints:\n{json.dumps(persona_profile, indent=2)}"
        prompt = f"Write an authentic Farcaster/Warpcast post for the crypto-native builder community. MUST be under 780 characters. RAW TEXT ONLY.\n\nSeed Idea:\n{seed_idea}"

        formatted = await generate_text(
            system_prompt=system_prompt, user_message=prompt
        )
        text = formatted or "Error generating text"
        if len(text) > self.max_length:
            text = text[: self.max_length - 3].rsplit(" ", 1)[0] + "..."
        return text

    async def publish(self, content: str, handle: str, dry_run: bool = False) -> dict:
        if dry_run:
            return {"status": "success", "url": "dry_run"}
        try:
            from publishers.postiz_publisher import PostizPublisher
            publisher = PostizPublisher(brand_key="")
            return await publisher.publish(text=content, platform="farcaster")
        except Exception:
            return {"status": "skipped", "reason": "No Farcaster publisher configured"}


class ThreadsAdapter(BasePlatformAdapter):
    def __init__(self):
        super().__init__("Threads")
        self.max_length = 500  # Threads limit
        self.preamble = (
            "CRITICAL RULES FOR THREADS (META) — CASUAL SOCIAL:\n"
            "0. LANGUAGE: ALL OUTPUT MUST BE IN ENGLISH. Never write in Chinese or any other language.\n"
            "1. MAX 480 CHARACTERS. Threads has a 500 char limit. Keep it tight.\n"
            "2. CONVERSATIONAL: Threads is Instagram's text layer. Casual, lifestyle-adjacent, consumer-friendly.\n"
            "3. NO AI TROPES: DO NOT use: leverage, delve, crucial, testament, landscape, navigate, ecosystem.\n"
            "4. FORMATTING: Natural case (not all lowercase). Short paragraphs. Can use 1-2 line breaks.\n"
            "5. RELATABLE: Write like you're texting a smart friend about tech. No jargon unless you explain it.\n"
            "6. VISUAL THINKING: Reference images, aesthetics, design. Threads audience cares about how things look.\n"
            "7. EMOJIS: 0-2 emojis okay. Threads is more emoji-friendly than Twitter/Bluesky.\n"
            "8. NO HASHTAGS: Threads doesn't use them effectively.\n"
            "9. OUTPUT RAW TEXT ONLY: No prefixes, no quotes.\n"
            "10. BRAND ISOLATION: NEVER mention any sibling brands. Each brand is 100% independent. Only mention the brand specified in the persona context."
        )

    async def format_content(self, seed_idea: str, persona_profile: dict) -> str:
        print(f"✍️ [Adapter: {self.platform}] Formatting seed idea...")
        system_prompt = f"{self.preamble}\n\nPersona constraints:\n{json.dumps(persona_profile, indent=2)}"
        prompt = f"Write a casual, relatable Threads post about this. MUST be under 480 characters. Consumer-friendly, not too technical. RAW TEXT ONLY.\n\nSeed Idea:\n{seed_idea}"

        formatted = await generate_text(
            system_prompt=system_prompt, user_message=prompt
        )
        text = formatted or "Error generating text"
        if len(text) > self.max_length:
            text = text[: self.max_length - 3].rsplit(" ", 1)[0] + "..."
        return text

    async def publish(self, content: str, handle: str, dry_run: bool = False) -> dict:
        if dry_run:
            return {"status": "success", "url": "dry_run"}
        try:
            from publishers.postiz_publisher import PostizPublisher
            publisher = PostizPublisher(brand_key="")
            return await publisher.publish(text=content, platform="threads")
        except Exception:
            return {"status": "skipped", "reason": "No Threads publisher configured"}


class LinkedInAdapter(BasePlatformAdapter):
    def __init__(self):
        super().__init__("LinkedIn")
        self.preamble = (
            "CRITICAL RULES FOR LINKEDIN POSTS:\n"
            "0. LANGUAGE: ALL OUTPUT MUST BE IN ENGLISH. Never write in Chinese, Spanish, or any other language.\n"
            "1. NO AI CORPORATE FLUFF: ZERO use of leverage, delve, crucial, testament, landscape, realm, unlock, dive, paradigm shift, game-changer, revolutionize. EVER.\n"
            "2. THE HOOK: Start with a compelling opening line that makes people stop scrolling. Hard line break after.\n"
            "3. STORYTELLING: Write like a real person sharing something that matters to them. Use 'I' or 'We'. Authentic and grounded.\n"
            "4. CHOPPY FORMATTING: Very short paragraphs (1-2 sentences maximum). Let moments breathe.\n"
            "5. IMPERFECTION: Real people have rough edges. Don't make it sound like a PR team wrote it.\n"
            "6. VOICE: Follow the brand persona's voice and tone exactly.\n"
            "7. NO CTAs: Do not ask 'What are your thoughts?' End with your final point.\n"
            "8. YOU ARE NOT AN ASSISTANT: You are the person described in the persona.\n"
            "9. OUTPUT RAW TEXT ONLY: No prefixes like 'Draft:', no quotes.\n"
            "10. PROFESSIONAL TONE ONLY: Never use internet slang. Forbidden: tbh, ngl, larp, lmao, fr, af, imo, rn, lowkey, highkey, bussin, slay, based, cope, bruh, fam, vibe, yall.\n"
            "11. BRAND ISOLATION: NEVER mention any sibling brands.\n"
            "12. ZERO HASHTAGS: Do NOT include any hashtags. They reduce organic reach on LinkedIn."
        )

    async def format_content(self, seed_idea: str, persona_profile: dict) -> str:
        print(f"✍️ [Adapter: {self.platform}] Formatting seed idea...")
        system_prompt = f"{self.preamble}\n\nPersona constraints:\n{json.dumps(persona_profile, indent=2)}"
        prompt = f"Write a LinkedIn post that matches the persona's voice and brand positioning. Tell a story. Be authentic and human. RAW TEXT ONLY.\n\nSeed Idea:\n{seed_idea}"

        formatted = await generate_text(
            system_prompt=system_prompt, user_message=prompt, prefer_grok=False
        )  # Claude is better for long form
        return formatted or "Error generating text"

    async def publish(self, content: str, handle: str, dry_run: bool = False) -> dict:
        print(f"🚀 [Publish: {self.platform}] Posting as {handle}")
        if dry_run:
            print(f"[DRY RUN] {content}")
            return {"status": "success", "url": "dry_run"}

        # Primary: Postiz MCP publisher (supports all LinkedIn company pages)
        try:
            from publishers.postiz_publisher import PostizPublisher

            publisher = PostizPublisher(brand_key=handle)
            return await publisher.publish(text=content, platform="linkedin")
        except (ImportError, FileNotFoundError):
            pass

        # Fallback: n8n webhook (legacy)
        if N8N_WEBHOOK_URL:
            from publishers.n8n_webhook import N8NWebhookPublisher

            publisher = N8NWebhookPublisher(webhook_url=N8N_WEBHOOK_URL)
            return await publisher.publish(
                text=content,
                target_account_id=handle,
                platform_name="linkedin",
            )

        return {"status": "skipped", "reason": "No LinkedIn publisher configured"}
