"""
Public auth endpoints — password reset, email verification, etc.

These endpoints do NOT require a Bearer token (the caller, by definition,
can't sign in yet). They are rate-limited at the app level via slowapi
and silently swallow errors to prevent account enumeration.
"""

import html as html_lib
import logging
import re
from fastapi import APIRouter
from shared.email import send_email
from shared.config import LOCAL_MODE

router = APIRouter()
logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def _render_password_reset_html(display_name: str, reset_link: str) -> str:
    """Editorial dark/gold password-reset email matching the itinerary template."""
    BG, INK, GOLD, MUTE, RULE = "#FAF8F4", "#2A241A", "#B89968", "#8B7355", "#E5DCC9"
    SERIF = "'Cormorant Garamond', Georgia, 'Times New Roman', serif"
    SANS  = "'Inter Tight', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

    safe_name = html_lib.escape(display_name or "traveller")
    safe_link = html_lib.escape(reset_link, quote=True)

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Reset your Sonder password</title></head>
<body style="margin:0;padding:0;background:{BG};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BG};">
    <tr><td align="center" style="padding:48px 16px;">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;background:#FFFFFF;border:1px solid {RULE};">

        <tr><td style="padding:40px 48px 8px;text-align:center;">
          <p style="margin:0;font-family:{SANS};font-size:10px;letter-spacing:0.38em;text-transform:uppercase;color:{GOLD};">Sonder</p>
        </td></tr>

        <tr><td style="padding:24px 48px 0;text-align:center;">
          <p style="margin:0 0 6px;font-family:{SANS};font-size:10px;letter-spacing:0.28em;text-transform:uppercase;color:{MUTE};">Account</p>
          <h1 style="margin:0 0 12px;font-family:{SERIF};font-style:italic;font-weight:400;font-size:42px;color:{INK};line-height:1.05;letter-spacing:-0.01em;">Reset your password</h1>
        </td></tr>

        <tr><td style="padding:24px 48px 8px;">
          <p style="margin:0 0 18px;font-family:{SANS};font-size:14px;line-height:1.7;color:{INK};">
            Hi {safe_name},
          </p>
          <p style="margin:0 0 18px;font-family:{SANS};font-size:14px;line-height:1.7;color:{INK};">
            Someone — hopefully you — asked to reset the password for your Sonder
            account. Tap the link below to choose a new one.
          </p>
          <p style="margin:0 0 18px;font-family:{SANS};font-size:13px;line-height:1.6;color:{MUTE};">
            This link expires in one hour. If you didn't request this, you can
            safely ignore this email — your password won't change.
          </p>
        </td></tr>

        <tr><td style="padding:8px 48px 40px;text-align:center;">
          <a href="{safe_link}"
             style="display:inline-block;padding:16px 36px;background:{INK};color:#FFFFFF;
                    text-decoration:none;font-family:{SANS};font-size:11px;
                    letter-spacing:0.22em;text-transform:uppercase;font-weight:500;
                    border:1px solid {INK};">
            Reset password
          </a>
          <p style="margin:24px 0 0;font-family:{SANS};font-size:11px;line-height:1.5;color:{MUTE};">
            Or paste this link into your browser:<br/>
            <span style="color:{GOLD};word-break:break-all;">{safe_link}</span>
          </p>
        </td></tr>

        <tr><td style="padding:32px 48px 40px;border-top:1px solid {RULE};text-align:center;">
          <p style="margin:0 0 6px;font-family:{SANS};font-size:10px;letter-spacing:0.32em;text-transform:uppercase;color:{MUTE};">From</p>
          <p style="margin:0;font-family:{SERIF};font-style:italic;font-size:18px;color:{GOLD};">Sonder</p>
        </td></tr>

      </table>
      <p style="margin:20px 0 0;font-family:{SANS};font-size:11px;color:{MUTE};">
        Sent because someone requested a password reset for this address.
      </p>
    </td></tr>
  </table>
</body></html>"""


@router.post("/auth/password-reset")
async def request_password_reset(body: dict):
    """
    Send a custom-branded password reset email via Resend.

    Always returns {"sent": True} regardless of whether the address exists,
    to prevent account-enumeration attacks. Real errors are logged server-side.
    """
    email = (body.get("email") or "").strip()

    # Silently no-op on bad input — don't reveal validation rules
    if not email or not _EMAIL_RE.match(email):
        return {"sent": True}

    try:
        from firebase_admin import auth as fb_auth
        from mushahid.auth import _get_firebase_app

        if LOCAL_MODE:
            logger.warning(
                "Password reset requested for %s but LOCAL_MODE=true. "
                "Real Firebase Admin credentials are required to generate "
                "the reset link. Configure FIREBASE_PRIVATE_KEY/CLIENT_EMAIL "
                "and set LOCAL_MODE=false to enable.", email,
            )
            return {"sent": True}

        _get_firebase_app()
        reset_link = fb_auth.generate_password_reset_link(email)

        try:
            user_record = fb_auth.get_user_by_email(email)
            display_name = user_record.display_name
        except Exception:
            display_name = None

        html = _render_password_reset_html(display_name, reset_link)
        await send_email([email], "Reset your Sonder password", html)

    except Exception as exc:
        # Includes UserNotFoundError, network errors, etc.
        # Log for debugging, but never reveal to client (enumeration defense).
        logger.warning("Password reset failed for %s: %s", email, exc)

    return {"sent": True}
