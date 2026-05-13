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


async def send_itinerary_email(to_addresses: list[str], html_body: str, *, force: bool = False) -> None:
    """
    Send a rendered HTML itinerary email to one or more recipients.

    Expected input:
        to_addresses = ["user@example.com"]
        html_body    = "<html>...</html>"

    Pass force=True to send even when LOCAL_MODE=True (used by the test endpoint).
    """
    subject = "Your Sonder itinerary"

    if LOCAL_MODE and not force:
        logger.info("LOCAL_MODE — email not sent. Subject: %s | To: %s | Body preview: %s",
                    subject, to_addresses, html_body[:300])
        return

    if EMAIL_PROVIDER == "resend":
        await _send_via_resend(to_addresses, subject, html_body)
    elif EMAIL_PROVIDER == "sendgrid":
        await _send_via_sendgrid(to_addresses, subject, html_body)
    elif EMAIL_PROVIDER == "ses":
        await _send_via_ses(to_addresses, subject, html_body)
    else:
        raise ValueError(f"Unknown EMAIL_PROVIDER '{EMAIL_PROVIDER}'. Set to resend | sendgrid | ses.")


async def _send_via_resend(to_addresses: list[str], subject: str, html: str) -> None:
    import httpx
    payload = {"from": EMAIL_FROM, "to": to_addresses, "subject": subject, "html": html}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {EMAIL_API_KEY}", "Content-Type": "application/json"},
            content=json.dumps(payload),
        )
        resp.raise_for_status()


async def _send_via_sendgrid(to_addresses: list[str], subject: str, html: str) -> None:
    import httpx
    payload = {
        "personalizations": [{"to": [{"email": a} for a in to_addresses]}],
        "from": {"email": EMAIL_FROM},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {EMAIL_API_KEY}", "Content-Type": "application/json"},
            content=json.dumps(payload),
        )
        resp.raise_for_status()


async def _send_via_ses(to_addresses: list[str], subject: str, html: str) -> None:
    import boto3
    from shared.config import AWS_REGION
    client = boto3.client("ses", region_name=AWS_REGION)
    client.send_email(
        Source=EMAIL_FROM,
        Destination={"ToAddresses": to_addresses},
        Message={"Subject": {"Data": subject}, "Body": {"Html": {"Data": html}}},
    )
