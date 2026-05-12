import html as html_lib
import logging
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from shared.schemas import EmailItineraryRequest
from mushahid.auth import verify_token
from mushahid.realtime.firestore import get_itinerary

router = APIRouter()
logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def _render_itinerary_html(itinerary, include_notes: bool = True) -> str:
    days_html = ""
    for day in itinerary.days:
        acts = "".join(
            f"<li><b>{html_lib.escape(ia.time)}</b> — {html_lib.escape(ia.activity.name)}"
            f"{(' <em>' + html_lib.escape(ia.why_this) + '</em>') if ia.why_this else ''}</li>"
            for ia in day.activities
        )
        theme = html_lib.escape(day.theme) if day.theme else ""
        days_html += (
            f"<h3>Day {day.day_number}"
            f"{(' — ' + theme) if theme else ''}"
            f" (${day.daily_cost_usd:.0f})</h3><ul>{acts}</ul>"
        )

    notes_html = ""
    if include_notes and itinerary.notes:
        notes_html = "<h3>Notes</h3><ul>" + "".join(
            f"<li>{html_lib.escape(n)}</li>" for n in itinerary.notes
        ) + "</ul>"

    city = html_lib.escape(itinerary.destination.city)
    country = html_lib.escape(itinerary.destination.country)

    return f"""
    <html><body style="font-family:sans-serif;max-width:700px;margin:auto;padding:2rem">
    <h1>Sonder Itinerary</h1>
    <h2>{city}, {country}</h2>
    <p>Total budget: <b>${itinerary.total_budget_usd:.0f}</b></p>
    {days_html}{notes_html}
    </body></html>
    """


@router.post("/export/email/test")
async def email_itinerary_test(body: dict, uid: str = Depends(verify_token)):
    from shared.email import send_itinerary_email
    recipient = body.get("email")
    if not recipient or not _EMAIL_RE.match(recipient):
        raise HTTPException(status_code=422, detail="Invalid email address")
    html = """
    <html><body style="font-family:sans-serif;max-width:700px;margin:auto;padding:2rem">
    <h1>Sonder Itinerary — Test</h1>
    <h2>Bali, Indonesia</h2>
    <p>Jun 14 – Jun 21 · 7 days</p>
    <h3>Day 1 — Arrival &amp; First Light</h3>
    <ul>
      <li><b>3:00 PM</b> — Alaya Ubud</li>
      <li><b>5:00 PM</b> — Sacred Monkey Forest</li>
      <li><b>7:30 PM</b> — Locavore NXT</li>
    </ul>
    </body></html>
    """
    await send_itinerary_email([recipient], html)
    return {"sent": True}


@router.post("/export/email")
async def email_itinerary(body: EmailItineraryRequest, uid: str = Depends(verify_token)):
    invalid = [r for r in body.recipients if not _EMAIL_RE.match(r)]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Invalid email address(es): {invalid}")

    itinerary = await get_itinerary(body.itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised to export this itinerary")

    warning = None
    try:
        from shared.email import send_itinerary_email
        from mushahid.monitoring import capture
        html = _render_itinerary_html(itinerary, include_notes=body.include_notes)
        await send_itinerary_email(body.recipients, html)
        capture(uid, "itinerary_emailed", {
            "itinerary_id": body.itinerary_id,
            "recipient_count": len(body.recipients),
        })
    except Exception as exc:
        logger.error("Failed to send itinerary email for %s: %s", body.itinerary_id, exc)
        warning = "Email delivery failed — itinerary was not sent."

    response = {"sent_to": body.recipients}
    if warning:
        response["warning"] = warning
    return response


@router.get("/export/pdf/{itinerary_id}")
async def download_itinerary_pdf(itinerary_id: str, uid: str = Depends(verify_token)):
    itinerary = await get_itinerary(itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised to export this itinerary")

    html = _render_itinerary_html(itinerary, include_notes=True)

    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html).write_pdf()
    except ImportError:
        raise HTTPException(status_code=503, detail="PDF export is not available on this server")

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=sonder-{itinerary_id}.pdf"},
    )
