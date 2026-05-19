from shared.schemas import UserProfile, Destination, Activity, Itinerary, ValidationResult

ITINERARY_SYSTEM_PROMPT = """You are an expert travel planner. Create personalised, day-by-day trip itineraries.

Output ONLY valid JSON matching this exact schema — no markdown fences, no extra text:
{
  "itinerary_id": "<generate a short unique id e.g. itin_abc123>",
  "user_id": "<copy from input>",
  "destination": { <full Destination object> },
  "days": [
    {
      "day_number": 1,
      "trip_date": "YYYY-MM-DD",
      "theme": "<short evocative theme for the day>",
      "daily_cost_usd": <float>,
      "activities": [
        {
          "time": "9:00 AM",
          "why_this": null,
          "activity": { <full Activity object> }
        }
      ]
    }
  ],
  "total_budget_usd": <float>,
  "notes": [],
  "co_traveller_ids": []
}

Rules:
- If a list of available activities is provided, prefer those. When the list is sparse or empty, you may invent plausible local activities that fit the destination — use real venues and accurate descriptions.
- Respect must_haves exactly — every item must appear at least once across the trip.
- Exclude anything in avoid_list entirely.
- Keep daily_cost_usd within the daily budget.
- Match the pace: relaxed = 2-3 activities/day, moderate = 3-4, packed = 4-5.
- Each Activity object needs name, category, cost_usd (float), duration_hours (float), tags (list of strings), and description.
- KEEP OUTPUT TIGHT: description max 100 characters per activity; tags max 3 items; theme max 5 words. activity_id can be omitted; the parser fills it in.
- Leave why_this as null — it will be populated by a separate explainer pass.
"""

REFINEMENT_SYSTEM_PROMPT = """You are revising a trip itinerary based on user feedback and validation issues.
Keep what the user liked. Fix only what was flagged.

Output ONLY valid JSON matching the same Itinerary schema — no markdown fences, no extra text.

Rules:
- Preserve the itinerary_id and user_id exactly.
- If budget was exceeded: replace expensive activities with cheaper alternatives.
- If pace was wrong: add or remove activities per day to match the target pace.
- If must_haves are missing: insert them, displacing lower-priority activities if needed.
- If avoid_list items appear: remove them and fill the slot with a suitable alternative.
"""


def build_itinerary_prompt(
    user_profile: UserProfile,
    destination: Destination,
    activities: list[Activity],
) -> str:
    c = user_profile.constraints

    trip_days = 1
    if c and c.start_date and c.end_date:
        trip_days = max((c.end_date - c.start_date).days, 1)

    budget_usd   = (c.budget_usd if c else 0) or 0
    daily_budget = round(budget_usd / trip_days, 2) if trip_days else 0
    pace         = c.pace.value if (c and c.pace) else "moderate"
    must_haves   = (c.must_haves if c else []) or []
    avoid_list   = (c.avoid_list if c else []) or []
    group_size   = c.group_size if c else 1
    start_date   = c.start_date if c else None
    end_date     = c.end_date if c else None

    # Persona signals come from the LLM-inferred top dimensions stored on the profile.
    cs = user_profile.compatibility_signals or {}
    top_push      = cs.get("top_push") or []
    top_interests = cs.get("top_interests") or []
    push_str      = ", ".join(top_push) if top_push else "—"
    interest_str  = ", ".join(top_interests) if top_interests else "—"

    # The free-text persona anchor the user wrote.
    small_thing = ""
    if user_profile.persona_answers and user_profile.persona_answers.small_thing:
        small_thing = user_profile.persona_answers.small_thing.strip()

    mood = user_profile.emotion_intent.value if user_profile.emotion_intent else "—"

    if activities:
        activity_list = "\n".join(
            f"- id:{a.activity_id} | {a.name} | {a.category} | ${a.cost_usd:.0f} | {a.duration_hours}h"
            f" | tags: {', '.join(a.tags)} | desc: {a.description}"
            for a in activities
        )
        activity_block = f"Available activities (prefer these):\n{activity_list}"
    else:
        activity_block = (
            "No pre-fetched activities. Invent plausible, real-feeling activities "
            f"for {destination.city}, {destination.country}. Use real venues where you can."
        )

    return f"""Plan a {trip_days}-day trip to {destination.city}, {destination.country} for {group_size} person(s).

User ID: {user_profile.user_id}
Dates: {start_date} to {end_date}
Total budget: ${budget_usd:.0f} USD (${daily_budget:.0f}/day)
Pace: {pace}
Must include: {", ".join(must_haves) if must_haves else "none"}
Avoid: {", ".join(avoid_list) if avoid_list else "none"}
Push motivations: {push_str}
Pull interests: {interest_str}
Mood: {mood}
Something they said: {small_thing or "—"}

{activity_block}

Output the full itinerary as JSON."""


def build_refinement_prompt(
    itinerary: Itinerary,
    feedback: str,
    validation_result: ValidationResult,
) -> str:
    suggestions = "\n".join(f"- {s}" for s in (validation_result.improvement_suggestions or []))
    issues_str = (
        f"{validation_result.feedback}\n{suggestions}".strip()
        if validation_result.improvement_suggestions
        else validation_result.feedback
    )

    return f"""Here is the current itinerary:
{itinerary.model_dump_json(indent=2)}

User feedback: "{feedback}"

Validation issues to fix:
{issues_str}

Revise the itinerary to address the feedback and fix all validation issues. Output the updated itinerary as JSON."""
