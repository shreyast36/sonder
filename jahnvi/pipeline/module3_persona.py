"""
Module 3 — Persona inference.

Scores users on Push-Pull motivation dimensions (see jahnvi/data/dimensions.py).
  PUSH → why they travel → feeds travel_style_embedding and co-traveller matching
  PULL → what they want  → feeds destination and activity search in Pinecone

Budget is a continuous 0–1 score (not tiered).

NOTE — infer_emotion() is a stub. Wire in your chosen emotion model (e.g. GoEmotions)
and map its output to EmotionIntent before this module is used in production.
"""

import logging

from jahnvi.schemas.user import UserProfile, PersonaQuestionAnswers
from jahnvi.schemas.enums import EmotionIntent
from jahnvi.data.dimensions import PUSH_DIMENSIONS, PULL_DIMENSIONS, PACE_SIGNALS, ALL_DIMENSIONS

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


def _score_dimension_set(text: str, dimensions: dict[str, list[str]]) -> dict[str, float]:
    """
    Score a set of dimensions by keyword hit density, normalised to 0.0–1.0.
    5 hits per 50 words → 1.0; scales linearly below that.
    """
    if not text.strip():
        return {dim: 0.0 for dim in dimensions}

    word_count = max(len(text.split()), 1)
    scores = {}
    for dim, keywords in dimensions.items():
        hits    = sum(1 for kw in keywords if kw in text)
        density = hits / (word_count / 50)
        scores[dim] = round(min(density / 5.0, 1.0), 3)
    return scores


def _infer_pace(text: str) -> str:
    for pace, keywords in PACE_SIGNALS.items():
        if any(kw in text for kw in keywords):
            return pace
    return "moderate"


# ── Public functions ──────────────────────────────────────────────────────────

def infer_persona(answers: PersonaQuestionAnswers) -> dict:
    """
    Score the user's push motivations, pull preferences, pace, and top interests.
    No archetype buckets — downstream systems use the scores directly.

    Expected output:
        {
            "push": {"escape": 0.8, "rest": 0.6, "adventure_seeking": 0.2, ...},
            "pull": {"food": 0.9, "culture": 0.5, "nature": 0.3, ...},
            "top_push":      ["escape", "rest"],
            "top_interests": ["food", "culture", "discovery"],
            "pace":          "relaxed",
        }
    """
    text = _combined_text(answers)
    push = _score_dimension_set(text, PUSH_DIMENSIONS)
    pull = _score_dimension_set(text, PULL_DIMENSIONS)
    pace = _infer_pace(text)

    top_push      = sorted(push, key=push.get, reverse=True)[:2]
    top_interests = sorted(pull, key=pull.get, reverse=True)[:3]

    return {
        "push":          push,
        "pull":          pull,
        "top_push":      top_push,
        "top_interests": top_interests,
        "pace":          pace,
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

    Expected output:
        {
            "push":          {"escape": 0.8, "rest": 0.6, ...},
            "pull":          {"food": 0.9, "culture": 0.5, ...},
            "top_push":      ["escape", "rest"],
            "top_interests": ["food", "culture", "discovery"],
            "pace":          "relaxed",
            "budget_score":  0.35,
            "travel_style":  "couple",
        }
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

    # Push/pull dimensions + pace
    if profile.persona_answers:
        persona = infer_persona(profile.persona_answers)
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
    Includes both push motivation language and pull preference language.
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
                      pa.must_not_miss, pa.dream_trip, pa.leave_behind]:
            if field:
                parts.append(field)

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
    Re-score push/pull dimensions incorporating refinement feedback, then re-embed.
    Called by the refinement loop before each re-ranking pass.

    Feedback is appended to the persona text so explicit signals shift scores accordingly.
    """
    existing = _combined_text(profile.persona_answers) if profile.persona_answers else ""
    merged   = f"{existing} {feedback.lower()}".strip()

    push          = _score_dimension_set(merged, PUSH_DIMENSIONS)
    pull          = _score_dimension_set(merged, PULL_DIMENSIONS)
    pace          = _infer_pace(merged)
    top_push      = sorted(push, key=push.get, reverse=True)[:2]
    top_interests = sorted(pull, key=pull.get, reverse=True)[:3]

    updated_signals = {
        **(profile.compatibility_signals or {}),
        "push":            push,
        "pull":            pull,
        "top_push":        top_push,
        "top_interests":   top_interests,
        "pace":            pace,
        "feedback_weight": 0.4,
    }

    updated = profile.model_copy(update={"compatibility_signals": updated_signals})
    updated = updated.model_copy(update={
        "travel_style_embedding": await build_travel_style_embedding(updated),
    })
    return updated
