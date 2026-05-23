import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from shared.schemas import ChatSession, ChatStartResponse, ApprovalStatus
from mushahid.auth import verify_token, verify_token_string
from mushahid.utils.sanitize import sanitize_user_input
from mushahid.realtime.firestore import (
    write_chat_session, append_chat_message, get_chat_session,
    list_chat_messages, get_presence,
)
from shreyas.cotraveller.chat import manager
from shreyas.cotraveller.presence import set_online, set_offline, is_online

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory session store; mirrors Firestore for the WS hot path.
_sessions: dict = {}

_MAX_WS_MSG_BYTES = 64 * 1024  # 64 KB per message

# Synthetic-user reply pacing — feels human, doesn't melt the LLM bill.
# Frontend clears its typing indicator after 3.5s, so the keepalive task
# re-emits typing every 2s while the LLM is thinking.
#
# Tuned down (was 0.6-1.4 / 0.6-1.2) because the SMALL-tier chat_reply
# call already lands in ~1.5s — adding ~2s of cosmetic delay made the
# whole turn read as 3-5s, which felt sluggish in user testing. The
# new ranges still keep the "they paused before typing" feel without
# stacking unnecessary latency.
_REPLY_BEFORE_TYPING_S  = (0.25, 0.7)   # short pause before the indicator appears
_REPLY_AFTER_REPLY_S    = (0.2,  0.45)  # small pause between LLM finish and broadcast
_TYPING_KEEPALIVE_S     = 2.0


async def _receive_json_checked(websocket: WebSocket) -> dict:
    text = await websocket.receive_text()
    if len(text.encode()) > _MAX_WS_MSG_BYTES:
        await websocket.close(code=1009, reason="Message too large")
        raise WebSocketDisconnect(code=1009)
    return json.loads(text)


class ChatStartRequest(BaseModel):
    profile_id: str
    itinerary_id: str
    # Optional: the match_score the user saw on MatchDetail when they
    # initiated the chat. Persisted on ChatSession so the persona's
    # reciprocal approval can use the same ground-truth number instead
    # of guessing at decision time.
    match_score: float | None = None


