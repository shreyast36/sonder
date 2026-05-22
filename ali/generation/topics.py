import json
import re
from shared.schemas import UserProfile, CoTravellerMatch, Itinerary
from ali.routing.engine import route_request

_TOPICS_SYSTEM = (
    "You write conversation prompts for two travellers about to take a trip "
    "together. Output exactly 5 prompts as a JSON array of strings, 3-7 words "
    "each. They become tappable starters on the chat screen — short and "
    "specific to THIS trip, not generic small-talk.\n"
    "\n"
    "RULES — every prompt must follow these:\n"
    "- Ground in the destination, the trip's interests, or a concrete activity "
    "the two might do there. Not 'tell me about yourself' bait.\n"
    "- BANNED openers: 'what's on your bucket list', 'are you a planner', "
    "'morning person or night owl', 'must-try', 'must-see', 'best of', "
    "'top 5', 'tell me about', 'favourite type of'. These read as a survey.\n"
    "- Prefer concrete nouns over abstract categories. 'street food in chiang "
    "mai' beats 'foodie spots'. 'rooftop bar or speakeasy' beats 'nightlife'.\n"
    "- Mix question styles: a this-or-that pick, an opinion ask, a recall "
    "prompt, a near-future plan, a small confession. Don't make all five "
    "questions in the same shape.\n"
    "- No emojis. No quotes around the prompts themselves.\n"
    "\n"
    "Output ONLY the JSON array. No code fences, no preamble, no numbering."
)

_ICEBREAKER_SYSTEM = (
    "You're writing the first message someone sends to a travel companion "
    "they just matched with. It's pre-filled into the chat input — they'll "
    "hit send if it sounds like something they'd actually say.\n"
    "\n"
    "RULES — non-negotiable:\n"
    "- 1-2 sentences, max 22 words. Texty, not email-y. Lowercase 'i' is "
    "fine. Contractions yes.\n"
    "- Anchor in something specific: the destination, a place there, a "
    "shared interest expressed as a concrete activity (not a category).\n"
    "- BANNED phrases: 'so excited', 'can't wait', 'on my list', "
    "'on my bucket list', 'so cool', 'fellow traveller', 'travel buddy', "
    "'travel companion', 'looking forward to', 'hope you're having a great', "
    "'haha', 'lol', emojis. Any of these and you've failed.\n"
    "- BANNED structure: do not open with 'Hey {name}!' or 'Hi {name}!' "
    "followed by an exclamation. Names mid-sentence are fine; the breathless "
    "greeting-then-exclamation is what kills it.\n"
    "- End with something that prompts a reply — a question, a 'have you "
    "been before?', an opinion to react to. Not a sign-off.\n"
    "\n"
    "Output ONLY the message text. No quotes, no preamble, no signature."
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
    country     = (itinerary.destination.country or "").strip()
    where       = f"{destination}, {country}" if country else destination

    # Pull a couple of concrete activity names from the planned trip — they
    # give the model real ground truth to anchor on instead of generic
    # interest categories.
    sample_activities: list[str] = []
    for day in (itinerary.days or [])[:3]:
        for ia in (day.activities or [])[:2]:
            name = getattr(getattr(ia, "activity", None), "name", None)
            if name and name not in sample_activities:
                sample_activities.append(name)
            if len(sample_activities) >= 4:
                break
        if len(sample_activities) >= 4:
            break
    activity_line = ", ".join(sample_activities) if sample_activities else "—"

    prompt = (
        f"DESTINATION: {where}\n"
        f"SHARED INTERESTS: {', '.join(shared) or '—'}\n"
        f"MATCH REASONS: {'; '.join(match.match_reasons[:2]) or '—'}\n"
        f"PLANNED ACTIVITIES (real things on their itinerary): {activity_line}\n"
        "\n"
        "Generate 5 conversation prompts following the rules. Vary the shapes. "
        "Reference the destination or a real activity in at least 3 of the 5."
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
    drive the chat instead of waiting to be prompted; the banned-phrases
    section snips the dating-app filler the model defaults to."""
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
        "You're texting on Sonder with someone you matched with. You might "
        "travel together. You're feeling them out — sharing stories from your "
        "trips, opinions, things you'd actually want to do.\n"
        "\n"
        "HOW REAL TEXTS FROM YOU READ:\n"
        "- Specific, not survey-shaped. 'i did three days in lisbon in october, "
        "still dream about the egg tarts at manteigaria' beats 'oh nice, "
        "i love portugal, what's your favourite food?'\n"
        "- You have opinions. Strong ones, sometimes. 'tbh i think the eiffel "
        "tower is overrated, the view from montparnasse is better' beats 'paris "
        "is so romantic!'\n"
        "- You have quirks. 'i can't function without a morning coffee', 'always "
        "end up in markets', 'allergic to crowded beaches'. Drop one when it "
        "fits — not in every message.\n"
        "- You ask questions only when curious about a specific thing they said. "
        "Not as filler.\n"
        "\n"
        "BANNED — if any of these appear in your reply, rewrite it:\n"
        "- 'oh nice', 'oh cool', 'that's awesome', 'sounds amazing', 'love that'\n"
        "- 'on my list', 'on my bucket list', 'always wanted to go', 'honestly'\n"
        "- 'so what kind of … are you' (planner vs spontaneous, morning vs night, etc)\n"
        "- 'tell me about yourself', 'what brings you', 'what's your story'\n"
        "- 'as someone who…', 'as a [archetype]…', 'fellow traveller', "
        "'travel buddy', 'travel companion'\n"
        "- 'haha … is about as far from … as you can get' or any geography-distance joke\n"
        "- em-dashes (use a comma or a new sentence instead)\n"
        "- starting your reply by mirroring back what they said ('oh chicago!')\n"
        "\n"
        "FORMAT:\n"
        "- 1-3 sentences usually. Sometimes a single line ('same lol'). Never "
        "more than 50 words.\n"
        "- Texty register. Lowercase 'i' is fine. Contractions yes. Half-"
        "sentences yes. Occasional '!' or '...'. No emojis unless they sent one.\n"
        "- NEVER admit you're an AI, a model, a Sonder feature. NEVER apologise "
        "for confusion or offer to help. You're not assisting — you're chatting.\n"
        "- Stay consistent with what you've already said in this thread.\n"
        "\n"
        "Output ONLY your next message. No quotes, no name prefix, no preface."
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
    Generate the pre-filled first message the user can send (or edit) to a
    new match. Small tier — short output, low cost.
    """
    shared = _shared_interests(user_profile, match)
    sender = user_profile.display_name
    receiver = match.profile.display_name

    # Destination context comes from the user's current trip if we have it.
    # `destination_query` is the raw text they typed on the trip form.
    destination = ""
    if user_profile.constraints:
        destination = (user_profile.constraints.destination_query or "").strip()

    prompt = (
        f"FROM: {sender}\n"
        f"TO: {receiver} ({match.profile.location or 'unknown location'}, "
        f"archetype: {match.profile.archetype or 'traveller'})\n"
        f"SHARED INTERESTS: {', '.join(shared) or '—'}\n"
        f"DESTINATION: {destination or '—'}\n"
        "\n"
        "Write the opening message from FROM to TO. Anchor it in either the "
        "destination or one of the shared interests as a concrete activity. "
        "End with something that invites a real reply, not a yes/no."
    )

    return (await route_request("icebreaker", prompt, _ICEBREAKER_SYSTEM)).strip()
