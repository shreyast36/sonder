"""
Unified per-event notification fan-out: WS + Web Push + Email.

Every "thing happened to you" event in Sonder (chat message, join
request, verdict, comment, shared-itinerary proposal, response,
withdrawal, finalization) calls one of the helpers in this module
so the caller doesn't have to remember three transport layers.

Channels in priority order:
  1. WS notify_user — instant in-app banner if a tab is open
  2. Web Push     — OS notification when no tab is open
  3. Email        — fallback for users who missed the first two
                    (or who prefer email digest behavior). Per-event
                    cool-down so spam stays out of inboxes.

All three channels are fire-and-forget. A single transport failure
never blocks the others; the original request that triggered the
event returns long before email lands.

For email, we look up the user's verified address via the Firebase
Admin SDK (cached in-process). LOCAL_MODE skips Firebase lookup and
returns the uid string as the "address" — the email helper will
silently log instead of send in LOCAL_MODE so it doesn't matter.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# ── User-email lookup cache ──────────────────────────────────────────────

# uid → (email, fetched_at). Cached for the process lifetime; users
# rarely change their email and a wrong cached value just delays a
# single notif email by an hour at worst.
_email_cache: dict[str, tuple[str | None, float]] = {}
_EMAIL_CACHE_TTL_S = 3600.0


async def _lookup_email(uid: str) -> str | None:
    """Resolve a uid → verified email via Firebase Admin SDK. Returns
    None on lookup failure, on unverified email, or in LOCAL_MODE."""
    from shared.config import LOCAL_MODE
    if LOCAL_MODE:
        return None

    cached = _email_cache.get(uid)
    if cached and (time.time() - cached[1]) < _EMAIL_CACHE_TTL_S:
        return cached[0]

    try:
        from firebase_admin import auth as firebase_auth
        from mushahid.auth import _get_firebase_app
        _get_firebase_app()
        user = await asyncio.to_thread(lambda: firebase_auth.get_user(uid))
        # Only send to verified emails — sending to unverified ones is
        # an abuse-vector and a deliverability hit.
        email = user.email if (user.email_verified and user.email) else None
        _email_cache[uid] = (email, time.time())
        return email
    except Exception as e:
        logger.debug("notify._lookup_email failed for %s: %s", uid, e)
        _email_cache[uid] = (None, time.time())
        return None


# ── Per-event email cool-down ────────────────────────────────────────────

# (uid, kind) → last_sent_at unix ts. Drops a duplicate email if the
# same kind fired for the same user within the cool-down window. The
# push + WS still fire normally; only email is throttled.
_email_cooldown: dict[tuple[str, str], float] = {}
_EMAIL_COOLDOWN_S = 300.0  # 5 min


def _email_cooldown_ok(uid: str, kind: str) -> bool:
    key = (uid, kind)
    now = time.time()
    last = _email_cooldown.get(key, 0.0)
    if (now - last) < _EMAIL_COOLDOWN_S:
        return False
    _email_cooldown[key] = now
    return True


# ── HTML email template ──────────────────────────────────────────────────


def _email_html(title: str, body: str, link_url: str, link_label: str = "Open Sonder") -> str:
    """Minimal transactional template — single-column, brand-aligned,
    no inline images so it renders in any client without prefetch
    permission. Plain HTML so we don't need a templating engine."""
    safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
    safe_body  = body.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#080807;font-family:'Inter',Arial,sans-serif;color:#F4EDE0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#080807;padding:48px 24px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width:520px;background:#15151A;border:1px solid rgba(232,212,168,0.11);border-radius:14px;padding:36px 32px;">
        <tr><td>
          <p style="font-family:'Georgia',serif;font-style:italic;font-size:28px;color:#D4B686;margin:0 0 8px;line-height:1.1;">Sonder</p>
          <p style="font-size:11px;letter-spacing:0.28em;text-transform:uppercase;color:rgba(244,237,224,0.44);margin:0 0 24px;">{safe_title}</p>
          <p style="font-family:'Georgia',serif;font-style:italic;font-size:22px;color:#F4EDE0;margin:0 0 22px;line-height:1.4;">{safe_body}</p>
          <a href="{link_url}" style="display:inline-block;padding:14px 28px;background:linear-gradient(135deg,#F59E0B 0%,#D97706 100%);color:#0a0807;text-decoration:none;border-radius:24px;font-size:11px;font-weight:600;letter-spacing:0.22em;text-transform:uppercase;">{link_label}</a>
          <p style="font-size:11px;color:rgba(244,237,224,0.30);margin:36px 0 0;line-height:1.6;">You're receiving this because you have an active Sonder account. Reply to this email or visit your settings to manage notifications.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


