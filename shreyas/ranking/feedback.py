"""
Per-user ranker weight updates from user feedback.

The keyword map below routes free-text edits like "make this cheaper" or
"less packed" to the feature(s) they imply. `apply_text_feedback` reads
boost / reduce / clamp / renormalization hyperparameters from the policy's
`feedback_policy` dict — no hardcoded constants live here.

V1 keeps it deterministic: keyword → feature(s) → boost requested-direction,
reduce nothing else (we don't infer rejections from text yet, only from
structured per-activity feedback which goes through feature_logging).

V2 will add gradient updates from `feature_logging` event streams once we
have replacement deltas accumulated.

This module does NOT decide which surface a feedback message belongs to —
the caller passes `surface` ('cotraveller' | 'destination' | 'activity').
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# Keyword → list of features the keyword implies should be boosted. Keys
# are regex word boundaries so "cheap" and "cheaper" both fire. Multiple
# matching keywords stack additively (boost amount per match).
#
# Mapping rationale, not policy: "cheaper" obviously means user cares more
# about budget fit; "less packed" / "rushed" means pace matters more;
# "more local" / "less touristy" means tag/interest fit matters more.
TEXT_FEEDBACK_KEYWORDS: dict[str, list[str]] = {
    # Budget signals
    r"\b(cheap(?:er)?|expensive|pricey|costly|afford|budget|spend)\b": ["budget_ordinal_fit", "activity_cost_fit"],
    # Pace signals
    r"\b(packed|rushed|busy|hectic|crammed|slower|relaxed|chill)\b":   ["pace_ordinal_fit", "pace_duration_fit"],
    r"\b(less)\s+(packed|busy|crammed|rushed)\b":                       ["pace_ordinal_fit", "pace_duration_fit"],
    # Local / authentic signals
    r"\b(local|authentic|touristy|off[\s-]?the[\s-]?beaten|hidden)\b": ["tag_interest_overlap"],
    # Style signals
    r"\b(solo|couple|family|friends|group)\b":                          ["style_match"],
    # Interest signals — bumps the tag/interest overlap regardless of which interest
    r"\b(food|nightlife|nature|culture|history|adventure|art|music|beach|hiking|museum)\b": ["tag_interest_overlap", "interest_jaccard"],
}


def _surface_features(policy: Any) -> set[str]:
    """Set of features this policy actually uses — bounds what feedback can move."""
    return set(getattr(policy, "features", []) or [])


def _renormalize(weights: dict[str, float], strategy: str = "sum_to_one") -> dict[str, float]:
    if strategy != "sum_to_one":
        return weights
    total = sum(max(0.0, v) for v in weights.values())
    if total <= 0:
        # Degenerate — fall back to uniform across the same keys.
        if not weights:
            return weights
        u = 1.0 / len(weights)
        return {k: u for k in weights}
    return {k: max(0.0, v) / total for k, v in weights.items()}


def _clamp(weights: dict[str, float], min_weight: float) -> dict[str, float]:
    return {k: max(min_weight, v) for k, v in weights.items()}


def _features_for_text(text: str, policy_features: set[str]) -> list[str]:
    """Return the unique list of features the text implies, restricted to
    those the policy actually uses (no point boosting a feature this
    surface doesn't read)."""
    text_lower = (text or "").lower()
    hits: list[str] = []
    for pattern, feature_names in TEXT_FEEDBACK_KEYWORDS.items():
        if re.search(pattern, text_lower):
            for name in feature_names:
                if name in policy_features and name not in hits:
                    hits.append(name)
    return hits


def apply_text_feedback(
    current_weights: dict[str, float],
    text: str,
    policy: Any,
) -> tuple[dict[str, float], list[str]]:
    """
    Apply a text-feedback update to a user's per-surface weights for this
    ranking policy.

    Args:
        current_weights: viewer's existing weights for this surface (or the
            policy defaults if they don't have any yet).
        text: free-text feedback like "make this cheaper" or "less packed".
        policy: the policy module whose `features` + `feedback_policy` drive
            this update.

    Returns:
        (new_weights, boosted_feature_names) — new_weights is renormalised
        and clamped per the policy's feedback_policy; boosted is the list
        the caller can log for observability.
    """
    policy_features = _surface_features(policy)
    if not policy_features:
        return dict(current_weights or {}), []

    cfg = getattr(policy, "feedback_policy", {}) or {}
    boost_amount  = float(cfg.get("boost_amount", 0.10))
    reduce_amount = float(cfg.get("reduce_amount", 0.05))  # unused in V1 text path; kept for symmetry
    min_weight    = float(cfg.get("min_weight",   0.05))
    strategy      =       cfg.get("renormalization", "sum_to_one")

    # Start from the policy default if current_weights is empty / malformed.
    defaults = dict(getattr(policy, "weights", {}) or {})
    weights  = {name: float((current_weights or {}).get(name, defaults.get(name, 0.0))) for name in policy_features}

    boosted = _features_for_text(text, policy_features)
    for name in boosted:
        weights[name] = weights[name] + boost_amount

    # We don't auto-reduce from a single text edit in V1 — too easy to over-
    # fit on a casual "cheaper" comment. V2's gradient path uses
    # accept/reject deltas instead; reduce_amount is plumbed through for
    # that future path.
    _ = reduce_amount

    weights = _clamp(weights, min_weight=min_weight)
    weights = _renormalize(weights, strategy=strategy)
    return weights, boosted


def merge_user_weights(
    viewer_compatibility_signals: dict | None,
    surface: str,
    new_weights: dict[str, float],
) -> dict:
    """Return an updated compatibility_signals dict with new_weights merged
    in at signals['ranker_weights'][surface]. Caller persists this via
    update_user_profile."""
    base = dict(viewer_compatibility_signals or {})
    all_weights = dict(base.get("ranker_weights") or {})
    all_weights[surface] = dict(new_weights)
    base["ranker_weights"] = all_weights
    return base
