"""
Collaborative shared-itinerary routes.

After both sides approve in /chat/approve, the user lands on
/shared/{itinerary_id} where they can propose changes to the trip. The
synthetic co-traveller evaluates each proposal (accept / counter) via
the persona prompt in ali/generation/proposal_evaluator.py. Both sides
see live state — the activity_log feeds the "what they're doing"
indicator in the UI.

Endpoints:
    POST /api/shared/{itinerary_id}/init     bootstrap from the base
                                              itinerary + session
    GET  /api/shared/{itinerary_id}          full current state
    POST /api/shared/{itinerary_id}/propose  user proposes; persona
                                              auto-responds in the
                                              same response
    POST /api/shared/{itinerary_id}/respond  user accepts/counters a
                                              persona proposal

Persistence is Firestore-backed via firestore.write_shared_itinerary;
version is incremented on every write for optimistic locking. WS
broadcasts piggyback the existing chat session WS — both sides are
already connected there post-approval.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ali.generation.proposal_evaluator import evaluate_proposal
from mushahid.auth import verify_token
from mushahid.realtime.firestore import (
    get_chat_session, get_itinerary, get_shared_itinerary,
    write_shared_itinerary,
)
from mushahid.utils.sanitize import sanitize_user_input
from shared.schemas import (
    Activity, ActivityLogEntry, ChatSession, Itinerary, ItineraryActivity,
    ItineraryDay, ProposedChange, SharedItinerary,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _assert_participant(shared: SharedItinerary, uid: str) -> None:
    if uid not in (shared.user_ids or []):
        raise HTTPException(status_code=403, detail="Not a participant in this itinerary")


def _broadcast_async(session_id: str | None, payload: dict) -> None:
    """Best-effort WS broadcast over the chat session both sides joined
    during the chat phase. The shared-itinerary screen connects to the
    same WS so updates land. Failures are swallowed — the GET endpoint
    is the source-of-truth fallback."""
    if not session_id:
        return
    try:
        from shreyas.cotraveller.chat import manager
        asyncio.create_task(manager.broadcast_to_session(session_id, payload))
    except Exception as e:
        logger.debug("shared broadcast failed for %s: %s", session_id, e)


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _all_existing_titles(itin: Itinerary) -> list[str]:
    out: list[str] = []
    for day in itin.days or []:
        for ia in day.activities or []:
            name = getattr(getattr(ia, "activity", None), "name", "") or ""
            if name:
                out.append(name.strip())
    return out


def _accepted_titles(changes: list[ProposedChange]) -> list[str]:
    return [c.title for c in changes if c.status == "accepted" and c.title]


def _rejected_titles(changes: list[ProposedChange]) -> list[str]:
    return [c.title for c in changes if c.status == "countered" and c.title]


def _is_duplicate(title: str, *, existing: list[str], accepted: list[str], rejected: list[str]) -> bool:
    """Substring-match against committed activities + decision history.
    Loose match so 'ramen at Ichiran' collides with 'Ichiran ramen'."""
    if not title:
        return True
    t = _normalize(title)
    if not t:
        return True
    for other in existing + accepted + rejected:
        o = _normalize(other)
        if not o:
            continue
        if t == o or t in o or o in t:
            return True
    return False


def _make_proposed_activity(title: str) -> Activity:
    return Activity(
        activity_id=_new_id("act"),
        name=title,
        category="proposed",
        cost_usd=0.0,
        duration_hours=2.0,
        tags=["proposed"],
    )


def _apply_add(itin: Itinerary, day_number: int, title: str) -> Itinerary:
    """Append a new ItineraryActivity to the given day. If day_number is
    out of range, append to the last day rather than failing the
    negotiation flow."""
    days = list(itin.days or [])
    if not days:
        return itin
    target_idx = None
    for i, d in enumerate(days):
        if d.day_number == day_number:
            target_idx = i
            break
    if target_idx is None:
        target_idx = len(days) - 1
    day = days[target_idx]
    new_acts = list(day.activities or [])
    new_acts.append(ItineraryActivity(
        activity=_make_proposed_activity(title),
        time="TBD",
        why_this="Added during shared itinerary negotiation.",
    ))
    days[target_idx] = day.model_copy(update={"activities": new_acts})
    return itin.model_copy(update={"days": days})


def _apply_change(itin: Itinerary, change: ProposedChange) -> Itinerary:
    """Apply an accepted change to the base itinerary. v1 supports add;
    move + replace fall through as no-ops with a log line so we know."""
    if change.kind == "add":
        return _apply_add(itin, change.day_number, change.title)
    logger.info("shared: change kind=%s not yet implemented, skipping apply", change.kind)
    return itin


async def _load_or_bootstrap(itinerary_id: str, uid: str) -> tuple[SharedItinerary, ChatSession | None]:
    """Load the SharedItinerary, bootstrapping it from the base itinerary
    + the user's chat session if no shared doc exists yet."""
    shared = await get_shared_itinerary(itinerary_id)
    if shared:
        return shared, None

    base = await get_itinerary(itinerary_id)
    if base is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    # Find a chat session linking this user to a persona for this trip.
    # We need both user_ids to seed the shared doc. The chat session has
    # them and is created at /chat/start.
    session = await _find_session(itinerary_id, uid)
    if session is None:
        raise HTTPException(
            status_code=409,
            detail="No chat session for this itinerary — start a chat + approve the match first",
        )

    shared = SharedItinerary(
        itinerary_id=itinerary_id,
        user_ids=[session.user_id, session.profile_id],
        itinerary=base,
        notes=[],
        version=0,
    )
    shared.activity_log.append(ActivityLogEntry(
        entry_id=_new_id("act"),
        actor_id="system",
        kind="joined",
        title="",
        day_number=None,
        created_at=_now_iso(),
    ))
    await write_shared_itinerary(shared)
    return shared, session


