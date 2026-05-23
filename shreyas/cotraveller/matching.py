"""
Co-traveller match scoring — thin wrapper around the generic ranking engine.

The old hardcoded W_INTERESTS / W_PACE / W_TRAVEL_STYLE / W_BUDGET formula
moved into shreyas.ranking.policies.cotraveller (with equal priors and
per-user weight overrides). This module just preserves the public surface
the routes + orchestrator already call: `score_compatibility` returns one
CoTravellerMatch, `get_top_matches` returns a sorted list, and
`regenerate_matches` refreshes the candidate pool.

All scoring decisions — features, weights, taxonomy similarity, feedback
hyperparameters — live in shreyas/ranking/. This file owns: humanizing
the engine output into CoTravellerMatch shape.
"""

from __future__ import annotations

import logging

from shared.schemas import (
    UserProfile, CoTravellerProfile, CoTravellerMatch,
)
from shreyas.ranking.engine import rank, RankedCandidate
from shreyas.ranking.policies import load_policy
from shreyas.ranking.salience import compute_answer_salience

logger = logging.getLogger(__name__)


def _humanize_dim(dim_id: str) -> str:
    """exploration_local → exploration & local; food_drink → food & drink."""
    return dim_id.replace("_", " & ", 1).replace("_", " ")


def _build_match(viewer: UserProfile, rc: RankedCandidate) -> CoTravellerMatch:
    """Convert engine output to the CoTravellerMatch shape consumers expect.
    match_reasons come from the top-contributing feature snippets; the
    compatibility_breakdown is the per-feature raw scores."""
    candidate: CoTravellerProfile = rc.candidate

    raw_breakdown = {name: round(raw, 3) for name, (raw, _w) in rc.feature_scores.items()}
    # Keep the legacy keys the frontend reads so the UI doesn't break.
    legacy_breakdown = {
        "interests":    raw_breakdown.get("salience_weighted_question_overlap",
                        raw_breakdown.get("interest_jaccard", 0.0)),
        "pace":         raw_breakdown.get("pace_ordinal_fit", 0.0),
        "budget":       raw_breakdown.get("budget_ordinal_fit", 0.0),
        "travel_style": raw_breakdown.get("style_match", 0.0),
    }

    # Top-3 feature snippets become match_reasons. Filter out the
    # "feature error" and other low-signal snippets and fall back to a
    # generic archetype line if nothing useful surfaced.
    reasons: list[str] = []
    for snippet in rc.explanation_summary(top_k=3):
        s = (snippet or "").strip()
        if not s or s.startswith("feature error") or s == "no answer overlap":
            continue
        # Try to humanise dim ids that leak into snippets (e.g.
        # "both into food_drink" → "both into food & drink").
        for token in s.split():
            if "_" in token and token.replace("_", "").isalnum():
                s = s.replace(token, _humanize_dim(token))
        if s not in reasons:
            reasons.append(s)
    if not reasons:
        reasons.append(f"Reads as a {candidate.archetype.lower()}")

    return CoTravellerMatch(
        profile=candidate,
        match_score=rc.final_score,
        match_reasons=reasons[:4],
        compatibility_breakdown={**legacy_breakdown, **raw_breakdown},
    )


def _resolve_salience(viewer: UserProfile) -> dict[str, float]:
    """Read salience from compatibility_signals.answer_salience if it was
    persisted by /persona-infer; otherwise compute it from the profile's
    answers + constraints on the fly. Keeps the engine working even for
    users who pre-date the persisted-salience write."""
    cs = viewer.compatibility_signals or {}
    cached = cs.get("answer_salience") if isinstance(cs, dict) else None
    if isinstance(cached, dict) and cached:
        # Defensively coerce to float.
        return {k: float(v) for k, v in cached.items() if isinstance(v, (int, float))}
    return compute_answer_salience(viewer.persona_answers, viewer.constraints)


def score_compatibility(viewer: UserProfile, candidate: CoTravellerProfile) -> CoTravellerMatch:
    """One-candidate convenience wrapper. Runs the engine with a single
    candidate and unwraps the result. Used by the profile-detail endpoint."""
    policy = load_policy("cotraveller")
    salience = _resolve_salience(viewer)
    # No retrieval score available for a one-off (this code path doesn't
    # come from Pinecone) — pass 0.0 and let other features carry it.
    ranked = rank(viewer, [(candidate, 0.0)], policy, ctx={"salience": salience})
    if not ranked:
        # Shouldn't happen, but be defensive.
        return CoTravellerMatch(
            profile=candidate,
            match_score=0.0,
            match_reasons=[f"Reads as a {candidate.archetype.lower()}"],
            compatibility_breakdown={},
        )
    return _build_match(viewer, ranked[0])


def get_top_matches(
    viewer: UserProfile,
    candidates: list[CoTravellerProfile],
    top_n: int = 6,
) -> list[CoTravellerMatch]:
    """Score + sort + cap. Candidates come from Pinecone retrieval with no
    score attached today; we pass retrieval_score=0 and let features carry
    the signal. Once `search_cotravellers` is updated to return
    (profile, score) tuples, this is the seam to thread them through."""
    if not candidates:
        return []
    policy = load_policy("cotraveller")
    salience = _resolve_salience(viewer)
    pairs = [(c, 0.0) for c in candidates]
    ranked = rank(viewer, pairs, policy, ctx={"salience": salience}, top_n=top_n)
    return [_build_match(viewer, rc) for rc in ranked]


async def regenerate_matches(
    viewer: UserProfile,
    excluded_profile_ids: list[str],
    feedback: str = "",
    top_n: int = 6,
) -> list[CoTravellerMatch]:
    """Pull a fresh batch of candidates, skip already-shown profile_ids,
    re-score, return top_n. When feedback is provided, refine the user's
    embedding first so retrieval pulls a different pool."""
    from shreyas.retrieval.search import search_cotravellers
    from ali.vector.embeddings import build_refined_query, embed_text

    if feedback:
        refined_vec = await embed_text(build_refined_query(viewer, feedback))
        viewer = viewer.model_copy(update={"travel_style_embedding": refined_vec})

    candidates = await search_cotravellers(viewer, top_k=80)
    fresh = [c for c in candidates if c.profile_id not in (excluded_profile_ids or [])]
    return get_top_matches(viewer, fresh, top_n)