@router.post("/chat/start", response_model=ChatStartResponse)
async def start_chat(body: ChatStartRequest, uid: str = Depends(verify_token)):
    from ali.generation.topics import generate_topics, generate_persona_opener
    from shared.schemas import UserProfile, CoTravellerMatch, CoTravellerProfile, Itinerary, Destination
    from shared.schemas import PacePreference, BudgetStyle, TravelStyle
    from mushahid.realtime.firestore import get_user_profile, get_itinerary

    profile_id   = body.profile_id
    itinerary_id = body.itinerary_id

    # Resolve the user's actual display name from their Firestore profile
    # so the persona's opener can address them by name. Falls back to uid
    # if the profile lookup fails — better a placeholder than no greeting.
    user_display_name = uid
    try:
        prof = await get_user_profile(uid)
        if prof:
            name = (prof.get("display_name") or "").strip()
            if name:
                user_display_name = name
    except Exception as e:
        logger.warning("start_chat: get_user_profile(%s) failed: %s", uid, e)

    user_profile = UserProfile(
        user_id=uid, display_name=user_display_name,
        constraints=None, persona_answers=None,
    )

    # Best-effort fetch of the real synthetic profile so the opener has
    # something to anchor on. Fall back to a neutral CoTravellerProfile
    # when Pinecone is unreachable so chat still starts.
    candidate = None
    try:
        from shreyas.retrieval.search import get_cotraveller_by_id
        candidate = await get_cotraveller_by_id(profile_id)
    except Exception as e:
        logger.warning("get_cotraveller_by_id failed for %s: %s", profile_id, e)

    if candidate is None:
        candidate = CoTravellerProfile(
            profile_id=profile_id, display_name=profile_id,
            age=25, location="Unknown", archetype="Explorer",
            interests=[], pace=PacePreference.moderate,
            budget_style=BudgetStyle.mid_range, travel_style=TravelStyle.solo,
        )

    match = CoTravellerMatch(
        profile=candidate,
        match_score=0.85,
        match_reasons=["Similar travel interests"],
        compatibility_breakdown={},
    )

    # Load the real itinerary so the opener can reference the actual
    # destination + planned stops. Fall back to a stub when Firestore is
    # unreachable (chat still works, opener is just less specific).
    real_itinerary: Itinerary | None = None
    trip_destination: str | None = None
    itinerary_digest: str | None = None
    try:
        real_itinerary = await get_itinerary(itinerary_id) if itinerary_id else None
    except Exception as e:
        logger.warning("start_chat: get_itinerary(%s) failed: %s", itinerary_id, e)

    if real_itinerary is not None:
        dest = getattr(real_itinerary, "destination", None)
        city    = (getattr(dest, "city", "") or "").strip() if dest else ""
        country = (getattr(dest, "country", "") or "").strip() if dest else ""
        if city and country:
            trip_destination = f"{city}, {country}"
        elif city:
            trip_destination = city

        days = getattr(real_itinerary, "days", None) or []
        digest_lines: list[str] = []
        for day in days[:5]:
            day_no = getattr(day, "day_number", None) or len(digest_lines) + 1
            activities = getattr(day, "activities", []) or []
            names: list[str] = []
            for act in activities[:3]:
                name = getattr(act, "name", None) or getattr(act, "activity_name", "") or ""
                name = (name or "").strip()
                if name:
                    names.append(name)
            if names:
                digest_lines.append(f"Day {day_no}: {' / '.join(names)}")
        if digest_lines:
            itinerary_digest = "\n".join(digest_lines)

    # If the itinerary didn't load, still pass a stub to generate_topics so
    # it doesn't crash on getattr(itinerary, "destination").
    itinerary_for_topics = real_itinerary or Itinerary(
        itinerary_id=itinerary_id or "", user_id=uid,
        destination=Destination(
            destination_id="dest_stub", city=trip_destination or "Destination", country="",
            avg_daily_cost_usd=100.0, tags=[], description="",
        ),
        days=[], total_budget_usd=0.0,
    )

    opener, topics = await asyncio.gather(
        generate_persona_opener(
            candidate, user_display_name,
            trip_destination=trip_destination,
            itinerary_digest=itinerary_digest,
        ),
        generate_topics(user_profile, match, itinerary_for_topics),
    )

    session_id = str(uuid.uuid4())
    session = ChatSession(
        session_id=session_id,
        user_id=uid,
        profile_id=profile_id,
        itinerary_id=itinerary_id,
        approval_status=ApprovalStatus.pending,
        created_at=datetime.now(timezone.utc).isoformat(),
        match_score=body.match_score,
    )
    _sessions[session_id] = {"session": session, "messages": []}
    await write_chat_session(session)

    # Persist the persona's opener as the first message so it shows up
    # when the user lands on /chat/{session_id}. From the user's POV it
    # looks like the persona texted them first — which is exactly what we
    # want.
    if opener:
        opener_msg = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "sender_id":  profile_id,
            "content":    opener,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }
        try:
            await append_chat_message(session_id, opener_msg)
            _sessions[session_id]["messages"].append(opener_msg)
        except Exception as e:
            logger.warning("start_chat: failed to persist opener for %s: %s", session_id, e)

    from mushahid.monitoring import capture
    capture(uid, "chat_started", {"session_id": session_id, "profile_id": profile_id})

    # `icebreaker` field of the response is now the persona's opener — kept
    # the field name for back-compat with the existing pydantic response
    # model. Frontend ignores it (the message is already in the session
    # history) but consumers that read the field still see meaningful text.
    return ChatStartResponse(session=session, icebreaker=opener, topics=topics)


async def _assert_participant(session_id: str, uid: str) -> None:
    """Raise 403/404 if uid is not a participant."""
    session_data = _sessions.get(session_id)
    if session_data:
        s = session_data["session"]
        if uid not in (s.user_id, s.profile_id):
            raise HTTPException(status_code=403, detail="Not a participant in this session")
        return
    try:
        stored = await get_chat_session(session_id)
    except Exception:
        stored = None
    if stored is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if uid not in (stored.get("user_id"), stored.get("profile_id")):
        raise HTTPException(status_code=403, detail="Not a participant in this session")


