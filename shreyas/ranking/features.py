"""
Feature registry — reusable, side-effect-free scoring functions.

Each feature has the signature:
    feature(viewer, candidate, ctx) -> tuple[float, str]

`viewer` is the user (or any object with constraints / compatibility_signals).
`candidate` is the thing being scored (CoTravellerProfile / Destination /
Activity / etc — whatever the policy is ranking).
`ctx` is a dict the engine populates per-rank-call. Keys it may carry:
  - "retrieval_score": float          (Pinecone cosine for this candidate)
  - "surface":         str            ("cotraveller" | "destination" | "activity")
  - "salience":        dict[str,float] (viewer's per-question salience)

Return: (raw_score in [0,1], one-line human-readable explanation snippet).

NO weights live here. NO taxonomy similarity values. NO policy decisions.
All features assume their callers will weight them. The engine never reads
constants from this module beyond function references.
"""

from __future__ import annotations

from typing import Any, Callable

from jahnvi.schemas.enums import PacePreference, BudgetStyle
from shreyas.ranking.salience import (
    PERSONA_QUESTION_FIELDS,
    candidate_persona_answers,
    overlap_score,
    viewer_persona_answers,
)


# ── Helpers ────────────────────────────────────────────────────────────────


_PACE_ORDER   = [PacePreference.relaxed, PacePreference.moderate, PacePreference.packed]
_BUDGET_ORDER = [BudgetStyle.budget,     BudgetStyle.mid_range,    BudgetStyle.luxury]


def _resolve_enum(value: Any, order: list) -> Any:
    """Coerce enum or string into the enum form `order` understands."""
    if value is None:
        return None
    if value in order:
        return value
    # Accept .value strings (e.g. "relaxed")
    for item in order:
        if getattr(item, "value", None) == value:
            return item
    return None


def _ordinal_alignment(a: Any, b: Any, order: list) -> float:
    """1.0 exact, 0.5 one step, 0.0 two+ steps. None inputs return 0.5
    (neutral — we don't know, don't punish)."""
    a = _resolve_enum(a, order)
    b = _resolve_enum(b, order)
    if a is None or b is None:
        return 0.5
    try:
        ai, bi = order.index(a), order.index(b)
    except ValueError:
        return 0.5
    return max(0.0, 1.0 - 0.5 * abs(ai - bi))


def _viewer_emotional_signature(viewer: Any) -> str:
    cs = getattr(viewer, "compatibility_signals", None) or {}
    if isinstance(cs, dict):
        return (cs.get("emotional_signature") or "").strip()
    return (getattr(cs, "emotional_signature", "") or "").strip()


def _candidate_emotional_signature(candidate: Any) -> str:
    cs = getattr(candidate, "compatibility_signals", None) or {}
    if isinstance(cs, dict):
        return (cs.get("emotional_signature") or "").strip()
    return (getattr(cs, "emotional_signature", "") or "").strip()


def _viewer_constraints(viewer: Any) -> Any:
    return getattr(viewer, "constraints", None)


def _viewer_pace(viewer: Any) -> Any:
    c = _viewer_constraints(viewer)
    return getattr(c, "pace", None) if c else None


def _viewer_budget_style(viewer: Any) -> Any:
    c = _viewer_constraints(viewer)
    return getattr(c, "budget_style", None) if c else None


def _viewer_travel_style(viewer: Any) -> Any:
    c = _viewer_constraints(viewer)
    return getattr(c, "who_travelling_with", None) if c else None


def _viewer_top_interests(viewer: Any) -> set[str]:
    cs = getattr(viewer, "compatibility_signals", None) or {}
    if isinstance(cs, dict):
        return set(cs.get("top_interests") or [])
    return set(getattr(cs, "top_interests", []) or [])


def _viewer_avoid_list(viewer: Any) -> set[str]:
    c = _viewer_constraints(viewer)
    return set((getattr(c, "avoid_list", []) or [])) if c else set()


def _candidate_tags(candidate: Any) -> set[str]:
    return set((getattr(candidate, "tags", []) or []))


