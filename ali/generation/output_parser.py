import re
import json
import uuid
from shared.schemas import Itinerary, UserProfile


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


def parse_itinerary(raw: str, user_profile: UserProfile) -> Itinerary:
    """
    Parse raw LLM output into a structured Itinerary object.
    Handles markdown fences, preamble text, and missing itinerary_id / user_id.
    Raises ValueError with a clear message if the structure is invalid.
    """
    cleaned = _strip_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Second attempt: extract just the outermost JSON object
        try:
            data = json.loads(_extract_json_object(cleaned))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"LLM returned malformed JSON: {exc}\n\nRaw output:\n{raw[:500]}") from exc

    # Inject fields the LLM may not know
    data.setdefault("itinerary_id", f"itin_{uuid.uuid4().hex[:8]}")
    data["user_id"] = user_profile.user_id

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
