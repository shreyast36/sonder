import json
from typing import AsyncIterator
from shared.schemas import UserProfile, Destination, Activity, ItineraryDay, Itinerary, ValidationResult
from ali.routing.engine import stream_request
from ali.generation.prompts import (
    ITINERARY_SYSTEM_PROMPT,
    REFINEMENT_SYSTEM_PROMPT,
    build_itinerary_prompt,
    build_refinement_prompt,
)


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
) -> AsyncIterator[str]:
    """
    Stream a revised itinerary incorporating user feedback and validation issues.
    Call this from the refinement loop instead of generate_itinerary() so that
    the feedback actually reaches the LLM via build_refinement_prompt().
    """
    prompt = build_refinement_prompt(itinerary, feedback, validation_result)
    async for chunk in stream_request("complex_refinement", prompt, REFINEMENT_SYSTEM_PROMPT):
        yield chunk


async def generate_itinerary_by_day(
    user_profile: UserProfile,
    destination: Destination,
    activities: list[Activity],
):
    """
    Stream the itinerary and yield each ItineraryDay as soon as its JSON is complete.
    Lets the orchestrator pipeline explain_day() calls while generation is still running.
    """
    prompt = build_itinerary_prompt(user_profile, destination, activities)
    buffer = ""
    days_started = False  # True once we've seen the "days": [ opening
    depth = 0
    in_string = False
    escape_next = False
    current_string = ""   # accumulates characters of the current JSON string token
    day_start_pos = None  # position in buffer where current day object opened

    async for chunk in stream_request("itinerary_generation", prompt, ITINERARY_SYSTEM_PROMPT):
        buffer += chunk

        # Scan new characters for complete day objects
        scan_from = max(0, len(buffer) - len(chunk) - 1)
        i = scan_from

        while i < len(buffer):
            c = buffer[i]

            if escape_next:
                escape_next = False
                i += 1
                continue
            if c == "\\" and in_string:
                escape_next = True
                i += 1
                continue
            if c == '"':
                if in_string:
                    # Closing quote — check if this string token was the "days" key
                    if not days_started and current_string == "days":
                        days_started = True
                    current_string = ""
                in_string = not in_string
                i += 1
                continue
            if in_string:
                current_string += c
                i += 1
                continue

            # Outside strings — track structure
            if not days_started:
                i += 1
                continue

            if c == "{":
                depth += 1
                if depth == 1:
                    day_start_pos = i  # start of a new day object
            elif c == "}":
                depth -= 1
                if depth == 0 and day_start_pos is not None:
                    # Complete day object found
                    day_json = buffer[day_start_pos : i + 1]
                    try:
                        day_data = json.loads(day_json)
                        yield ItineraryDay.model_validate(day_data)
                    except Exception:
                        pass  # malformed partial — skip, full parse will catch it
                    day_start_pos = None

            i += 1
