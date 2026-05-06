import json
from typing import AsyncIterator
from fastapi.responses import StreamingResponse


def format_event(event_name: str, data: dict) -> str:
    """
    Format a single SSE event string.

    Expected input:
        event_name = "persona_inferred"
        data       = {"archetype": "Cultural Explorer", "emotion": "excited"}

    Expected output:
        "event: persona_inferred\ndata: {\"archetype\": \"Cultural Explorer\", \"emotion\": \"excited\"}\n\n"
    """
    return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"


def stream_pipeline_events(generator: AsyncIterator[str]) -> StreamingResponse:
    """
    Wrap an async generator of SSE strings into a FastAPI StreamingResponse.

    Expected usage (in plan_trip.py):
        return stream_pipeline_events(orchestrator.run_plan_trip_pipeline(user_profile))
    """
    return StreamingResponse(generator, media_type="text/event-stream")
