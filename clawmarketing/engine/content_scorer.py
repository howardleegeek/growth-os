"""
ContentScorer — Structural quality scoring for social media content.
No LLM calls. Pure heuristics adapted from XActions contentOptimizer + Bluesky quality_gate.

Returns a 0-100 score with breakdown by dimension.
"""

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# --- Scoring weights (sum to ~100 when all bonuses apply) ---

# Template / sycophantic phrases (hard penalty)
_SYCOPHANTIC_STARTS = [
    "great point", "love this", "spot on", "so true", "absolutely",
    "well said", "couldn't agree more", "i love this", "this is great",
    "great take", "great thread", "amazing point", "brilliant point",
    "perfect take", "this is spot on", "totally agree", "100% agree",
]

# AI tropes (penalty per occurrence)
_AI_TROPES = [
    "leverage", "delve", "crucial", "testament", "landscape", "realm",
    "tapestry", "navigate", "innovative", "unlock", "dive", "paradigm",
    "ecosystem", "synergy", "holistic", "robust", "cutting-edge",
    "groundbreaking", "revolutionize", "game-changer", "disruptive",
    "seamless", "empower", "utilize", "optimize", "streamline",
]

# Spam / CTA phrases
_SPAM_PHRASES = [
    "click here", "buy now", "check out my", "link in bio",
    "follow me", "free money", "dm me", "limited time", "act now",
    "sign up", "what do you think?", "drop a comment",
    "thoughts?", "agree or disagree?",
]

# Natural connectors (bonus)
_NATURAL_CONNECTORS = [
    "though", "but", "tbh", "ngl", "imo", "honestly",
    "actually", "however", "still", "anyway", "fwiw",
    "imho", "personally", "lowkey", "highkey",
]

# Sincerity markers (bonus) — phrases that show genuine empathy, honesty, accountability
_SINCERITY_MARKERS = [
    "we hear you", "hear you", "you're right", "that's fair",
    "we messed up", "we get it", "fair point", "fair criticism",
    "full stop", "no excuses", "genuinely sorry", "sorry for",
    "unacceptable", "we own that", "valid concern", "we take that seriously",
    "dm us", "dm your", "we'll sort it", "let's fix this",
    "honest answer", "real talk", "not gonna lie",
]

# LinkedIn professional: these are OK on Twitter/Bluesky but bad on LinkedIn
_LINKEDIN_SLANG = {
    "tbh", "ngl", "larp", "lmao", "fr", "af", "imo", "rn",
    "lowkey", "highkey", "bussin", "slay", "based", "cope",
    "copium", "bruh", "fam", "vibe", "vibes", "yall",
}

# Prompt leakage detection
_PROMPT_LEAK_PHRASES = [
    "critical rules", "you are a", "you are an ai", "as an ai",
    "instructions:", "your role is", "system prompt", "do not reveal",
    "i am an ai", "i'm an ai", "as a language model", "i cannot",
]

# Markdown detection (prompt leakage)
_MARKDOWN_RE = re.compile(
    r"(\*\*[A-Z])"
    r"|^[-*]\s+\*\*"
    r"|^#{1,3}\s"
    r"|```"
    r"|\[.*?\]\(.*?\)",
    re.MULTILINE,
)

# Emoji pattern
_EMOJI_RE = re.compile(
    r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
    r"\U00002702-\U000027B0\U0000FE0F\U0000200D"
    r"\U00002600-\U000026FF\U00002700-\U000027BF]"
)

# Hashtag pattern
_HASHTAG_RE = re.compile(r"(?<!\S)#{1,2}[\w]+", re.UNICODE)

# Unfilled template variables
_TEMPLATE_VAR_RE = re.compile(r"\[[A-Z][A-Z0-9_]*\]")

# Platform char limits
PLATFORM_LIMITS = {
    "twitter": 280,
    "bluesky": 300,
    "linkedin": 3000,
    "farcaster": 800,
    "threads": 500,
}


@dataclass
class ScoreResult:
    """Detailed scoring result."""
    score: int  # 0-100
    grade: str  # A/B/C/D/F
    passed: bool  # score >= threshold
    breakdown: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)


