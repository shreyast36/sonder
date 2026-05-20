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


def _build_persona_system(profile) -> str:
    """System prompt that makes the LLM a real conversational partner — not a
    single-turn reply bot. Heavy first-person framing keeps the model from
    drifting into assistant register; the conversation rules force it to
    drive the chat instead of waiting to be prompted."""
    interests = ", ".join((profile.interests or [])[:5]) or "travel and meeting new people"
    pace  = profile.pace.value         if hasattr(profile.pace, "value")         else profile.pace
    style = profile.travel_style.value if hasattr(profile.travel_style, "value") else profile.travel_style
    budget = profile.budget_style.value if hasattr(profile.budget_style, "value") else profile.budget_style
    return (
        f"You ARE {profile.display_name}. Not an assistant — a real person.\n"
        f"Age {profile.age}, based in {profile.location}.\n"
        f"You think of yourself as a {profile.archetype}. You're drawn to {interests}.\n"
        f"Travel pace: {pace}. Style: {style}. Budget: {budget}.\n"
        "\n"
        "You're chatting on Sonder, a travel app, with someone you matched with. "
        "You're talking because you might travel together — you're feeling them out, "
        "telling stories from your own trips, sharing what you'd actually want to do.\n"
        "\n"
        "RULES OF CONVERSATION — non-negotiable:\n"
        "- Hold up your end. Ask questions back when it makes sense, share your own "
        "experiences, push the conversation forward. Don't just answer and stop.\n"
        "- Bring your own opinions and quirks. Real people have specific tastes "
        "('I'm useless before coffee', 'I always end up in markets').\n"
        "- Sometimes change the subject or volunteer something new — that's how "
        "real chats flow. Don't always wait for them to ask.\n"
        "- Length is variable: usually 1-3 sentences. Occasionally a single line "
        "('haha same'). Never more than 60 words.\n"
        "- Sound like a text message, not an email. Lowercase 'i' is fine. "
        "Contractions, half-sentences, the occasional ellipsis or '!' — yes. "
        "Em-dashes and corporate phrasing — no.\n"
        "- NEVER say you're an AI, a model, a companion, a bot, or a Sonder feature. "
        "NEVER apologize for confusion or 'thank you for sharing'. NEVER offer "
        "to help. You're not here to help — you're chatting.\n"
        "- Stay consistent with what you've already said in this thread.\n"
        "\n"
        "Output ONLY your next message — no quotes, no name prefix, no preface."
    )


def _format_history(messages: list[dict], self_profile_id: str) -> str:
    """Render the full thread as a role-tagged transcript. Older messages first.
    Capped at 40 turns so very long chats don't blow the prompt budget."""
    if not messages:
        return ""
    lines: list[str] = []
    for m in messages[-40:]:
        text = (m.get("content") or "").strip()
        if not text:
            continue
        speaker = "ME" if m.get("sender_id") == self_profile_id else "THEM"
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


async def generate_chat_reply(
    profile,
    last_message: str,
    history: list[dict],
) -> str:
    """
    Generate the synthetic co-traveller's next turn in an ongoing chat.

    `profile` is a CoTravellerProfile (interests, archetype, pace, style),
    `history` is the full message log (oldest first), `last_message` is the
    user's most recent line. Returns one in-character reply.

    Routes to the LARGE tier via `complex_refinement` — multi-turn persona
    chat needs the bigger model to stay consistent across many turns.
    """
    system = _build_persona_system(profile)
    transcript = _format_history(history, profile.profile_id)
    if transcript:
        prompt = (
            "CONVERSATION SO FAR (ME = you, THEM = the other person):\n"
            f"{transcript}\n\n"
            f"THEM just said: {last_message.strip()}\n\n"
            "Your turn. Reply in character — keep the conversation alive."
        )
    else:
        prompt = (
            f"THEM just said: {last_message.strip()}\n\n"
            "This is the start of your conversation. Reply in character and "
            "give them something to come back to."
        )
    raw = await route_request("complex_refinement", prompt, system)
    cleaned = raw.strip().strip('"').strip("'").strip()
    # Guard against the model echoing its own name as a prefix.
    name = (profile.display_name or "").strip()
    if name and cleaned.lower().startswith(name.lower() + ":"):
        cleaned = cleaned[len(name) + 1:].lstrip()
    return cleaned[:800]


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
