"""
Feedback classifier for the itinerary revision loop.

Routes a user's free-text feedback to either a SMALL targeted edit
path (activity swap, timing change, restaurant replacement,
neighborhood adjustment, pacing tweak) or the LARGE planning path
(destination change, trip restructure, major budget shift, complete
vibe change, multi-day rewrites).

The two paths use different LLM tiers so cheap edits stay cheap and
deep rewrites get the head-room they need:
  - SMALL → ali.routing 'quick_edit' task
  - LARGE → ali.routing 'complex_refinement' task

Classification is a small LLM call returning a structured JSON
verdict. Falls back to LARGE on parse failure — better to over-spend
on a single revision than ship a bad small-edit.

The classifier also extracts dedupe hints (target_day_numbers,
target_categories) the revision pipeline reads when assembling the
prompt — so 'day 3 dinner is too expensive' touches only day 3's
dinner activity, not the whole itinerary.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from ali.routing.engine import route_request

logger = logging.getLogger(__name__)


_SYSTEM = """\
You classify itinerary revision feedback on a travel app. The user
just looked at a generated trip plan and wrote feedback. You decide:

1. SCOPE: is this a small targeted edit, or a large structural rewrite?
2. TARGETS: which days / activity types does the feedback reference?
3. KEEP: which parts of the trip should be EXPLICITLY preserved?

SMALL scope examples:
- "day 2 dinner is too expensive"
- "swap the museum on day 1 for something more chill"
- "drop the early-morning hike"
- "less walking between activities"
- "the brunch place looks generic"
- "move the wine tasting later in the day"

LARGE scope examples:
- "different destination, maybe Lisbon instead"
- "make this a family trip instead of solo"
- "cut the trip to 5 days"
- "the whole vibe is wrong — too touristy"
- "rebuild everything around food"
- "we'd rather backpack than stay in hotels"

Heuristics:
- A specific day number, activity name, or single category mention → SMALL.
- A "the whole trip" / "everything" / "rebuild" / "different X" → LARGE.
- A vague complaint with no targets ("doesn't feel like me") → LARGE
  (the revision needs to re-examine the persona signal, not nudge one
  activity).

Output ONLY valid JSON, no preamble, no markdown:

{
  "scope": "small" | "large",
  "summary": "one-line restatement of what the user wants changed",
  "target_day_numbers": [<int>, ...],
  "target_categories": ["food" | "lodging" | "activity" | "pacing" | "budget" | "transport" | "vibe", ...],
  "preserve": ["one-line note about what NOT to change", ...]
}

Fields can be empty lists when not applicable. Day numbers are
integers if mentioned, else []."""


def _parse_json_object(raw: str) -> dict | None:
    """Lenient JSON parser — strips fences + trailing commas. Returns
    None on hard failure so the caller can fall back."""
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```\s*$", "", raw).strip()
    try:
        out = json.loads(raw)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    end = -1
    for i in range(start, len(raw)):
        c = raw[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
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
                end = i
                break
    if end == -1:
        return None
    candidate = re.sub(r",(\s*[}\]])", r"\1", raw[start:end + 1])
    try:
        out = json.loads(candidate)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        return None


async def classify_revision_feedback(feedback: str, itinerary_summary: str = "") -> dict[str, Any]:
    """Run the classifier and normalise the verdict. Always returns
    a dict with all expected keys so the caller can read them
    unconditionally. Defaults to 'large' on any uncertainty."""
    user_prompt = (
        f"USER FEEDBACK:\n{feedback}\n\n"
        + (f"CURRENT TRIP CONTEXT:\n{itinerary_summary}\n\n" if itinerary_summary else "")
        + "Return the JSON verdict."
    )
    try:
        raw = await route_request("quick_edit", user_prompt, _SYSTEM)
    except Exception as e:
        logger.warning("classify_revision_feedback: LLM call failed: %s", e)
        return _default_verdict(feedback, scope="large")

    parsed = _parse_json_object(raw)
    if not parsed:
        logger.warning("classify_revision_feedback: JSON parse failed, defaulting to large")
        return _default_verdict(feedback, scope="large")

    scope = (parsed.get("scope") or "").strip().lower()
    if scope not in ("small", "large"):
        scope = "large"

    days_raw = parsed.get("target_day_numbers") or []
    target_days: list[int] = []
    for d in days_raw if isinstance(days_raw, list) else []:
        try:
            target_days.append(int(d))
        except (TypeError, ValueError):
            continue

    cats_raw = parsed.get("target_categories") or []
    target_cats = [str(c).strip().lower() for c in cats_raw if str(c).strip()] if isinstance(cats_raw, list) else []

    preserve_raw = parsed.get("preserve") or []
    preserve = [str(p).strip() for p in preserve_raw if str(p).strip()] if isinstance(preserve_raw, list) else []

    summary = str(parsed.get("summary") or feedback)[:240].strip()

    return {
        "scope":               scope,
        "summary":             summary,
        "target_day_numbers":  target_days,
        "target_categories":   target_cats,
        "preserve":            preserve,
    }


def _default_verdict(feedback: str, *, scope: str = "large") -> dict[str, Any]:
    return {
        "scope":               scope,
        "summary":             (feedback or "")[:240].strip(),
        "target_day_numbers":  [],
        "target_categories":   [],
        "preserve":            [],
    }
