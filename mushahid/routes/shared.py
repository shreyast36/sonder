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


# Connective words that carry no information about *which* activity is
# being proposed. Stripped before token comparison so "ramen at Ichiran"
# vs "Ichiran ramen" collide cleanly but "Ippudo ramen" doesn't.
_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "at", "in", "on", "by", "to", "for", "from", "with",
    "of", "and", "or", "near", "around", "via", "&", "+",
    "stop", "visit", "go", "doing", "trip", "tour",
})

# Token-Jaccard threshold above which two titles are considered the same
# activity. 0.6 is the empirical sweet spot:
#   "ramen at Ichiran" ↔ "Ichiran ramen"   → 1.0 ✓ dupe
#   "Ichiran ramen"    ↔ "Ippudo ramen"    → 0.33 ✓ distinct
#   "Senso-ji temple"  ↔ "Senso ji temple" → 1.0 ✓ dupe (punct stripped)
_DUPE_THRESHOLD = 0.6


def _tokens(title: str) -> set[str]:
    """Lowercase, strip punctuation, split on whitespace, drop stopwords.
    Empty set when the title is unusable — caller treats that as a dupe
    so we don't ship empty counters."""
    if not title:
        return set()
    import re
    cleaned = re.sub(r"[^a-z0-9\s]+", " ", title.lower())
    parts   = cleaned.split()
    return {p for p in parts if p and p not in _STOPWORDS and len(p) > 1}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


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


def _is_finalized(shared: SharedItinerary) -> bool:
    """Was a `finalized` entry ever appended to this itinerary's activity
    log? v1 stores the lock state as a log entry rather than a dedicated
    field; the latest such entry being present is the canonical signal."""
    return any(e.kind == "finalized" for e in (shared.activity_log or []))


def _is_duplicate(title: str, *, existing: list[str], accepted: list[str], rejected: list[str]) -> bool:
    """Token-Jaccard match against committed activities + decision
    history. "ramen at Ichiran" and "Ichiran ramen" collide (J=1.0);
    "Ichiran ramen" and "Ippudo ramen" don't (J=0.33). Threshold
    tuned at _DUPE_THRESHOLD."""
    if not title:
        return True
    my_tokens = _tokens(title)
    if not my_tokens:
        # Stopword-only titles (e.g. "the stop") collapse to empty —
        # treat as dupe so we don't ship vacuous counters.
        return True
    for other in existing + accepted + rejected:
        other_tokens = _tokens(other)
        if not other_tokens:
            continue
        if _jaccard(my_tokens, other_tokens) >= _DUPE_THRESHOLD:
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
        description=title,
    )


def _find_activity(itin: Itinerary, activity_id: str) -> tuple[int, int] | None:
    """Locate an activity by id. Returns (day_idx, activity_idx) or None."""
    if not activity_id:
        return None
    for di, day in enumerate(itin.days or []):
        for ai, ia in enumerate(day.activities or []):
            if getattr(getattr(ia, "activity", None), "activity_id", None) == activity_id:
                return di, ai
    return None


def _apply_add(itin: Itinerary, day_number: int, title: str) -> Itinerary:
    """Append a new ItineraryActivity to the given day. If day_number is
    out of range, append to the last day rather than failing the
    negotiation flow."""
    days = list(itin.days or [])
    if not days:
        return itin
    target_idx = next((i for i, d in enumerate(days) if d.day_number == day_number), None)
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


def _apply_replace(itin: Itinerary, replaces_activity_id: str, title: str) -> Itinerary:
    """Swap the activity identified by `replaces_activity_id` for a new
    one with `title`, keeping the same day + time slot. If the target
    activity doesn't exist, the change degrades to an add on the
    requested change's day (handled by caller)."""
    located = _find_activity(itin, replaces_activity_id)
    if located is None:
        return itin
    di, ai = located
    days = list(itin.days or [])
    day  = days[di]
    new_acts = list(day.activities or [])
    old_ia = new_acts[ai]
    new_ia = ItineraryActivity(
        activity=_make_proposed_activity(title),
        time=getattr(old_ia, "time", "TBD") or "TBD",
        why_this="Replaced during shared itinerary negotiation.",
    )
    new_acts[ai] = new_ia
    days[di] = day.model_copy(update={"activities": new_acts})
    return itin.model_copy(update={"days": days})


