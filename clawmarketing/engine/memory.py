import json
import os
from pathlib import Path
from typing import Dict, Any, List


class NarrativeMemory:
    """Manages state and history for omnichannel narratives."""

    def __init__(self, db_dir: str = "~/.oyster-narrative-v2"):
        self.db_dir = Path(os.path.expanduser(db_dir))
        self.db_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, campaign_name: str) -> Path:
        safe_name = campaign_name.replace(" ", "_").lower()
        return self.db_dir / f"{safe_name}_memory.json"

    def get_campaign_state(self, campaign_name: str) -> Dict[str, Any]:
        """Load the current state of a specific campaign."""
        db_file = self._get_file_path(campaign_name)
        if not db_file.exists():
            return {
                "campaign": campaign_name,
                "current_arc": "Initial launch and awareness.",
                "history": [],  # List of previous seed ideas to avoid repetition
                "persona": {},
            }

        try:
            with open(db_file) as f:
                return json.load(f)
        except Exception:
            return {
                "campaign": campaign_name,
                "current_arc": "Continuing narrative.",
                "history": [],
                "persona": {},
            }

    def save_campaign_state(
        self,
        campaign_name: str,
        current_arc: str,
        new_seed_idea: str,
        persona_metadata: dict = None,
    ) -> bool:
        """Update campaign state with the new arc and historical seed idea."""
        state = self.get_campaign_state(campaign_name)

        state["current_arc"] = current_arc
        if persona_metadata:
            state["persona"] = persona_metadata
        history = state.get("history", [])
        history.insert(0, new_seed_idea)

        # Keep last 50 seed ideas (was 20 — too small, topics cycled every 5 days)
        state["history"] = history[:50]

        db_file = self._get_file_path(campaign_name)
        try:
            with open(db_file, "w") as f:
                json.dump(state, f, indent=2)
            return True
        except Exception:
            return False

    def save_performance_feedback(self, campaign_name: str, feedback: str) -> bool:
        """Save analytics performance feedback for the campaign.

        Stores feedback text that gets injected into ideator as reflection rules.
        """
        state = self.get_campaign_state(campaign_name)
        perf = state.get("performance_feedback", [])
        perf.insert(0, feedback)
        state["performance_feedback"] = perf[:10]  # Keep last 10

        db_file = self._get_file_path(campaign_name)
        try:
            with open(db_file, "w") as f:
                json.dump(state, f, indent=2)
            return True
        except Exception:
            return False

    def get_performance_feedback(self, campaign_name: str, limit: int = 3) -> str:
        """Get recent performance feedback as a string for injection into ideator."""
        state = self.get_campaign_state(campaign_name)
        perf = state.get("performance_feedback", [])
        if not perf:
            return ""
        return "\n".join(perf[:limit])

    def save_analytics(self, campaign_name: str, metrics: List[Dict[str, Any]]) -> bool:
        """Save analytics data to the campaign state."""
        state = self.get_campaign_state(campaign_name)

        # We can store analytics by ID to avoid duplicates or just keep a rolling window
        analytics_history = state.get("analytics", [])

        # Update existing or append new
        existing_ids = {
            a.get("id"): i for i, a in enumerate(analytics_history) if "id" in a
        }

        for metric in metrics:
            m_id = metric.get("id")
            if m_id in existing_ids:
                analytics_history[existing_ids[m_id]] = metric
            else:
                analytics_history.append(metric)
                # Keep index map updated
                existing_ids[m_id] = len(analytics_history) - 1

        # Keep last 100 entries max to prevent file bloat
        # Sort by created_at desc if available, but simplest is just slice from end
        state["analytics"] = analytics_history[-100:]

        db_file = self._get_file_path(campaign_name)
        try:
            with open(db_file, "w") as f:
                json.dump(state, f, indent=2)
            return True
        except Exception:
            return False
