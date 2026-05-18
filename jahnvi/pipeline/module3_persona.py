"""
Module 3 — Persona inference.

Persona dimension labels (top_push, top_interests) and reveal copy now
come from the LLM via mushahid/routes/persona.py. This module only:
  - Embeds the user persona text via HF (durable user_vector).
  - Maintains build_travel_style_embedding / build_compatibility_embedding
    for downstream Pinecone retrieval + co-traveller matching.

NOTE — infer_emotion() is a stub. Wire in your chosen emotion model
(e.g. GoEmotions) and map its output to EmotionIntent before this module
is used in production.
"""

import logging

from jahnvi.schemas.user import UserProfile, TripConstraints, PersonaQuestionAnswers
from jahnvi.schemas.enums import EmotionIntent, PacePreference
from jahnvi.data.dimensions import PUSH_DIMENSIONS, PULL_DIMENSIONS
from jahnvi.data.convert_to_embeddings import build_persona_text, embed_text

logger = logging.getLogger(__name__)

_BUDGET_CEILING_USD = 15_000.0


def _resolve_pace(pace: PacePreference | str | None) -> str:
    if isinstance(pace, PacePreference):
        return pace.value
    return pace or "moderate"


# ── Public functions ──────────────────────────────────────────────────────────

async def infer_persona(
    constraints: TripConstraints | None = None,
    answers: PersonaQuestionAnswers | None = None,
    pace: PacePreference | str | None = None,
) -> dict:
    """
    Embed persona text → user_vector via the configured provider
    (OpenAI text-embedding-3-small by default, same as the Pinecone corpus).
    Dimension labels (top_push, top_interests) and reveal copy come from
    the LLM downstream of this call; this function returns empty lists for
    them so the result shape stays compatible with legacy callers.

    Expected output:
        {
            "push":          {},        # populated by LLM, not here
            "pull":          {},
            "top_push":      [],
            "top_interests": [],
            "pace":          "relaxed",
            "user_vector":   [0.012, -0.034, ...],   # 1536-dim
        }
    """
    text = build_persona_text(constraints, answers)
    user_vector = await embed_text(text) if text else []

    resolved_pace = pace if pace is not None else (constraints.pace if constraints else None)
    pace_value = _resolve_pace(resolved_pace)

    return {
        "push":          {},
        "pull":          {},
        "top_push":      [],
        "top_interests": [],
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
    Extract structured signals for co-traveller matching.

    push/pull dimension scores now come from the LLM at /persona-infer time
    and are expected to live on profile.compatibility_signals already. This
    function only fills in budget + travel_style + pace from constraints.
    """
    signals: dict = dict(profile.compatibility_signals or {})

    budget_usd = (profile.constraints.budget_usd if profile.constraints else 0) or 0
    signals["budget_score"] = round(min(budget_usd / _BUDGET_CEILING_USD, 1.0), 3)

    if profile.constraints and profile.constraints.who_travelling_with:
        signals["travel_style"] = profile.constraints.who_travelling_with.value
    else:
        signals.setdefault("travel_style", "solo")

    pace = profile.constraints.pace if profile.constraints else None
    signals.setdefault("pace", _resolve_pace(pace))

    # Fill these with empty defaults if the LLM stage hasn't run yet.
    signals.setdefault("push", {dim: 0.0 for dim in PUSH_DIMENSIONS})
    signals.setdefault("pull", {dim: 0.0 for dim in PULL_DIMENSIONS})
    signals.setdefault("top_push", [])
    signals.setdefault("top_interests", [])

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
    Refinement feedback path. Appends the feedback to the persona text and
    re-embeds for travel_style_embedding. Dimension re-scoring is handled
    by re-calling /persona-infer (LLM-side), not here.
    """
    feedback_clean = (feedback or "").strip()
    if feedback_clean:
        existing_pa = profile.persona_answers
        merged_small = (existing_pa.small_thing if existing_pa else "") or ""
        if merged_small:
            merged_small = f"{merged_small}. {feedback_clean}"
        else:
            merged_small = feedback_clean
        new_pa = (existing_pa.model_copy(update={"small_thing": merged_small})
                  if existing_pa else PersonaQuestionAnswers(small_thing=merged_small))
        profile = profile.model_copy(update={"persona_answers": new_pa})

    updated = profile.model_copy(update={
        "travel_style_embedding": await build_travel_style_embedding(profile),
    })
    return updated
