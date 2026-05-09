import json
import re
from shared.schemas import UserProfile, CoTravellerMatch, Itinerary
from ali.routing.engine import route_request

_TOPICS_SYSTEM = (
    "You are helping two travel companions break the ice before their trip. "
    "Generate exactly 5 short conversation starter topics (3-6 words each). "
    "Output ONLY a JSON array of 5 strings — no explanation, no numbering, no extra text. "
    'Example: ["Must-try street food spots", "Beach or temple day first?", ...]'
)

_ICEBREAKER_SYSTEM = (
    "You are helping someone send their first message to a new travel companion. "
    "Write a single warm, friendly opening message (1-2 sentences, max 25 words). "
    "Reference a shared interest or the destination. Do not use generic greetings. "
    "Output ONLY the message text — no quotes, no explanation."
)


def _shared_interests(user_profile: UserProfile, match: CoTravellerMatch) -> list[str]:
    user_interests = set()
    if user_profile.persona_answers:
        pa = user_profile.persona_answers
        scored = [
            ("food", pa.food_interest), ("adventure", pa.adventure_interest),
            ("culture", pa.culture_interest), ("nature", pa.nature_interest),
            ("nightlife", pa.nightlife_interest),
        ]
        user_interests = {k for k, v in scored if v >= 3}
    match_interests = set(match.profile.interests)
    shared = user_interests & match_interests
    return list(shared) if shared else list(match_interests)[:3]


async def generate_topics(
    user_profile: UserProfile,
    match: CoTravellerMatch,
    itinerary: Itinerary,
) -> list[str]:
    """
    Generate 5 conversation starter topics for the chat screen.
    Routes to the SMALL model tier — fast and cheap.
    """
    shared = _shared_interests(user_profile, match)
    destination = itinerary.destination.city

    prompt = (
        f"Two travellers are going to {destination} together.\n"
        f"Shared interests: {', '.join(shared)}.\n"
        f"Match reasons: {'; '.join(match.match_reasons[:2])}.\n"
        f"Generate 5 short conversation starter topics for their chat."
    )

    raw = await route_request("chat_topics", prompt, _TOPICS_SYSTEM)

    # Parse JSON array — strip fences if present
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    try:
        topics = json.loads(cleaned)
        if isinstance(topics, str):
            topics = json.loads(topics)
        if isinstance(topics, list):
            return [str(t) for t in topics[:5]]
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: split by newlines if JSON parse fails
    lines = [ln.strip().lstrip("-•0123456789. ") for ln in raw.splitlines() if ln.strip()]
    return lines[:5]


async def generate_icebreaker(user_profile: UserProfile, match: CoTravellerMatch) -> str:
    """
    Generate a single warm opening message for the chat screen.
    Routes to the SMALL model tier.
    """
    shared = _shared_interests(user_profile, match)
    sender = user_profile.display_name
    receiver = match.profile.display_name

    prompt = (
        f"{sender} wants to say hi to {receiver}, their new travel companion.\n"
        f"Receiver is from {match.profile.location}, archetype: {match.profile.archetype}.\n"
        f"Shared interests: {', '.join(shared)}.\n"
        f"Write a warm first message from {sender} to {receiver}."
    )

    return (await route_request("icebreaker", prompt, _ICEBREAKER_SYSTEM)).strip()
