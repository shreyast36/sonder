"""
Collaborative-itinerary helpers used after two travellers mutually approve.

These were the original V1 stubs. Most production traffic now goes through
mushahid/routes/shared.py which owns the propose/respond/finalize lifecycle.
This module remains a thin direct-mutation API for callers that want simpler
add-activity / add-note operations bypassing the proposal queue.
"""

from datetime import datetime, timezone

from fastapi import HTTPException

from shared.schemas import (
    Activity,
    ItineraryActivity,
    ItineraryUpdateEvent,
    SharedItinerary,
)
from shared.schemas import Itinerary  # noqa: F401  (re-exported for clarity in callers)

from mushahid.realtime.firestore import (
    get_shared_itinerary,
    write_shared_itinerary,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _broadcast(itinerary_id: str, event: ItineraryUpdateEvent) -> None:
    """Fire-and-forget WebSocket fan-out to both participants. Import locally
    to avoid a circular dependency with the chat module at process start."""
    try:
        from shreyas.cotraveller.chat import manager as ws_manager
        await ws_manager.broadcast_to_session(itinerary_id, {
            "type":         "shared_itinerary_update",
            "event_type":   event.event_type,
            "user_id":      event.user_id,
            "payload":      event.payload,
            "timestamp":    event.timestamp,
        })
    except Exception:
        # WebSocket fan-out must never break the write path.
        pass


async def create_shared_itinerary(itinerary: Itinerary, user_ids: list[str]) -> SharedItinerary:
    """Create the shared doc on mutual approval. Idempotent — re-calling with
    the same itinerary id returns the existing doc rather than overwriting."""
    existing = await get_shared_itinerary(itinerary.itinerary_id)
    if existing is not None:
        return existing

    shared = SharedItinerary(
        itinerary_id    = itinerary.itinerary_id,
        user_ids        = list(user_ids),
        itinerary       = itinerary,
        notes           = [],
        last_updated_by = None,
        version         = 0,
    )
    await write_shared_itinerary(shared)
    return shared


async def add_activity(
    itinerary_id:   str,
    user_id:        str,
    activity:       Activity,
    day_number:     int,
    client_version: int,
) -> SharedItinerary:
    """Append an activity to the matching day. Raises HTTP 409 when the
    client's version is behind the stored version (frontend re-fetches via
    sync_changes and retries)."""
    current = await get_shared_itinerary(itinerary_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Shared itinerary not found")
    if current.version != client_version:
        raise HTTPException(status_code=409, detail="Conflict — re-fetch and retry")
    if user_id not in current.user_ids:
        raise HTTPException(status_code=403, detail="Not a participant in this shared itinerary")

    new_entry = ItineraryActivity(activity=activity, time="", why_this=None)
    days = list(current.itinerary.days)
    target = next((d for d in days if d.day_number == day_number), None)
    if target is None:
        raise HTTPException(status_code=400, detail=f"Day {day_number} not in itinerary")
    target.activities = list(target.activities) + [new_entry]

    updated = current.model_copy(update={
        "itinerary":       current.itinerary.model_copy(update={"days": days}),
        "last_updated_by": user_id,
        "version":         current.version + 1,
    })
    await write_shared_itinerary(updated)

    await _broadcast(itinerary_id, ItineraryUpdateEvent(
        event_type   = "activity_added",
        itinerary_id = itinerary_id,
        user_id      = user_id,
        payload      = {
            "day_number":    day_number,
            "activity_name": activity.name,
            "version":       updated.version,
        },
        timestamp    = _now_iso(),
    ))
    return updated


async def add_note(
    itinerary_id:   str,
    user_id:        str,
    note:           str,
    client_version: int,
) -> SharedItinerary:
    """Append a note. Same 409 semantics as add_activity."""
    current = await get_shared_itinerary(itinerary_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Shared itinerary not found")
    if current.version != client_version:
        raise HTTPException(status_code=409, detail="Conflict — re-fetch and retry")
    if user_id not in current.user_ids:
        raise HTTPException(status_code=403, detail="Not a participant in this shared itinerary")

    note_entry = {"user_id": user_id, "note": note, "timestamp": _now_iso()}
    updated = current.model_copy(update={
        "notes":           list(current.notes) + [note_entry],
        "last_updated_by": user_id,
        "version":         current.version + 1,
    })
    await write_shared_itinerary(updated)

    await _broadcast(itinerary_id, ItineraryUpdateEvent(
        event_type   = "note_added",
        itinerary_id = itinerary_id,
        user_id      = user_id,
        payload      = {"note": note, "version": updated.version},
        timestamp    = note_entry["timestamp"],
    ))
    return updated


async def sync_changes(itinerary_id: str) -> SharedItinerary:
    """Latest server state — called by the client after a 409 to rebase
    its local version and retry."""
    current = await get_shared_itinerary(itinerary_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Shared itinerary not found")
    return current
