"""
GET  /api/itineraries/current        → user's saved itinerary (dashboard card)
POST /api/itineraries/{id}/save      → mark this itinerary as the user's active trip

The orchestrator already writes every generated itinerary to Firestore via
write_itinerary on `done`. These routes layer a "current trip" pointer on top:
the user explicitly chooses which generated itinerary shows on their dashboard.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mushahid.auth import verify_token
from mushahid.realtime.firestore import (
    get_itinerary, get_user_profile, update_user_profile,
    get_companion_prefs, write_companion_prefs,
)
from mushahid.utils.sanitize import sanitize_user_input
from shared.config import LOCAL_MODE

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/itineraries/current")
async def get_current_itinerary(uid: str = Depends(verify_token)):
    """Return the itinerary the user marked as their active dashboard trip.
    204-equivalent {"itinerary": null} when nothing is saved yet, so the
    dashboard can render an empty state without treating 404 as an error."""
    try:
        profile = await get_user_profile(uid)
    except Exception as e:
        logger.warning("get_current_itinerary profile read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    current_id = (profile or {}).get("current_itinerary_id")
    if not current_id:
        return {"itinerary": None}

    try:
        itinerary = await get_itinerary(current_id)
    except Exception as e:
        logger.warning("get_current_itinerary itinerary read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    if itinerary is None:
        # Pointer is stale (itinerary was deleted). Treat as no current trip
        # rather than 500; the next save will overwrite the pointer.
        return {"itinerary": None}
    return {"itinerary": itinerary.model_dump(mode="json")}


@router.post("/itineraries/{itinerary_id}/save")
async def save_itinerary_as_current(itinerary_id: str, uid: str = Depends(verify_token)):
    """Mark this itinerary as the user's current dashboard trip. Verifies the
    user owns the itinerary before updating the pointer."""
    try:
        itinerary = await get_itinerary(itinerary_id)
    except Exception as e:
        logger.warning("save_itinerary read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised to save this itinerary")

    try:
        await update_user_profile(uid, {"current_itinerary_id": itinerary_id})
    except Exception as e:
        logger.warning("save_itinerary profile update failed: %s", e)
        if LOCAL_MODE:
            # In LOCAL_MODE update_user_profile silently no-ops if no profile exists.
            raise HTTPException(status_code=503, detail=f"Profile update failed: {type(e).__name__}") from e
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    return {"saved": True, "itinerary_id": itinerary_id}


# ── Companion preferences (per-trip) ──────────────────────────────────────────

class CompanionPrefsBody(BaseModel):
    party_arrival:  Optional[str] = None
    chat_lull:      Optional[str] = None
    spontaneity:    Optional[str] = None
    companion_text: Optional[str] = None


async def _verify_itinerary_owner(itinerary_id: str, uid: str):
    try:
        itinerary = await get_itinerary(itinerary_id)
    except Exception as e:
        logger.warning("itinerary read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised")
    return itinerary


@router.get("/itineraries/{itinerary_id}/companion-prefs")
async def get_companion_prefs_route(itinerary_id: str, uid: str = Depends(verify_token)):
    """Return the user's saved companion preferences for this trip, or
    {"prefs": null} when they haven't answered the intake yet."""
    await _verify_itinerary_owner(itinerary_id, uid)
    try:
        prefs = await get_companion_prefs(itinerary_id)
    except Exception as e:
        logger.warning("get_companion_prefs failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    return {"prefs": prefs}


@router.post("/itineraries/{itinerary_id}/companion-prefs")
async def save_companion_prefs(
    itinerary_id: str,
    body: CompanionPrefsBody,
    uid: str = Depends(verify_token),
):
    """Persist intake answers. Free-text companion_text is sanitised + capped
    at 200 chars before storage so it's safe to embed into the persona text."""
    await _verify_itinerary_owner(itinerary_id, uid)

    raw = body.model_dump()
    cleaned = {
        "party_arrival":  (raw.get("party_arrival")  or None),
        "chat_lull":      (raw.get("chat_lull")      or None),
        "spontaneity":    (raw.get("spontaneity")    or None),
        "companion_text": None,
        "itinerary_id":   itinerary_id,
        "user_id":        uid,
    }
    if raw.get("companion_text"):
        cleaned["companion_text"] = sanitize_user_input(raw["companion_text"])[:200]

    try:
        await write_companion_prefs(itinerary_id, cleaned)
    except Exception as e:
        logger.warning("write_companion_prefs failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    return {"saved": True, "prefs": cleaned}
