"""
Web Push send helper.

pywebpush is sync (uses requests under the hood), so every send runs in a
worker thread via asyncio.to_thread to avoid blocking the event loop. On
HTTP 404/410 the push service is telling us the subscription is gone —
we delete it from Firestore so we stop sending to it.
"""

import asyncio
import json
import logging

from shared.config import VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT
from mushahid.realtime.firestore import (
    list_push_subscriptions, delete_push_subscription,
)

logger = logging.getLogger(__name__)

_VAPID_CLAIMS = {"sub": VAPID_SUBJECT} if VAPID_SUBJECT else {"sub": "mailto:ops@sonder.app"}


def _enabled() -> bool:
    return bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)


def _send_one(sub_record: dict, payload: dict) -> int | None:
    """Synchronous push to one subscription. Returns the HTTP status from the
    push service when pywebpush raises WebPushException, else None on success."""
    try:
        from pywebpush import webpush, WebPushException
    except Exception as e:
        logger.warning("pywebpush unavailable: %s", e)
        return None

    info = {
        "endpoint": sub_record.get("endpoint"),
        "keys": sub_record.get("keys") or {},
    }
    try:
        webpush(
            subscription_info=info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=dict(_VAPID_CLAIMS),
            ttl=60 * 60 * 24,  # push service holds undelivered notifs up to 24h
        )
        return None
    except WebPushException as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status not in (404, 410):
            logger.warning("web push failed (%s): %s", status, e)
        return status
    except Exception as e:
        logger.warning("web push unexpected error: %s", e)
        return None


async def send_web_push(user_id: str, payload: dict) -> None:
    """Fan out a payload to every active subscription for a user.

    payload shape (consumed by the service worker's push handler):
        {"title": "...", "body": "...", "url": "/chat/<session_id>",
         "tag": "sonder-chat-<session_id>"}
    """
    if not _enabled():
        return
    subs = await list_push_subscriptions(user_id)
    if not subs:
        return

    # Run sends in parallel; clean up dead subscriptions as we discover them.
    async def _one(sub):
        status = await asyncio.to_thread(_send_one, sub, payload)
        if status in (404, 410):
            await delete_push_subscription(user_id, sub.get("endpoint") or "")

    await asyncio.gather(*[_one(s) for s in subs], return_exceptions=True)