async def _find_session(itinerary_id: str, uid: str) -> ChatSession | None:
    """Find the chat session that links uid + a persona for this itin.
    Firestore index assumed on (user_id, itinerary_id). Falls back to
    None when no session exists."""
    try:
        from mushahid.realtime.firestore import get_db
        from shared.config import LOCAL_MODE
        if LOCAL_MODE:
            # In-memory chat-sessions are imported lazily to avoid the
            # circular dep; routes/chat owns the _sessions dict.
            from mushahid.routes.chat import _sessions
            for s_meta in _sessions.values():
                s = s_meta["session"]
                if getattr(s, "itinerary_id", None) == itinerary_id and uid in (s.user_id, s.profile_id):
                    return s
            return None
        docs = await asyncio.to_thread(
            lambda: list(
                get_db().collection("chat_sessions")
                .where("itinerary_id", "==", itinerary_id)
                .limit(5).stream()
            )
        )
        for d in docs:
            data = d.to_dict() or {}
            if uid in (data.get("user_id"), data.get("profile_id")):
                return ChatSession(**{k: v for k, v in data.items() if k != "messages"})
        return None
    except Exception as e:
        logger.warning("_find_session failed for %s/%s: %s", itinerary_id, uid, e)
        return None


# ── Request models ────────────────────────────────────────────────────────


class ProposeRequest(BaseModel):
    kind:        str = "add"           # "add" only in v1
    day_number:  int
    title:       str = Field(..., min_length=1, max_length=140)
    message:     str = Field(default="", max_length=400)
    version:     int


class RespondRequest(BaseModel):
    change_id:  str
    decision:   str                     # "accept" | "counter"
    title:      str | None = None       # required when decision="counter"
    message:    str = ""
    version:    int


# ── Routes ────────────────────────────────────────────────────────────────


@router.get("/shared/{itinerary_id}")
async def get_state(itinerary_id: str, uid: str = Depends(verify_token)):
    """Return the full SharedItinerary. Bootstraps on first read so the
    frontend can render immediately after the approval step without a
    separate init call."""
    shared, _ = await _load_or_bootstrap(itinerary_id, uid)
    _assert_participant(shared, uid)
    return shared.model_dump(mode="json")


