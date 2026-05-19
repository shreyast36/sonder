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
    """Append the itinerary to the user's saved history AND mark it current
    (the dashboard hero card). Past trips remain queryable via /itineraries/list.
    Re-saving the same id is a no-op for the history (no duplicate)."""
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
        profile = await get_user_profile(uid) or {}
        saved_ids = list(profile.get("saved_itinerary_ids") or [])
        if itinerary_id not in saved_ids:
            saved_ids.append(itinerary_id)
        await update_user_profile(uid, {
            "current_itinerary_id": itinerary_id,
            "saved_itinerary_ids":  saved_ids,
        })
    except Exception as e:
        logger.warning("save_itinerary profile update failed: %s", e)
        if LOCAL_MODE:
            raise HTTPException(status_code=503, detail=f"Profile update failed: {type(e).__name__}") from e
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    return {"saved": True, "itinerary_id": itinerary_id}


@router.get("/itineraries/list")
async def list_saved_itineraries(uid: str = Depends(verify_token)):
    """All of the user's saved itineraries, newest-saved first. Each entry
    is a slim summary (id, destination, day count, total budget, dates) for
    rendering a 'Past trips' carousel — full itinerary fetched on-demand
    via /api/itineraries/current after switching."""
    try:
        profile = await get_user_profile(uid) or {}
    except Exception as e:
        logger.warning("list_saved_itineraries profile read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    saved_ids = list(profile.get("saved_itinerary_ids") or [])
    current_id = profile.get("current_itinerary_id")

    # Backfill: older users have a current_id but no saved list.
    if current_id and current_id not in saved_ids:
        saved_ids.append(current_id)

    summaries = []
    for iid in reversed(saved_ids):   # newest-saved first
        try:
            it = await get_itinerary(iid)
        except Exception as e:
            logger.warning("itinerary fetch failed for %s: %s", iid, e)
            continue
        if it is None or it.user_id != uid:
            continue
        days = it.days or []
        summaries.append({
            "itinerary_id":    it.itinerary_id,
            "is_current":      it.itinerary_id == current_id,
            "city":            it.destination.city,
            "country":         it.destination.country,
            "day_count":       len(days),
            "trip_start":      str(days[0].trip_date) if days and days[0].trip_date else None,
            "trip_end":        str(days[-1].trip_date) if days and days[-1].trip_date else None,
            "total_budget_usd": it.total_budget_usd,
        })
    return {"trips": summaries}


class SetCurrentBody(BaseModel):
    itinerary_id: str


@router.post("/itineraries/set-current")
async def set_current_itinerary(body: SetCurrentBody, uid: str = Depends(verify_token)):
    """Switch which saved trip is the dashboard hero. Trip must already be
    in the user's saved list (i.e. previously saved). Doesn't add to history."""
    itinerary = await get_itinerary(body.itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised")
    try:
        profile = await get_user_profile(uid) or {}
        saved_ids = list(profile.get("saved_itinerary_ids") or [])
        if body.itinerary_id not in saved_ids:
            raise HTTPException(status_code=409, detail="Save the itinerary first before switching to it")
        await update_user_profile(uid, {"current_itinerary_id": body.itinerary_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("set_current_itinerary failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    return {"current_itinerary_id": body.itinerary_id}


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