def _apply_move(itin: Itinerary, replaces_activity_id: str, target_day_number: int) -> Itinerary:
    """Move an existing activity to a different day, preserving its
    Activity object (so we don't lose category/cost/tags). No-op if the
    activity doesn't exist or the target day matches the current day."""
    located = _find_activity(itin, replaces_activity_id)
    if located is None:
        return itin
    di, ai = located
    days = list(itin.days or [])
    if days[di].day_number == target_day_number:
        return itin
    target_di = next((i for i, d in enumerate(days) if d.day_number == target_day_number), None)
    if target_di is None:
        return itin
    moved = days[di].activities[ai]
    src_acts = list(days[di].activities or [])
    src_acts.pop(ai)
    days[di] = days[di].model_copy(update={"activities": src_acts})
    dst_acts = list(days[target_di].activities or [])
    dst_acts.append(moved.model_copy(update={
        "why_this": "Rescheduled during shared itinerary negotiation.",
    }))
    days[target_di] = days[target_di].model_copy(update={"activities": dst_acts})
    return itin.model_copy(update={"days": days})


def _apply_change(itin: Itinerary, change: ProposedChange) -> Itinerary:
    """Commit an accepted change to the base itinerary. Supports all
    three v1 kinds. Replace/move silently no-op when their target
    activity_id can't be resolved — the caller already accepted the
    decision so failing loudly here would feel worse than degrading."""
    if change.kind == "add":
        return _apply_add(itin, change.day_number, change.title)
    if change.kind == "replace":
        return _apply_replace(itin, change.replaces_activity_id or "", change.title)
    if change.kind == "move":
        return _apply_move(itin, change.replaces_activity_id or "", change.day_number)
    logger.info("shared: unknown change kind=%s, skipping apply", change.kind)
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
    kind:        str = "add"                          # "add" | "replace" | "move"
    day_number:  int
    title:       str = Field(default="", max_length=140)  # required for add/replace
    message:     str = Field(default="", max_length=400)
    replaces_activity_id: str | None = None           # required for replace/move
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
    if _is_finalized(shared):
        raise HTTPException(status_code=409, detail="itinerary is finalised — no more changes")
    if body.kind not in ("add", "replace", "move"):
        raise HTTPException(status_code=400, detail=f"Unsupported change kind: {body.kind}")

    title   = sanitize_user_input(body.title or "")[:140].strip()
    message = sanitize_user_input(body.message)[:400].strip()
    # add/replace need a title; move only repositions an existing
    # activity and doesn't carry a new title.
    if body.kind in ("add", "replace") and not title:
        raise HTTPException(status_code=400, detail="title is required for add/replace")
    if body.kind in ("replace", "move") and not body.replaces_activity_id:
        raise HTTPException(status_code=400, detail="replaces_activity_id is required for replace/move")

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
        replaces_activity_id=body.replaces_activity_id,
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

    # Evaluation runs off the request path — frontend already sees the
    # user's proposal and the "evaluating" entry, polls/WS picks up the
    # verdict when the background task writes it back.
    if profile_id:
        asyncio.create_task(_evaluate_proposal_async(
            itinerary_id=itinerary_id,
            uid=uid,
            profile_id=profile_id,
            user_change_id=user_change.change_id,
            session_id=session.session_id if session else None,
        ))

    return {
        "shared":       shared.model_dump(mode="json"),
        "decision":     "pending",
        "message":      "",
        "user_change":  user_change.model_dump(),
        "counter":      None,
    }


