"""
Twitter algorithm signal weights — the map I built from reading the source.

Source: https://github.com/twitter/the-algorithm (released 2023-03-31)

The ranker is at src/scala/com/twitter/home_mixer/.../HeavyRankerScoringPipeline.scala
It takes a candidate tweet and scores it as a weighted sum of predicted
probabilities of downstream user actions.

The weights below are the coefficients of that sum. Positive weights boost
distribution; negative weights suppress it. The magnitudes are asymmetric by
design — Twitter protects user experience by penalizing bad signals far more
than it rewards good ones.

I use this dict as the scoring function for every candidate post my content
engine generates. Posts with a projected score below threshold never ship.
"""

from dataclasses import dataclass
from typing import Literal


# --------------------------------------------------------------------------- #
# Canonical weight map
# --------------------------------------------------------------------------- #

SIGNAL_WEIGHTS: dict[str, float] = {
    # --- Positive signals ---
    "author_replies_own_post": 75.0,    # Biggest lever. Always self-reply <3min.
    "being_replied_to":         27.0,   # Reply-inducing hooks: questions, contrarian.
    "profile_click":            24.0,   # Treat bio as landing page.
    "deep_dwell_over_2min":     20.0,   # Long-form threads, not single tweets.
    "retweet":                   2.0,   # Low ROI; don't optimize.
    "like":                      1.0,   # Baseline — every post should clear this.

    # --- Negative signals ---
    "negative_feedback":      -148.0,   # "Not interested" / "block" / mute clusters.
    "report":                 -738.0,   # One report neutralizes ~738 good posts.
}


# --------------------------------------------------------------------------- #
# Author diversity decay — second-order weight
# --------------------------------------------------------------------------- #
#
# Same account posting multiple times in a short window gets diminishing returns:
#
#   post 1: 100%
#   post 2:  62.5%
#   post 3:  43.75%
#   post 4:  30.6%   (etc.)
#
# Implication: 3 high-quality posts per day > 10 mediocre posts.

AUTHOR_DIVERSITY_DECAY = 0.625  # multiplier per additional post from same author


def effective_weight(base_score: float, post_index_today: int) -> float:
    """Apply diversity decay to a raw score."""
    return base_score * (AUTHOR_DIVERSITY_DECAY ** (post_index_today - 1))


# --------------------------------------------------------------------------- #
# Signal projection — the thing you score candidate posts against
# --------------------------------------------------------------------------- #

Signal = Literal[
    "author_replies_own_post",
    "being_replied_to",
    "profile_click",
    "deep_dwell_over_2min",
    "retweet",
    "like",
    "negative_feedback",
    "report",
]


@dataclass
class PostProjection:
    """Predicted probabilities of each signal firing for a candidate post.

    These come from a classifier I trained on 2,000+ labeled historical posts.
    The classifier is small (logistic regression + embedding features) — the
    point is not model sophistication; the point is that the objective is now
    explicit instead of vibes.
    """
    p_author_replies_own_post:  float
    p_being_replied_to:         float
    p_profile_click:            float
    p_deep_dwell_over_2min:     float
    p_retweet:                  float
    p_like:                     float
    p_negative_feedback:        float
    p_report:                   float

    def score(self, post_index_today: int = 1) -> float:
        """Expected distribution score under the published Twitter weights."""
        raw = (
              self.p_author_replies_own_post * SIGNAL_WEIGHTS["author_replies_own_post"]
            + self.p_being_replied_to        * SIGNAL_WEIGHTS["being_replied_to"]
            + self.p_profile_click           * SIGNAL_WEIGHTS["profile_click"]
            + self.p_deep_dwell_over_2min    * SIGNAL_WEIGHTS["deep_dwell_over_2min"]
            + self.p_retweet                 * SIGNAL_WEIGHTS["retweet"]
            + self.p_like                    * SIGNAL_WEIGHTS["like"]
            + self.p_negative_feedback       * SIGNAL_WEIGHTS["negative_feedback"]
            + self.p_report                  * SIGNAL_WEIGHTS["report"]
        )
        return effective_weight(raw, post_index_today)


# --------------------------------------------------------------------------- #
# Safety tier system — the thing that stops one bad post from tanking a month
# --------------------------------------------------------------------------- #
#
# Because negative signals are asymmetric (-148× and -738×), a single bad post
# can neutralize a month of good ones. I don't trust my own judgment on this,
# so every post is classified into a safety tier before it ships:
#
#   TIER A: Zero risk. Educational, data-driven, no opinions on people.
#   TIER B: Low risk. Contrarian on *ideas*, never on *people*.
#   TIER C: Medium risk. Controversial-on-ideas; limit to 10% of volume.
#   TIER D: High risk. BLOCKED.
#
# Rule: no more than 10% of daily post volume can be Tier C.
# Never ship Tier D. Ever.

SAFETY_TIER_MAX_SHARE: dict[str, float] = {
    "A": 1.00,
    "B": 0.40,
    "C": 0.10,
    "D": 0.00,   # hard block
}


# --------------------------------------------------------------------------- #
# Threshold — below this, kill the post
# --------------------------------------------------------------------------- #

MIN_SHIPPABLE_SCORE = 5.0  # empirically, posts below 5.0 underperform floor


if __name__ == "__main__":
    # Example: a high-effort thread with a self-reply lined up
    example = PostProjection(
        p_author_replies_own_post=0.95,   # I always self-reply
        p_being_replied_to=0.35,
        p_profile_click=0.15,
        p_deep_dwell_over_2min=0.45,      # it's a thread
        p_retweet=0.05,
        p_like=0.60,
        p_negative_feedback=0.01,
        p_report=0.0001,
    )
    print(f"Projected score: {example.score():.2f}")
    print(f"Above ship threshold: {example.score() >= MIN_SHIPPABLE_SCORE}")
