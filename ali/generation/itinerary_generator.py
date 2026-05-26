import json
import logging
from typing import AsyncIterator
from shared.schemas import UserProfile, Destination, Activity, ItineraryDay, Itinerary, ValidationResult
from ali.routing.engine import stream_request
from ali.generation.prompts import (
    ITINERARY_SYSTEM_PROMPT,
    REFINEMENT_SYSTEM_PROMPT,
    build_itinerary_prompt,
    build_refinement_prompt,
    build_targeted_day_refinement_prompt,
)
from ali.generation.output_parser import _patch_activity, parse_itinerary

logger = logging.getLogger(__name__)


def _patch_day_in_place(day_data: dict, activities: list[Activity]) -> dict:
    """Fill in activity fields the LLM may have omitted so per-day validation
    succeeds. Mirrors what parse_itinerary does on a full itinerary."""
    known = {a.name: a for a in (activities or [])}
    for ia in day_data.get("activities", []) or []:
        if isinstance(ia, dict) and isinstance(ia.get("activity"), dict):
            ia["activity"] = _patch_activity(ia["activity"], known)
    return day_data


async def generate_itinerary(
    user_profile: UserProfile,
    destination: Destination,
    activities: list[Activity],
) -> AsyncIterator[str]:
    """
    Stream itinerary generation token-by-token for Mushahid's SSE layer.
    Each yielded string is a raw token chunk — do not buffer before yielding.
    """
    prompt = build_itinerary_prompt(user_profile, destination, activities)
    async for chunk in stream_request("itinerary_generation", prompt, ITINERARY_SYSTEM_PROMPT):
        yield chunk


async def generate_refined_itinerary(
    itinerary: Itinerary,
    feedback: str,
    validation_result: ValidationResult,
    task_type: str = "complex_refinement",
) -> AsyncIterator[str]:
    """
    Stream a revised itinerary incorporating user feedback and validation issues.
    `task_type` selects the LLM tier — pass "quick_edit" for SMALL-scope user
    revisions so they route to the cheap fast model.
    """
    prompt = build_refinement_prompt(itinerary, feedback, validation_result)
    async for chunk in stream_request(task_type, prompt, REFINEMENT_SYSTEM_PROMPT):
        yield chunk


async def generate_refined_days(
    itinerary: Itinerary,
    target_day_numbers: list[int],
    feedback: str,
    validation_result: ValidationResult,
) -> AsyncIterator[str]:
    """Stream revised day(s) only instead of the full itinerary.

    Uses the targeted prompt so the LLM outputs a small JSON array (the revised
    days only), dramatically reducing output token count and generation time
    compared to a full itinerary rewrite.
    """
    prompt = build_targeted_day_refinement_prompt(
        itinerary, target_day_numbers, feedback, validation_result
    )
    async for chunk in stream_request("complex_refinement", prompt, REFINEMENT_SYSTEM_PROMPT):
        yield chunk


async def _stream_days_from_text(
    text_stream: AsyncIterator[str],
    activities: list[Activity],
    *,
    days_key: bool,
):
    """Forward-only JSON brace counter that yields ItineraryDay objects as
    soon as each day's `{...}` closes in the stream.

    `days_key=True`  → wait for the `"days"` field before counting day objects
                       (full itinerary regen wraps days inside the itinerary).
    `days_key=False` → the LLM is streaming a bare JSON array of day objects
                       (targeted-day regen prompt format), so start counting
                       day objects as soon as we enter the array.

    Yields tuples of (ItineraryDay, raw_buffer_so_far) — the raw buffer is
    kept by the caller so a streaming failure can fall back to a one-shot
    parse without losing tokens already consumed.
    """
    buffer = ""
    cursor = 0
    started = not days_key   # bare-array form starts immediately
    depth = 0
    in_string = False
    escape_next = False
    current_string = ""
    day_start_pos = None

    async for chunk in text_stream:
        buffer += chunk
        while cursor < len(buffer):
            c = buffer[cursor]
            if escape_next:
                escape_next = False
            elif in_string:
                if c == "\\":
                    escape_next = True
                elif c == '"':
                    if days_key and not started and current_string == "days":
                        started = True
                    current_string = ""
                    in_string = False
                else:
                    current_string += c
            elif c == '"':
                in_string = True
            elif started:
                if c == "{":
                    depth += 1
                    if depth == 1:
                        day_start_pos = cursor
                elif c == "}":
                    depth -= 1
                    if depth == 0 and day_start_pos is not None:
                        day_json = buffer[day_start_pos : cursor + 1]
                        try:
                            day_data = json.loads(day_json)
                            day_data = _patch_day_in_place(day_data, activities)
                            yield ItineraryDay.model_validate(day_data), buffer
                        except Exception as e:
                            logger.debug("Streaming day parse skipped: %s", e)
                        day_start_pos = None
            cursor += 1


