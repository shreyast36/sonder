"""
Web Push subscription routes.

The frontend service worker hands its PushSubscription back to the
backend via POST /api/push/subscribe; we store it in Firestore so the
chat code can target it later. The public VAPID key is served here too
so the SPA doesn't need it baked into Vite's env.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from shared.config import VAPID_PUBLIC_KEY
from mushahid.auth import verify_token
from mushahid.realtime.firestore import (
    write_push_subscription, delete_push_subscription,
)

router = APIRouter()


@router.get("/push/vapid-public-key")
async def get_vapid_public_key():
    """Public — the frontend needs this to subscribe. Returns 503 when web
    push isn't configured so the client can fall back gracefully."""
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Web push not configured")
    return {"key": VAPID_PUBLIC_KEY}


class PushKeys(BaseModel):
    p256dh: str
    auth:   str


class PushSubscriptionIn(BaseModel):
    endpoint:        str
    keys:            PushKeys
    expiration_time: int | None = None


@router.post("/push/subscribe")
async def subscribe(sub: PushSubscriptionIn, uid: str = Depends(verify_token)):
    """Upsert a subscription for the signed-in user. The same browser
    subscribing twice (e.g. after permission re-grant) overwrites by endpoint
    hash — no duplicate fan-out."""
    await write_push_subscription(uid, sub.model_dump())
    return {"ok": True}


class PushUnsubscribeIn(BaseModel):
    endpoint: str


@router.post("/push/unsubscribe")
async def unsubscribe(body: PushUnsubscribeIn, uid: str = Depends(verify_token)):
    await delete_push_subscription(uid, body.endpoint)
    return {"ok": True}
