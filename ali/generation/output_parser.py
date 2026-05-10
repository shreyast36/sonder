import re
import json
import uuid
from shared.schemas import Itinerary, UserProfile, Destination, Activity
from typing import Optional


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences LLMs often wrap JSON in."""
    raw = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if match:
        return match.group(1).strip()
    return raw


def _extract_json_object(raw: str) -> str:
    """Find the outermost {...} block in raw, in case the LLM added preamble text."""
    start = raw.find("{")
    if start == -1:
        raise ValueError("No JSON object found in LLM output")
    depth = 0
    in_string = False
    escape_next = False
    for i in range(start, len(raw)):
        c = raw[i]
        if escape_next:
            escape_next = False
            continue
        if c == "\\" and in_string:
            escape_next = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    raise ValueError("Unterminated JSON object in LLM output")


def _patch_activity(act_data: dict, known: dict[str, Activity]) -> dict:
    """Fill in required Activity fields the LLM may omit, matching by name."""
    name = act_data.get("name", "")
    source = known.get(name)
    if source:
        act_data.setdefault("activity_id", source.activity_id)
        act_data.setdefault("description", source.description)
        act_data.setdefault("category", source.category)
        act_data.setdefault("cost_usd", source.cost_usd)
        act_data.setdefault("duration_hours", source.duration_hours)
        act_data.setdefault("tags", source.tags)
    else:
        act_data.setdefault("activity_id", f"act_{uuid.uuid4().hex[:6]}")
        act_data.setdefault("description", "")
    return act_data


def _patch_destination(dest_data: dict, known: Optional[Destination]) -> dict:
    """Fill in required Destination fields using the known destination object."""
    if known:
        dest_data.setdefault("destination_id", known.destination_id)
        dest_data.setdefault("city", known.city)
        dest_data.setdefault("country", known.country)
        dest_data.setdefault("avg_daily_cost_usd", known.avg_daily_cost_usd)
        dest_data.setdefault("tags", known.tags)
        dest_data.setdefault("description", known.description)
    else:
        dest_data.setdefault("destination_id", f"dest_{uuid.uuid4().hex[:6]}")
        dest_data.setdefault("city", dest_data.get("name", "Unknown"))
        dest_data.setdefault("country", "")
        dest_data.setdefault("avg_daily_cost_usd", 0.0)
        dest_data.setdefault("tags", [])
        dest_data.setdefault("description", "")
    return dest_data


def parse_itinerary(
    raw: str,
    user_profile: UserProfile,
    destination: Optional[Destination] = None,
    activities: Optional[list[Activity]] = None,
) -> Itinerary:
    """
    Parse raw LLM output into a structured Itinerary object.
    Pass destination and activities to fill in any fields the LLM omitted.
    """
    cleaned = _strip_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            data = json.loads(_extract_json_object(cleaned))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"LLM returned malformed JSON: {exc}\n\nRaw output:\n{raw[:500]}") from exc

    # Always generate itinerary_id server-side — never trust the LLM for this.
    # LLM-generated IDs are not cryptographically unique and could collide with
    # another user's document, causing a silent Firestore overwrite.
    data["itinerary_id"] = f"itin_{uuid.uuid4().hex[:8]}"
    data["user_id"] = user_profile.user_id

    # Patch destination
    if "destination" in data and isinstance(data["destination"], dict):
        data["destination"] = _patch_destination(data["destination"], destination)
    elif destination:
        data["destination"] = destination.model_dump()

    # Patch activities inside days
    known_by_name = {a.name: a for a in (activities or [])}
    for day in data.get("days", []):
        for ia in day.get("activities", []):
            if "activity" in ia and isinstance(ia["activity"], dict):
                ia["activity"] = _patch_activity(ia["activity"], known_by_name)

    try:
        return Itinerary.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Itinerary failed schema validation: {exc}") from exc


def validate_structure(itinerary: Itinerary) -> bool:
    """
    Quick structural sanity check before passing to Mushahid's validator.
    Returns True only if all checks pass.
    """
    if not itinerary.days:
        return False
    if any(not day.activities for day in itinerary.days):
        return False
    if itinerary.total_budget_usd <= 0:
        return False
    return True
