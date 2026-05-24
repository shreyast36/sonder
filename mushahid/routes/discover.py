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
import random

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
    """Feed of trips flagged is_open_to_join, viewer's own included so
    they can confirm their toggle landed. Each card carries
    `your_request_status` (for trips owned by others) or `is_yours=True`
    (for the viewer's own trip) so the frontend can render the right
    state."""
    trips = await list_open_trips(limit=limit)

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
        cards.append(await _trip_card(t, viewer_uid=uid,
                                      status_by_trip=status_by_trip))
    return {"trips": cards}


async def _trip_card(
    t: dict, *, viewer_uid: str, status_by_trip: dict[str, str] | None = None,
) -> dict:
    """Shape one Itinerary doc into the card the Discover frontend
    renders. Shared between the list endpoint and the open/close
    broadcasts so the wire format stays in sync."""
    owner_id = t.get("user_id")
    owner_name, owner_avatar = (
        await _profile_summary(owner_id) if owner_id else ("Traveller", None)
    )
    dest = t.get("destination") or {}
    days = t.get("days") or []
    start_date = (days[0].get("trip_date") if days else None)
    end_date   = (days[-1].get("trip_date") if days else None)
    tid = t.get("itinerary_id")
    return {
        "itinerary_id":         tid,
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
        "is_yours":             owner_id == viewer_uid,
        "your_request_status":  (status_by_trip or {}).get(tid) if owner_id != viewer_uid else None,
    }


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

    # Fan out to every connected user so Discover lights up in real
    # time — they don't need to wait for the 10s poll. The viewer
    # themselves is excluded; their UI already knows it just opened.
    try:
        fresh = await get_itinerary(itinerary_id)
        if fresh is not None:
            card = await _trip_card(
                fresh.model_dump(mode="json") if hasattr(fresh, "model_dump") else dict(fresh),
                viewer_uid="",  # broadcast card is rendered by recipients, not the opener
            )
            # `is_yours` is recipient-relative; recompute on the client.
            card.pop("is_yours", None)
            card["owner_uid"] = uid
            await ws_manager.broadcast_global(
                {"type": "discover_trip_open", "trip": card},
                exclude_user=uid,
            )
    except Exception as e:
        logger.debug("broadcast_global(discover_trip_open) failed: %s", e)

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

    try:
        await ws_manager.broadcast_global(
            {"type": "discover_trip_close", "itinerary_id": itinerary_id},
            exclude_user=uid,
        )
    except Exception as e:
        logger.debug("broadcast_global(discover_trip_close) failed: %s", e)

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
    # Synthetic trips have no human owner to approve, so resolve the
    # request inline using the same match-score signal we use for
    # mutual approval on chat. The persona was snapshotted onto the
    # trip doc at open time; if it isn't there (older synth trips),
    # we treat the request as a normal pending one for the (absent)
    # owner. Probability = match_score directly — same calibration as
    # the chat persona decision.
    snapshot = await _synthetic_owner_snapshot(itinerary_id)
    if snapshot:
        match_score = await _score_against_synthetic(uid, snapshot)
        p_approve   = float(match_score) if match_score is not None else 0.5
        roll        = random.random()
        verdict     = "approved" if roll < p_approve else "denied"
        req["status"]      = verdict
        req["match_score"] = match_score
        req["auto_resolved"] = True
        req["resolved_at"] = _now_iso()
        await write_join_request(req)

        if verdict == "approved":
            try:
                companions = list(itin.co_traveller_ids or [])
                if uid not in companions:
                    companions.append(uid)
                updated = itin.model_copy(update={"co_traveller_ids": companions})
                await write_itinerary(updated)
            except Exception as e:
                logger.warning("synthetic auto-approve: write_itinerary failed: %s", e)

        logger.info(
            "synthetic join %s score=%.3f p=%.2f roll=%.2f -> %s",
            itinerary_id, match_score or 0.0, p_approve, roll, verdict,
        )
        try:
            await ws_manager.notify_user(uid, {"type": "join_request_resolved", "request": req})
        except Exception as e:
            logger.debug("notify_user(join_request_resolved) failed: %s", e)
        # Also web-push so the verdict reaches the requester even if
        # they've closed the tab.
        _push_join_resolved(uid, req, itin)
        return {"request": req, "duplicated": False, "auto_resolved": True}

    # Non-synthetic: persist as proposed, ping the human owner.
    await write_join_request(req)
    try:
        await ws_manager.notify_user(itin.user_id, {"type": "join_request_new", "request": req})
    except Exception as e:
        logger.debug("notify_user(join_request_new) failed: %s", e)
    _push_join_new(itin.user_id, req, itin)
    return {"request": req, "duplicated": False}


