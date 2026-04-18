import os
import random
import re
from pathlib import Path
from typing import Optional, Dict, List

BASE_DIR = Path(__file__).parent


def load_markdown_file(file_path: Path) -> str:
    """Read a markdown file and return its content, or an empty string if missing."""
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def get_brand_markdown(brand_key: str) -> str:
    """Load the Markdown definition for a Brand (STP/Positioning)."""
    # Safe key matching (e.g., 'clawglasses' -> 'clawglasses.md')
    safe_key = brand_key.lower().replace(" ", "")
    brand_file = BASE_DIR / "brands" / f"{safe_key}.md"

    content = load_markdown_file(brand_file)
    if not content:
        # Fallback to a generic tech brand if not found
        return f"# Target Audience & Positioning\nTargeting tech builders. Positioning as an innovative solution for the future."
    return content


def _parse_pillar_table(brand_md: str) -> List[Dict]:
    """Parse a Content Pillars markdown table from brand markdown.

    Expected format:
        ## 5. Content Pillars
        | Pillar | Weight | Topics |
        |--------|--------|--------|
        | Name   | 35%    | topic1, topic2 |

    Returns list of dicts with keys: name, weight (float), topics (str).
    """
    if not brand_md:
        return []

    # Find the Content Pillars section
    section_match = re.search(
        r"##\s*\d*\.?\s*Content\s+Pillars\s*\n(.*?)(?=\n##|\Z)",
        brand_md,
        re.DOTALL | re.IGNORECASE,
    )
    if not section_match:
        return []

    section = section_match.group(1)

    # Parse markdown table rows (skip header and separator)
    rows = [
        line.strip()
        for line in section.strip().split("\n")
        if line.strip().startswith("|")
    ]
    if len(rows) < 3:
        return []

    # rows[0] = header, rows[1] = separator, rows[2:] = data
    pillars = []
    for row in rows[2:]:
        cells = [c.strip() for c in row.split("|")]
        # split on | gives empty strings at edges: ['', 'Name', '35%', 'topics', '']
        cells = [c for c in cells if c]
        if len(cells) < 3:
            continue
        name = cells[0].strip()
        weight_str = cells[1].strip().rstrip("%")
        topics = cells[2].strip()
        try:
            weight = float(weight_str)
        except ValueError:
            continue
        pillars.append({"name": name, "weight": weight, "topics": topics})

    return pillars


def pick_next_pillar(brand_key: str, pillar_history: List[str] = None) -> str:
    """Select the next content pillar based on weighted rotation.

    Returns a string like "Agentic Vision: on-device inference, computer vision"
    or empty string if no pillar table found.
    """
    brand_md = get_brand_markdown(brand_key)
    pillars = _parse_pillar_table(brand_md)
    if not pillars:
        return ""

    if not pillar_history:
        # No history: weighted random pick
        weights = [p["weight"] for p in pillars]
        chosen = random.choices(pillars, weights=weights, k=1)[0]
        return f"{chosen['name']}: {chosen['topics']}"

    # Calculate actual vs target distribution
    total_history = len(pillar_history) or 1
    pillar_names = {p["name"] for p in pillars}

    actual_counts = {}
    for name in pillar_names:
        actual_counts[name] = sum(1 for h in pillar_history if h == name)

    # Score = target_pct - actual_pct (higher = more underrepresented)
    scores = []
    for p in pillars:
        target_pct = p["weight"] / 100.0
        actual_pct = actual_counts.get(p["name"], 0) / total_history
        gap = target_pct - actual_pct
        scores.append((p, gap))

    # Sort by gap descending, pick from top candidates with some randomness
    scores.sort(key=lambda x: x[1], reverse=True)

    # Take top half (at least 2) and do weighted random among them
    n_candidates = max(2, len(scores) // 2)
    candidates = scores[:n_candidates]

    # Shift gaps to positive weights (min gap becomes weight 0.1)
    min_gap = min(g for _, g in candidates)
    pick_weights = [max(0.1, g - min_gap + 0.1) for _, g in candidates]

    chosen = random.choices(
        [p for p, _ in candidates], weights=pick_weights, k=1
    )[0]
    return f"{chosen['name']}: {chosen['topics']}"


def get_persona_markdown(persona_key: str) -> str:
    """Load the Markdown definition for a Persona (Voice/Vibe)."""
    safe_key = persona_key.lower().replace(" ", "")
    persona_file = BASE_DIR / "personas" / f"{safe_key}.md"

    content = load_markdown_file(persona_file)
    if not content:
        # Generic Degen/Founder fallback
        return "# Persona: Degen Founder\nYou are a blunt, fast-moving founder who hates corporate buzzwords."
    return content


def get_full_context(brand_key: str, persona_key: str) -> str:
    """Return a unified Markdown block injecting both Brand and Persona rules."""
    brand_md = get_brand_markdown(brand_key)
    persona_md = get_persona_markdown(persona_key)

    return f"""--- BRAND & PRODUCT POSITIONING ---
{brand_md}

--- CREATOR PERSONA ---
{persona_md}
"""
