"""
Module 3 — Persona inference.

Produces continuous dimension scores (0.0–1.0) rather than fixed archetype buckets.
Dimension vocabulary lives in jahnvi/data/dimensions.py — nothing is hardcoded here.
Budget is normalised as a continuous score, not tiered.

NOTE — infer_emotion() is a stub. Wire in your chosen emotion model (e.g. GoEmotions)
and map its output to EmotionIntent before this module is used in production.
"""

import logging

from jahnvi.schemas.user import UserProfile, PersonaQuestionAnswers
from jahnvi.schemas.enums import EmotionIntent
from jahnvi.data.dimensions import TRAVEL_DIMENSIONS, PACE_SIGNALS

logger = logging.getLogger(__name__)

_BUDGET_CEILING_USD = 15_000.0


def _combined_text(answers: PersonaQuestionAnswers) -> str:
    return " ".join([
        answers.travel_goal, answers.travel_personality, answers.pace_preference,
        answers.must_not_miss, answers.leave_behind, answers.ideal_companion,
        answers.dream_trip, answers.memorable_moment, answers.natural_drift,
        answers.impulsive_decision, answers.experiences_avoided,
        answers.perfect_afternoon, answers.lose_track_of_time, answers.small_special,
    ]).lower()


def _score_dimensions(text: str) -> dict[str, float]:
    """
    Score each dimension by keyword hit density, normalised to 0.0–1.0.
    5 hits per 50 words → 1.0; scales linearly below that.
    """
    if not text.strip():
        return {dim: 0.0 for dim in TRAVEL_DIMENSIONS}

    word_count = max(len(text.split()), 1)
    scores = {}
    for dim, keywords in TRAVEL_DIMENSIONS.items():
        hits    = sum(1 for kw in keywords if kw in text)
        density = hits / (word_count / 50)
        scores[dim] = round(min(density / 5.0, 1.0), 3)
    return scores


def _infer_pace(text: str) -> str:
    for pace, keywords in PACE_SIGNALS.items():
        if any(kw in text for kw in keywords):
            return pace
    return "moderate"


def score_persona(answers: PersonaQuestionAnswers) -> dict[str, float]:
    """
    Return raw dimension scores for a set of persona answers.

    Expected output:
        {"adventure": 0.8, "food": 0.9, "culture": 0.3, "wellness": 0.1, ...}
    """
    return _score_dimensions(_combined_text(answers))


def infer_persona(answers: PersonaQuestionAnswers) -> dict:
    """
    Return dimension scores, top interests, and inferred pace.
    No archetype buckets — downstream systems use the scores directly.

    Expected output:
        {
            "dimensions":    {"adventure": 0.8, "food": 0.9, ...},
            "top_interests": ["food", "adventure", "discovery"],
            "pace":          "relaxed",
        }
    """
    text       = _combined_text(answers)
    dimensions = _score_dimensions(text)
    pace       = _infer_pace(text)
    top        = sorted(dimensions, key=dimensions.get, reverse=True)[:3]
    return {"dimensions": dimensions, "top_interests": top, "pace": pace}


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
    Budget is a continuous 0–1 score; dimensions are continuous 0–1 scores.

    Expected output:
        {
            "dimensions":    {"adventure": 0.8, "food": 0.9, ...},
            "top_interests": ["food", "adventure", "discovery"],
            "pace":          "relaxed",
            "budget_score":  0.35,
            "travel_style":  "couple",
        }
    """
    signals: dict = {}

    budget_usd = (profile.constraints.budget_usd if profile.constraints else 0) or 0
    signals["budget_score"] = round(min(budget_usd / _BUDGET_CEILING_USD, 1.0), 3)

    if profile.constraints and profile.constraints.who_travelling_with:
        signals["travel_style"] = profile.constraints.who_travelling_with.value
    else:
        signals["travel_style"] = "solo"

    if profile.persona_answers:
        persona = infer_persona(profile.persona_answers)
        signals["dimensions"]    = persona["dimensions"]
        signals["top_interests"] = persona["top_interests"]
        signals["pace"]          = persona["pace"]
    else:
        signals["dimensions"]    = {dim: 0.0 for dim in TRAVEL_DIMENSIONS}
        signals["top_interests"] = []
        signals["pace"]          = "moderate"

    return signals


async def build_travel_style_embedding(profile: UserProfile) -> list[float]:
    """
    Embed the user's travel persona for destination and activity search in Pinecone.
    Stored in profile.travel_style_embedding.
    """
    from shreyas.retrieval.embeddings import embed_text

    parts: list[str] = []

    if profile.constraints:
        c = profile.constraints
        if c.destination_query:
            parts.append(c.destination_query)
        if c.who_travelling_with:
            parts.append(c.who_travelling_with.value)
        if c.must_haves:
            parts.extend(c.must_haves)

    if profile.persona_answers:
        pa = profile.persona_answers
        for field in [pa.travel_goal, pa.travel_personality, pa.pace_preference,
                      pa.must_not_miss, pa.dream_trip]:
            if field:
                parts.append(field)

    if profile.emotion_intent:
        parts.append(profile.emotion_intent.value)

    if profile.compatibility_signals:
        cs = profile.compatibility_signals
        if cs.get("top_interests"):
            parts.extend(cs["top_interests"])
        if cs.get("pace"):
            parts.append(cs["pace"])

    embed_string = " | ".join(p.strip() for p in parts if p.strip()) or profile.display_name
    return await embed_text(embed_string)


async def build_compatibility_embedding(profile: UserProfile) -> list[float]:
    """
    Embed CompatibilityAnswers for co-traveller matching.
    Separate from travel_style_embedding — Shreyas uses this exclusively.
    """
    from shreyas.retrieval.embeddings import embed_text

    if not profile.compatibility_answers:
        return await embed_text(profile.display_name)

    ca = profile.compatibility_answers
    parts = [
        ca.trust_behaviour, ca.space_behaviour, ca.natural_role,
        ca.travelled_well_with, ca.when_plans_fall_apart, ca.comfortable_silence,
        ca.late_night_conversations, ca.independence_needed, ca.travel_again,
    ]
    embed_string = " | ".join(p.strip() for p in parts if p.strip()) or profile.display_name
    return await embed_text(embed_string)


async def update_profile_from_feedback(profile: UserProfile, feedback: str) -> UserProfile:
    """
    Re-score dimensions incorporating refinement feedback, then re-embed.
    Called by the refinement loop before each re-ranking pass.

    Feedback text is appended to the existing persona text so explicit
    signals in the feedback shift dimension scores accordingly.
    """
    existing  = _combined_text(profile.persona_answers) if profile.persona_answers else ""
    merged    = f"{existing} {feedback.lower()}".strip()

    dimensions    = _score_dimensions(merged)
    pace          = _infer_pace(merged)
    top_interests = sorted(dimensions, key=dimensions.get, reverse=True)[:3]

    updated_signals = {
        **(profile.compatibility_signals or {}),
        "dimensions":      dimensions,
        "top_interests":   top_interests,
        "pace":            pace,
        "feedback_weight": 0.4,
    }

    updated = profile.model_copy(update={"compatibility_signals": updated_signals})
    updated = updated.model_copy(update={
        "travel_style_embedding": await build_travel_style_embedding(updated),
    })
    return updated