def _push_join_new(owner_uid: str, req: dict, itin) -> None:
    """Push + email the trip owner that someone wants to join. Reaches
    them with tab closed (push) or later in inbox (email). All channels
    fire-and-forget; failure of one never blocks the others."""
    if not owner_uid:
        return
    from mushahid.realtime.notify import notify_event
    import asyncio as _asyncio
    requester = req.get("requester_name") or "Someone"
    where     = getattr(getattr(itin, "destination", None), "city", "") or "your trip"
    _asyncio.create_task(notify_event(
        recipient_uid=owner_uid, kind="join_request",
        title=f"{requester} wants in",
        body=f"They asked to join {where}. Open Sonder to decide.",
        link_path="/dashboard",
        tag=f"sonder-join-{req.get('request_id')}",
    ))


def _push_join_resolved(requester_uid: str, req: dict, itin) -> None:
    """Push + email the verdict back to the requester. Important for
    the synthetic-trip flow where resolution is instant and the user
    might not be looking at the modal anymore."""
    if not requester_uid:
        return
    from mushahid.realtime.notify import notify_event
    import asyncio as _asyncio
    where    = getattr(getattr(itin, "destination", None), "city", "") or "the trip"
    status   = req.get("status")
    approved = status == "approved"
    body     = (
        f"You're in. {where} just got a new companion — open it to start planning."
        if approved else
        f"Not this time. {where} passed on your request — plenty more opening up right now."
    )
    _asyncio.create_task(notify_event(
        recipient_uid=requester_uid, kind="join_verdict",
        title=("You're in" if approved else "Not this time"),
        body=body,
        link_path=(f"/shared/{itin.itinerary_id}" if approved else "/dashboard"),
        tag=f"sonder-join-{req.get('request_id')}",
    ))


async def _synthetic_owner_snapshot(itinerary_id: str) -> dict | None:
    """Read the synthetic-owner persona snapshot off the itinerary doc.
    Returns None when the trip isn't synthetic or the snapshot wasn't
    persisted (older synth trips). Bypasses the Itinerary pydantic
    model since `synthetic_owner` isn't a schema field."""
    try:
        from mushahid.realtime.firestore import get_db, LOCAL_MODE, _store
        if LOCAL_MODE:
            doc = _store.get(f"itinerary:{itinerary_id}")
            if isinstance(doc, dict) and doc.get("is_synthetic"):
                snap = doc.get("synthetic_owner")
                return snap if isinstance(snap, dict) else None
            return None
        import asyncio as _asyncio
        snapshot = await _asyncio.to_thread(
            lambda: get_db().collection("itineraries").document(itinerary_id).get()
        )
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        if not data.get("is_synthetic"):
            return None
        snap = data.get("synthetic_owner")
        return snap if isinstance(snap, dict) else None
    except Exception as e:
        logger.warning("synthetic_owner_snapshot failed for %s: %s", itinerary_id, e)
        return None


