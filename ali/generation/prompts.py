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
- The available pool below mixes three kinds of records (tagged in `category` and `tags`): hotels, restaurants, and activities. Use them appropriately:
  • Pick ONE hotel and use it as the first item on day 1 ("Check in at <hotel>") and the last on the final day ("Check out").
  • Use restaurants for meal slots — lunch (~12-2pm) and dinner (~7-9pm), one per day.
  • Use activities for sightseeing/experiences in morning, afternoon, and evening slots.
- Prefer items from the pool over invented ones. When the pool is sparse for a category, you may invent plausible real venues for that destination.
- Respect must_haves exactly — every item must appear at least once across the trip.
- Exclude anything in avoid_list entirely.
- Keep daily_cost_usd within the daily budget.
- Match the pace: relaxed = 2-3 activities/day, moderate = 3-4, packed = 4-5 (meals and hotel check-in/out don't count toward this).
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

    style_value = c.who_travelling_with.value if (c and c.who_travelling_with) else "solo"
    group_hints = _group_planning_hints(style_value, group_size)

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

GROUP SHAPE: {style_value} (party of {group_size}).
{group_hints}

{activity_block}

Output the full itinerary as JSON."""


def _group_planning_hints(style: str, party_size: int) -> str:
    """Activity-shaping guidance per group type. The generator already
    knows the headcount; this tells it what KIND of trip a party of N
    in this style wants — single-table-for-N at dinner for a family,
    private rooms not dorms for a couple, splittable groups for
    friends, etc. Without this the LLM defaults to a generic
    solo-friendly trip regardless of group shape."""
    if style == "solo":
        return (
            "- Favour solo-friendly venues: counter seating, walking-distance "
            "stops, communal tables OK, no booth-for-two-with-no-bar.\n"
            "- Mix in 1-2 activities per day where meeting other travellers "
            "is plausible (walking tours, cooking classes, hostel-bar "
            "evenings) — don't force it, but don't engineer isolation.\n"
            "- No private-car transfers when one seat is wasted; default to "
            "trains / walking / metro."
        )
    if style == "couple":
        return (
            "- Every overnight is a private room (no shared dorms).\n"
            "- At least one slow shared activity per day: a long meal, a "
            "spa, a walk somewhere romantic at dusk. Avoid stacking "
            "high-stimulation activities back-to-back.\n"
            "- One restaurant per meal that takes a table for two; skip "
            "places with only counter seating unless explicitly atmospheric.\n"
            "- One activity per trip that's a shared first (an experience "
            "neither has had) — anchors the trip in memory."
        )
    if style == "family":
        # ASSUMPTION: kids are present in every family trip. We don't ask
        # for ages — plan for "mixed ages, probably with at least one
        # child under 12" as the default and let the user push back via
        # feedback if it's an all-adult family trip.
        return (
            f"- ASSUME CHILDREN ARE PRESENT in this party of {party_size}. "
            "Plan for mixed ages with at least one child under 12.\n"
            f"- All restaurants must seat the FULL party of {party_size} at "
            "ONE table AND have a kids-friendly menu (or at least mild, "
            "non-spicy options every age can eat). No fine-dining tasting "
            "menus, no bars, no adults-only or 21+ venues.\n"
            "- Pacing rules: walking blocks under 30 min between stops, "
            "dinner by 7pm, a mid-day break (nap window or hotel reset) "
            "every day. No 8pm museum openings, no 10pm walking tours.\n"
            "- At least one explicitly KID-FACING activity per day "
            "(playground, interactive museum, aquarium, zoo, scenic train "
            "ride, beach with calm water, hands-on workshop kids can join). "
            "Adults' interests can be threaded in around these anchors, "
            "not the other way around.\n"
            "- Avoid: clubs / bars / late-night anything; long single-"
            "sitting fine dining; activities with minimum-age rules the "
            "kids would fail (wine tastings, certain hikes, certain water "
            "sports); cities-as-walking-tour-marathon (kids tap out).\n"
            "- Lodging: apartment or multi-bedroom hotel suite, not "
            "single rooms. Kitchen access matters (kid breakfasts, late-"
            "night snacks). A pool or outdoor space at the lodging is a "
            "strong plus.\n"
            "- Logistics: factor in stroller-friendly routes when the "
            "destination has cobblestone / stairs reputation; flag if a "
            "scheduled activity requires car seats / extra transit time."
        )
    if style == "friends":
        return (
            f"- Default to shared experiences for the full group of "
            f"{party_size} (group reservations, group classes, single-table "
            f"meals). Restaurant bookings should take {party_size} at one "
            "table.\n"
            "- At least one activity per day where the group can SPLIT and "
            "rejoin (museum with multiple wings, shopping district, beach "
            "day with optional water sports). Honours that friend groups "
            "want time apart inside a shared trip.\n"
            "- Nightlife is on the table unless explicitly avoided — "
            "include 1-2 evening anchor venues across the trip.\n"
            f"- Lodging prefers apartment / villa over {party_size} separate "
            "hotel rooms; shared common space is the point."
        )
    # Unknown / None → no extra hints; the generic prompt is fine.
    return ""


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
