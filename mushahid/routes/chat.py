import asyncio
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from shared.schemas import ChatSession, ChatStartResponse, ApprovalStatus
from mushahid.auth import verify_token, verify_token_string
from mushahid.utils.sanitize import sanitize_user_input
from mushahid.realtime.firestore import write_chat_session, append_chat_message, get_chat_session

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

    return ChatStartResponse(session=session, icebreaker=icebreaker, topics=topics)


async def _assert_participant(session_id: str, uid: str) -> None:
    """Raise 403/404 if uid is not a participant. Falls back to Firestore when session not in memory."""
    from fastapi import HTTPException
    session_data = _sessions.get(session_id)
    if session_data:
        s = session_data["session"]
        if uid not in (s.user_id, s.profile_id):
            raise HTTPException(status_code=403, detail="Not a participant in this session")
    else:
        try:
            stored = await get_chat_session(session_id)
        except Exception:
            stored = None
        if stored is None:
            raise HTTPException(status_code=404, detail="Session not found")
        if uid not in (stored.get("user_id"), stored.get("profile_id")):
            raise HTTPException(status_code=403, detail="Not a participant in this session")


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


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # First message must be {"type": "auth", "token": "<firebase_id_token>"}.
    # Tokens must never travel in query params — they appear in server logs.
    try:
        auth_msg = await asyncio.wait_for(_receive_json_checked(websocket), timeout=10.0)
        token = auth_msg.get("token", "")
        uid = verify_token_string(token)
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Ownership check — uid must be a participant in this session.
    # Check in-memory first; fall back to Firestore (handles server restarts).
    session_data = _sessions.get(session_id)
    if session_data:
        session_obj = session_data["session"]
        if uid not in (session_obj.user_id, session_obj.profile_id):
            await websocket.close(code=4003, reason="Not a participant in this session")
            return
    else:
        try:
            stored = await get_chat_session(session_id)
        except Exception:
            stored = None
        if stored is None:
            await websocket.close(code=4004, reason="Session not found")
            return
        if uid not in (stored.get("user_id"), stored.get("profile_id")):
            await websocket.close(code=4003, reason="Not a participant in this session")
            return

    try:
        from shreyas.cotraveller.chat import ConnectionManager
        manager = ConnectionManager()
        await manager.connect(websocket, session_id)
        try:
            while True:
                msg = await _receive_json_checked(websocket)
                if "content" in msg:
                    msg["content"] = sanitize_user_input(msg["content"])
                msg["sender_id"] = uid
                msg["timestamp"] = datetime.now(timezone.utc).isoformat()
                await append_chat_message(session_id, msg)
                await manager.broadcast_to_session(session_id, msg)
        except WebSocketDisconnect:
            manager.disconnect(websocket, session_id)
    except (NotImplementedError, Exception):
        try:
            while True:
                msg = await _receive_json_checked(websocket)
                content = sanitize_user_input(msg.get("content", ""))
                outgoing = {
                    "type": msg.get("type", "message"),
                    "sender_id": uid,
                    "content": content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await append_chat_message(session_id, outgoing)
                await websocket.send_json(outgoing)
        except WebSocketDisconnect:
            pass
