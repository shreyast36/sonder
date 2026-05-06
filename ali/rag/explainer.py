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


async def explain_itinerary(itinerary: Itinerary, user_profile: UserProfile) -> Itinerary:
    """
    Populate the why_this field for every activity in the itinerary.
    Returns the same itinerary with all why_this fields filled in.

    Expected output:
        Itinerary with all ItineraryActivity.why_this fields populated.
        (Same structure as input, just with explanations added.)
    """
    # TODO: for each day, for each activity: retrieve context, generate explanation, set why_this
    raise NotImplementedError
