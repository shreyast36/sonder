"""
Web Push subscription routes.

The frontend service worker hands its PushSubscription back to the
backend via POST /api/push/subscribe; we store it in Firestore so the
chat code can target it later. The public VAPID key is served here too
so the SPA doesn't need it baked into Vite's env.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from shared.config import VAPID_PUBLIC_KEY
from mushahid.auth import verify_token
from mushahid.realtime.firestore import (
    write_push_subscription, delete_push_subscription,
    list_push_subscriptions,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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


@router.post("/push/test")
async def send_test_push(uid: str = Depends(verify_token)):
    """Fire a test web push to the caller's own browser. Returns a
    diagnostic payload so the user can tell exactly which layer is
    broken when push isn't reaching their OS:

      {
        "vapid_configured":     bool,    # backend .env has VAPID keys
        "subscription_count":   int,     # # of devices the user has subscribed
        "send_attempted":       bool,    # actually called send_web_push
        "send_error":           str|null # exception class if it blew up
      }

    Workflow: hit this from the browser devtools console
      fetch('/api/push/test', { method: 'POST',
        headers: { Authorization: `Bearer ${await firebase.auth().currentUser.getIdToken()}` }
      }).then(r => r.json()).then(console.log)

    If subscription_count is 0, the browser never subscribed — re-grant
    notification permission OR check pushSupported() in lib/push.js.
    If vapid_configured is false, the backend has no keys to sign with.
    If both are true and OS notification doesn't fire, the service
    worker isn't installed (check chrome://serviceworker-internals)."""
    from shared.config import VAPID_PRIVATE_KEY
    from mushahid.realtime.web_push import send_web_push

    vapid_ok = bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)
    subs = await list_push_subscriptions(uid)
    diag = {
        "vapid_configured":   vapid_ok,
        "subscription_count": len(subs),
        "send_attempted":     False,
        "send_error":         None,
    }
    if not vapid_ok:
        return diag
    if not subs:
        return diag

    try:
        await send_web_push(uid, {
            "title": "Sonder test push",
            "body":  "If you see this, web push is wired correctly.",
            "url":   "/dashboard",
            "tag":   "sonder-test-push",
        })
        diag["send_attempted"] = True
    except Exception as e:
        diag["send_attempted"] = True
        diag["send_error"] = f"{type(e).__name__}: {e}"
        logger.warning("send_test_push failed for %s: %s", uid, e)
    return diag