@router.post("/shared/{itinerary_id}/propose")
async def propose(itinerary_id: str, body: ProposeRequest, uid: str = Depends(verify_token)):
    """User proposes a change. Persona evaluates synchronously and either:
      - accepts → change committed to itinerary
      - counters → user's change marked countered, persona's counter
                   becomes a new pending proposal the user must respond to

    The full updated SharedItinerary is returned so the frontend can
    render without re-fetching. An "evaluating" activity log entry is
    pushed before the LLM call so the UI can show "they're thinking..."
    in real time via the WS broadcast.
    """
    shared, session = await _load_or_bootstrap(itinerary_id, uid)
    _assert_participant(shared, uid)
    if body.version != shared.version:
        raise HTTPException(status_code=409, detail={"error": "version conflict", "current_version": shared.version})
    if body.kind not in ("add",):
        raise HTTPException(status_code=400, detail=f"Unsupported change kind: {body.kind}")

    title   = sanitize_user_input(body.title)[:140].strip()
    message = sanitize_user_input(body.message)[:400].strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is empty after sanitisation")

    # Resolve the persona for evaluation.
    profile_id = next((u for u in (shared.user_ids or []) if u != uid), None)
    if not session:
        session = await _find_session(itinerary_id, uid)

    # User proposal as a ProposedChange.
    user_change = ProposedChange(
        change_id=_new_id("chg"),
        proposer_id=uid,
        kind=body.kind,
        day_number=body.day_number,
        title=title,
        message=message,
        status="proposed",
        created_at=_now_iso(),
    )
    shared.proposed_changes.append(user_change)
    shared.activity_log.append(ActivityLogEntry(
        entry_id=_new_id("act"), actor_id=uid, kind="proposed",
        title=title, day_number=body.day_number, created_at=_now_iso(),
    ))
    # Mark "they're thinking" so the other side sees a live indicator
    # before the LLM call returns.
    if profile_id:
        shared.activity_log.append(ActivityLogEntry(
            entry_id=_new_id("act"), actor_id=profile_id, kind="evaluating",
            title=title, day_number=body.day_number, created_at=_now_iso(),
        ))
    shared.version += 1
    shared.last_updated_by = uid
    await write_shared_itinerary(shared)
    _broadcast_async(session.session_id if session else None, {
        "type": "shared_proposed", "version": shared.version,
        "change_id": user_change.change_id, "actor_id": uid,
    })

    # Evaluate via persona LLM.
    persona_change: ProposedChange | None = None
    persona_message = ""
    persona_decision = "accept"
    if profile_id:
        try:
            from shreyas.retrieval.search import get_cotraveller_by_id
            candidate = await get_cotraveller_by_id(profile_id)
        except Exception as e:
            logger.warning("shared propose: get_cotraveller_by_id failed: %s", e)
            candidate = None

        existing_titles  = _all_existing_titles(shared.itinerary)
        accepted_titles  = _accepted_titles(shared.proposed_changes)
        rejected_titles  = _rejected_titles(shared.proposed_changes)
        history_payload  = [c.model_dump() for c in shared.proposed_changes[-8:]]
        proposal_payload = user_change.model_dump()
        itin_state       = shared.itinerary.model_dump(mode="json")

        if candidate is not None:
            try:
                verdict = await evaluate_proposal(
                    candidate, itin_state, proposal_payload, history_payload,
                    accepted_titles, rejected_titles,
                )
            except Exception as e:
                logger.warning("shared propose: evaluate_proposal failed: %s", e)
                verdict = {"decision": "accept", "message": "yeah works for me.", "counterproposal_title": None}
        else:
            verdict = {"decision": "accept", "message": "sure, let's do it.", "counterproposal_title": None}

        persona_decision = verdict["decision"]
        persona_message  = verdict["message"]
        counter_title    = verdict["counterproposal_title"]

        # Backend dedupe — overrides the model if it tried to counter
        # with something already on the table.
        if persona_decision == "counter" and counter_title:
            if _is_duplicate(counter_title, existing=existing_titles,
                             accepted=accepted_titles, rejected=rejected_titles):
                logger.info("shared propose: counter '%s' was duplicate, flipping to accept", counter_title)
                persona_decision = "accept"
                counter_title = None
                persona_message = persona_message or "yeah okay, let's go with yours."

        # Update the user's proposal status and (when accepting) commit
        # the change to the itinerary.
        if persona_decision == "accept":
            user_change.status = "accepted"
            shared.itinerary = _apply_change(shared.itinerary, user_change)
            shared.activity_log.append(ActivityLogEntry(
                entry_id=_new_id("act"), actor_id=profile_id, kind="accepted",
                title=user_change.title, day_number=user_change.day_number,
                created_at=_now_iso(),
            ))
        else:
            user_change.status = "countered"
            persona_change = ProposedChange(
                change_id=_new_id("chg"),
                proposer_id=profile_id,
                kind="add",
                day_number=user_change.day_number,
                title=counter_title or "",
                message=persona_message,
                counter_to_id=user_change.change_id,
                status="proposed",
                created_at=_now_iso(),
            )
            shared.proposed_changes.append(persona_change)
            shared.activity_log.append(ActivityLogEntry(
                entry_id=_new_id("act"), actor_id=profile_id, kind="countered",
                title=counter_title or "", day_number=user_change.day_number,
                created_at=_now_iso(),
            ))

    shared.version += 1
    shared.last_updated_by = profile_id or uid
    await write_shared_itinerary(shared)
    _broadcast_async(session.session_id if session else None, {
        "type": "shared_responded", "version": shared.version,
        "decision": persona_decision,
        "change_id": (persona_change.change_id if persona_change else user_change.change_id),
        "actor_id":  profile_id,
    })

    return {
        "shared":       shared.model_dump(mode="json"),
        "decision":     persona_decision,
        "message":      persona_message,
        "user_change":  user_change.model_dump(),
        "counter":      persona_change.model_dump() if persona_change else None,
    }


