import pytest
from jahnvi.pipeline.module1_constraints import capture_constraints
from jahnvi.pipeline.module2_preferences import get_questions, parse_answers
from jahnvi.pipeline.module3_persona import (
    infer_persona, infer_emotion, build_compatibility_signals,
    build_travel_style_embedding, update_profile_from_feedback,
)
from shared.schemas import TripConstraints, PersonaQuestionAnswers, EmotionIntent


# ── Module 1 — capture_constraints ───────────────────────────────────────────

def test_capture_constraints_stub():
    with pytest.raises(NotImplementedError):
        capture_constraints({
            "destination_type": "beach",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "budget_usd": 2000.0,
            "group_size": 2,
            "pace_preference": "relaxed",
        })
    # TODO: returns TripConstraints with dates parsed to date objects


# ── Module 2 — parse_answers ──────────────────────────────────────────────────

def test_get_questions_stub():
    with pytest.raises(NotImplementedError):
        get_questions()
    # TODO: returns list of dicts with 'key', 'question', 'type' fields


def test_parse_answers_stub():
    with pytest.raises(NotImplementedError):
        parse_answers({
            "food_interest": 5, "adventure_interest": 2,
            "culture_interest": 4, "nature_interest": 3,
            "nightlife_interest": 1, "budget_style": "mid_range",
            "travel_style": "couple", "pace_preference": "relaxed",
            "energy_level": 3,
        })
    # TODO: returns PersonaQuestionAnswers with validated int fields (ge=1, le=5)


# ── Module 3 — persona inference ──────────────────────────────────────────────

def test_infer_persona_stub(persona_answers):
    with pytest.raises(NotImplementedError):
        infer_persona(persona_answers)
    # TODO: returns dict with keys: archetype, top_interests, energy, label


def test_infer_emotion_stub():
    with pytest.raises(NotImplementedError):
        infer_emotion({"pace": "relaxed", "energy_level": 3, "top_interests": ["food"]})
    # TODO: returns EmotionIntent enum value


def test_build_compatibility_signals_stub(user_profile):
    with pytest.raises(NotImplementedError):
        build_compatibility_signals(user_profile)
    # TODO: returns dict with at least 'pace' and 'top_interests' keys


def test_build_travel_style_embedding_stub(user_profile):
    with pytest.raises(NotImplementedError):
        build_travel_style_embedding(user_profile)
    # TODO: returns list[float] of length EMBED_DIMENSIONS (calls shreyas embed_text)


def test_update_profile_from_feedback_stub(user_profile):
    with pytest.raises(NotImplementedError):
        update_profile_from_feedback(user_profile, "I want more adventure activities")
    # TODO: returns updated UserProfile with adjusted compatibility_signals
