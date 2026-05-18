"""
Module 3 — Persona inference.

Scores users on Push-Pull motivation dimensions (see jahnvi/data/dimensions.py)
via HF sentence-embedding similarity (see jahnvi/data/convert_to_embeddings.py).
  PUSH → why they travel → feeds travel_style_embedding and co-traveller matching
  PULL → what they want  → feeds destination and activity search in Pinecone

Pace is structured on TripConstraints, not inferred.

NOTE — infer_emotion() is a stub. Wire in your chosen emotion model (e.g. GoEmotions)
and map its output to EmotionIntent before this module is used in production.
"""

import logging

import numpy as np

from jahnvi.schemas.user import UserProfile, TripConstraints, PersonaQuestionAnswers
from jahnvi.schemas.enums import EmotionIntent, PacePreference
from jahnvi.data.dimensions import PUSH_DIMENSIONS, PULL_DIMENSIONS
from jahnvi.data.convert_to_embeddings import (
    build_persona_text, dimension_prototypes, embed_text,
)

logger = logging.getLogger(__name__)

_BUDGET_CEILING_USD = 15_000.0


def _score_against_prototypes(text: str) -> dict[str, float]:
    """Cosine similarity between user text embedding and each dimension prototype."""
    if not text or not text.strip():
        return {dim: 0.0 for dim in {**PUSH_DIMENSIONS, **PULL_DIMENSIONS}}

    user_vec = np.asarray(embed_text(text))
    protos = dimension_prototypes()
    return {
        dim: round(float(np.dot(user_vec, np.asarray(proto))), 3)
        for dim, proto in protos.items()
    }


def _resolve_pace(pace: PacePreference | str | None) -> str:
    if isinstance(pace, PacePreference):
        return pace.value
    return pace or "moderate"


# ── Public functions ──────────────────────────────────────────────────────────

def infer_persona(
    constraints: TripConstraints | None = None,
    answers: PersonaQuestionAnswers | None = None,
    pace: PacePreference | str | None = None,
) -> dict:
    """
    Score push motivations + pull preferences via HF embedding + cosine vs
    pre-computed dimension prototypes. pace is structured (from constraints
    or passed in); falls back to 'moderate'.

    Expected output:
        {
            "push": {"escape_reset": 0.32, "connection": 0.11, ...},
            "pull": {"food_drink": 0.41, "culture_history": 0.18, ...},
            "top_push":      ["escape_reset", "connection"],
            "top_interests": ["food_drink", "culture_history", "exploration_local"],
            "pace":          "relaxed",
            "user_vector":   [0.012, -0.034, ...],   # 768-dim, normalized
        }
    """
    text = build_persona_text(constraints, answers)
    scores = _score_against_prototypes(text)

    push = {d: scores[d] for d in PUSH_DIMENSIONS}
    pull = {d: scores[d] for d in PULL_DIMENSIONS}

    resolved_pace = pace if pace is not None else (constraints.pace if constraints else None)
    pace_value = _resolve_pace(resolved_pace)

    top_push      = sorted(push, key=push.get, reverse=True)[:2]
    top_interests = sorted(pull, key=pull.get, reverse=True)[:3]

    user_vector = embed_text(text) if text else []

    return {
        "push":          push,
        "pull":          pull,
        "top_push":      top_push,
        "top_interests": top_interests,
        "pace":          pace_value,
        "user_vector":   user_vector,
    }


def infer_emotion(answers: PersonaQuestionAnswers) -> EmotionIntent:
    """
    TODO: wire in your chosen emotion model (e.g. GoEmotions via HuggingFace pipeline)
    and map its output labels to EmotionIntent values.

    Stub returns EmotionIntent.curious until implemented.
    """
    return EmotionIntent.curious


