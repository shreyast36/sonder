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
    {"id": "small_special",       "question": "What small thing always makes a trip feel special?",          "type": "free_text"},
]

_ALL_QUESTION_IDS = {q["id"] for q in PART2_QUESTIONS + SCREEN3_QUESTIONS}


def get_questions() -> list[dict]:
    """
    Return all persona preference questions shown across Screen 2 (Part 2) and Screen 3.
    Frontend renders PART2_QUESTIONS as a group and SCREEN3_QUESTIONS one at a time.
    """
    return PART2_QUESTIONS + SCREEN3_QUESTIONS


def parse_answers(raw: dict) -> PersonaQuestionAnswers:
    """
    Map raw form values (free-text strings keyed by question id) into a PersonaQuestionAnswers.
    Any key not present in raw defaults to an empty string — all fields are optional.

    Expected input:
        {
            "travel_goal":     "I want to feel alive again",
            "pace_preference": "Slow mornings, free afternoons",
            ...
        }

    Expected output:
        PersonaQuestionAnswers(
            travel_goal     = "I want to feel alive again",
            pace_preference = "Slow mornings, free afternoons",
            ...  # unset fields default to ""
        )
    """
    return PersonaQuestionAnswers(**{
        field: str(raw.get(field) or "")
        for field in _ALL_QUESTION_IDS
    })
