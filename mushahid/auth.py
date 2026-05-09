from fastapi import Header, HTTPException, Query, status


async def verify_token(authorization: str = Header(...)) -> str:
    """
    FastAPI dependency. Verifies a Firebase ID token from the Authorization header.
    Returns the user UID on success. Raises HTTP 401 on invalid or expired token.

    Usage — add to any protected route:
        @router.post("/plan-trip")
        async def plan_trip(request: Request, body: PlanTripRequest, uid: str = Depends(verify_token)):
            ...

    Expected header:
        Authorization: Bearer <firebase_id_token>

    Expected output:
        "firebase_uid_abc123"
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.replace("Bearer ", "")
    # TODO: from firebase_admin import auth as firebase_auth
    # TODO: try:
    # TODO:     decoded = firebase_auth.verify_id_token(token)
    # TODO:     return decoded["uid"]
    # TODO: except firebase_auth.InvalidIdTokenError:
    # TODO:     raise HTTPException(status_code=401, detail="Invalid or expired token")
    raise NotImplementedError


async def verify_ws_token(token: str = Query(..., description="Firebase ID token")) -> str:
    """
    WebSocket auth dependency. Browsers cannot set Authorization headers on WebSocket
    connections, so the Firebase ID token is passed as a query parameter instead.

    Usage:
        @router.websocket("/ws/chat/{session_id}")
        async def chat_ws(websocket: WebSocket, session_id: str, uid: str = Depends(verify_ws_token)):
            ...

    Client connects to:
        wss://api.sonder.app/ws/chat/session_abc?token=<firebase_id_token>

    On invalid token: close the WebSocket with code 1008 (Policy Violation) before accepting.
    """
    # TODO: same verification logic as verify_token
    # Note: cannot close the WebSocket here — the websocket object is only available in
    # the route handler. On failure, raise HTTPException(1008); FastAPI maps it to a
    # WebSocket close. Handle the close in the route if you need custom close logic.
    raise NotImplementedError
