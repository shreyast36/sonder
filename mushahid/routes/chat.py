from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from shared.schemas import ChatSession, ChatStartResponse, ApprovalStatus
from mushahid.auth import verify_token, verify_ws_token

router = APIRouter()


@router.post("/chat/start", response_model=ChatStartResponse)
async def start_chat(user_id: str, profile_id: str, itinerary_id: str, uid: str = Depends(verify_token)):
    """
    Create a new chat session and return AI-generated conversation starters.
    itinerary_id is required so generate_topics() can personalise topics to the trip.

    Expected output:
        ChatStartResponse(
            session    = ChatSession(session_id="session_abc123", user_id="...", profile_id="maya_001", ...),
            icebreaker = "Hey Maya! Both foodies in Bali — what's top of your must-eat list?",
            topics     = ["Must-try local food in Bali", "Beach vs adventure balance", ...]
        )
    """
    # TODO: load UserProfile, CoTravellerMatch, Itinerary from Firestore by user_id / profile_id / itinerary_id
    # TODO: session = ChatSession(session_id=..., user_id=user_id, profile_id=profile_id, ...)
    # TODO: write session to Firestore
    # TODO: icebreaker, topics = await asyncio.gather(
    #           generate_icebreaker(user_profile, match),
    #           generate_topics(user_profile, match, itinerary)
    #       )
    # TODO: return ChatStartResponse(session=session, icebreaker=icebreaker, topics=topics)
    raise NotImplementedError


@router.post("/chat/approve")
async def approve_match(session_id: str, user_id: str, uid: str = Depends(verify_token)):
    """
    Record user's approval. Triggers shared itinerary creation if both users approve.

    Expected output:
        { "status": "approved" }  ← if both approved
        { "status": "pending" }   ← waiting on the other user
    """
    # TODO: call shreyas/cotraveller/approval.py approve_match()
    raise NotImplementedError


@router.post("/chat/deny")
async def deny_match(session_id: str, user_id: str, uid: str = Depends(verify_token)):
    """
    Record user's denial. Closes session and notifies the other participant.

    Expected output:
        { "status": "denied" }
    """
    # TODO: call shreyas/cotraveller/approval.py deny_match()
    raise NotImplementedError


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str, uid: str = Depends(verify_ws_token)):
    """
    Real-time chat WebSocket. Proxies to Shreyas's ConnectionManager.

    Message types the client can send:
        { "type": "message", "content": "Hey! Excited to connect!" }
        { "type": "typing" }
        { "type": "seen", "message_id": "msg_001" }

    Message types the server broadcasts:
        { "type": "message",  "sender_id": "...", "content": "...", "timestamp": "..." }
        { "type": "typing",   "user_id": "..." }
        { "type": "seen",     "message_id": "...", "user_id": "..." }
    """
    # TODO: manager.connect(websocket, session_id)
    # TODO: loop receive_json → broadcast_to_session, handle disconnect
    raise NotImplementedError
