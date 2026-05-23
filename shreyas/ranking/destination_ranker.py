"""
Destination ranking — thin wrapper around the generic engine.

Pre-ranking budget + avoid_list filters run upstream in the orchestrator
via shreyas.ranking.filters.apply_destination_filters. By the time
`rank_destinations` is called, every candidate is feasibility-eligible —
ordering is what's left to decide, and that's all the engine + policy
does.
"""

from __future__ import annotations

from shared.schemas import Destination, UserProfile
from shreyas.ranking.engine import rank
from shreyas.ranking.policies import load_policy
from shreyas.ranking.salience import compute_answer_salience


def _resolve_salience(viewer: UserProfile) -> dict[str, float]:
    cs = viewer.compatibility_signals or {}
    cached = cs.get("answer_salience") if isinstance(cs, dict) else None
    if isinstance(cached, dict) and cached:
        return {k: float(v) for k, v in cached.items() if isinstance(v, (int, float))}
    return compute_answer_salience(viewer.persona_answers, viewer.constraints)


def _trip_days(viewer: UserProfile) -> int:
    c = viewer.constraints
    if not c or not c.start_date or not c.end_date:
        return 1
    return max(1, (c.end_date - c.start_date).days + 1)


def score_destination(dest: Destination, viewer: UserProfile, pinecone_score: float) -> float:
    """Convenience one-candidate scorer — useful in tests + sanity checks.
    Returns the final score in [0,1]."""
    policy = load_policy("destination")
    ranked = rank(
        viewer, [(dest, pinecone_score)], policy,
        ctx={"salience": _resolve_salience(viewer), "trip_days": _trip_days(viewer)},
    )
    return ranked[0].final_score if ranked else 0.0


def rank_destinations(
    candidates: list[tuple[Destination, float]],
    viewer: UserProfile,
    top_n: int = 5,
) -> list[Destination]:
    """Sort destinations by the policy's combined score; return the top_n
    underlying Destination objects in order. Caller is responsible for
    having already applied apply_destination_filters."""
    if not candidates:
        return []
    policy = load_policy("destination")
    ranked = rank(
        viewer, candidates, policy,
        ctx={"salience": _resolve_salience(viewer), "trip_days": _trip_days(viewer)},
        top_n=top_n,
    )
    return [rc.candidate for rc in ranked]


__all__ = ["score_destination", "rank_destinations"]