async def _evaluate_proposal_async(
    *, itinerary_id: str, uid: str, profile_id: str,
    user_change_id: str, session_id: str | None,
) -> None:
    """Background persona evaluation for a user proposal. Re-reads the
    SharedItinerary (state may have moved since the request returned),
    runs evaluate_proposal, applies the verdict, writes + broadcasts.
    Failures are logged and dropped — the user's proposal still stands
    as pending, and the frontend will retry via the next poll."""
    try:
        shared = await get_shared_itinerary(itinerary_id)
        if shared is None:
            return
        user_change = next((c for c in shared.proposed_changes if c.change_id == user_change_id), None)
        if user_change is None or user_change.status != "proposed":
            return

        try:
            from shreyas.retrieval.search import get_cotraveller_by_id
            candidate = await get_cotraveller_by_id(profile_id)
        except Exception as e:
            logger.warning("shared propose bg: get_cotraveller_by_id failed: %s", e)
            candidate = None

        try:
            from mushahid.routes.cotraveller import _load_user_profile
            viewer = await _load_user_profile(uid, itinerary_id)
        except Exception as e:
            logger.warning("shared propose bg: _load_user_profile failed: %s", e)
            viewer = None

        existing_titles  = _all_existing_titles(shared.itinerary)
        accepted_titles  = _accepted_titles(shared.proposed_changes)
        rejected_titles  = _rejected_titles(shared.proposed_changes)
        history_payload  = [c.model_dump() for c in shared.proposed_changes[-8:]]
        proposal_payload = user_change.model_dump()
        itin_state       = shared.itinerary.model_dump(mode="json")

        if candidate is not None:
            try:
                verdict = await evaluate_proposal(
                    candidate, viewer, itin_state, proposal_payload, history_payload,
                    accepted_titles, rejected_titles,
                )
            except Exception as e:
                logger.warning("shared propose bg: evaluate_proposal failed: %s", e)
                verdict = {"decision": "accept", "message": "yeah works for me.", "counterproposal_title": None}
        else:
            verdict = {"decision": "accept", "message": "sure, let's do it.", "counterproposal_title": None}

        persona_decision = verdict["decision"]
        persona_message  = verdict["message"]
        counter_title    = verdict["counterproposal_title"]

        if persona_decision == "counter" and counter_title:
            if _is_duplicate(counter_title, existing=existing_titles,
                             accepted=accepted_titles, rejected=rejected_titles):
                logger.info("shared propose bg: counter '%s' was duplicate, flipping to accept", counter_title)
                persona_decision = "accept"
                counter_title = None
                persona_message = persona_message or "yeah okay, let's go with yours."

        persona_change: ProposedChange | None = None
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
        shared.last_updated_by = profile_id
        await write_shared_itinerary(shared)
        _broadcast_async(session_id, {
            "type": "shared_responded", "version": shared.version,
            "decision": persona_decision,
            "change_id": (persona_change.change_id if persona_change else user_change.change_id),
            "actor_id":  profile_id,
        })
    except Exception as e:
        logger.warning("shared propose bg: top-level failure for %s: %s", itinerary_id, e)


@router.post("/shared/{itinerary_id}/respond")
async def respond(itinerary_id: str, body: RespondRequest, uid: str = Depends(verify_token)):
    """User accepts or counters a persona's counterproposal. Accepting
    commits the persona's change. Countering opens a fresh user-side
    proposal that the persona will evaluate (same as POST /propose)."""
    shared, session = await _load_or_bootstrap(itinerary_id, uid)
    _assert_participant(shared, uid)
    if body.version != shared.version:
        raise HTTPException(status_code=409, detail={"error": "version conflict", "current_version": shared.version})
    if _is_finalized(shared):
        raise HTTPException(status_code=409, detail="itinerary is finalised — no more changes")
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


# ── Withdraw ──────────────────────────────────────────────────────────────


class WithdrawRequest(BaseModel):
    change_id: str
    version:   int


