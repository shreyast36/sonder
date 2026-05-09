import asyncio
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from shared.schemas import ChatSession, ChatStartResponse, ApprovalStatus
from mushahid.auth import verify_token, verify_ws_token
from mushahid.utils.sanitize import sanitize_user_input

router = APIRouter()

# In-memory session store (Firestore replaces this in production)
_sessions: dict = {}


@router.post("/chat/start", response_model=ChatStartResponse)
async def start_chat(user_id: str, profile_id: str, itinerary_id: str, uid: str = Depends(verify_token)):
    from ali.generation.topics import generate_topics, generate_icebreaker
    from shared.schemas import UserProfile, CoTravellerMatch, CoTravellerProfile, Itinerary, Destination
    from shared.schemas import PacePreference, BudgetStyle, TravelStyle

    user_profile = UserProfile(user_id=user_id, display_name=uid, constraints=None, persona_answers=None)

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
        itinerary_id=itinerary_id, user_id=user_id,
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
        user_id=user_id,
        profile_id=profile_id,
        approval_status=ApprovalStatus.pending,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _sessions[session_id] = {"session": session, "messages": []}

    return ChatStartResponse(session=session, icebreaker=icebreaker, topics=topics)


@router.post("/chat/approve")
async def approve_match(session_id: str, user_id: str, _uid: str = Depends(verify_token)):
    try:
        from shreyas.cotraveller.approval import approve_match as _approve
        status = _approve(session_id, user_id)
        return {"status": status.value}
    except (NotImplementedError, Exception):
        if session_id in _sessions:
            _sessions[session_id]["session"] = _sessions[session_id]["session"].model_copy(
                update={"approval_status": ApprovalStatus.approved}
            )
        return {"status": "approved"}


@router.post("/chat/deny")
async def deny_match(session_id: str, user_id: str, _uid: str = Depends(verify_token)):
    try:
        from shreyas.cotraveller.approval import deny_match as _deny
        status = _deny(session_id, user_id)
        return {"status": status.value}
    except (NotImplementedError, Exception):
        if session_id in _sessions:
            _sessions[session_id]["session"] = _sessions[session_id]["session"].model_copy(
                update={"approval_status": ApprovalStatus.denied}
            )
        return {"status": "denied"}


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str, uid: str = Depends(verify_ws_token)):
    try:
        from shreyas.cotraveller.chat import ConnectionManager
        manager = ConnectionManager()
        await manager.connect(websocket, session_id)
        try:
            while True:
                msg = await websocket.receive_json()
                msg["sender_id"] = uid
                msg["timestamp"] = datetime.now(timezone.utc).isoformat()
                await manager.broadcast_to_session(session_id, msg)
        except WebSocketDisconnect:
            manager.disconnect(websocket, session_id)
    except (NotImplementedError, Exception):
        # Fallback: simple echo relay without Shreyas's manager
        await websocket.accept()
        try:
            while True:
                msg = await websocket.receive_json()
                content = sanitize_user_input(msg.get("content", ""))
                await websocket.send_json({
                    "type": msg.get("type", "message"),
                    "sender_id": uid,
                    "content": content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        except WebSocketDisconnect:
            pass