@router.post("/shared/{itinerary_id}/respond")
async def respond(itinerary_id: str, body: RespondRequest, uid: str = Depends(verify_token)):
    """User accepts or counters a persona's counterproposal. Accepting
    commits the persona's change. Countering opens a fresh user-side
    proposal that the persona will evaluate (same as POST /propose)."""
    shared, session = await _load_or_bootstrap(itinerary_id, uid)
    _assert_participant(shared, uid)
    if body.version != shared.version:
        raise HTTPException(status_code=409, detail={"error": "version conflict", "current_version": shared.version})
    if body.decision not in ("accept", "counter"):
        raise HTTPException(status_code=400, detail="decision must be 'accept' or 'counter'")

    target = next((c for c in shared.proposed_changes if c.change_id == body.change_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="change_id not found")
    if target.status != "proposed":
        raise HTTPException(status_code=409, detail=f"change is {target.status}, not open for response")
    if target.proposer_id == uid:
        raise HTTPException(status_code=400, detail="cannot respond to your own proposal")

    if body.decision == "accept":
        target.status = "accepted"
        shared.itinerary = _apply_change(shared.itinerary, target)
        shared.activity_log.append(ActivityLogEntry(
            entry_id=_new_id("act"), actor_id=uid, kind="accepted",
            title=target.title, day_number=target.day_number,
            created_at=_now_iso(),
        ))
    else:
        title   = sanitize_user_input(body.title or "")[:140].strip()
        message = sanitize_user_input(body.message)[:400].strip()
        if not title:
            raise HTTPException(status_code=400, detail="counter requires a title")
        existing_titles = _all_existing_titles(shared.itinerary)
        accepted_titles = _accepted_titles(shared.proposed_changes)
        rejected_titles = _rejected_titles(shared.proposed_changes)
        if _is_duplicate(title, existing=existing_titles,
                         accepted=accepted_titles, rejected=rejected_titles):
            raise HTTPException(status_code=409, detail=f"'{title}' is already on the itinerary or has been considered")

        target.status = "countered"
        user_change = ProposedChange(
            change_id=_new_id("chg"),
            proposer_id=uid,
            kind="add",
            day_number=target.day_number,
            title=title,
            message=message,
            counter_to_id=target.change_id,
            status="proposed",
            created_at=_now_iso(),
        )
        shared.proposed_changes.append(user_change)
        shared.activity_log.append(ActivityLogEntry(
            entry_id=_new_id("act"), actor_id=uid, kind="countered",
            title=title, day_number=target.day_number,
            created_at=_now_iso(),
        ))

    shared.version += 1
    shared.last_updated_by = uid
    await write_shared_itinerary(shared)
    _broadcast_async(session.session_id if session else None, {
        "type": "shared_responded", "version": shared.version,
        "decision": body.decision,
        "change_id": body.change_id,
        "actor_id":  uid,
    })
    return {"shared": shared.model_dump(mode="json")}