def _candidate_interests(candidate: Any) -> set[str]:
    """For CoTravellerProfile interests OR Destination/Activity tags."""
    interests = getattr(candidate, "interests", None)
    if interests:
        return set(interests)
    return _candidate_tags(candidate)


# ── Features ──────────────────────────────────────────────────────────────


def pinecone_passthrough(viewer: Any, candidate: Any, ctx: dict) -> tuple[float, str]:
    """Return the candidate's retrieval cosine score unchanged. The engine
    already exposes this as RankedCandidate.retrieval_score; the feature
    form is kept so V1 policies can include it in the weighted sum without
    a special case. In V2 it should be removed from the feature registry
    and read from RankedCandidate.retrieval_score directly."""
    score = float(ctx.get("retrieval_score") or 0.0)
    return max(0.0, min(1.0, score)), "vector similarity"


def salience_weighted_question_overlap(viewer: Any, candidate: Any, ctx: dict) -> tuple[float, str]:
    """Per-question answer alignment, weighted by viewer's salience.
    The salience distribution sums to 1.0, so the result is naturally in
    [0,1] without further normalization."""
    salience: dict[str, float] = ctx.get("salience") or {}
    if not salience:
        return 0.0, "no answer overlap"

    viewer_ans    = viewer_persona_answers(viewer)
    candidate_ans = candidate_persona_answers(candidate)
    per_q = overlap_score(viewer_ans, candidate_ans)

    score = sum(salience.get(field, 0.0) * per_q.get(field, 0.0) for field in PERSONA_QUESTION_FIELDS)
    score = max(0.0, min(1.0, score))

    top_field = max(per_q, key=lambda f: per_q[f] * salience.get(f, 0.0), default=None)
    if top_field and per_q.get(top_field, 0.0) > 0:
        snippet = f"answers align on {top_field}"
    else:
        snippet = "answers don't strongly align"
    return score, snippet


def signature_proximity(viewer: Any, candidate: Any, ctx: dict) -> tuple[float, str]:
    """Identity check on emotional signature. 1.0 if same key, 0.0 otherwise.
    No similarity matrix — we don't have enough data to claim proximity
    between distinct signatures yet. The feedback loop can learn richer
    relationships once interaction logs accumulate."""
    v = _viewer_emotional_signature(viewer)
    c = _candidate_emotional_signature(candidate)
    if v and c and v == c:
        return 1.0, f"shared signature ({v})"
    return 0.0, "different emotional signature"


def pace_ordinal_fit(viewer: Any, candidate: Any, ctx: dict) -> tuple[float, str]:
    v_pace = _viewer_pace(viewer)
    c_pace = getattr(candidate, "pace", None)
    score = _ordinal_alignment(v_pace, c_pace, _PACE_ORDER)
    return score, "pace alignment"


def budget_ordinal_fit(viewer: Any, candidate: Any, ctx: dict) -> tuple[float, str]:
    v_budget = _viewer_budget_style(viewer)
    c_budget = getattr(candidate, "budget_style", None)
    score = _ordinal_alignment(v_budget, c_budget, _BUDGET_ORDER)
    return score, "budget chemistry"


def style_match(viewer: Any, candidate: Any, ctx: dict) -> tuple[float, str]:
    v_style = _viewer_travel_style(viewer)
    c_style = getattr(candidate, "travel_style", None)
    if v_style is None or c_style is None:
        return 0.5, "travel style unknown"
    same = v_style == c_style
    val = getattr(v_style, "value", v_style)
    return (1.0 if same else 0.0), (f"both travel as {val}" if same else "different travel style")


def interest_jaccard(viewer: Any, candidate: Any, ctx: dict) -> tuple[float, str]:
    v = _viewer_top_interests(viewer)
    c = _candidate_interests(candidate)
    if not v or not c:
        return 0.0, "no interest overlap"
    shared = v & c
    union  = v | c
    score = len(shared) / max(1, len(union))
    if shared:
        first = next(iter(sorted(shared)))
        return score, f"both into {first.replace('_', ' ')}"
    return score, "different interests"


