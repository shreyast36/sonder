import asyncio
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from shared.schemas import ChatSession, ChatStartResponse, ApprovalStatus
from shared.config import LOCAL_MODE
from mushahid.auth import verify_token, verify_token_string
from mushahid.utils.sanitize import sanitize_user_input
from mushahid.realtime.firestore import (
    write_chat_session, append_chat_message, get_chat_session,
    list_chat_messages, get_presence,
)
from shreyas.cotraveller.chat import manager
from shreyas.cotraveller.presence import set_online, set_offline, is_online

router = APIRouter()

# In-memory session store (Firestore replaces this in production)
_sessions: dict = {}

_MAX_WS_MSG_BYTES = 64 * 1024  # 64 KB per message


async def _receive_json_checked(websocket: WebSocket) -> dict:
    text = await websocket.receive_text()
    if len(text.encode()) > _MAX_WS_MSG_BYTES:
        await websocket.close(code=1009, reason="Message too large")
        raise WebSocketDisconnect(code=1009)
    return json.loads(text)


@router.post("/chat/start", response_model=ChatStartResponse)
async def start_chat(profile_id: str, itinerary_id: str, uid: str = Depends(verify_token)):
    from ali.generation.topics import generate_topics, generate_icebreaker
    from shared.schemas import UserProfile, CoTravellerMatch, CoTravellerProfile, Itinerary, Destination
    from shared.schemas import PacePreference, BudgetStyle, TravelStyle

    user_profile = UserProfile(user_id=uid, display_name=uid, constraints=None, persona_answers=None)

    match = CoTravellerMatch(
        profile=CoTravellerProfile(
            profile_id=profile_id, display_name=profile_id,
            age=25, location="Unknown", archetype="Explorer",
            interests=[], pace=PacePreference.moderate,
            budget_style=BudgetStyle.mid_range, travel_style=TravelStyle.solo,
        ),
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
    """Raise 403/404 if uid is not a participant. Falls back to Firestore when session not in memory."""
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


async def _load_session(session_id: str) -> dict:
    """Return {'user_id', 'profile_id'} for a session, from memory or Firestore. 404 otherwise."""
    cached = _sessions.get(session_id)
    if cached:
        s = cached["session"]
        return {"user_id": s.user_id, "profile_id": s.profile_id}
    stored = await get_chat_session(session_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"user_id": stored.get("user_id"), "profile_id": stored.get("profile_id")}


@router.get("/chat/session/{session_id}")
async def get_session(session_id: str, uid: str = Depends(verify_token)):
    """Session metadata for the chat page to know its profile_id, status, etc."""
    await _assert_participant(session_id, uid)
    cached = _sessions.get(session_id)
    if cached:
        return cached["session"].model_dump(mode="json")
    stored = await get_chat_session(session_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # Strip the messages list — the dedicated endpoint returns those.
    return {k: v for k, v in stored.items() if k != "messages"}


@router.get("/chat/{session_id}/messages")
async def get_messages(session_id: str, uid: str = Depends(verify_token)):
    """Replay history when the chat page mounts (so refresh doesn't lose the thread)."""
    await _assert_participant(session_id, uid)
    msgs = await list_chat_messages(session_id)
    # Honour in-memory store too (LOCAL_MODE non-Firestore path).
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


async def _authenticate_ws(websocket: WebSocket, session_id: str) -> str | None:
    """
    Run first-message auth. Returns the effective uid for the connection, or
    None if auth failed (and the socket has been closed).

    Auth message shape:
        Normal:        {"type": "auth", "token": "<firebase_id_token>"}
        Impersonation: {"type": "auth", "impersonate_profile_id": "<profile_id>"}
                       — only honoured when LOCAL_MODE=true; lets the dev open
                       a second window posing as the synthetic co-traveller.
    """
    try:
        auth_msg = await asyncio.wait_for(_receive_json_checked(websocket), timeout=10.0)
    except Exception:
        await websocket.close(code=4001, reason="Authentication timed out")
        return None

    impersonate = auth_msg.get("impersonate_profile_id")
    if impersonate:
        if not LOCAL_MODE:
            await websocket.close(code=4003, reason="Impersonation only allowed in LOCAL_MODE")
            return None
        session = await _load_session_safe(session_id)
        if session is None:
            await websocket.close(code=4004, reason="Session not found")
            return None
        if impersonate != session["profile_id"]:
            await websocket.close(code=4003, reason="Impersonation profile_id mismatch")
            return None
        return impersonate

    token = auth_msg.get("token", "")
    try:
        uid = verify_token_string(token)
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return None

    session = await _load_session_safe(session_id)
    if session is None:
        await websocket.close(code=4004, reason="Session not found")
        return None
    if uid not in (session["user_id"], session["profile_id"]):
        await websocket.close(code=4003, reason="Not a participant in this session")
        return None
    return uid


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


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    uid = await _authenticate_ws(websocket, session_id)
    if uid is None:
        return

    await manager.connect(websocket, session_id, uid)
    await set_online(uid)
    await manager.send_presence(session_id, uid, True)

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
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, session_id)
        # Only mark this uid offline if they have no other live sockets in the room.
        if uid not in manager.participants(session_id):
            await set_offline(uid)
            await manager.send_presence(session_id, uid, False)
