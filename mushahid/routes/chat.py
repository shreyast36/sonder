from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from shared.schemas import ChatSession, ApprovalStatus

router = APIRouter()


@router.post("/chat/start", response_model=ChatSession)
async def start_chat(user_id: str, profile_id: str):
    """
    Create a new chat session between a user and a co-traveller profile.

    Expected output:
        ChatSession(
            session_id      = "session_abc123",
            user_id         = "firebase_uid_abc",
            profile_id      = "maya_001",
            approval_status = ApprovalStatus.pending,
            created_at      = "2025-06-01T09:00:00Z"
        )
    """
    # TODO: create ChatSession, write to Firestore, return session
    raise NotImplementedError


@router.post("/chat/approve")
async def approve_match(session_id: str, user_id: str):
    """
    Record user's approval. Triggers shared itinerary creation if both users approve.

    Expected output:
        { "status": "approved" }  ← if both approved
        { "status": "pending" }   ← waiting on the other user
    """
    # TODO: call shreyas/cotraveller/approval.py approve_match()
    raise NotImplementedError


@router.post("/chat/deny")
async def deny_match(session_id: str, user_id: str):
    """
    Record user's denial. Closes session and notifies the other participant.

    Expected output:
        { "status": "denied" }
    """
    # TODO: call shreyas/cotraveller/approval.py deny_match()
    raise NotImplementedError


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
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
