from typing import AsyncIterator
from shared.schemas import UserProfile, Destination, Activity, Itinerary
from ali.routing.engine import stream_request
from ali.generation.prompts import ITINERARY_SYSTEM_PROMPT, build_itinerary_prompt
from ali.generation.output_parser import parse_itinerary, validate_structure


async def generate_itinerary(
    user_profile: UserProfile,
    destination: Destination,
    activities: list[Activity],
) -> AsyncIterator[str]:
    """
    Generate a day-by-day itinerary. Streams token chunks for Mushahid's SSE layer.

    Expected input:
        user_profile = UserProfile(constraints=TripConstraints(budget_usd=2000, ...), ...)
        destination  = Destination(city="Bali", country="Indonesia", ...)
        activities   = [Activity(name="Uluwatu Temple", ...), ...]  # ranked by Shreyas

    Expected streaming output (token chunks):
        '{"days"' → ': [{"day' → '_number": 1' → ', "theme": "Culture...' → ...

    Final assembled output (after all chunks):
        Itinerary(
            itinerary_id    = "itin_abc123",
            destination     = Destination(city="Bali", ...),
            days            = [
                ItineraryDay(day_number=1, theme="Culture & Coastal Views", daily_cost_usd=140, activities=[
                    ItineraryActivity(time="9:00 AM",  activity=Activity(name="Uluwatu Temple"), why_this=None),
                    ItineraryActivity(time="1:00 PM",  activity=Activity(name="Padang Padang Beach"), why_this=None),
                    ItineraryActivity(time="6:00 PM",  activity=Activity(name="Jimbaran Bay Dinner"), why_this=None),
                ]),
                ...
            ],
            total_budget_usd = 840.0
        )

    Note: why_this fields are populated separately by ali/rag/explainer.py after generation.
    """
    prompt = build_itinerary_prompt(user_profile, destination, activities)
    # TODO: async for chunk in stream_request("itinerary_generation", prompt, ITINERARY_SYSTEM_PROMPT): yield chunk
    raise NotImplementedError