def build_compatibility_signals(profile: UserProfile) -> dict:
    """
    Extract structured signals for Shreyas's co-traveller matching algorithm.

    PUSH signals drive matching — two people travelling for the same reason
    are more compatible than two people who want the same destination.
    """
    signals: dict = {}

    # Budget — continuous score, not tiered
    budget_usd = (profile.constraints.budget_usd if profile.constraints else 0) or 0
    signals["budget_score"] = round(min(budget_usd / _BUDGET_CEILING_USD, 1.0), 3)

    # Travel style — from constraints
    if profile.constraints and profile.constraints.who_travelling_with:
        signals["travel_style"] = profile.constraints.who_travelling_with.value
    else:
        signals["travel_style"] = "solo"

    # Push/pull dimensions + pace (pace is structured from constraints)
    if profile.constraints or profile.persona_answers:
        persona = infer_persona(profile.constraints, profile.persona_answers)
        signals["push"]          = persona["push"]
        signals["pull"]          = persona["pull"]
        signals["top_push"]      = persona["top_push"]
        signals["top_interests"] = persona["top_interests"]
        signals["pace"]          = persona["pace"]
    else:
        signals["push"]          = {dim: 0.0 for dim in PUSH_DIMENSIONS}
        signals["pull"]          = {dim: 0.0 for dim in PULL_DIMENSIONS}
        signals["top_push"]      = []
        signals["top_interests"] = []
        signals["pace"]          = "moderate"

    return signals


async def build_travel_style_embedding(profile: UserProfile) -> list[float]:
    """
    Embed the user's travel persona for destination and activity search in Pinecone.
    Uses Shreyas's corpus embedder (NOT the HF persona embedder) to keep vector
    space consistent with the seeded Pinecone index.
    """
    from shreyas.retrieval.embeddings import embed_text as corpus_embed

    parts: list[str] = []

    if profile.constraints:
        c = profile.constraints
        if c.destination_query:
            parts.append(c.destination_query)
        if c.who_travelling_with:
            parts.append(c.who_travelling_with.value)
        if c.must_haves:
            parts.extend(c.must_haves)

    if profile.persona_answers and profile.persona_answers.small_thing:
        parts.append(profile.persona_answers.small_thing)

    if profile.emotion_intent:
        parts.append(profile.emotion_intent.value)

    if profile.compatibility_signals:
        cs = profile.compatibility_signals
        if cs.get("top_push"):
            parts.extend(cs["top_push"])
        if cs.get("top_interests"):
            parts.extend(cs["top_interests"])
        if cs.get("pace"):
            parts.append(cs["pace"])

    embed_string = " | ".join(p.strip() for p in parts if p.strip()) or profile.display_name
    return await corpus_embed(embed_string)


async def build_compatibility_embedding(profile: UserProfile) -> list[float]:
    """
    Embed CompatibilityAnswers for co-traveller matching.
    Separate from travel_style_embedding — Shreyas uses this exclusively.
    """
    from shreyas.retrieval.embeddings import embed_text as corpus_embed

    if not profile.compatibility_answers:
        return await corpus_embed(profile.display_name)

    ca = profile.compatibility_answers
    parts = [
        ca.trust_behaviour, ca.space_behaviour, ca.natural_role,
        ca.travelled_well_with, ca.when_plans_fall_apart, ca.comfortable_silence,
        ca.late_night_conversations, ca.independence_needed, ca.travel_again,
    ]
    embed_string = " | ".join(p.strip() for p in parts if p.strip()) or profile.display_name
    return await corpus_embed(embed_string)


async def update_profile_from_feedback(profile: UserProfile, feedback: str) -> UserProfile:
    """
    Re-score push/pull dimensions incorporating refinement feedback, then re-embed.
    Called by the refinement loop before each re-ranking pass.

    Feedback is concatenated with the persona text and re-embedded so explicit
    signals shift the cosine scores accordingly.
    """
    base_text = build_persona_text(
        profile.constraints if profile.constraints else None,
        profile.persona_answers if profile.persona_answers else None,
    )
    merged_text = f"{base_text}. {feedback}".strip(". ").strip()

    scores = _score_against_prototypes(merged_text)
    push = {d: scores[d] for d in PUSH_DIMENSIONS}
    pull = {d: scores[d] for d in PULL_DIMENSIONS}

    pace = profile.constraints.pace if profile.constraints else None
    pace_value = _resolve_pace(pace)

    top_push      = sorted(push, key=push.get, reverse=True)[:2]
    top_interests = sorted(pull, key=pull.get, reverse=True)[:3]

    updated_signals = {
        **(profile.compatibility_signals or {}),
        "push":            push,
        "pull":            pull,
        "top_push":        top_push,
        "top_interests":   top_interests,
        "pace":            pace_value,
        "feedback_weight": 0.4,
    }

    updated = profile.model_copy(update={"compatibility_signals": updated_signals})
    updated = updated.model_copy(update={
        "travel_style_embedding": await build_travel_style_embedding(updated),
    })
    return updated
