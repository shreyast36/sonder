# TODO: Shreyas — WebSocket chat engine.
# - ConnectionManager: manages active WebSocket connections keyed by session_id.
#   connect(websocket, session_id), disconnect(session_id),
#   send_to_session(session_id, message), broadcast_to_session(session_id, message)
# - Persist messages to Firestore via realtime/firestore.py (Mushahid's module).
# - Emit typing indicators and seen receipts as separate event types.
