from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from shared.schemas import EmailItineraryRequest
from mushahid.auth import verify_token
from mushahid.realtime.firestore import get_itinerary

router = APIRouter()


def _render_itinerary_html(itinerary, include_notes: bool = True) -> str:
    days_html = ""
    for day in itinerary.days:
        acts = "".join(
            f"<li><b>{ia.time}</b> — {ia.activity.name}"
            f"{(' <em>' + ia.why_this + '</em>') if ia.why_this else ''}</li>"
            for ia in day.activities
        )
        days_html += (
            f"<h3>Day {day.day_number}"
            f"{(' — ' + day.theme) if day.theme else ''}"
            f" (${day.daily_cost_usd:.0f})</h3><ul>{acts}</ul>"
        )

    notes_html = ""
    if include_notes and itinerary.notes:
        notes_html = "<h3>Notes</h3><ul>" + "".join(f"<li>{n}</li>" for n in itinerary.notes) + "</ul>"

    return f"""
    <html><body style="font-family:sans-serif;max-width:700px;margin:auto;padding:2rem">
    <h1>Sonder Itinerary</h1>
    <h2>{itinerary.destination.city}, {itinerary.destination.country}</h2>
    <p>Total budget: <b>${itinerary.total_budget_usd:.0f}</b></p>
    {days_html}{notes_html}
    </body></html>
    """


@router.post("/export/email")
async def email_itinerary(body: EmailItineraryRequest, _uid: str = Depends(verify_token)):
    itinerary = await get_itinerary(body.itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    try:
        from shared.email import send_itinerary_email
        html = _render_itinerary_html(itinerary, include_notes=body.include_notes)
        await send_itinerary_email(body.recipients, html)
    except Exception:
        pass  # email is best-effort; don't fail the request

    return {"sent_to": body.recipients}


@router.get("/export/pdf/{itinerary_id}")
async def download_itinerary_pdf(itinerary_id: str, _uid: str = Depends(verify_token)):
    itinerary = await get_itinerary(itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    html = _render_itinerary_html(itinerary, include_notes=True)

    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html).write_pdf()
    except Exception:
        pdf_bytes = html.encode()

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=sonder-{itinerary_id}.pdf"},
    )
