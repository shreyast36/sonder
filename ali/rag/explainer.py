from shared.schemas import Activity, Itinerary, UserProfile
from ali.rag.retriever import retrieve_activity_context
from ali.routing.engine import route_request


async def explain_activity(
    activity: Activity,
    context: list[str],
    user_profile: UserProfile,
) -> str:
    """
    Generate the "Why this?" explanation shown under each activity card (Screen 3).
    Routes to the LARGE model tier for grounded, personalised explanations.

    Expected input:
        activity     = Activity(name="Uluwatu Temple", category="culture", duration_hours=2.0)
        context      = ["Uluwatu sits on a 70m cliff...", "Perfect for slow travellers..."]
        user_profile = UserProfile(persona_answers=PersonaQuestionAnswers(culture_interest=5, pace="relaxed"))

    Expected output:
        "This matches your relaxed pace and love for culture.
         Uluwatu Temple offers a serene 2-hour experience on dramatic ocean cliffs —
         the sunset Kecak dance here is one of Bali's most memorable cultural moments."
    """
    # TODO: build prompt with activity + context + user persona, route to "rag_explanation"
    raise NotImplementedError


async def explain_day(day, user_profile: UserProfile):
    """
    [Gap 4] Populate why_this for every activity in a single ItineraryDay.
    Called by the orchestrator immediately as each day is yielded by generate_itinerary_by_day(),
    without waiting for all days to finish — enabling pipelined explanation.

    Expected input:
        day          = ItineraryDay(day_number=1, theme="Culture & Coastal Views", activities=[...])
        user_profile = UserProfile(...)

    Expected output:
        ItineraryDay with all ItineraryActivity.why_this fields populated.

    Implementation note:
        Explanations for all activities within the day can run concurrently:
        asyncio.gather(*[explain_activity(a.activity, context, user_profile) for a in day.activities])
    """
    # TODO: for each activity in day.activities:
    #           context = await retrieve_activity_context(activity, user_profile)
    #           activity.why_this = await explain_activity(activity, context, user_profile)
    # TODO: return day with all why_this fields populated
    raise NotImplementedError


async def explain_itinerary(itinerary: Itinerary, user_profile: UserProfile) -> Itinerary:
    """
    Populate the why_this field for every activity in the full itinerary.
    Runs all days concurrently via asyncio.gather — use this when you have
    the full itinerary already assembled (e.g. after a refinement pass).
    For the initial generation pipeline, prefer explain_day() called per day.

    Expected output:
        Itinerary with all ItineraryActivity.why_this fields populated.
    """
    # TODO: import asyncio
    # TODO: explained_days = await asyncio.gather(*[explain_day(day, user_profile) for day in itinerary.days])
    # TODO: itinerary.days = list(explained_days)
    # TODO: return itinerary
    raise NotImplementedError
