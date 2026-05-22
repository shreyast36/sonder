import asyncio
from shared.schemas import Activity, Itinerary, ItineraryDay, UserProfile
from ali.rag.retriever import retrieve_activity_context
from ali.routing.engine import route_request

_EXPLAIN_SYSTEM = (
    "You write the one-line 'why this?' caption that appears under each "
    "activity on a travel itinerary. The traveller will read these all in "
    "a row — they have to feel earned, not auto-generated.\n"
    "\n"
    "RULES — non-negotiable:\n"
    "- ONE sentence. Max 22 words. No semicolons.\n"
    "- Anchor in something specific about THIS activity — a detail from its "
    "description or context (the dish, the neighbourhood, the time of day, "
    "the view, the medium). Not 'this matches your interests'.\n"
    "- Reference the user's persona only if it adds a real bridge — "
    "'because you said the small thing was X' is fine. 'matches your love of "
    "food and culture' is not.\n"
    "- BANNED phrases: 'perfect for', 'matches your love of', 'your interest "
    "in', 'as someone who', 'aligns with', 'right up your alley', 'this is "
    "your kind of', 'must-do', 'must-try', 'a great way to'. Any of these "
    "and you've failed.\n"
    "- Editorial register, not marketing. Concrete nouns over adjectives. "
    "No exclamation marks. No emojis.\n"
    "\n"
    "Output ONLY the sentence. No quotes, no preface, no period if it ends "
    "on a noun phrase (period is fine if it ends on a full clause)."
)


def _build_explain_prompt(
    activity: Activity,
    context: list[str],
    user_profile: UserProfile,
) -> str:
    c = user_profile.constraints
    pace = c.pace.value if (c and c.pace) else "moderate"

    # Persona signals come from the LLM-inferred dimensions stored on compatibility_signals.
    cs = user_profile.compatibility_signals or {}
    top_interests = cs.get("top_interests") or []
    top_push      = cs.get("top_push") or []
    interest_str  = ", ".join(top_interests) if top_interests else "—"
    push_str      = ", ".join(top_push) if top_push else "—"

    # Emotional signature is private framing only — never surfaces as a label
    # in the user-visible sentence. Used by the LLM to choose which moments
    # to highlight and what pacing to write at.
    emotional_signature = (cs.get("emotional_signature") or "").strip()
    emotional_tone      = (cs.get("emotional_tone") or "").strip()

    small_thing = ""
    if user_profile.persona_answers and user_profile.persona_answers.small_thing:
        small_thing = user_profile.persona_answers.small_thing.strip()

    mood = user_profile.emotion_intent.value if user_profile.emotion_intent else "excited"
    context_block = "\n".join(f"- {c}" for c in context) if context else "No additional context available."

    framing_block = ""
    if emotional_signature or emotional_tone:
        framing_block = (
            "\nPRIVATE EMOTIONAL FRAMING (never expose these words):\n"
            f"- signature: {emotional_signature or '—'}\n"
            f"- tone: {emotional_tone or '—'}\n"
            "Let this shape which moment of the activity you highlight and the\n"
            "cadence of the sentence — not its vocabulary.\n"
        )

    return f"""ACTIVITY: {activity.name}
TYPE: {activity.category} · {activity.duration_hours}h · ~${activity.cost_usd:.0f}
DESCRIPTION: {activity.description}

CONTEXT SNIPPETS (use these for specifics — places, dishes, vibes):
{context_block}

TRAVELLER:
- Pace: {pace}
- Mood: {mood}
- Drawn to (PULL): {interest_str}
- Travelling because (PUSH): {push_str}
- Something they said: "{small_thing or "—"}"
{framing_block}
Write one sentence under 22 words. Lead with a specific detail of THIS
activity (from description or context), not with the traveller's profile.
Only mention persona if it adds a non-generic bridge. Follow all BANNED-
phrase rules from the system. NEVER use the signature key as a word."""


async def explain_activity(
    activity: Activity,
    context: list[str],
    user_profile: UserProfile,
) -> str:
    """Generate the 'Why this?' explanation for a single activity."""
    prompt = _build_explain_prompt(activity, context, user_profile)
    return await route_request("rag_explanation", prompt, _EXPLAIN_SYSTEM)


async def explain_day(day: ItineraryDay, user_profile: UserProfile) -> ItineraryDay:
    """
    Populate why_this for every activity in a single ItineraryDay concurrently.
    Returns a new ItineraryDay with all why_this fields populated.
    """
    async def _explain_one(itinerary_activity):
        context = await retrieve_activity_context(itinerary_activity.activity)
        why = await explain_activity(itinerary_activity.activity, context, user_profile)
        return itinerary_activity.model_copy(update={"why_this": why})

    explained = await asyncio.gather(*[_explain_one(ia) for ia in day.activities])
    return day.model_copy(update={"activities": list(explained)})


async def explain_itinerary(itinerary: Itinerary, user_profile: UserProfile) -> Itinerary:
    """
    Populate why_this for every activity in the full itinerary, all days concurrently.
    Use this after a full itinerary is assembled (e.g. after refinement).
    For the initial generation pipeline, use explain_day() per day instead.
    """
    explained_days = await asyncio.gather(
        *[explain_day(day, user_profile) for day in itinerary.days]
    )
    return itinerary.model_copy(update={"days": list(explained_days)})
