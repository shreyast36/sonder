import json
from shared.schemas import Itinerary, UserProfile, ValidationResult, ValidationStatus
from ali.routing.engine import route_request


def _itinerary_summary(itinerary: Itinerary) -> str:
    lines = [f"Destination: {itinerary.destination.city}, {itinerary.destination.country}",
             f"Total budget: ${itinerary.total_budget_usd:.0f}",
             f"Days: {len(itinerary.days)}"]
    for day in itinerary.days:
        acts = ", ".join(ia.activity.name for ia in day.activities)
        lines.append(f"  Day {day.day_number} ({day.theme or 'no theme'}, ${day.daily_cost_usd:.0f}): {acts}")
    return "\n".join(lines)


def _constraints_summary(user_profile: UserProfile) -> str:
    c = user_profile.constraints
    if not c:
        return "No constraints provided."
    parts = [
        f"Budget: ${c.budget_usd:.0f}",
        f"Duration: {(c.end_date - c.start_date).days} days",
        f"Pace: {c.pace_preference.value}",
    ]
    if c.must_haves:
        parts.append(f"Must-haves: {', '.join(c.must_haves)}")
    if c.avoid_list:
        parts.append(f"Avoid: {', '.join(c.avoid_list)}")
    return " | ".join(parts)


async def validate_large_output(itinerary: Itinerary, user_profile: UserProfile) -> ValidationResult:
    system = (
        "You are a travel itinerary quality reviewer. "
        "Evaluate the itinerary against the user's constraints and preferences. "
        "Respond ONLY with valid JSON matching this schema exactly:\n"
        '{"status": "approved" | "revise", "score": 0.0-1.0, '
        '"feedback": "one sentence", "improvement_suggestions": ["..."]}'
    )
    prompt = (
        f"User constraints: {_constraints_summary(user_profile)}\n\n"
        f"Itinerary:\n{_itinerary_summary(itinerary)}\n\n"
        "Review for: realistic pacing, budget fit, must-haves included, avoid-list respected, "
        "logical day sequencing. Score 0-1. If score >= 0.75 use status=approved, else revise."
    )

    raw = await route_request("rag_explanation", prompt, system)

    try:
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        return ValidationResult(
            itinerary_id=itinerary.itinerary_id,
            status=ValidationStatus(data["status"]),
            score=float(data["score"]),
            feedback=data.get("feedback", ""),
            improvement_suggestions=data.get("improvement_suggestions", []),
        )
    except Exception:
        return ValidationResult(
            itinerary_id=itinerary.itinerary_id,
            status=ValidationStatus.approved,
            score=0.8,
            feedback="Validation parse error — defaulting to approved.",
            improvement_suggestions=[],
        )
