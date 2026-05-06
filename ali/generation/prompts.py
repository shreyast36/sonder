from shared.schemas import UserProfile, Destination, Activity, Itinerary
from shared.schemas import ValidationResult

ITINERARY_SYSTEM_PROMPT = """
You are an expert travel planner. Your job is to create personalised, day-by-day trip itineraries.
Always output valid JSON matching the Itinerary schema.
Respect the user's budget, pace preference, must-haves, and avoid list exactly.
"""
# TODO: Ali — refine this system prompt. Add output JSON schema example to reduce hallucinations.


REFINEMENT_SYSTEM_PROMPT = """
You are revising a trip itinerary based on user feedback and validation issues.
Keep what the user liked. Fix only what was flagged.
Output valid JSON matching the Itinerary schema.
"""
# TODO: Ali — refine this prompt. Include specific instructions for each validation failure type.


def build_itinerary_prompt(
    user_profile: UserProfile,
    destination: Destination,
    activities: list[Activity],
) -> str:
    """
    Build the user-turn prompt for itinerary generation.

    Expected output (example):
        "Create a 7-day beach trip itinerary for Bali, Indonesia for 2 people.
         Budget: $2000 total ($285/day). Pace: relaxed. Must include: snorkeling, local food.
         Avoid: nightclubs.
         Persona: Cultural Explorer — loves food (5/5) and culture (4/5).
         Mood: excited.
         Available activities: [Uluwatu Temple, Padang Padang Beach, Jimbaran Bay Dinner, ...]
         Output the itinerary as JSON."
    """
    # TODO: format trip_days, daily_budget, must_haves, avoid_list, persona archetype, activity names
    raise NotImplementedError


def build_refinement_prompt(
    itinerary: Itinerary,
    feedback: str,
    validation_result: ValidationResult,
) -> str:
    """
    Build the prompt for the refinement loop when an itinerary needs revision.

    Expected output (example):
        "Here is the current itinerary: {...}
         User feedback: 'I want more time at each place, fewer activities per day.'
         Validation issues: budget exceeded by $120; Day 3 is too packed for a relaxed pace.
         Please revise the itinerary to fix these issues while keeping the destinations the user liked."
    """
    # TODO: serialise current itinerary, inject feedback and validation feedback
    raise NotImplementedError
