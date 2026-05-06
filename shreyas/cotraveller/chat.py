from fastapi import WebSocket
from shared.schemas import ChatMessage


class ConnectionManager:
    """
    Manages active WebSocket connections for real-time chat sessions.

    Expected behaviour:
        - One ConnectionManager instance shared across the app (singleton via mushahid/main.py)
        - Keyed by session_id — each chat session has its own room
        - Supports multiple connections per session (both users in the same room)

    Example usage (in mushahid/routes/chat.py):
        manager = ConnectionManager()

        @app.websocket("/ws/chat/{session_id}")
        async def chat_ws(websocket: WebSocket, session_id: str):
            await manager.connect(websocket, session_id)
            try:
                while True:
                    data = await websocket.receive_json()
                    await manager.broadcast_to_session(session_id, data)
            except WebSocketDisconnect:
                manager.disconnect(websocket, session_id)
    """

    def __init__(self):
        # TODO: initialise connections dict: { session_id: list[WebSocket] }
        pass

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept connection and add to session room."""
        # TODO: await websocket.accept(), append to self.connections[session_id]
        raise NotImplementedError

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """Remove a connection from its session room."""
        # TODO: remove websocket from self.connections[session_id]
        raise NotImplementedError

    async def send_to_socket(self, websocket: WebSocket, message: dict) -> None:
        """Send a message to a single connection."""
        # TODO: await websocket.send_json(message)
        raise NotImplementedError

    async def broadcast_to_session(self, session_id: str, message: dict) -> None:
        """
        Broadcast a message to all connections in a session room.

        Expected message shape:
            {
                "type": "message",          # "message" | "typing" | "seen"
                "sender_id": "user_abc",
                "content": "Hey! Excited to connect!",
                "timestamp": "2025-06-01T09:30:00Z"
            }
        """
        # TODO: iterate self.connections[session_id], call send_to_socket on each
        raise NotImplementedError

    async def send_typing_indicator(self, session_id: str, user_id: str) -> None:
        """Broadcast a typing event to the other participant."""
        # TODO: broadcast {"type": "typing", "user_id": user_id}
        raise NotImplementedError

    async def send_seen_receipt(self, session_id: str, message_id: str, user_id: str) -> None:
        """Broadcast a seen receipt event."""
        # TODO: broadcast {"type": "seen", "message_id": message_id, "user_id": user_id}
        raise NotImplementedError
