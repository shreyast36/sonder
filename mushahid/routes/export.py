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


def _format_trip_date_range(itinerary) -> str:
    """Pull dates off the first/last day; fall back gracefully if missing."""
    days = itinerary.days or []
    if not days:
        return ""
    try:
        from datetime import date
        def _fmt(v):
            if isinstance(v, date):
                return v.strftime("%b %-d") if hasattr(v, "strftime") else str(v)
            # ISO string fallback
            s = str(v)[:10]
            try:
                return date.fromisoformat(s).strftime("%b %-d")
            except Exception:
                return s
        start_raw = days[0].trip_date
        end_raw = days[-1].trip_date
        if not start_raw or not end_raw:
            return f"{len(days)} day{'s' if len(days) != 1 else ''}"
        # Windows strftime doesn't support %-d; fall back without the dash
        try:
            start = _fmt(start_raw)
            end = _fmt(end_raw)
        except ValueError:
            start = str(start_raw)[:10]
            end = str(end_raw)[:10]
        return f"{start} – {end}  ·  {len(days)} day{'s' if len(days) != 1 else ''}"
    except Exception:
        return f"{len(days)} day{'s' if len(days) != 1 else ''}"


def _render_itinerary_html(itinerary, include_notes: bool = True) -> str:
    BG, INK, GOLD, MUTE, RULE = "#FAF8F4", "#2A241A", "#B89968", "#8B7355", "#E5DCC9"
    SERIF = "'Cormorant Garamond', Georgia, 'Times New Roman', serif"
    SANS  = "'Inter Tight', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

    def day_block(day) -> str:
        rows = []
        for ia in day.activities:
            time = html_lib.escape(ia.time or "")
            name = html_lib.escape(ia.activity.name)
            why = html_lib.escape(ia.why_this) if ia.why_this else (
                html_lib.escape(ia.activity.description or "")
            )
            rows.append(f"""
            <tr>
              <td valign="top" style="padding:18px 0;border-top:1px solid {RULE};">
                <p style="margin:0 0 4px;font-family:{SANS};font-size:10px;letter-spacing:0.18em;text-transform:uppercase;color:{GOLD};">{time}</p>
                <p style="margin:0 0 6px;font-family:{SERIF};font-size:22px;color:{INK};line-height:1.2;">{name}</p>
                <p style="margin:0;font-family:{SANS};font-size:13px;line-height:1.55;color:{MUTE};">{why}</p>
              </td>
            </tr>""")
        theme = html_lib.escape(day.theme) if day.theme else "Day plan"
        cost = f"${day.daily_cost_usd:.0f}" if day.daily_cost_usd else ""
        cost_chip = (
            f'<span style="font-family:{SANS};font-size:9px;letter-spacing:0.18em;'
            f'text-transform:uppercase;color:{MUTE};margin-left:12px;">{cost} day</span>'
        ) if cost else ""
        return f"""
        <tr><td style="padding:40px 48px 8px;">
          <p style="margin:0 0 6px;font-family:{SANS};font-size:9px;letter-spacing:0.32em;text-transform:uppercase;color:{MUTE};">Day {day.day_number}{cost_chip}</p>
          <h2 style="margin:0 0 18px;font-family:{SERIF};font-style:italic;font-weight:400;font-size:32px;color:{INK};line-height:1;">{theme}</h2>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{"".join(rows)}</table>
        </td></tr>"""

    days_html = "".join(day_block(d) for d in itinerary.days)

    notes_html = ""
    if include_notes and itinerary.notes:
        items = "".join(
            f'<li style="margin:0 0 6px;font-family:{SANS};font-size:13px;line-height:1.55;color:{MUTE};">'
            f"{html_lib.escape(n)}</li>"
            for n in itinerary.notes
        )
        notes_html = f"""
        <tr><td style="padding:32px 48px 8px;border-top:1px solid {RULE};">
          <p style="margin:0 0 12px;font-family:{SANS};font-size:9px;letter-spacing:0.32em;text-transform:uppercase;color:{MUTE};">Notes</p>
          <ul style="margin:0;padding-left:18px;">{items}</ul>
        </td></tr>"""

    city = html_lib.escape(itinerary.destination.city or "")
    country = html_lib.escape(itinerary.destination.country or "")
    title = city + (f", {country}" if country else "")
    date_range = _format_trip_date_range(itinerary)
    budget_line = (
        f"Total budget · ${itinerary.total_budget_usd:.0f}"
        if itinerary.total_budget_usd else ""
    )

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Your Sonder Itinerary</title></head>
<body style="margin:0;padding:0;background:{BG};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BG};">
    <tr><td align="center" style="padding:48px 16px;">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="max-width:640px;background:#FFFFFF;border:1px solid {RULE};">

        <tr><td style="padding:40px 48px 8px;text-align:center;">
          <p style="margin:0;font-family:{SANS};font-size:10px;letter-spacing:0.38em;text-transform:uppercase;color:{GOLD};">Sonder</p>
        </td></tr>

        <tr><td style="padding:24px 48px 48px;text-align:center;border-bottom:1px solid {RULE};">
          <p style="margin:0 0 8px;font-family:{SANS};font-size:10px;letter-spacing:0.28em;text-transform:uppercase;color:{MUTE};">Your itinerary</p>
          <h1 style="margin:0 0 12px;font-family:{SERIF};font-weight:400;font-size:54px;color:{INK};line-height:1;letter-spacing:-0.02em;">{title}</h1>
          <p style="margin:0;font-family:{SANS};font-size:13px;color:{MUTE};letter-spacing:0.04em;">{html_lib.escape(date_range)}</p>
          {f'<p style="margin:10px 0 0;font-family:{SANS};font-size:11px;color:{MUTE};letter-spacing:0.08em;">{budget_line}</p>' if budget_line else ''}
        </td></tr>

        {days_html}
        {notes_html}

        <tr><td style="padding:40px 48px 48px;border-top:1px solid {RULE};text-align:center;">
          <p style="margin:0 0 8px;font-family:{SANS};font-size:10px;letter-spacing:0.32em;text-transform:uppercase;color:{MUTE};">Curated for you by</p>
          <p style="margin:0;font-family:{SERIF};font-style:italic;font-size:20px;color:{GOLD};">Sonder</p>
        </td></tr>

      </table>
      <p style="margin:24px 0 0;font-family:{SANS};font-size:11px;color:{MUTE};">You're receiving this because you requested an itinerary export.</p>
    </td></tr>
  </table>
