# TODO: Mushahid — chat HTTP routes and WebSocket endpoint.
# POST /chat/start  → create ChatSession in Firestore, return session_id
# POST /chat/approve → call Shreyas's approval.py approve_match()
# POST /chat/deny   → call Shreyas's approval.py deny_match()
# WS   /ws/chat/{session_id} → proxy to Shreyas's ConnectionManager
#   Forward messages, typing events, and seen receipts.