async def stream_refined_itinerary_by_day(
    itinerary: Itinerary,
    feedback: str,
    validation_result: ValidationResult,
):
    """Full-itinerary refinement, yielded day-by-day as each one finishes
    parsing. Mirrors `generate_itinerary_by_day` but for the refinement
    prompt + tier.

    Yields (ItineraryDay, raw_buffer_so_far) tuples; the caller can keep
    the last raw_buffer to do a fallback whole-itinerary parse if the
    streaming detector missed everything.
    """
    text = generate_refined_itinerary(itinerary, feedback, validation_result, task_type="complex_refinement")
    activities = [ia.activity for day in itinerary.days for ia in day.activities]
    async for item in _stream_days_from_text(text, activities, days_key=True):
        yield item


async def stream_refined_days_by_day(
    itinerary: Itinerary,
    target_day_numbers: list[int],
    feedback: str,
    validation_result: ValidationResult,
):
    """Targeted-day refinement, yielded day-by-day as each one finishes
    parsing. Output prompt is a bare JSON array of day objects so we
    don't wait for a `days` key.
    """
    text = generate_refined_days(itinerary, target_day_numbers, feedback, validation_result)
    activities = [ia.activity for day in itinerary.days for ia in day.activities]
    async for item in _stream_days_from_text(text, activities, days_key=False):
        yield item


async def generate_itinerary_by_day(
    user_profile: UserProfile,
    destination: Destination,
    activities: list[Activity],
):
    """
    Stream the itinerary and yield each ItineraryDay as soon as its JSON is
    complete. Lets the orchestrator fire `day_ready` events and start
    explaining days while generation is still running.

    Falls back to a full-buffer parse via parse_itinerary() when the streaming
    detector produces no days (LLM wrapped JSON in fences, used a different
    key order, or schema-validated partial days kept failing). That way the
    pipeline never ends up with zero days when the raw output is actually fine.
    """
    prompt = build_itinerary_prompt(user_profile, destination, activities)
    buffer = ""
    cursor = 0            # forward-only — never re-scans previous chars
    days_started = False  # flips once we've seen the "days" key
    depth = 0
    in_string = False
    escape_next = False
    current_string = ""   # accumulates the current JSON string token
    day_start_pos = None  # position where the current day object opened
    yielded = 0

    async for chunk in stream_request("itinerary_generation", prompt, ITINERARY_SYSTEM_PROMPT):
        buffer += chunk

        while cursor < len(buffer):
            c = buffer[cursor]

            if escape_next:
                escape_next = False
            elif in_string:
                if c == "\\":
                    escape_next = True
                elif c == '"':
                    if not days_started and current_string == "days":
                        days_started = True
                    current_string = ""
                    in_string = False
                else:
                    current_string += c
            elif c == '"':
                in_string = True
            elif days_started:
                if c == "{":
                    depth += 1
                    if depth == 1:
                        day_start_pos = cursor
                elif c == "}":
                    depth -= 1
                    if depth == 0 and day_start_pos is not None:
                        day_json = buffer[day_start_pos : cursor + 1]
                        try:
                            day_data = json.loads(day_json)
                            day_data = _patch_day_in_place(day_data, activities)
                            yield ItineraryDay.model_validate(day_data)
                            yielded += 1
                        except Exception as e:
                            logger.debug("Streaming day parse skipped at pos %d: %s", cursor, e)
                        day_start_pos = None

            cursor += 1

    if yielded > 0:
        return

    # Streaming detection found nothing. Try parse_itinerary on the full buffer
    # — handles markdown fences, key-order quirks, and patches missing fields.
    if not buffer.strip():
        return
    try:
        itinerary = parse_itinerary(buffer, user_profile, destination, activities)
    except Exception as e:
        logger.warning("Fallback parse_itinerary failed: %s; raw head: %r", e, buffer[:200])
        return
    for day in itinerary.days:
        yield day