# ── Public helper ────────────────────────────────────────────────────────


async def notify_event(
    *,
    recipient_uid: str,
    kind: str,
    title: str,
    body: str,
    link_path: str = "/dashboard",
    tag: str | None = None,
    extra_ws_payload: dict | None = None,
    ws_type: str | None = None,
) -> None:
    """Fan out one user-facing event across all three transports.

    Args:
      recipient_uid: target user's uid.
      kind: machine-readable event tag for email cool-down + telemetry
            ("chat_msg" | "join_request" | "join_verdict" | "comment" |
             "shared_proposal" | "shared_response" | "shared_finalized").
      title: short headline (used as the OS notification title + email
             subject prefix).
      body: 1-2 sentence preview (used as OS notification body + email
            body line).
      link_path: deep-link path within the app (e.g. /chat/abc, /shared/xyz).
      tag: web-push notification tag for de-duplication. Defaults to kind.
      extra_ws_payload: extra fields to merge into the WS event so the
                       frontend can render rich state (e.g. the persona
                       name, the join-request object).
      ws_type: explicit WS event type. Falls back to f"{kind}_notification".

    All three channels are fire-and-forget. Caller never awaits an
    individual send_email round-trip — that runs in asyncio.create_task.
    """
    if not recipient_uid:
        return

    # 1. WS notify — instant in-app banner if any tab is open.
    try:
        from shreyas.cotraveller.chat import manager as ws_manager
        ws_event = {
            "type":      ws_type or f"{kind}_notification",
            "title":     title,
            "body":      body,
            "link":      link_path,
        }
        if extra_ws_payload:
            ws_event.update(extra_ws_payload)
        await ws_manager.notify_user(recipient_uid, ws_event)
    except Exception as e:
        logger.debug("notify_event WS push failed (%s): %s", kind, e)

    # 2. Web push — OS notification, reaches user with tab closed.
    try:
        from mushahid.realtime.web_push import send_web_push
        asyncio.create_task(send_web_push(recipient_uid, {
            "title": title,
            "body":  body[:140],
            "url":   link_path,
            "tag":   tag or f"sonder-{kind}",
        }))
    except Exception as e:
        logger.debug("notify_event web push failed (%s): %s", kind, e)

    # 3. Email — fallback channel, throttled per (uid, kind) so a
    #    chatty thread doesn't dump 30 emails on someone.
    if not _email_cooldown_ok(recipient_uid, kind):
        return
    asyncio.create_task(_send_email_async(
        recipient_uid=recipient_uid, kind=kind,
        title=title, body=body, link_path=link_path,
    ))


async def _send_email_async(
    *, recipient_uid: str, kind: str, title: str, body: str, link_path: str,
) -> None:
    """Background email send. Looks up the user's verified email,
    composes the HTML template, fires via the configured provider.
    Never raises — failures log and drop."""
    try:
        email = await _lookup_email(recipient_uid)
        if not email:
            return
        from shared.email import send_email
        from shared.config import LOCAL_MODE
        # Frontend base URL for deep links inside the email. In LOCAL_MODE
        # the env var probably isn't set; default to discoversonder.com
        # which is the prod frontend.
        import os
        base = os.getenv("FRONTEND_BASE_URL") or "https://discoversonder.com"
        link_url = base.rstrip("/") + (link_path if link_path.startswith("/") else "/" + link_path)
        html = _email_html(title, body, link_url)
        await send_email(
            to_addresses=[email],
            subject=f"Sonder · {title}",
            html_body=html,
        )
    except Exception as e:
        logger.warning("notify._send_email_async (%s -> %s) failed: %s",
                       kind, recipient_uid, e)
