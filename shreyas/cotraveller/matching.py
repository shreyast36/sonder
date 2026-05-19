"""
Fine-grained co-traveller match scoring.

Candidates come from shreyas.retrieval.search.search_cotravellers (already
pre-filtered by vector similarity). This module re-scores them with explicit
signal overlap so the final match_score and match_reasons we expose to the
user are interpretable.

Signals + weights (sum to 1.0):
  - interests overlap (PULL dim ids)   0.45
  - pace alignment                     0.20
  - travel_style alignment             0.20
  - budget_style alignment             0.15
"""

import logging
from shared.schemas import (
    UserProfile, CoTravellerProfile, CoTravellerMatch,
    PacePreference, BudgetStyle, TravelStyle,
)

logger = logging.getLogger(__name__)

# Ordinal distance for graded enums — closer values get partial credit.
_PACE_ORDER   = [PacePreference.relaxed, PacePreference.moderate, PacePreference.packed]
_BUDGET_ORDER = [BudgetStyle.budget, BudgetStyle.mid_range, BudgetStyle.luxury]

W_INTERESTS    = 0.45
W_PACE         = 0.20
W_TRAVEL_STYLE = 0.20
W_BUDGET       = 0.15


def _interest_overlap(user_interests: list[str], cand_interests: list[str]) -> tuple[float, list[str]]:
    """Jaccard-ish overlap on dim ids. Returns (0..1 score, shared list)."""
    u = set(i for i in (user_interests or []) if i)
    c = set(i for i in (cand_interests or []) if i)
    if not u or not c:
        return 0.0, []
    shared = sorted(u & c)
    union  = u | c
    return len(shared) / max(1, len(union)), shared


def _ordinal_alignment(a, b, order: list) -> float:
    """1.0 for exact match, 0.5 for one step apart, 0.0 for two+ steps."""
    if a is None or b is None:
        return 0.5
    try:
        ai, bi = order.index(a), order.index(b)
    except ValueError:
        return 0.5
    distance = abs(ai - bi)
    return max(0.0, 1.0 - 0.5 * distance)


def _travel_style_alignment(a, b) -> float:
    if a is None or b is None:
        return 0.5
    return 1.0 if a == b else 0.4


def _user_signals(user_profile: UserProfile) -> dict:
    """Pull the user's matching signals from compatibility_signals + constraints."""
    cs = user_profile.compatibility_signals or {}
    c  = user_profile.constraints
    return {
        "interests":    list(cs.get("top_interests") or []),
        "pace":         (c.pace if c else None),
        "budget_style": getattr(c, "budget_style", None) if c else None,
        "travel_style": (c.who_travelling_with if c else None),
    }


def _humanize_dim(dim_id: str) -> str:
    """exploration_local -> exploration & local; food_drink -> food & drink."""
    return dim_id.replace("_", " & ", 1).replace("_", " ")


def score_compatibility(user_profile: UserProfile, candidate: CoTravellerProfile) -> CoTravellerMatch:
    u = _user_signals(user_profile)

    interest_score, shared_interests = _interest_overlap(u["interests"], candidate.interests)
    pace_score                       = _ordinal_alignment(u["pace"], candidate.pace, _PACE_ORDER)
    budget_score                     = _ordinal_alignment(u["budget_style"], candidate.budget_style, _BUDGET_ORDER)
    style_score                      = _travel_style_alignment(u["travel_style"], candidate.travel_style)

    match_score = (
        W_INTERESTS    * interest_score +
        W_PACE         * pace_score +
        W_BUDGET       * budget_score +
        W_TRAVEL_STYLE * style_score
    )
    match_score = max(0.0, min(1.0, match_score))

    # Match reasons — surface the strongest signals as short copy.
    reasons: list[str] = []
    if shared_interests:
        pretty = ", ".join(_humanize_dim(d) for d in shared_interests[:2])
        reasons.append(f"Both drawn to {pretty}")
    if pace_score >= 0.95 and u["pace"] is not None:
        reasons.append(f"Same {u['pace'].value} pace")
    elif pace_score >= 0.45 and u["pace"] is not None:
        reasons.append("Compatible pace")
    if style_score >= 0.95 and u["travel_style"] is not None:
        reasons.append(f"Both travel as {u['travel_style'].value}")
    if budget_score >= 0.95 and u["budget_style"] is not None:
        reasons.append(f"Same {u['budget_style'].value.replace('_', '-')} budget")
    if not reasons:
        reasons.append(f"Reads as a {candidate.archetype.lower()}")

    return CoTravellerMatch(
        profile=candidate,
        match_score=match_score,
        match_reasons=reasons[:4],
        compatibility_breakdown={
            "interests":    round(interest_score, 3),
            "pace":         round(pace_score, 3),
            "budget":       round(budget_score, 3),
            "travel_style": round(style_score, 3),
        },
    )


def get_top_matches(
    user_profile: UserProfile,
    candidates: list[CoTravellerProfile],
    top_n: int = 6,
) -> list[CoTravellerMatch]:
    if not candidates:
        return []
    scored = [score_compatibility(user_profile, c) for c in candidates]
    scored.sort(key=lambda m: m.match_score, reverse=True)
    return scored[:top_n]


async def regenerate_matches(
    user_profile: UserProfile,
    excluded_profile_ids: list[str],
    feedback: str = "",
    top_n: int = 6,
) -> list[CoTravellerMatch]:
    """Pull a fresh batch of candidates, skip any already-shown profile_ids,
    re-score, return top_n. When feedback is provided, refine the user's
    embedding first so the new batch reflects what they actually want."""
    from shreyas.retrieval.search import search_cotravellers
    from ali.vector.embeddings import build_refined_query, embed_text

    if feedback:
        refined_vec = await embed_text(build_refined_query(user_profile, feedback))
        user_profile = user_profile.model_copy(update={"travel_style_embedding": refined_vec})

    candidates = await search_cotravellers(user_profile, top_k=80)
    fresh = [c for c in candidates if c.profile_id not in (excluded_profile_ids or [])]
    return get_top_matches(user_profile, fresh, top_n)
