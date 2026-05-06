from shared.schemas import UserProfile, CoTravellerMatch, Itinerary
from ali.routing.engine import route_request


async def generate_topics(
    user_profile: UserProfile,
    match: CoTravellerMatch,
    itinerary: Itinerary,
) -> list[str]:
    """
    Generate 5 AI conversation starters for the chat screen (Screen 5).
    Routes to the SMALL model tier — must be fast.

    Expected input:
        user_profile = UserProfile(persona_answers=PersonaQuestionAnswers(food_interest=5, culture_interest=4))
        match        = CoTravellerMatch(profile=CoTravellerProfile(interests=["food","culture"]), match_score=0.92)
        itinerary    = Itinerary(destination=Destination(city="Bali"), ...)

    Expected output:
        [
            "Must-try local food in Bali",
            "Beach vs adventure balance",
            "Cultural experiences to explore",
            "Budget-friendly activities",
            "Best time to travel & weather"
        ]
    """
    # TODO: build prompt from shared interests + itinerary destination, route to "chat_topics"
    raise NotImplementedError


async def generate_icebreaker(user_profile: UserProfile, match: CoTravellerMatch) -> str:
    """
    Generate a single opening message suggestion shown on the chat screen.
    Routes to the SMALL model tier.

    Expected output:
        "Hey Maya! I'm from Mumbai too — can't wait to explore Bali's food scene together! 🍜"

    (Tone: warm, personal, references a shared interest)
    """
    # TODO: build prompt, route to "icebreaker"
    raise NotImplementedError
