"""
Module 2 — Persona preference questions.

PersonaQuestionAnswers now only carries the gold free-text field
(`small_thing`); the four radio-style probes (social_role, trip_feeling,
friction_response, ideal_atmosphere) live on TripConstraints. This
module exposes the question prompts the frontend renders and a thin
parser from raw form payload → PersonaQuestionAnswers.

PART2_QUESTIONS / SCREEN3_QUESTIONS predate the schema simplification —
they're kept as legacy reference for any FE flow that still surfaces
the old long-form prompts, but `parse_answers` only writes what the
current schema can hold.
"""

from jahnvi.schemas.user import PersonaQuestionAnswers

PART2_QUESTIONS = [
    {"id": "travel_goal",        "question": "What do you want to feel on this trip?",                        "type": "free_text"},
    {"id": "travel_personality", "question": "How do your friends describe you as a traveller?",              "type": "free_text"},
    {"id": "pace_preference",    "question": "How do you like your days to feel?",                            "type": "free_text"},
    {"id": "must_not_miss",      "question": "What's the one thing that would make this trip unforgettable?", "type": "free_text"},
    {"id": "leave_behind",       "question": "What do you want to leave behind?",                             "type": "free_text"},
    {"id": "ideal_companion",    "question": "Describe your ideal travel companion.",                          "type": "free_text"},
    {"id": "dream_trip",         "question": "In a few words, what does your ideal trip feel like?",          "type": "free_text"},
]

SCREEN3_QUESTIONS = [
    {"id": "memorable_moment",    "question": "What's a travel moment you keep coming back to?",             "type": "free_text"},
    {"id": "natural_drift",       "question": "Where do you naturally drift when you have no plan?",         "type": "free_text"},
    {"id": "impulsive_decision",  "question": "Tell us about a time you made an impulsive travel decision.", "type": "free_text"},
    {"id": "experiences_avoided", "question": "What kinds of experiences do you usually avoid?",             "type": "free_text"},
    {"id": "perfect_afternoon",   "question": "Describe your perfect unplanned afternoon.",                  "type": "free_text"},
    {"id": "lose_track_of_time",  "question": "What makes you completely lose track of time?",               "type": "free_text"},
    {"id": "small_thing",         "question": "A small thing that's made you weirdly happy lately.",         "type": "free_text"},
]


def get_questions() -> list[dict]:
    """
    Return all persona preference questions. The frontend renders these in
    its own order — see TripPreferences.jsx::PERSONA_SCREENS for the
    canonical user-facing copy.
    """
    return PART2_QUESTIONS + SCREEN3_QUESTIONS


def parse_answers(raw: dict) -> PersonaQuestionAnswers:
    """
    Map raw form values into a PersonaQuestionAnswers. The current schema
    only carries `small_thing`; everything else in the raw payload is
    ignored here (the radio-style probes go onto TripConstraints in
    module1_constraints).

    Expected input:
        {"small_thing": "...", ...other free-text fields the FE may include}

    Expected output:
        PersonaQuestionAnswers(small_thing="...")
    """
    small_thing = ""
    for key in ("small_thing", "small_special"):
        value = raw.get(key)
        if value:
            small_thing = str(value).strip()
            break
    return PersonaQuestionAnswers(small_thing=small_thing)