async def _load_session_safe(session_id: str) -> dict | None:
    cached = _sessions.get(session_id)
    if cached:
        s = cached["session"]
        return {
            "user_id":      s.user_id,
            "profile_id":   s.profile_id,
            "itinerary_id": getattr(s, "itinerary_id", None),
        }
    try:
        stored = await get_chat_session(session_id)
    except Exception:
        return None
    if stored is None:
        return None
    return {
        "user_id":      stored.get("user_id"),
        "profile_id":   stored.get("profile_id"),
        "itinerary_id": stored.get("itinerary_id"),
    }


@router.get("/chat/session/{session_id}")
async def get_session(session_id: str, uid: str = Depends(verify_token)):
    """Session metadata so the chat page knows its profile_id, status, etc."""
    await _assert_participant(session_id, uid)
    cached = _sessions.get(session_id)
    if cached:
        return cached["session"].model_dump(mode="json")
    stored = await get_chat_session(session_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {k: v for k, v in stored.items() if k != "messages"}


@router.get("/chat/{session_id}/messages")
async def get_messages(session_id: str, uid: str = Depends(verify_token)):
    """Replay history when the chat page mounts (so refresh doesn't lose the thread)."""
    await _assert_participant(session_id, uid)
    msgs = await list_chat_messages(session_id)
    cached = _sessions.get(session_id)
    if cached and not msgs:
        msgs = list(cached.get("messages", []))
    return {"messages": msgs}


@router.get("/chat/{session_id}/presence/{user_id}")
async def get_user_presence(session_id: str, user_id: str, uid: str = Depends(verify_token)):
    """Is the other participant online right now? Boolean + last_seen."""
    await _assert_participant(session_id, uid)
    online = await is_online(user_id)
    doc = await get_presence(user_id) or {}
    return {"user_id": user_id, "online": online, "last_seen": doc.get("last_seen")}


def _derived_status(user_dec: ApprovalStatus, profile_dec: ApprovalStatus) -> ApprovalStatus:
    """Overall session status from the two per-side decisions:
    - either side denied → denied (terminal, deal off)
    - both approved → approved (matched)
    - else → pending (someone still deciding)
    """
    if user_dec == ApprovalStatus.denied or profile_dec == ApprovalStatus.denied:
        return ApprovalStatus.denied
    if user_dec == ApprovalStatus.approved and profile_dec == ApprovalStatus.approved:
        return ApprovalStatus.approved
    return ApprovalStatus.pending


async def _apply_decision(session_id: str, *, side: str, decision: ApprovalStatus) -> ChatSession | None:
    """Mutate the session's decision for one side and recompute the overall
    approval_status. Persists to Firestore and updates the in-memory mirror.
    `side` is "user" or "profile". Returns the updated ChatSession or None
    if the session wasn't found."""
    sess_meta = _sessions.get(session_id)
    if sess_meta:
        current: ChatSession = sess_meta["session"]
    else:
        stored = await get_chat_session(session_id)
        if not stored:
            return None
        current = ChatSession(**{k: v for k, v in stored.items() if k != "messages"})

    user_dec    = current.user_decision
    profile_dec = current.profile_decision
    if side == "user":
        user_dec = decision
    else:
        profile_dec = decision

    updated = current.model_copy(update={
        "user_decision":    user_dec,
        "profile_decision": profile_dec,
        "approval_status":  _derived_status(user_dec, profile_dec),
    })
    if sess_meta:
        sess_meta["session"] = updated
    else:
        _sessions[session_id] = {"session": updated, "messages": []}
    try:
        await write_chat_session(updated)
    except Exception as e:
        logger.warning("approval write_chat_session failed for %s: %s", session_id, e)
    return updated


async def _schedule_persona_decision(session_id: str, profile_id: str) -> None:
    """Simulate the synthetic persona's reciprocal decision. A short
    randomised delay sells the "they're reviewing" UI state; the verdict
    is gated on the match_score the user actually saw on MatchDetail
    (persisted to ChatSession.match_score at /chat/start). When no score
    was passed through, default to approved — personas only surface as
    matches if ranking already liked them."""
    try:
        await asyncio.sleep(random.uniform(2.4, 5.0))

        verdict = ApprovalStatus.approved
        sess_meta = _sessions.get(session_id)
        if sess_meta:
            score = sess_meta["session"].match_score
        else:
            stored = await get_chat_session(session_id)
            score = stored.get("match_score") if stored else None
        # 0.55 floor is calibrated against the cotraveller policy's
        # 6-feature equal-weight scoring — features each in [0,1] mean
        # the typical curated match lands in the 0.55-0.85 band, so
        # this threshold denies the bottom ~15-20% of surfaced matches.
        # See shreyas/ranking/policies/cotraveller.py for the feature set.
        if isinstance(score, (int, float)) and score < 0.55:
            verdict = ApprovalStatus.denied

        updated = await _apply_decision(session_id, side="profile", decision=verdict)
        if updated is None:
            return
        # Push the decision via the existing chat WS so the approval page
        # (if it's listening) flips state in real time. Polling fallback
        # picks it up if no socket is connected.
        try:
            await manager.broadcast_to_session(session_id, {
                "type":             "decision_update",
                "user_decision":    updated.user_decision.value,
                "profile_decision": updated.profile_decision.value,
                "approval_status":  updated.approval_status.value,
            })
        except Exception:
            pass
    except Exception as e:
        logger.warning("persona decision task failed for session=%s: %s", session_id, e)


async def _apply_chat_signals(
    session_id: str,
    session_meta: dict,
    user_id: str,
    message: str,
) -> None:
    """Scan a user message for compatibility cues, update the session's
    live_weights, and refresh match_score by re-ranking the candidate
    against the user with the new weights. Fire-and-forget from the WS
    handler — must never raise. The refreshed score is what the persona's
    reciprocal-approval threshold reads at decision time.
    """
    try:
        from shreyas.cotraveller.chat_signal_scanner import scan_and_apply
        from shreyas.ranking.policies import load_policy
        from shreyas.retrieval.search import get_cotraveller_by_id
        from shreyas.cotraveller.matching import score_compatibility
        from mushahid.realtime.firestore import get_user_profile
        from shared.schemas import UserProfile

        policy = load_policy("cotraveller")

        # Pull current live_weights off the session (in-memory first,
        # Firestore fallback). Default to policy weights when absent.
        sess_meta = _sessions.get(session_id)
        if sess_meta:
            current: ChatSession = sess_meta["session"]
        else:
            stored = await get_chat_session(session_id)
            if not stored:
                return
            current = ChatSession(**{k: v for k, v in stored.items() if k != "messages"})

        new_weights, fired = scan_and_apply(message, current.live_weights, policy)
        if not fired:
            return   # No signals fired — nothing to refresh.

        # Re-rank the candidate against the user with updated weights.
        # The matching engine reads per-user weight overrides from
        # compatibility_signals.ranker_weights[surface] — inject the
        # session weights there as a transient overlay.
        profile_id = current.profile_id
        candidate = await get_cotraveller_by_id(profile_id)
        if candidate is None:
            return

        viewer_doc = await get_user_profile(user_id) or {}
        # Build a UserProfile with the session weights spliced in.
        viewer_signals = dict(viewer_doc.get("compatibility_signals") or {})
        rw = dict(viewer_signals.get("ranker_weights") or {})
        rw["cotraveller"] = new_weights
        viewer_signals["ranker_weights"] = rw
        viewer = UserProfile(
            user_id=user_id,
            display_name=viewer_doc.get("display_name") or "",
            constraints=viewer_doc.get("constraints"),
            persona_answers=viewer_doc.get("persona_answers"),
            compatibility_signals=viewer_signals,
            travel_style_embedding=viewer_doc.get("travel_style_embedding") or [],
        )

        match = score_compatibility(viewer, candidate)
        new_score = float(match.match_score)

        updated = current.model_copy(update={
            "live_weights": new_weights,
            "match_score":  new_score,
        })
        if sess_meta:
            sess_meta["session"] = updated
        else:
            _sessions[session_id] = {"session": updated, "messages": []}
        try:
            await write_chat_session(updated)
        except Exception as e:
            logger.warning("chat signal write_chat_session failed for %s: %s", session_id, e)

        logger.info(
            "chat_signal session=%s fired=%s score=%.3f (was %.3f)",
            session_id, fired, new_score,
            current.match_score if current.match_score is not None else -1.0,
        )
    except Exception as e:
        logger.warning("chat signal scan failed for session=%s: %s", session_id, e)


class DecisionRequest(BaseModel):
    session_id: str


@router.post("/chat/approve")
async def approve_match(body: DecisionRequest, uid: str = Depends(verify_token)):
    session_id = body.session_id
    await _assert_participant(session_id, uid)
    from mushahid.monitoring import capture, EVENT_MATCH_APPROVED
    capture(uid, EVENT_MATCH_APPROVED, {"session_id": session_id})

    updated = await _apply_decision(session_id, side="user", decision=ApprovalStatus.approved)
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Kick off the persona's reciprocal decision in the background so the
    # response returns immediately (frontend goes into "waiting for them"
    # state, then polls / listens for the decision_update event).
    asyncio.create_task(_schedule_persona_decision(session_id, updated.profile_id))
    return {
        "user_decision":    updated.user_decision.value,
        "profile_decision": updated.profile_decision.value,
        "approval_status":  updated.approval_status.value,
    }


@router.post("/chat/deny")
async def deny_match(body: DecisionRequest, uid: str = Depends(verify_token)):
    session_id = body.session_id
    await _assert_participant(session_id, uid)
    from mushahid.monitoring import capture, EVENT_MATCH_DENIED
    capture(uid, EVENT_MATCH_DENIED, {"session_id": session_id})

    # User denied — the match is closed regardless of the persona's verdict.
    # Stamp the profile side as denied too so the session is terminal.
    updated = await _apply_decision(session_id, side="user", decision=ApprovalStatus.denied)
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found")
    updated = await _apply_decision(session_id, side="profile", decision=ApprovalStatus.denied)
    return {
        "user_decision":    updated.user_decision.value if updated else "denied",
        "profile_decision": updated.profile_decision.value if updated else "denied",
        "approval_status":  "denied",
    }


async def _push_chat_notification(
    recipient_user_id: str,
    session_id: str,
    sender_id: str,
    preview: str,
) -> None:
    """Fan out a chat notification on both channels:

    1. WebSocket /ws/notifications — drives the in-app banner / Notification-
       API fallback while the SPA is open in any tab.
    2. Web Push (VAPID) — reaches the user even when the browser is closed,
       via the service worker's push handler.

    Both calls are best-effort. If the recipient has no global socket open
    OR no push subscription, the corresponding channel silently no-ops."""
    if not recipient_user_id:
        return
    sender_name = sender_id
    sender_is_seed = False
    try:
        from shreyas.retrieval.search import get_cotraveller_by_id
        cand = await get_cotraveller_by_id(sender_id)
        if cand:
            if cand.display_name:
                sender_name = cand.display_name
            sender_is_seed = bool(getattr(cand, "is_seed", False))
    except Exception:
        pass

    short_preview = preview[:140]
    timestamp     = datetime.now(timezone.utc).isoformat()

    # In-app channel — includes is_seed so the banner can render the
    # "Sonder Curated" badge for synthetic senders.
    await manager.notify_user(recipient_user_id, {
        "type":        "chat_notification",
        "session_id":  session_id,
        "sender_id":   sender_id,
        "sender_name": sender_name,
        "sender_is_seed": sender_is_seed,
        "preview":     short_preview,
        "timestamp":   timestamp,
    })

    # Closed-browser push. Runs concurrently with the WS notify so the
    # in-app banner doesn't have to wait on a push service round-trip.
    from mushahid.realtime.web_push import send_web_push
    asyncio.create_task(send_web_push(recipient_user_id, {
        "title": sender_name,
        "body":  short_preview,
        "url":   f"/chat/{session_id}",
        "tag":   f"sonder-chat-{session_id}",
    }))


async def _typing_keepalive(session_id: str, profile_id: str) -> None:
    """Re-emit typing every 2s. The frontend clears its indicator after 3.5s,
    so without this the indicator vanishes while the LLM is still thinking."""
    try:
        while True:
            await manager.broadcast_to_session(
                session_id, {"type": "typing", "user_id": profile_id}
            )
            await asyncio.sleep(_TYPING_KEEPALIVE_S)
    except asyncio.CancelledError:
        return


async def _send_synthetic_reply(
    session_id: str,
    session_meta: dict,
    last_message: str,
    user_message_id: str,
) -> None:
    """
    Drive a reply from the synthetic co-traveller (profile_id side).

    Fetches the candidate's persona from Pinecone, builds the full chat
    history, calls the LLM in-character (LARGE tier — needed for
    multi-turn consistency), and broadcasts + persists the reply. Keeps
    the typing indicator alive throughout the LLM call so the UI feels
    real-time. Failures are logged and dropped.
    """
    profile_id = session_meta.get("profile_id")
    if not profile_id:
        return

    keepalive: asyncio.Task | None = None
    try:
        from shreyas.retrieval.search import get_cotraveller_by_id
        from ali.generation.topics import generate_chat_reply

        candidate = await get_cotraveller_by_id(profile_id)
        if candidate is None:
            logger.warning("synthetic reply: no profile in Pinecone for %s", profile_id)
            return

        # Resolve trip destination + an itinerary digest so the persona's
        # reply stays anchored to (a) where the user is actually going and
        # (b) the specific activities planned. Without these the model
        # defaults to the persona's own preferred_destination / volunteers
        # their home city. The digest also gives the persona concrete
        # things to ask about ("how are you feeling about the Tsukiji
        # market stop?") instead of generic small talk.
        trip_destination: str | None = None
        itinerary_digest: str | None = None
        itinerary_id = session_meta.get("itinerary_id")
        if itinerary_id:
            try:
                from mushahid.realtime.firestore import get_itinerary
                itin = await get_itinerary(itinerary_id)
                dest = getattr(itin, "destination", None) if itin else None
                city    = (getattr(dest, "city", "") or "").strip()
                country = (getattr(dest, "country", "") or "").strip()
                if city and country:
                    trip_destination = f"{city}, {country}"
                elif city:
                    trip_destination = city

                # Build a compact day-by-day activity digest (one short line
                # per activity, max ~3 activities per day, max 5 days) so the
                # persona has concrete itinerary content to reference without
                # blowing the prompt budget.
                if itin and getattr(itin, "days", None):
                    digest_lines: list[str] = []
                    for day in itin.days[:5]:
                        day_no = getattr(day, "day_number", None) or len(digest_lines) + 1
                        activities = getattr(day, "activities", []) or []
                        names: list[str] = []
                        for act in activities[:3]:
                            name = getattr(act, "name", None) or getattr(act, "activity_name", "") or ""
                            name = (name or "").strip()
                            if name:
                                names.append(name)
                        if names:
                            digest_lines.append(f"Day {day_no}: {' / '.join(names)}")
                    if digest_lines:
                        itinerary_digest = "\n".join(digest_lines)
            except Exception as e:
                logger.warning("synthetic reply: failed to load itinerary %s for destination: %s",
                               itinerary_id, e)

        # Tiny pause before the typing dots appear so it doesn't fire in the
        # same tick as the user's message — feels more natural.
        await asyncio.sleep(random.uniform(*_REPLY_BEFORE_TYPING_S))

        # Synthetic user "reads" the message before starting to reply — flips
        # the user's bubble to "Seen" right as the typing dots appear.
        if user_message_id:
            await manager.broadcast_to_session(session_id, {
                "type": "seen",
                "message_id": user_message_id,
                "user_id": profile_id,
            })

        keepalive = asyncio.create_task(_typing_keepalive(session_id, profile_id))

        history = await list_chat_messages(session_id)
        reply_text = await generate_chat_reply(
            candidate, last_message, history,
            trip_destination=trip_destination,
            itinerary_digest=itinerary_digest,
        )
        if not reply_text:
            return

        # Run the validator + repair orchestrator. Catches assistant-voice
        # leaks, semantic drift, repetitive token loops, memory contradictions
        # against earlier chat turns, and unsafe content. Gracefully skipped
        # when SMALL_VALIDATOR_PROVIDER isn't configured (preserves the
        # pre-validator behaviour for envs that haven't set it up yet).
        try:
            from shared.config import SMALL_VALIDATOR_PROVIDER as _VALIDATOR_PROVIDER
            if _VALIDATOR_PROVIDER:
                from mushahid.validation.critic import validate_and_repair_chat_reply_wired
                profile_json = candidate.model_dump_json() if hasattr(candidate, "model_dump_json") else json.dumps({
                    "display_name": getattr(candidate, "display_name", ""),
                    "archetype":    getattr(candidate, "archetype", ""),
                    "location":     getattr(candidate, "location", ""),
                })
                # Render the transcript the same way the LLM persona prompt
                # rendered it — keeps the validator's contradiction check
                # consistent with what the model actually saw.
                history_lines: list[str] = []
                for m in history[-40:]:
                    text = (m.get("content") or "").strip()
                    if not text:
                        continue
                    speaker = "ME" if m.get("sender_id") == profile_id else "THEM"
                    history_lines.append(f"{speaker}: {text}")
                history_str = "\n".join(history_lines)
                # Prefer the user's actual trip destination so validator repairs
                # don't reintroduce the persona's own preferred_destination.
                fallback_city = trip_destination or getattr(candidate, "preferred_destination", None) or None

                validated_reply, telemetry = await validate_and_repair_chat_reply_wired(
                    profile_json=profile_json,
                    history=history_str,
                    last_message=last_message,
                    reply=reply_text,
                    city=fallback_city,
                )
                if validated_reply and validated_reply != reply_text:
                    logger.info(
                        "chat reply validator changed output for session %s — "
                        "repaired or fell back",
                        session_id,
                    )
                if telemetry:
                    # Compact log line + PostHog event so we can compute
                    # validator pass rate, repair rate, and anomaly histogram
                    # across all chat sessions in dashboards.
                    props = telemetry.get("properties", {}) if isinstance(telemetry, dict) else {}
                    logger.info(
                        "chat_validator session=%s passed_first_try=%s repairs=%s anomalies=%s latency_ms=%s",
                        session_id,
                        props.get("validator_passed_first_try"),
                        props.get("repair_count"),
                        props.get("detected_anomalies"),
                        props.get("total_latency_ms"),
                    )
                    from mushahid.monitoring import capture, EVENT_CHAT_VALIDATOR_EXECUTION
                    capture(session_meta.get("user_id") or "", EVENT_CHAT_VALIDATOR_EXECUTION, {
                        "session_id":        session_id,
                        "profile_id":        profile_id,
                        **props,
                    })
                reply_text = validated_reply or reply_text
        except Exception as e:
            # Validator is a quality gate, not a correctness gate — never
            # block the user-facing flow on it. Fall through with the raw
            # LLM reply.
            logger.warning("chat reply validator pipeline failed open for %s: %s", session_id, e)

        # Hold typing for a beat after the LLM finishes so the reply doesn't
        # appear instantaneously with the indicator still showing.
        await asyncio.sleep(random.uniform(*_REPLY_AFTER_REPLY_S))

        outgoing = {
            "type": "message",
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "sender_id": profile_id,
            "content": reply_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seen": False,
        }
        await append_chat_message(session_id, outgoing)
        await manager.broadcast_to_session(session_id, outgoing)

        # Notify the human via their global channel so they get a banner /
        # OS notification when they navigated away from the chat page.
        await _push_chat_notification(
            session_meta.get("user_id") or "", session_id, profile_id, reply_text,
        )

        # Analytics: synthetic reply landed. Counts toward response-quality
        # funnel; pair with chat_message_sent to compute send→reply latency.
        try:
            from mushahid.monitoring import capture, EVENT_CHAT_REPLY_SENT
            capture(session_meta.get("user_id") or "", EVENT_CHAT_REPLY_SENT, {
                "session_id":     session_id,
                "profile_id":     profile_id,
                "reply_length":   len(reply_text or ""),
                "history_length": len(history or []),
            })
        except Exception:
            pass
    except Exception as e:
        logger.warning("synthetic reply failed for %s: %s", session_id, e)
    finally:
        if keepalive is not None:
            keepalive.cancel()


@router.websocket("/ws/notifications")
async def notifications_websocket(websocket: WebSocket):
    """
    Global per-user channel. The frontend opens this once on app boot (from
    the root layout) and keeps it alive across navigation. Backend pushes
    chat_notification events here whenever a new message arrives in any of
    the user's sessions. First-message auth, same shape as chat.
    """
    await websocket.accept()
    try:
        auth_msg = await asyncio.wait_for(_receive_json_checked(websocket), timeout=10.0)
        uid = verify_token_string(auth_msg.get("token", ""))
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    await manager.connect_user_channel(websocket, uid)
    try:
        # We don't expect inbound traffic on this channel, but keep the loop
        # alive so the client can ping for liveness if it wants.
        while True:
            msg = await _receive_json_checked(websocket)
            if msg.get("type") == "ping":
                await manager.handle_ping(uid)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_user_channel(websocket, uid)


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # First-message auth — tokens never travel in query params (server logs).
    try:
        auth_msg = await asyncio.wait_for(_receive_json_checked(websocket), timeout=10.0)
        token = auth_msg.get("token", "")
        uid = verify_token_string(token)
    except WebSocketDisconnect:
        # Client disconnected before sending auth — connection is already closed,
        # so we must NOT call websocket.close() again (would raise RuntimeError).
        return
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    session_meta = await _load_session_safe(session_id)
    if session_meta is None:
        await websocket.close(code=4004, reason="Session not found")
        return
    if uid not in (session_meta["user_id"], session_meta["profile_id"]):
        await websocket.close(code=4003, reason="Not a participant in this session")
        return

    await manager.connect(websocket, session_id, uid)
    await set_online(uid)
    await manager.send_presence(session_id, uid, True)

    # Synthetic co-traveller is always "online" while a session is open — they
    # have no WebSocket of their own, so without this the user sees them as
    # offline forever. Broadcast once on connect so the UI flips immediately.
    synthetic_id = session_meta["profile_id"] if uid == session_meta["user_id"] else None
    if synthetic_id:
        await set_online(synthetic_id)
        await manager.send_presence(session_id, synthetic_id, True)

    try:
        while True:
            msg = await _receive_json_checked(websocket)
            mtype = msg.get("type", "message")

            if mtype == "ping":
                await manager.handle_ping(uid)
                continue

            if mtype == "typing":
                await manager.send_typing_indicator(session_id, uid, websocket)
                continue

            if mtype == "seen":
                message_id = msg.get("message_id", "")
                if message_id:
                    await manager.send_seen_receipt(session_id, message_id, uid, websocket)
                continue

            if mtype == "message":
                content = sanitize_user_input(msg.get("content", ""))
                if not content:
                    continue
                outgoing = {
                    "type": "message",
                    "message_id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "sender_id": uid,
                    "content": content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "seen": False,
                }
                await append_chat_message(session_id, outgoing)
                await manager.broadcast_to_session(session_id, outgoing)

                # Analytics: chat message sent by the real user. Powers
                # send-rate, sessions-with-replies, and chat-active funnel.
                if uid == session_meta["user_id"]:
                    try:
                        from mushahid.monitoring import capture, EVENT_CHAT_MESSAGE_SENT
                        capture(uid, EVENT_CHAT_MESSAGE_SENT, {
                            "session_id":     session_id,
                            "profile_id":     session_meta["profile_id"],
                            "message_length": len(content or ""),
                        })
                    except Exception:
                        pass

                # Notify the recipient via their global channel — they get a
                # banner/OS push when they're not on this chat page. We send
                # regardless of room presence; the client suppresses the
                # banner when it's already on /chat/{session_id}.
                recipient = session_meta["profile_id"] if uid == session_meta["user_id"] else session_meta["user_id"]
                await _push_chat_notification(recipient, session_id, uid, content)

                # If the human sent it, the synthetic co-traveller replies.
                # Fire-and-forget — the WS handler keeps reading inbound.
                if uid == session_meta["user_id"]:
                    asyncio.create_task(_send_synthetic_reply(
                        session_id, session_meta, content, outgoing["message_id"],
                    ))
                    # Scan the user's message for compatibility signals
                    # and re-rank the candidate with updated session weights.
                    # The refreshed match_score is what the persona's
                    # reciprocal approval threshold reads.
                    asyncio.create_task(_apply_chat_signals(
                        session_id, session_meta, uid, content,
                    ))
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, session_id)
        if uid not in manager.participants(session_id):
            await set_offline(uid)
            await manager.send_presence(session_id, uid, False)
