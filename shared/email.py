"""
Transactional email utility. Used by mushahid/routes/export.py to send
shared itinerary emails to both co-travellers.

Provider is configured via EMAIL_PROVIDER in shared/config.py.
Supported values: "resend" | "sendgrid" | "ses"
Falls back to logging the email content when LOCAL_MODE=True (no real send).
"""

import json
from shared.config import EMAIL_PROVIDER, EMAIL_API_KEY, EMAIL_FROM, LOCAL_MODE
from shared.schemas import SharedItinerary


def render_itinerary_html(shared: SharedItinerary, include_notes: bool = True) -> str:
    """
    Render a SharedItinerary as an HTML email body.

    Expected output: HTML string with day-by-day activities, costs, and optional notes.
    Keep it simple — inline styles only (email clients strip <style> blocks).
    """
    # TODO: build HTML string — iterate shared.itinerary.days, format each ItineraryDay
    #       Include: destination, dates, total_budget_usd (formatted in user's currency if available),
    #                per-day theme + activities (name, time, why_this, cost_usd),
    #                shared.notes if include_notes
    raise NotImplementedError


async def send_itinerary_email(
    to_addresses: list[str],
    shared: SharedItinerary,
    include_notes: bool = True,
) -> None:
    """
    Send the shared itinerary to one or both co-travellers.

    Expected input:
        to_addresses = ["user@example.com", "cotraveller@example.com"]
        shared       = SharedItinerary(itinerary=Itinerary(destination=Destination(city="Bali"), ...), notes=[...])

    In LOCAL_MODE, logs the rendered HTML to stdout instead of sending.
    """
    subject = f"Your {shared.itinerary.destination.city} itinerary — Sonder"
    html_body = render_itinerary_html(shared, include_notes=include_notes)

    if LOCAL_MODE:
        # TODO: log subject + first 500 chars of html_body for local dev inspection
        raise NotImplementedError

    if EMAIL_PROVIDER == "resend":
        await _send_via_resend(to_addresses, subject, html_body)
    elif EMAIL_PROVIDER == "sendgrid":
        await _send_via_sendgrid(to_addresses, subject, html_body)
    elif EMAIL_PROVIDER == "ses":
        await _send_via_ses(to_addresses, subject, html_body)
    else:
        raise ValueError(f"Unknown EMAIL_PROVIDER '{EMAIL_PROVIDER}'. Set to resend | sendgrid | ses.")


async def _send_via_resend(to_addresses: list[str], subject: str, html: str) -> None:
    """
    Send via Resend (resend.com). Requires EMAIL_API_KEY and EMAIL_FROM in .env.

    Resend API docs: https://resend.com/docs/api-reference/emails/send-email
    """
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
    """
    Send via SendGrid. Requires EMAIL_API_KEY and EMAIL_FROM in .env.
    """
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
    """
    Send via AWS SES. Uses boto3 — requires AWS credentials in shared/config.py.
    Destination email addresses must be verified in SES (or production access enabled).
    """
    # TODO: import boto3
    # TODO: client = boto3.client("ses", region_name=AWS_REGION)
    # TODO: client.send_email(
    #           Source=EMAIL_FROM,
    #           Destination={"ToAddresses": to_addresses},
    #           Message={"Subject": {"Data": subject}, "Body": {"Html": {"Data": html}}}
    #       )
    raise NotImplementedError