async def _score_against_synthetic(viewer_uid: str, snap: dict) -> float | None:
    """Compute a [0,1] match score between the signed-in viewer and the
    snapshotted synthetic persona using the same compatibility engine
    that powers the matches list. Returns None on failure so the caller
    can fall back to a neutral default."""
    try:
        from shared.schemas import UserProfile, CoTravellerProfile
        from jahnvi.schemas.enums import PacePreference, BudgetStyle, TravelStyle
        from shreyas.cotraveller.matching import score_compatibility

        prof = await get_user_profile(viewer_uid) or {}
        viewer = UserProfile(
            user_id      = viewer_uid,
            display_name = prof.get("display_name") or "",
            constraints  = prof.get("constraints"),
            persona_answers      = prof.get("persona_answers"),
            compatibility_signals= prof.get("compatibility_signals"),
            travel_style_embedding = prof.get("travel_style_embedding") or [],
        )
        candidate = CoTravellerProfile(
            profile_id   = snap.get("profile_id") or "ct_synth",
            display_name = snap.get("display_name") or "Traveller",
            age          = 28,
            location     = snap.get("location") or "",
            archetype    = snap.get("archetype") or "Traveller",
            interests    = list(snap.get("interests") or []),
            pace         = PacePreference(snap.get("pace") or "moderate"),
            budget_style = BudgetStyle(snap.get("budget_style") or "mid_range"),
            travel_style = TravelStyle(snap.get("travel_style") or "solo"),
            avatar_url   = snap.get("avatar_url"),
            quirks       = list(snap.get("quirks") or []),
            is_seed      = bool(snap.get("is_seed", True)),
        )
        result = score_compatibility(viewer, candidate)
        return float(result.match_score)
    except Exception as e:
        logger.warning("_score_against_synthetic failed: %s", e)
        return None


@router.get("/discover/trips/{itinerary_id}/preview")
async def trip_preview(itinerary_id: str, uid: str = Depends(verify_token)):
    """Lightweight detail payload for the trip-detail modal. Returns
    the persona snapshot (if any) + the user's match preview so the
    UI can render compatibility hints before the user commits to a
    request."""
    itin = await get_itinerary(itinerary_id)
    if itin is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    snap = await _synthetic_owner_snapshot(itinerary_id)
    owner_summary: dict
    match_score: float | None = None
    if snap:
        owner_summary = {
            "display_name": snap.get("display_name"),
            "location":     snap.get("location"),
            "archetype":    snap.get("archetype"),
            "interests":    list(snap.get("interests") or [])[:6],
            "quirks":       list(snap.get("quirks") or [])[:3],
            "pace":         snap.get("pace"),
            "budget_style": snap.get("budget_style"),
            "travel_style": snap.get("travel_style"),
            "avatar_url":   snap.get("avatar_url"),
            "is_synthetic": True,
        }
        match_score = await _score_against_synthetic(uid, snap)
    else:
        name, avatar = await _profile_summary(itin.user_id) if itin.user_id else ("Traveller", None)
        owner_summary = {
            "display_name": name, "avatar_url": avatar, "is_synthetic": False,
        }

    dest = itin.destination
    days = itin.days or []
    return {
        "itinerary_id": itinerary_id,
        "owner":        owner_summary,
        "destination":  {
            "city":    dest.city if dest else "",
            "country": dest.country if dest else "",
            "tags":    list(dest.tags or []) if dest else [],
        },
        "trip_start":   str(days[0].trip_date) if days and days[0].trip_date else None,
        "trip_end":     str(days[-1].trip_date) if days and days[-1].trip_date else None,
        "day_count":    len(days),
        "note":         snap and snap.get("open_join_note") or "",
        "match_score":  match_score,
        "is_synthetic": bool(snap),
        "is_open_to_join": bool(getattr(itin, "is_open_to_join", False)),
    }


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

    # Also web-push so the requester learns the verdict even when
    # they've left the tab.
    try:
        itin_for_push = await get_itinerary(req["itinerary_id"])
        if itin_for_push is not None:
            _push_join_resolved(req["requester_id"], req, itin_for_push)
    except Exception as e:
        logger.debug("respond: web push failed: %s", e)

    return {"request": req}