@router.post("/shared/{itinerary_id}/withdraw")
async def withdraw(itinerary_id: str, body: WithdrawRequest, uid: str = Depends(verify_token)):
    """Proposer retracts their own pending proposal. Idempotent — calling
    on a non-pending change returns 409 with current status so the
    frontend can refresh."""
    shared, session = await _load_or_bootstrap(itinerary_id, uid)
    _assert_participant(shared, uid)
    if body.version != shared.version:
        raise HTTPException(status_code=409, detail={"error": "version conflict", "current_version": shared.version})
    if _is_finalized(shared):
        raise HTTPException(status_code=409, detail="itinerary is finalised — no more changes")

    target = next((c for c in shared.proposed_changes if c.change_id == body.change_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="change_id not found")
    if target.proposer_id != uid:
        raise HTTPException(status_code=403, detail="can only withdraw your own proposals")
    if target.status != "proposed":
        raise HTTPException(status_code=409, detail=f"change is {target.status}, not open for withdrawal")

    target.status = "withdrawn"
    shared.activity_log.append(ActivityLogEntry(
        entry_id=_new_id("act"), actor_id=uid, kind="withdrawn",
        title=target.title, day_number=target.day_number,
        created_at=_now_iso(),
    ))
    shared.version += 1
    shared.last_updated_by = uid
    await write_shared_itinerary(shared)
    _broadcast_async(session.session_id if session else None, {
        "type": "shared_withdrawn", "version": shared.version,
        "change_id": body.change_id, "actor_id": uid,
    })
    return {"shared": shared.model_dump(mode="json")}


# ── Persona-initiated suggestion ──────────────────────────────────────────


class SuggestRequest(BaseModel):
    version: int


@router.post("/shared/{itinerary_id}/persona-suggest")
async def persona_suggest(itinerary_id: str, body: SuggestRequest, uid: str = Depends(verify_token)):
    """Ask the synthetic persona to spontaneously propose ONE improvement.
    The persona's suggestion is added as a pending ProposedChange the
    user can then accept or counter — same flow as a user-initiated
    proposal, just authored by the other side."""
    from ali.generation.proposal_evaluator import suggest_proposal

    shared, session = await _load_or_bootstrap(itinerary_id, uid)
    _assert_participant(shared, uid)
    if body.version != shared.version:
        raise HTTPException(status_code=409, detail={"error": "version conflict", "current_version": shared.version})
    if _is_finalized(shared):
        raise HTTPException(status_code=409, detail="itinerary is finalised — no more changes")

    profile_id = next((u for u in (shared.user_ids or []) if u != uid), None)
    if not profile_id:
        raise HTTPException(status_code=409, detail="no synthetic counterpart on this itinerary")

    # Push an "evaluating" entry + return immediately so the UI shows
    # the persona working on it. The actual LLM call runs in the
    # background; polling/WS pick up the suggested change when it
    # lands. eval_entry_id is passed through so the background task
    # can drop it on the no-result paths instead of leaving an
    # orphaned "is reviewing" row in the feed.
    eval_entry_id = _new_id("act")
    shared.activity_log.append(ActivityLogEntry(
        entry_id=eval_entry_id, actor_id=profile_id, kind="evaluating",
        title="", day_number=None, created_at=_now_iso(),
    ))
    shared.version += 1
    await write_shared_itinerary(shared)
    _broadcast_async(session.session_id if session else None, {
        "type": "shared_suggesting", "version": shared.version, "actor_id": profile_id,
    })

    asyncio.create_task(_persona_suggest_async(
        itinerary_id=itinerary_id,
        uid=uid,
        profile_id=profile_id,
        eval_entry_id=eval_entry_id,
        session_id=session.session_id if session else None,
    ))

    return {"shared": shared.model_dump(mode="json"), "suggested": None}


async def _persona_suggest_async(
    *, itinerary_id: str, uid: str, profile_id: str,
    eval_entry_id: str, session_id: str | None,
) -> None:
    """Background persona-initiated suggestion. Same shape as the
    request-path version, but runs after we've already returned. On
    the no-result paths the evaluating entry is dropped so the feed
    doesn't show "is reviewing" forever."""
    from ali.generation.proposal_evaluator import suggest_proposal
    try:
        shared = await get_shared_itinerary(itinerary_id)
        if shared is None:
            return

        def _drop_evaluating():
            shared.activity_log[:] = [e for e in shared.activity_log if e.entry_id != eval_entry_id]

        try:
            from shreyas.retrieval.search import get_cotraveller_by_id
            candidate = await get_cotraveller_by_id(profile_id)
        except Exception as e:
            logger.warning("persona_suggest bg: get_cotraveller_by_id failed: %s", e)
            candidate = None

        existing_titles = _all_existing_titles(shared.itinerary)
        accepted_titles = _accepted_titles(shared.proposed_changes)
        rejected_titles = _rejected_titles(shared.proposed_changes)
        history_payload = [c.model_dump() for c in shared.proposed_changes[-8:]]
        itin_state      = shared.itinerary.model_dump(mode="json")

        try:
            from mushahid.routes.cotraveller import _load_user_profile
            viewer = await _load_user_profile(uid, itinerary_id)
        except Exception as e:
            logger.warning("persona_suggest bg: _load_user_profile failed: %s", e)
            viewer = None

        suggestion: dict | None = None
        if candidate is not None:
            try:
                suggestion = await suggest_proposal(
                    candidate, viewer, itin_state, history_payload,
                    accepted_titles, rejected_titles,
                )
            except Exception as e:
                logger.warning("persona_suggest bg: suggest_proposal failed: %s", e)
                suggestion = None

        if suggestion is None or not suggestion.get("title"):
            _drop_evaluating()
            shared.version += 1
            await write_shared_itinerary(shared)
            _broadcast_async(session_id, {
                "type": "shared_responded", "version": shared.version,
                "decision": "no_suggestion", "actor_id": profile_id,
            })
            return

        title = suggestion["title"][:140]
        if _is_duplicate(title, existing=existing_titles,
                         accepted=accepted_titles, rejected=rejected_titles):
            logger.info("persona_suggest bg: model returned duplicate '%s', dropping", title)
            _drop_evaluating()
            shared.version += 1
            await write_shared_itinerary(shared)
            _broadcast_async(session_id, {
                "type": "shared_responded", "version": shared.version,
                "decision": "no_suggestion", "actor_id": profile_id,
            })
            return

        day_number = max(1, min(int(suggestion.get("day_number") or 1), len(shared.itinerary.days or []) or 1))
        persona_change = ProposedChange(
            change_id=_new_id("chg"),
            proposer_id=profile_id,
            kind="add",
            day_number=day_number,
            title=title,
            message=(suggestion.get("message") or "")[:400],
            status="proposed",
            created_at=_now_iso(),
        )
        shared.proposed_changes.append(persona_change)
        # Drop the evaluating entry now that the persona has resolved into
        # a concrete proposal — the "proposed" entry below replaces it.
        _drop_evaluating()
        shared.activity_log.append(ActivityLogEntry(
            entry_id=_new_id("act"), actor_id=profile_id, kind="proposed",
            title=title, day_number=day_number, created_at=_now_iso(),
        ))
        shared.version += 1
        shared.last_updated_by = profile_id
        await write_shared_itinerary(shared)
        _broadcast_async(session_id, {
            "type": "shared_proposed", "version": shared.version,
            "change_id": persona_change.change_id, "actor_id": profile_id,
        })
    except Exception as e:
        logger.warning("persona_suggest bg: top-level failure for %s: %s", itinerary_id, e)


# ── Finalize ──────────────────────────────────────────────────────────────


class FinalizeRequest(BaseModel):
    version: int


@router.post("/shared/{itinerary_id}/finalize")
async def finalize(itinerary_id: str, body: FinalizeRequest, uid: str = Depends(verify_token)):
    """Lock the itinerary in. After both sides finalize (or one side
    finalizes and the other doesn't object within the session), no more
    propose/respond/withdraw is allowed. v1 implementation: any
    participant can flip the lock; the other side's UI just shows the
    final state."""
    shared, session = await _load_or_bootstrap(itinerary_id, uid)
    _assert_participant(shared, uid)
    if body.version != shared.version:
        raise HTTPException(status_code=409, detail={"error": "version conflict", "current_version": shared.version})

    open_changes = [c for c in shared.proposed_changes if c.status == "proposed"]
    if open_changes:
        raise HTTPException(
            status_code=409,
            detail=f"{len(open_changes)} change(s) still pending — resolve or withdraw before finalising",
        )

    # Record finalisation in the activity log; no dedicated field on the
    # schema yet (kept v1 minimal). The frontend reads the trailing
    # "finalized" entry to decide whether to lock the input surfaces.
    shared.activity_log.append(ActivityLogEntry(
        entry_id=_new_id("act"), actor_id=uid, kind="finalized",
        title="", day_number=None, created_at=_now_iso(),
    ))
    shared.version += 1
    shared.last_updated_by = uid
    await write_shared_itinerary(shared)
    _broadcast_async(session.session_id if session else None, {
        "type": "shared_finalized", "version": shared.version, "actor_id": uid,
    })
    return {"shared": shared.model_dump(mode="json")}
