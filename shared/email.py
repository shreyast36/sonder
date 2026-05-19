"""
Transactional email utility. Used by mushahid/routes/export.py to send
itinerary emails.

Provider is configured via EMAIL_PROVIDER in shared/config.py.
Supported values: "resend" | "sendgrid" | "ses"
Falls back to logging when LOCAL_MODE=True.
"""

import json
import logging
from shared.config import EMAIL_PROVIDER, EMAIL_API_KEY, EMAIL_FROM, LOCAL_MODE

logger = logging.getLogger(__name__)


async def send_email(to_addresses: list[str], subject: str, html_body: str, *, force: bool = False) -> None:
    """
    Generic transactional email send via the configured provider.

    Pass force=True to send even when LOCAL_MODE=True (used by test endpoints
    that need real delivery during local development).
    """
    if LOCAL_MODE and not force:
        logger.info("LOCAL_MODE — email not sent. Subject: %s | To: %s | Body preview: %s",
                    subject, to_addresses, html_body[:300])
        return

    # Catch the simplest misconfigurations before talking to the provider so
    # the user gets a concrete "set EMAIL_API_KEY" message instead of an
    # opaque 401 from Resend/SendGrid.
    if not EMAIL_API_KEY and EMAIL_PROVIDER in ("resend", "sendgrid"):
        raise RuntimeError(
            f"EMAIL_API_KEY is not set — required for EMAIL_PROVIDER={EMAIL_PROVIDER}. "
            "Add it to the backend env (Render → Environment) and redeploy."
        )
    if not EMAIL_FROM:
        raise RuntimeError(
            "EMAIL_FROM is not set — required as the verified sender address."
        )

    if EMAIL_PROVIDER == "resend":
        await _send_via_resend(to_addresses, subject, html_body)
    elif EMAIL_PROVIDER == "sendgrid":
        await _send_via_sendgrid(to_addresses, subject, html_body)
    elif EMAIL_PROVIDER == "ses":
        await _send_via_ses(to_addresses, subject, html_body)
    else:
        raise ValueError(f"Unknown EMAIL_PROVIDER '{EMAIL_PROVIDER}'. Set to resend | sendgrid | ses.")


async def send_itinerary_email(to_addresses: list[str], html_body: str, *, force: bool = False) -> None:
    """Backwards-compatible wrapper around send_email for itinerary delivery."""
    await send_email(to_addresses, "Your Sonder itinerary", html_body, force=force)


def _raise_provider_error(provider: str, resp) -> None:
    """Surface the provider's response body so the user sees why the send
    failed (unverified domain, bad key, rate limit) instead of an opaque
    HTTPStatusError."""
    body = resp.text or ""
    try:
        parsed = resp.json()
        msg = parsed.get("message") or parsed.get("error") or parsed
    except Exception:
        msg = body[:300]
    raise RuntimeError(f"{provider} {resp.status_code}: {msg}")


async def _send_via_resend(to_addresses: list[str], subject: str, html: str) -> None:
    import httpx
    payload = {"from": EMAIL_FROM, "to": to_addresses, "subject": subject, "html": html}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {EMAIL_API_KEY}", "Content-Type": "application/json"},
            content=json.dumps(payload),
        )
    if resp.status_code >= 400:
        _raise_provider_error("resend", resp)


async def _send_via_sendgrid(to_addresses: list[str], subject: str, html: str) -> None:
    import httpx
    payload = {
        "personalizations": [{"to": [{"email": a} for a in to_addresses]}],
        "from": {"email": EMAIL_FROM},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {EMAIL_API_KEY}", "Content-Type": "application/json"},
            content=json.dumps(payload),
        )
    if resp.status_code >= 400:
        _raise_provider_error("sendgrid", resp)


async def _send_via_ses(to_addresses: list[str], subject: str, html: str) -> None:
    import boto3
    from shared.config import AWS_REGION
    client = boto3.client("ses", region_name=AWS_REGION)
    client.send_email(
        Source=EMAIL_FROM,
        Destination={"ToAddresses": to_addresses},
        Message={"Subject": {"Data": subject}, "Body": {"Html": {"Data": html}}},
    )
