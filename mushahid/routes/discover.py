"""
Discover surface: open trips + join requests + (in feed.py) social posts.

Routes here:
    GET  /api/discover/trips                          paginated feed of
                                                       trips marked open
    POST /api/itineraries/{id}/open                   owner toggles
                                                       is_open_to_join + capacity
    POST /api/itineraries/{id}/close                  owner closes
    POST /api/discover/trips/{id}/join-request        another user requests to join
    GET  /api/discover/join-requests                  list MY requests
                                                       (?as=owner for ones I received)
    POST /api/discover/join-requests/{id}/respond     owner accepts/denies

Join approval flow:
    proposed → approved → owner's itinerary gets requester added to
                          co_traveller_ids; downstream UX nudges into
                          the shared-itinerary surface.
    proposed → denied   → terminal, requester sees the rejection.

Owner is identified by Itinerary.user_id at the time of request — that
field is the source of truth for ownership; we don't trust any
owner_id on the request body.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from mushahid.auth import verify_token
from mushahid.realtime.firestore import (
    get_itinerary, write_itinerary,
    list_open_trips, set_itinerary_open,
    write_join_request, get_join_request, list_join_requests_for_user,
    get_user_profile,
)
from mushahid.utils.sanitize import sanitize_user_input
from shreyas.cotraveller.chat import manager as ws_manager

router = APIRouter()
logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _profile_summary(user_id: str) -> tuple[str, str | None]:
    """Best-effort lookup of (display_name, avatar_url) for a user_id.
    Falls back to ('Traveller', None) when the lookup fails so we don't
    block feed render on a single missing profile."""
    try:
        p = await get_user_profile(user_id) or {}
        return (p.get("display_name") or "Traveller", p.get("avatar_url"))
    except Exception:
        return ("Traveller", None)


# ── Schemas (request models only — response shapes come from social.py)


class OpenTripRequest(BaseModel):
    join_capacity: int = Field(default=1, ge=0, le=4)
    note:          str = Field(default="", max_length=200)


class JoinRequestBody(BaseModel):
    message: str = Field(default="", max_length=400)


class RespondJoinRequest(BaseModel):
    decision: str   # "approve" | "deny"


# ── Routes ────────────────────────────────────────────────────────────────


@router.get("/discover/trips")
async def list_discover_trips(
    limit: int = Query(default=40, ge=1, le=100),
    uid:   str = Depends(verify_token),
):
    """Feed of trips other users have flagged is_open_to_join. Owner's
    own trips are excluded — you can't request to join your own. Each
    card carries `your_request_status` so the frontend can render the
    right state ('Request to join' vs 'Requested' vs 'Approved' vs 'Denied')."""
    trips = await list_open_trips(limit=limit)
    # Skip trips owned by the viewer.
    trips = [t for t in trips if t.get("user_id") != uid]

    # Pre-fetch the viewer's prior join-requests so each card knows its
    # status without an N+1 lookup later.
    my_requests = await list_join_requests_for_user(uid, as_owner=False)
    status_by_trip: dict[str, str] = {}
    for r in my_requests:
        tid = r.get("itinerary_id")
        if not tid:
            continue
        # If there are multiple historical requests for the same trip,
        # show the latest. Sort by created_at ascending and let later
        # entries overwrite earlier ones.
        prev = status_by_trip.get(tid)
        if prev is None or (r.get("created_at") or "") >= (prev or ""):
            status_by_trip[tid] = r.get("status") or "proposed"

    cards: list[dict] = []
    for t in trips:
        owner_id = t.get("user_id")
        owner_name, owner_avatar = await _profile_summary(owner_id) if owner_id else ("Traveller", None)
        dest = t.get("destination") or {}
        # ItineraryDay carries trip_date; we surface the trip window
        # from the first/last day so the feed shows real dates.
        days = t.get("days") or []
        start_date = (days[0].get("trip_date") if days else None)
        end_date   = (days[-1].get("trip_date") if days else None)
        cards.append({
            "itinerary_id":         t.get("itinerary_id"),
            "owner_id":             owner_id,
            "owner_name":           owner_name,
            "owner_avatar":         owner_avatar,
            "destination_city":     dest.get("city") or "",
            "destination_country":  dest.get("country") or "",
            "start_date":           start_date,
            "end_date":             end_date,
            "join_capacity":        int(t.get("join_capacity") or 1),
            "confirmed_companions": len(t.get("co_traveller_ids") or []),
            "note":                 t.get("open_join_note") or "",
            "your_request_status":  status_by_trip.get(t.get("itinerary_id")),
        })
    return {"trips": cards}


@router.post("/itineraries/{itinerary_id}/open")
async def open_itinerary(itinerary_id: str, body: OpenTripRequest, uid: str = Depends(verify_token)):
    """Owner-only: mark this itinerary as open to join."""
    itin = await get_itinerary(itinerary_id)
    if itin is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itin.user_id != uid:
        raise HTTPException(status_code=403, detail="Only the trip owner can open it")
    note = sanitize_user_input(body.note)[:200]
    ok = await set_itinerary_open(itinerary_id, is_open=True, join_capacity=body.join_capacity)
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to update itinerary state")
    # Persist the note alongside the open flag. set_itinerary_open writes
    # only the two canonical fields; piggyback the note onto a separate
    # merge so we don't expand that helper's contract.
    try:
        updated = itin.model_copy(update={
            "is_open_to_join": True,
            "join_capacity":   body.join_capacity,
        })
        await write_itinerary(updated)
        if note:
            from mushahid.realtime.firestore import get_db, LOCAL_MODE, _store
            if LOCAL_MODE:
                key = f"itinerary:{itinerary_id}"
                if key in _store:
                    _store[key] = {**_store[key], "open_join_note": note}
            else:
                import asyncio
                await asyncio.to_thread(
                    lambda: get_db().collection("itineraries").document(itinerary_id)
                                    .set({"open_join_note": note}, merge=True)
                )
    except Exception as e:
        logger.warning("open_itinerary note persist failed: %s", e)
    return {"itinerary_id": itinerary_id, "is_open_to_join": True, "join_capacity": body.join_capacity}


@router.post("/itineraries/{itinerary_id}/close")
async def close_itinerary(itinerary_id: str, uid: str = Depends(verify_token)):
    """Owner-only: take this trip off the discovery feed."""
    itin = await get_itinerary(itinerary_id)
    if itin is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itin.user_id != uid:
        raise HTTPException(status_code=403, detail="Only the trip owner can close it")
    ok = await set_itinerary_open(itinerary_id, is_open=False, join_capacity=itin.join_capacity)
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to update itinerary state")
    return {"itinerary_id": itinerary_id, "is_open_to_join": False}


@router.post("/discover/trips/{itinerary_id}/join-request")
async def request_to_join(itinerary_id: str, body: JoinRequestBody, uid: str = Depends(verify_token)):
    """Another user wants in on the trip. We persist a JoinRequest doc
    that the owner can later approve or deny. Idempotent on the
    (itinerary_id, requester_id) pair — re-requesting overwrites the
    prior `denied` / `withdrawn` request with a fresh `proposed`."""
    itin = await get_itinerary(itinerary_id)
    if itin is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if not getattr(itin, "is_open_to_join", False):
        raise HTTPException(status_code=409, detail="Trip is not open to joins right now")
    if itin.user_id == uid:
        raise HTTPException(status_code=400, detail="You can't request to join your own trip")
    if uid in (itin.co_traveller_ids or []):
        raise HTTPException(status_code=409, detail="You're already on this trip")

    # Look up the latest request from this user for this trip — if it
    # exists and is still proposed/approved, return it. Otherwise mint
    # a fresh one.
    existing = await list_join_requests_for_user(uid, as_owner=False)
    same_trip = [r for r in existing if r.get("itinerary_id") == itinerary_id]
    same_trip.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    if same_trip and same_trip[0].get("status") in ("proposed", "approved"):
        return {"request": same_trip[0], "duplicated": True}

    requester_name, requester_avatar = await _profile_summary(uid)
    req = {
        "request_id":       _new_id("jreq"),
        "itinerary_id":     itinerary_id,
        "owner_id":         itin.user_id,
        "requester_id":     uid,
        "requester_name":   requester_name,
        "requester_avatar": requester_avatar,
        "message":          sanitize_user_input(body.message)[:400],
        "status":           "proposed",
        "created_at":       _now_iso(),
    }
    await write_join_request(req)
    # Push to the trip owner's global notification socket so the
    # incoming-requests panel on their dashboard surfaces this
    # without a refresh. Failure is logged and ignored — the poll-
    # on-mount path is the fallback.
    try:
        await ws_manager.notify_user(itin.user_id, {"type": "join_request_new", "request": req})
    except Exception as e:
        logger.debug("notify_user(join_request_new) failed: %s", e)
    return {"request": req, "duplicated": False}


@router.get("/discover/join-requests")
async def my_join_requests(
    as_role: str = Query(default="requester", regex="^(requester|owner)$", alias="as"),
    uid:     str = Depends(verify_token),
):
    """List join requests this user is involved in. Default returns
    requests YOU made; ?as=owner returns requests on YOUR trips."""
    rows = await list_join_requests_for_user(uid, as_owner=(as_role == "owner"))
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"requests": rows}


@router.post("/discover/join-requests/{request_id}/respond")
async def respond_join_request(request_id: str, body: RespondJoinRequest, uid: str = Depends(verify_token)):
    """Owner accepts or denies a pending request. On approve, the
    requester is added to the trip's co_traveller_ids — the
    shared-itinerary surface bootstraps from there."""
    req = await get_join_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.get("owner_id") != uid:
        raise HTTPException(status_code=403, detail="Only the trip owner can respond")
    if req.get("status") != "proposed":
        raise HTTPException(status_code=409, detail=f"request is {req.get('status')}")
    if body.decision not in ("approve", "deny"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'deny'")

    new_status = "approved" if body.decision == "approve" else "denied"
    req["status"] = new_status
    req["resolved_at"] = _now_iso()
    await write_join_request(req)

    if new_status == "approved":
        try:
            itin = await get_itinerary(req["itinerary_id"])
            if itin is not None:
                companions = list(itin.co_traveller_ids or [])
                if req["requester_id"] not in companions:
                    companions.append(req["requester_id"])
                updated = itin.model_copy(update={"co_traveller_ids": companions})
                await write_itinerary(updated)
        except Exception as e:
            logger.warning("respond_join_request: failed to append requester to itinerary: %s", e)

    # Push the resolution to the requester's notification socket so
    # their Discover card flips badge state in real time.
    try:
        await ws_manager.notify_user(req["requester_id"],
                                     {"type": "join_request_resolved", "request": req})
    except Exception as e:
        logger.debug("notify_user(join_request_resolved) failed: %s", e)

    return {"request": req}
