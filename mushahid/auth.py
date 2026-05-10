import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import Header, HTTPException, Query, status
from shared.config import (
    FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY,
    FIREBASE_CLIENT_EMAIL, LOCAL_MODE,
)

_app = None


def _get_firebase_app():
    global _app
    if _app is not None:
        return _app
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": FIREBASE_PROJECT_ID,
        "private_key": FIREBASE_PRIVATE_KEY,
        "client_email": FIREBASE_CLIENT_EMAIL,
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    _app = firebase_admin.initialize_app(cred)
    return _app


def _verify(token: str) -> str:
    if LOCAL_MODE:
        return token or "local_dev_uid"
    _get_firebase_app()
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded["uid"]
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


async def verify_token(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    return _verify(authorization.removeprefix("Bearer "))


async def verify_ws_token(token: str = Query(...)) -> str:
    return _verify(token)
