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
- Only use activities from the provided list — do not invent new ones.
- Respect must_haves exactly — every item must appear at least once.
- Exclude anything in avoid_list entirely.
- Keep daily_cost_usd within the daily budget.
- Match the pace: relaxed = 2-3 activities/day, moderate = 3-4, fast = 4-5.
- Leave why_this as null — it will be populated separately.
"""

REFINEMENT_SYSTEM_PROMPT = """You are revising a trip itinerary based on user feedback and validation issues.
Keep what the user liked. Fix only what was flagged.

Output ONLY valid JSON matching the same Itinerary schema — no markdown fences, no extra text.

Rules:
- Preserve the itinerary_id and user_id exactly.
- If budget was exceeded: replace expensive activities with cheaper alternatives from the available list.
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
    trip_days = (c.end_date - c.start_date).days or 1
    daily_budget = round(c.budget_usd / trip_days, 2)

    persona = user_profile.compatibility_signals.get("top_interests", [])
    persona_str = ", ".join(persona) if persona else "general traveller"
    mood = user_profile.emotion_intent.value if user_profile.emotion_intent else "excited"

    interests = []
    if user_profile.persona_answers:
        pa = user_profile.persona_answers
        scored = [
            ("food", pa.food_interest),
            ("adventure", pa.adventure_interest),
            ("culture", pa.culture_interest),
            ("nature", pa.nature_interest),
            ("nightlife", pa.nightlife_interest),
        ]
        interests = [f"{k} ({v}/5)" for k, v in sorted(scored, key=lambda x: -x[1])]

    activity_list = "\n".join(
        f"- id:{a.activity_id} | {a.name} | {a.category} | ${a.cost_usd:.0f} | {a.duration_hours}h"
        f" | tags: {', '.join(a.tags)} | desc: {a.description}"
        for a in activities
    )

    return f"""Plan a {trip_days}-day trip to {destination.city}, {destination.country} for {c.group_size} person(s).

User ID: {user_profile.user_id}
Dates: {c.start_date} to {c.end_date}
Total budget: ${c.budget_usd:.0f} USD (${daily_budget:.0f}/day)
Pace: {c.pace_preference.value}
Must include: {", ".join(c.must_haves) if c.must_haves else "none"}
Avoid: {", ".join(c.avoid_list) if c.avoid_list else "none"}
Persona interests: {persona_str}
Interest scores: {", ".join(interests)}
Mood: {mood}

Available activities:
{activity_list}

Output the full itinerary as JSON."""


def build_refinement_prompt(
    itinerary: Itinerary,
    feedback: str,
    validation_result: ValidationResult,
) -> str:
    suggestions = "\n".join(f"- {s}" for s in validation_result.improvement_suggestions)
    issues_str = f"{validation_result.feedback}\n{suggestions}".strip() if validation_result.improvement_suggestions else validation_result.feedback

    return f"""Here is the current itinerary:
{itinerary.model_dump_json(indent=2)}

User feedback: "{feedback}"

Validation issues to fix:
{issues_str}

Revise the itinerary to address the feedback and fix all validation issues. Output the updated itinerary as JSON."""