</body></html>"""


_TEST_DAYS = [
    ("Arrival & First Light", [
        ("3:00 PM",  "Alaya Ubud",                 "Boutique resort with wellness focus — matched to your relaxed pace."),
        ("5:00 PM",  "Sacred Monkey Forest",       "A 10-minute walk from your hotel. UNESCO-listed and perfect for a gentle first evening."),
        ("7:30 PM",  "Locavore NXT",               "Ubud's most celebrated chef-led tasting menu. Reservations rare — booked ahead for you."),
    ]),
    ("Culture & Ceremony", [
        ("8:00 AM",  "Tirta Empul Temple",         "Best visited early. The ritual purification pools are a once-in-a-lifetime experience."),
        ("11:00 AM", "Tegalalang Rice Terraces",   "Most photogenic terraces near Ubud — morning light is ideal."),
        ("6:00 PM",  "Kecak Fire Dance, Uluwatu",  "Sunset backdrop and traditional Balinese performance — one of Bali's signature experiences."),
    ]),
    ("Coastline & Calm", [
        ("9:00 AM",  "Uluwatu Temple",             "Dramatic 70m cliff views. Aligns with the scenic nature preference you set."),
        ("11:30 AM", "Padang Padang Beach",        "Hidden cove accessed by carved stone stairs. Worth every step."),
        ("6:30 PM",  "Jimbaran Seafood, Beachside","Fresh catch grilled on the beach at sunset. Within your daily budget."),
    ]),
    ("Rest & Renewal", [
        ("10:00 AM", "Balinese Healing Massage",   "Your wellness travel flag — 90-min traditional massage at the resort."),
        ("1:00 PM",  "Campuhan Ridge Walk",        "Quiet 2km jungle ridge trail. Low effort, high reward."),
        ("6:00 PM",  "Sari Organik",               "Farm-to-table dinner in the rice fields. The most serene setting in Ubud."),
    ]),
]


def _render_test_itinerary_html() -> str:
    BG, INK, GOLD, MUTE, RULE = "#FAF8F4", "#2A241A", "#B89968", "#8B7355", "#E5DCC9"
    SERIF = "'Cormorant Garamond', Georgia, 'Times New Roman', serif"
    SANS  = "'Inter Tight', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

    def day_block(n: int, theme: str, acts) -> str:
        rows = "".join(
            f"""
            <tr>
              <td valign="top" style="padding:18px 0;border-top:1px solid {RULE};">
                <p style="margin:0 0 4px;font-family:{SANS};font-size:10px;letter-spacing:0.18em;text-transform:uppercase;color:{GOLD};">{html_lib.escape(time)}</p>
                <p style="margin:0 0 6px;font-family:{SERIF};font-size:22px;color:{INK};line-height:1.2;">{html_lib.escape(name)}</p>
                <p style="margin:0;font-family:{SANS};font-size:13px;line-height:1.55;color:{MUTE};">{html_lib.escape(why)}</p>
              </td>
            </tr>"""
            for time, name, why in acts
        )
        return f"""
        <tr><td style="padding:40px 48px 8px;">
          <p style="margin:0 0 6px;font-family:{SANS};font-size:9px;letter-spacing:0.32em;text-transform:uppercase;color:{MUTE};">Day {n}</p>
          <h2 style="margin:0 0 18px;font-family:{SERIF};font-style:italic;font-weight:400;font-size:32px;color:{INK};line-height:1;">{html_lib.escape(theme)}</h2>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>
        </td></tr>"""

    days_html = "".join(day_block(i + 1, theme, acts) for i, (theme, acts) in enumerate(_TEST_DAYS))

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Your Sonder Itinerary</title></head>
<body style="margin:0;padding:0;background:{BG};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BG};">
    <tr><td align="center" style="padding:48px 16px;">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="max-width:640px;background:#FFFFFF;border:1px solid {RULE};">

        <tr><td style="padding:40px 48px 8px;text-align:center;">
          <p style="margin:0;font-family:{SANS};font-size:10px;letter-spacing:0.38em;text-transform:uppercase;color:{GOLD};">Sonder</p>
        </td></tr>

        <tr><td style="padding:24px 48px 48px;text-align:center;border-bottom:1px solid {RULE};">
          <p style="margin:0 0 8px;font-family:{SANS};font-size:10px;letter-spacing:0.28em;text-transform:uppercase;color:{MUTE};">Your itinerary</p>
          <h1 style="margin:0 0 12px;font-family:{SERIF};font-weight:400;font-size:54px;color:{INK};line-height:1;letter-spacing:-0.02em;">Bali, Indonesia</h1>
          <p style="margin:0;font-family:{SANS};font-size:13px;color:{MUTE};letter-spacing:0.04em;">Jun 14 – Jun 21 &nbsp;·&nbsp; 7 days</p>
        </td></tr>

        {days_html}

        <tr><td style="padding:40px 48px 48px;border-top:1px solid {RULE};text-align:center;">
          <p style="margin:0 0 8px;font-family:{SANS};font-size:10px;letter-spacing:0.32em;text-transform:uppercase;color:{MUTE};">Curated for you by</p>
          <p style="margin:0;font-family:{SERIF};font-style:italic;font-size:20px;color:{GOLD};">Sonder</p>
        </td></tr>

      </table>
      <p style="margin:24px 0 0;font-family:{SANS};font-size:11px;color:{MUTE};">You're receiving this because you requested an itinerary export.</p>
    </td></tr>
  </table>
</body></html>"""


@router.post("/export/email/test")
async def email_itinerary_test(body: dict, uid: str = Depends(verify_token)):
    from shared.email import send_itinerary_email
    recipient = body.get("email")
    if not recipient or not _EMAIL_RE.match(recipient):
        raise HTTPException(status_code=422, detail="Invalid email address")
    html = _render_test_itinerary_html()
    await send_itinerary_email([recipient], html, force=True)
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
