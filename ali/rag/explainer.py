import asyncio
from shared.schemas import Activity, Itinerary, ItineraryDay, UserProfile
from ali.rag.retriever import retrieve_activity_context
from ali.routing.engine import route_request

_EXPLAIN_SYSTEM = (
    "You are a travel expert writing personalised activity recommendations. "
    "Write a single sentence (max 25 words) explaining why this specific activity suits this traveller. "
    "Ground the explanation in the provided context. Be warm and specific, not generic."
)


def _build_explain_prompt(
    activity: Activity,
    context: list[str],
    user_profile: UserProfile,
) -> str:
    pa = user_profile.persona_answers
    interests = ""
    if pa:
        scored = sorted(
            [("food", pa.food_interest), ("adventure", pa.adventure_interest),
             ("culture", pa.culture_interest), ("nature", pa.nature_interest)],
            key=lambda x: -x[1],
        )
        interests = ", ".join(f"{k} ({v}/5)" for k, v in scored[:3])

    pace = user_profile.constraints.pace_preference.value if user_profile.constraints else "moderate"
    mood = user_profile.emotion_intent.value if user_profile.emotion_intent else "excited"
    context_block = "\n".join(f"- {c}" for c in context) if context else "No additional context available."

    return f"""Activity: {activity.name} ({activity.category}, {activity.duration_hours}h, ${activity.cost_usd:.0f})
Description: {activity.description}

Traveller profile: pace={pace}, mood={mood}, top interests: {interests}

Context snippets:
{context_block}

Write one sentence explaining why this activity suits this traveller."""


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
