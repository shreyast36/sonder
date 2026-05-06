from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from shared.schemas import EmailItineraryRequest
from shared.email import send_itinerary_email
from mushahid.auth import verify_token

router = APIRouter()


@router.post("/export/email")
async def email_itinerary(body: EmailItineraryRequest, uid: str = Depends(verify_token)):
    """
    Send the shared itinerary to one or both co-travellers via email.
    Only participants (user_ids on the SharedItinerary) may trigger this.

    Expected input:
        EmailItineraryRequest(
            itinerary_id  = "itin_abc123",
            recipients    = ["user@example.com", "cotraveller@example.com"],
            include_notes = True
        )

    Expected output:
        { "sent_to": ["user@example.com", "cotraveller@example.com"] }
    """
    # TODO: load SharedItinerary from Firestore by itinerary_id
    # TODO: verify uid is in shared.user_ids (participants only)
    # TODO: await send_itinerary_email(body.recipients, shared, include_notes=body.include_notes)
    # TODO: return {"sent_to": body.recipients}
    raise NotImplementedError


@router.get("/export/pdf/{itinerary_id}")
async def download_itinerary_pdf(itinerary_id: str, uid: str = Depends(verify_token)):
    """
    Generate and stream a PDF of the shared itinerary.
    Uses weasyprint to render the same HTML template as the email.

    Expected output: StreamingResponse with Content-Type application/pdf and
                     Content-Disposition attachment; filename="sonder-itinerary.pdf"
    """
    # TODO: load SharedItinerary from Firestore
    # TODO: verify uid is a participant
    # TODO: html = render_itinerary_html(shared, include_notes=True)
    # TODO: pdf_bytes = weasyprint.HTML(string=html).write_pdf()
    # TODO: return StreamingResponse(
    #           iter([pdf_bytes]),
    #           media_type="application/pdf",
    #           headers={"Content-Disposition": f"attachment; filename=sonder-{itinerary_id}.pdf"}
    #       )
    raise NotImplementedError
