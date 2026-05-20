"""
In-process WebSocket room manager for chat sessions.

One module-level singleton (`manager`) is shared by the FastAPI app so every
WebSocket handler sees the same rooms. Each room is a list of (websocket,
user_id) tuples — we carry the user_id alongside the socket so broadcasts
can label senders without re-deriving from auth state.

In LOCAL_MODE / single-container this is in-memory and sufficient. Production
on ECS with >1 container needs Redis pub/sub fan-out — see CLAUDE.md.
"""

import logging
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[tuple[WebSocket, str]]] = {}

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str) -> None:
        # Socket is already accepted by the route (first-message auth runs before connect).
        self.rooms.setdefault(session_id, []).append((websocket, user_id))

    def disconnect(self, websocket: WebSocket, session_id: str) -> str | None:
        """Remove this socket from the room. Returns the user_id that left, if any."""
        room = self.rooms.get(session_id)
        if not room:
            return None
        leaver = None
        self.rooms[session_id] = []
        for ws, uid in room:
            if ws is websocket:
                leaver = uid
            else:
                self.rooms[session_id].append((ws, uid))
        if not self.rooms[session_id]:
            self.rooms.pop(session_id, None)
        return leaver

    def participants(self, session_id: str) -> list[str]:
        """Currently-connected user_ids in this room (deduped, order-preserving)."""
        seen = []
        for _, uid in self.rooms.get(session_id, []):
            if uid not in seen:
                seen.append(uid)
        return seen

    async def send_to_socket(self, websocket: WebSocket, message: dict) -> None:
        if websocket.application_state != WebSocketState.CONNECTED:
            return
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning("send_to_socket failed: %s", e)

    async def broadcast_to_session(
        self, session_id: str, message: dict, exclude: WebSocket | None = None
    ) -> None:
        for ws, _ in list(self.rooms.get(session_id, [])):
            if ws is exclude:
                continue
            await self.send_to_socket(ws, message)

    async def send_typing_indicator(
        self, session_id: str, user_id: str, sender_socket: WebSocket
    ) -> None:
        await self.broadcast_to_session(
            session_id, {"type": "typing", "user_id": user_id}, exclude=sender_socket
        )

    async def send_seen_receipt(
        self,
        session_id: str,
        message_id: str,
        user_id: str,
        sender_socket: WebSocket,
    ) -> None:
        await self.broadcast_to_session(
            session_id,
            {"type": "seen", "message_id": message_id, "user_id": user_id},
            exclude=sender_socket,
        )

    async def send_presence(self, session_id: str, user_id: str, online: bool) -> None:
        await self.broadcast_to_session(
            session_id, {"type": "presence", "user_id": user_id, "online": online}
        )

    async def handle_ping(self, user_id: str) -> None:
        from shreyas.cotraveller.presence import heartbeat
        await heartbeat(user_id)


# Singleton — every route imports this same instance.
manager = ConnectionManager()