def tag_interest_overlap(viewer: Any, candidate: Any, ctx: dict) -> tuple[float, str]:
    """Used for Destination + Activity ranking — overlap between candidate
    tags and viewer's top_interests, minus any avoid_list hits."""
    interests = _viewer_top_interests(viewer)
    avoid     = _viewer_avoid_list(viewer)
    tags      = _candidate_tags(candidate)
    if not interests or not tags:
        return 0.0, "no tag overlap"
    hits = tags & interests
    penalty = len(tags & avoid)
    raw = (len(hits) - penalty) / max(1, len(interests))
    score = max(0.0, min(1.0, raw))
    if hits:
        first = next(iter(sorted(hits)))
        return score, f"tagged {first.replace('_', ' ')}"
    return score, "no tag overlap"


def activity_cost_fit(viewer: Any, candidate: Any, ctx: dict) -> tuple[float, str]:
    """Soft within-budget signal for activities. Hard-infeasible candidates
    are dropped pre-ranking by filters.py — this just rewards activities
    that sit comfortably below the daily budget vs ones that strain it."""
    c = _viewer_constraints(viewer)
    budget = float(getattr(c, "budget_usd", 0) or 0)
    days   = ctx.get("trip_days") or 1
    daily_budget = budget / max(1, int(days)) if budget > 0 else 0.0
    cost = float(getattr(candidate, "cost_usd", 0) or 0)
    if daily_budget <= 0:
        return 0.5, "no budget set"
    if cost <= 0:
        return 1.0, "no cost"
    ratio = cost / daily_budget
    # 0 cost → 1.0; cost == daily_budget → 0.5; cost >= 2x daily → 0.0
    score = max(0.0, 1.0 - 0.5 * ratio)
    return min(1.0, score), "fits daily budget"


def pace_duration_fit(viewer: Any, candidate: Any, ctx: dict) -> tuple[float, str]:
    """For activities: relaxed users prefer longer activities, packed users
    prefer shorter ones, moderate is neutral. Duration above 8h or below
    0.5h is suspect either way."""
    pace = _resolve_enum(_viewer_pace(viewer), _PACE_ORDER)
    duration = float(getattr(candidate, "duration_hours", 0) or 0)
    if duration <= 0:
        return 0.5, "no duration"

    if pace == PacePreference.relaxed:
        # Prefer 2–6h activities
        score = 1.0 if 2.0 <= duration <= 6.0 else max(0.0, 1.0 - abs(duration - 4.0) / 4.0)
    elif pace == PacePreference.packed:
        # Prefer 0.5–2.5h activities (more per day)
        score = 1.0 if 0.5 <= duration <= 2.5 else max(0.0, 1.0 - abs(duration - 1.5) / 2.5)
    else:
        # Moderate — accept a wide range
        score = 1.0 if 1.0 <= duration <= 5.0 else max(0.0, 1.0 - abs(duration - 3.0) / 4.0)
    return max(0.0, min(1.0, score)), "pace fits duration"


# ── Registry ──────────────────────────────────────────────────────────────


FeatureFn = Callable[[Any, Any, dict], tuple[float, str]]


FEATURE_REGISTRY: dict[str, FeatureFn] = {
    "pinecone_passthrough":                pinecone_passthrough,
    "salience_weighted_question_overlap":  salience_weighted_question_overlap,
    "signature_proximity":                 signature_proximity,
    "pace_ordinal_fit":                    pace_ordinal_fit,
    "budget_ordinal_fit":                  budget_ordinal_fit,
    "style_match":                         style_match,
    "interest_jaccard":                    interest_jaccard,
    "tag_interest_overlap":                tag_interest_overlap,
    "activity_cost_fit":                   activity_cost_fit,
    "pace_duration_fit":                   pace_duration_fit,
}


def get_feature(name: str) -> FeatureFn:
    """Look up a feature implementation by name. Raises KeyError on unknown
    name — fail loudly when a policy references a feature that doesn't
    exist rather than silently scoring zero."""
    if name not in FEATURE_REGISTRY:
        raise KeyError(f"Unknown feature {name!r}. Known: {sorted(FEATURE_REGISTRY)}")
    return FEATURE_REGISTRY[name]
