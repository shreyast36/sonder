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
_REPLY_BEFORE_TYPING_S  = (0.6, 1.4)   # short pause before the indicator appears
_REPLY_AFTER_REPLY_S    = (0.6, 1.2)   # small pause between LLM finish and broadcast
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


@router.post("/chat/start", response_model=ChatStartResponse)
async def start_chat(body: ChatStartRequest, uid: str = Depends(verify_token)):
    from ali.generation.topics import generate_topics, generate_icebreaker
    from shared.schemas import UserProfile, CoTravellerMatch, CoTravellerProfile, Itinerary, Destination
    from shared.schemas import PacePreference, BudgetStyle, TravelStyle

    profile_id   = body.profile_id
    itinerary_id = body.itinerary_id

    user_profile = UserProfile(user_id=uid, display_name=uid, constraints=None, persona_answers=None)

    # Best-effort fetch of the real synthetic profile so the icebreaker has
    # something to anchor on. Fall back to a neutral CoTravellerMatch when
    # Pinecone is unreachable so chat still starts.
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

    dummy_itinerary = Itinerary(
        itinerary_id=itinerary_id, user_id=uid,
        destination=Destination(
            destination_id="dest_001", city="Destination", country="",
            avg_daily_cost_usd=100.0, tags=[], description="",
        ),
        days=[], total_budget_usd=0.0,
    )

    icebreaker, topics = await asyncio.gather(
        generate_icebreaker(user_profile, match),
        generate_topics(user_profile, match, dummy_itinerary),
    )

    session_id = str(uuid.uuid4())
    session = ChatSession(
        session_id=session_id,
        user_id=uid,
        profile_id=profile_id,
        approval_status=ApprovalStatus.pending,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _sessions[session_id] = {"session": session, "messages": []}
    await write_chat_session(session)

    from mushahid.monitoring import capture
    capture(uid, "chat_started", {"session_id": session_id, "profile_id": profile_id})

    return ChatStartResponse(session=session, icebreaker=icebreaker, topics=topics)


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
        return {"user_id": s.user_id, "profile_id": s.profile_id}
    try:
        stored = await get_chat_session(session_id)
    except Exception:
        return None
    if stored is None:
        return None
    return {"user_id": stored.get("user_id"), "profile_id": stored.get("profile_id")}


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


@router.post("/chat/approve")
async def approve_match(session_id: str, _uid: str = Depends(verify_token)):
    await _assert_participant(session_id, _uid)
    try:
        from shreyas.cotraveller.approval import approve_match as _approve
        status = _approve(session_id, _uid)
        return {"status": status.value}
    except (NotImplementedError, Exception):
        if session_id in _sessions:
            _sessions[session_id]["session"] = _sessions[session_id]["session"].model_copy(
                update={"approval_status": ApprovalStatus.approved}
            )
        return {"status": "approved"}


@router.post("/chat/deny")
async def deny_match(session_id: str, _uid: str = Depends(verify_token)):
    await _assert_participant(session_id, _uid)
    try:
        from shreyas.cotraveller.approval import deny_match as _deny
        status = _deny(session_id, _uid)
        return {"status": status.value}
    except (NotImplementedError, Exception):
        if session_id in _sessions:
            _sessions[session_id]["session"] = _sessions[session_id]["session"].model_copy(
                update={"approval_status": ApprovalStatus.denied}
            )
        return {"status": "denied"}


async def _push_chat_notification(
    recipient_user_id: str,
    session_id: str,
    sender_id: str,
    preview: str,
) -> None:
    """Fan out a chat notification to the recipient's global channels. Best-
    effort — if they have no channel open (offline / different device), it
    silently no-ops. Sender info + preview let the client render the banner
    without a follow-up REST hit."""
    if not recipient_user_id:
        return
    sender_name = sender_id
    try:
        from shreyas.retrieval.search import get_cotraveller_by_id
        cand = await get_cotraveller_by_id(sender_id)
        if cand and cand.display_name:
            sender_name = cand.display_name
    except Exception:
        pass
    await manager.notify_user(recipient_user_id, {
        "type": "chat_notification",
        "session_id": session_id,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "preview": preview[:140],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


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
        reply_text = await generate_chat_reply(candidate, last_message, history)
        if not reply_text:
            return

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
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, session_id)
        if uid not in manager.participants(session_id):
            await set_offline(uid)
            await manager.send_presence(session_id, uid, False)