class ContentScorer:
    """Score social media content quality. No LLM calls."""

    def __init__(self, *, threshold: int = 60):
        self.threshold = threshold

    def score(
        self,
        text: str,
        *,
        platform: str = "twitter",
        brand: str = "",
    ) -> ScoreResult:
        """Score content quality. Returns ScoreResult with 0-100 score."""
        breakdown = {}
        issues = []
        suggestions = []
        score = 50  # Base score

        stripped = text.strip()
        lower = stripped.lower()
        char_limit = PLATFORM_LIMITS.get(platform, 280)

        # === HARD REJECTS (score = 0) ===

        # Prompt leakage
        # Reasoning model <think> tags (MiniMax M1, DeepSeek, etc.)
        if "<think>" in lower:
            issues.append("REJECT: Reasoning model <think> block detected")
            return ScoreResult(score=0, grade="F", passed=False,
                             breakdown={"prompt_leak": -100}, issues=issues)

        if _MARKDOWN_RE.search(stripped):
            issues.append("REJECT: Markdown formatting detected (prompt leakage)")
            return ScoreResult(score=0, grade="F", passed=False,
                             breakdown={"prompt_leak": -100}, issues=issues)

        for pleak in _PROMPT_LEAK_PHRASES:
            if pleak in lower:
                issues.append(f"REJECT: Prompt leakage phrase '{pleak}'")
                return ScoreResult(score=0, grade="F", passed=False,
                                 breakdown={"prompt_leak": -100}, issues=issues)

        # Unfilled template variables
        unfilled = _TEMPLATE_VAR_RE.findall(stripped)
        if unfilled:
            issues.append(f"REJECT: Unfilled template vars: {', '.join(unfilled)}")
            return ScoreResult(score=0, grade="F", passed=False,
                             breakdown={"template_var": -100}, issues=issues)

        # Empty or too short
        if len(stripped) < 10:
            issues.append("REJECT: Too short (under 10 chars)")
            return ScoreResult(score=0, grade="F", passed=False,
                             breakdown={"length": -100}, issues=issues)

        # === LENGTH SCORING ===
        length = len(stripped)
        if platform in ("twitter", "bluesky"):
            # Sweet spot: 70-200 chars for short-form
            if 70 <= length <= 200:
                breakdown["length"] = 15
                score += 15
            elif 40 <= length <= 70:
                breakdown["length"] = 8
                score += 8
            elif 200 < length <= char_limit:
                breakdown["length"] = 5
                score += 5
            elif length > char_limit:
                overage = length - char_limit
                penalty = min(30, overage // 5)
                breakdown["length"] = -penalty
                score -= penalty
                issues.append(f"Over {platform} limit by {overage} chars")
            else:
                breakdown["length"] = 0
        elif platform == "linkedin":
            # LinkedIn: longer is OK, sweet spot 200-1500
            if 200 <= length <= 1500:
                breakdown["length"] = 15
                score += 15
            elif 100 <= length < 200:
                breakdown["length"] = 8
                score += 8
            elif length > 1500:
                breakdown["length"] = 5
                score += 5
            else:
                breakdown["length"] = 0
        else:
            if 50 <= length <= char_limit * 0.8:
                breakdown["length"] = 10
                score += 10

        # === ENGAGEMENT HOOKS (optimized for Twitter algorithm weights) ===

        # Question presence (reply-inducing, 27x algorithm weight)
        has_question = "?" in stripped
        if has_question:
            # Twitter/Bluesky: questions are critical for replies (27x weight)
            q_bonus = 20 if platform in ("twitter", "bluesky") else 12
            breakdown["question"] = q_bonus
            score += q_bonus
        else:
            breakdown["question"] = 0
            if platform in ("twitter", "bluesky"):
                # Hard penalty for Twitter without a question — replies are the #1 signal
                breakdown["question"] = -5
                score -= 5
                issues.append("No question mark — replies drive 27x algorithm weight")
            suggestions.append("Add a question to boost replies (27x algorithm weight)")

        # "you" opening — addressing the reader directly (drives profile clicks, 24x)
        words = stripped.split()
        if words and words[0].lower() in ("you", "your", "you're"):
            breakdown["you_opening"] = 10
            score += 10
        else:
            breakdown["you_opening"] = 0

        # Bold claim / hot take indicators (drives retweets + debate)
        hot_take_markers = [
            "hot take", "unpopular opinion", "hear me out", "nobody talks about",
            "the truth is", "here's the thing", "controversial take",
            "most people don't realize", "stop", "enough with",
            "wrong about", "overrated", "underrated", "myth",
        ]
        has_hot_take = any(marker in lower for marker in hot_take_markers)
        if has_hot_take:
            breakdown["hot_take"] = 12
            score += 12
        else:
            breakdown["hot_take"] = 0

        # Numbers / specifics (credibility + bookmark signal)
        num_count = len(re.findall(r"\d+", stripped))
        if num_count >= 3:
            breakdown["specifics"] = 10  # Data-rich = bookmark-worthy
            score += 10
        elif num_count >= 1:
            breakdown["specifics"] = 5
            score += 5
        else:
            breakdown["specifics"] = 0
            if platform in ("twitter", "bluesky"):
                suggestions.append("Add numbers/data — drives bookmarks and saves")

        # === AUTHENTICITY CHECKS ===

        # Natural connectors (human writing signal)
        has_connector = False
        for conn in _NATURAL_CONNECTORS:
            if platform == "linkedin" and conn in _LINKEDIN_SLANG:
                continue
            if re.search(rf"\b{re.escape(conn)}\b", lower):
                has_connector = True
                break
        if has_connector:
            breakdown["natural_voice"] = 8
            score += 8
        else:
            breakdown["natural_voice"] = 0

        # Sincerity markers (genuine empathy + accountability = trust + engagement)
        sincerity_count = sum(1 for m in _SINCERITY_MARKERS if m in lower)
        if sincerity_count >= 2:
            breakdown["sincerity"] = 15  # Multiple sincerity signals = very human
            score += 15
        elif sincerity_count == 1:
            breakdown["sincerity"] = 8
            score += 8
        else:
            breakdown["sincerity"] = 0

        # Fragment / run-on (imperfection = good for Twitter/Bluesky)
        sentences = re.split(r'[.!?]+', stripped)
        sentences = [s.strip() for s in sentences if s.strip()]
        if platform in ("twitter", "bluesky") and len(sentences) <= 2:
            breakdown["brevity"] = 5
            score += 5
        else:
            breakdown["brevity"] = 0

        # === PENALTY CHECKS ===

        # Sycophantic opening
        for syc in _SYCOPHANTIC_STARTS:
            if lower.startswith(syc):
                breakdown["sycophantic"] = -20
                score -= 20
                issues.append(f"Sycophantic opening: '{syc}'")
                break
        else:
            breakdown["sycophantic"] = 0

        # AI tropes
        trope_count = sum(1 for t in _AI_TROPES if t in lower)
        if trope_count > 0:
            penalty = min(25, trope_count * 8)
            breakdown["ai_tropes"] = -penalty
            score -= penalty
            found = [t for t in _AI_TROPES if t in lower]
            issues.append(f"AI tropes detected: {', '.join(found[:5])}")
        else:
            breakdown["ai_tropes"] = 0

        # Spam/CTA phrases
        spam_count = sum(1 for s in _SPAM_PHRASES if s in lower)
        if spam_count > 0:
            penalty = min(30, spam_count * 15)
            breakdown["spam"] = -penalty
            score -= penalty
            issues.append(f"Spam/CTA phrases: {spam_count}")
        else:
            breakdown["spam"] = 0

        # Hashtags (bad on all platforms)
        hashtag_count = len(_HASHTAG_RE.findall(stripped))
        if hashtag_count > 0:
            penalty = min(15, hashtag_count * 5)
            breakdown["hashtags"] = -penalty
            score -= penalty
            issues.append(f"{hashtag_count} hashtag(s) found — remove them")
        else:
            breakdown["hashtags"] = 0

        # Emoji overuse
        emoji_count = len(_EMOJI_RE.findall(stripped))
        if emoji_count > 2:
            penalty = min(15, (emoji_count - 2) * 5)
            breakdown["emoji_overuse"] = -penalty
            score -= penalty
            issues.append(f"{emoji_count} emojis — max 1-2 recommended")
        elif emoji_count == 0 and platform in ("twitter", "bluesky"):
            breakdown["emoji_overuse"] = 2  # Slight bonus for no emojis
            score += 2
        else:
            breakdown["emoji_overuse"] = 0

        # ALL CAPS detection
        caps_words = [w for w in words if len(w) >= 3 and w.isupper()]
        if len(caps_words) >= 3:
            penalty = min(15, len(caps_words) * 3)
            breakdown["all_caps"] = -penalty
            score -= penalty
            issues.append(f"{len(caps_words)} ALL CAPS words")
        else:
            breakdown["all_caps"] = 0

        # Excessive punctuation
        excess_punct = re.findall(r"([!?.,:;])\1{3,}", stripped)
        if excess_punct:
            breakdown["punct"] = -5
            score -= 5
            issues.append("Excessive repeated punctuation")
        else:
            breakdown["punct"] = 0

        # LinkedIn: professional tone check
        if platform == "linkedin":
            slang_found = [w for w in words if w.lower().rstrip(".,!?:;") in _LINKEDIN_SLANG]
            if slang_found:
                penalty = min(20, len(slang_found) * 5)
                breakdown["linkedin_slang"] = -penalty
                score -= penalty
                issues.append(f"LinkedIn slang: {', '.join(slang_found[:5])}")
            else:
                breakdown["linkedin_slang"] = 0

        # === CLAMP & GRADE ===
        score = max(0, min(100, score))

        if score >= 85:
            grade = "A"
        elif score >= 70:
            grade = "B"
        elif score >= 55:
            grade = "C"
        elif score >= 40:
            grade = "D"
        else:
            grade = "F"

        passed = score >= self.threshold

        return ScoreResult(
            score=score,
            grade=grade,
            passed=passed,
            breakdown=breakdown,
            issues=issues,
            suggestions=suggestions,
        )

    def score_batch(
        self,
        posts: list[dict],
        *,
        threshold: int | None = None,
    ) -> list[dict]:
        """Score a batch of posts. Returns list of {post, score_result}."""
        results = []
        t = threshold or self.threshold
        for post in posts:
            result = self.score(
                post.get("content", ""),
                platform=post.get("platform", "twitter"),
                brand=post.get("brand", ""),
            )
            results.append({
                "post": post,
                "score": result,
            })
        return results
