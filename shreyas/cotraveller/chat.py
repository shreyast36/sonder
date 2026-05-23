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
        # Per-user notification channels — sockets opened from the global app
        # shell (any page) so we can push "you got a message" events when the
        # user isn't on the matching /chat/:sessionId page.
        self.user_channels: dict[str, list[WebSocket]] = {}

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

    # ── Notification channels ──────────────────────────────────────────────

    async def connect_user_channel(self, websocket: WebSocket, user_id: str) -> None:
        """Register a global notification socket for a user. Called from
        /ws/notifications after auth."""
        self.user_channels.setdefault(user_id, []).append(websocket)

    def disconnect_user_channel(self, websocket: WebSocket, user_id: str) -> None:
        chans = self.user_channels.get(user_id)
        if not chans:
            return
        self.user_channels[user_id] = [w for w in chans if w is not websocket]
        if not self.user_channels[user_id]:
            self.user_channels.pop(user_id, None)

    async def notify_user(self, user_id: str, event: dict) -> None:
        """Push an event to all of a user's global notification sockets."""
        for ws in list(self.user_channels.get(user_id, [])):
            await self.send_to_socket(ws, event)

    async def broadcast_global(self, event: dict, *, exclude_user: str | None = None) -> None:
        """Fan an event out to every connected notification channel.
        Used for app-wide signals like a new open trip or a new social
        post, where every signed-in user should see the update in real
        time. Local in-memory only — production will need Redis pub/sub
        across containers (same caveat as broadcast_to_session)."""
        for user_id, sockets in list(self.user_channels.items()):
            if exclude_user and user_id == exclude_user:
                continue
            for ws in list(sockets):
                await self.send_to_socket(ws, event)

    def user_has_open_session(self, user_id: str, session_id: str) -> bool:
        """True if the user is currently connected to this chat session room
        — used to suppress notifications for the page they're actively on."""
        return user_id in (uid for _, uid in self.rooms.get(session_id, []))


# Singleton — every route imports this same instance.
manager = ConnectionManager()
