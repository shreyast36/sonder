"""
Travel journal routes.

POST   /api/itineraries/{id}/journal              create / update an entry for a day
GET    /api/itineraries/{id}/journal              list this trip's entries
DELETE /api/journal/{entry_id}                    delete one
GET    /api/destinations/{city}/journal           public entries tagged to a city
                                                  (?country=Japan to disambiguate)

Entries are short notes (optional photos) the user writes after travelling.
When is_public is true, the entry surfaces on the destination page for
future planners. Ownership is enforced against the itinerary's user_id.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from mushahid.auth import verify_token
from mushahid.realtime.firestore import (
    get_itinerary, get_user_profile,
    write_journal_entry, get_journal_entry,
    list_journal_entries_for_trip, list_public_journal_entries_for_city,
)
from mushahid.utils.sanitize import sanitize_user_input

router = APIRouter()
logger = logging.getLogger(__name__)


class JournalEntryBody(BaseModel):
    day_number: Optional[int] = Field(None, ge=1, le=60)
    text:       str = Field(..., min_length=1, max_length=1200)
    photos:     list[str] = Field(default_factory=list, max_length=6)
    is_public:  bool = False
    entry_id:   Optional[str] = None   # set to update; omit to create


async def _verify_owner(itinerary_id: str, uid: str):
    try:
        itinerary = await get_itinerary(itinerary_id)
    except Exception as e:
        logger.warning("journal itinerary read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised")
    return itinerary


@router.post("/itineraries/{itinerary_id}/journal")
async def upsert_journal_entry(
    itinerary_id: str,
    body: JournalEntryBody,
    uid: str = Depends(verify_token),
):
    itinerary = await _verify_owner(itinerary_id, uid)
    # Author display + avatar for rendering on the destination feed without
    # an extra round-trip per entry.
    profile = await get_user_profile(uid) or {}
    display_name = profile.get("display_name") or "Traveller"
    avatar_url   = profile.get("avatar_url")   or None

    eid = body.entry_id
    if eid:
        existing = await get_journal_entry(eid)
        if existing is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        if existing.get("user_id") != uid:
            raise HTTPException(status_code=403, detail="Not authorised")
    else:
        eid = f"je_{uuid.uuid4().hex[:12]}"

    city_raw    = itinerary.destination.city    or ""
    country_raw = itinerary.destination.country or ""
    now = datetime.now(timezone.utc).isoformat()

    entry = {
        "entry_id":      eid,
        "user_id":       uid,
        "itinerary_id":  itinerary_id,
        "day_number":    body.day_number,
        "text":          sanitize_user_input(body.text)[:1200],
        "photos":        list(body.photos)[:6],
        "is_public":     bool(body.is_public),
        "city":          city_raw,
        "country":       country_raw,
        "city_lower":    city_raw.strip().lower(),
        "country_lower": country_raw.strip().lower(),
        "display_name":  display_name,
        "avatar_url":    avatar_url,
        "created_at":    now if not body.entry_id else None,
        "updated_at":    now,
    }
    entry = {k: v for k, v in entry.items() if v is not None or k in ("photos",)}

    try:
        await write_journal_entry(eid, entry)
    except Exception as e:
        logger.warning("write_journal_entry failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    return {"entry": entry}


@router.get("/itineraries/{itinerary_id}/journal")
async def list_trip_journal(itinerary_id: str, uid: str = Depends(verify_token)):
    await _verify_owner(itinerary_id, uid)
    try:
        entries = await list_journal_entries_for_trip(itinerary_id)
    except Exception as e:
        logger.warning("list_trip_journal failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    return {"entries": entries}


@router.delete("/journal/{entry_id}")
async def delete_journal_entry(entry_id: str, uid: str = Depends(verify_token)):
    try:
        existing = await get_journal_entry(entry_id)
    except Exception as e:
        logger.warning("delete_journal_entry read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    if existing is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    if existing.get("user_id") != uid:
        raise HTTPException(status_code=403, detail="Not authorised")

    # Soft-delete by setting deleted_at + clearing text/photos; keeps the
    # entry id stable in case the destination feed has surfaced it.
    now = datetime.now(timezone.utc).isoformat()
    try:
        await write_journal_entry(entry_id, {
            "entry_id":   entry_id,
            "user_id":    uid,
            "deleted_at": now,
            "text":       "",
            "photos":     [],
            "is_public":  False,
        })
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    return {"deleted": True}


@router.get("/destinations/{city}/journal")
async def list_destination_feed(
    city: str,
    country: Optional[str] = Query(None),
    limit: int = Query(40, ge=1, le=100),
    uid: str = Depends(verify_token),
):
    """Public entries pinned to a destination. Authentication is required so
    we can later layer on rate-limiting / abuse signals, but visibility is
    public to every signed-in Sonder member."""
    try:
        entries = await list_public_journal_entries_for_city(city, country, limit=limit)
    except Exception as e:
        logger.warning("list_destination_feed failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    # Strip user_id from the public payload — display_name + avatar are
    # enough to render, no contact info leaks.
    public = [
        {k: v for k, v in e.items() if k not in ("user_id",) and not e.get("deleted_at")}
        for e in entries if not e.get("deleted_at")
    ]
    return {"entries": public, "city": city, "country": country}
