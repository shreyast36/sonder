from fastapi import APIRouter, Query
from shared.schemas import VisaInfo, VisaRequirement

router = APIRouter()

# Static lookup: (nationality_upper, destination_lower) -> (requirement, notes)
_VISA_TABLE: dict[tuple[str, str], tuple[VisaRequirement, str]] = {
    ("US", "portugal"):    (VisaRequirement.visa_free,      "US citizens can stay up to 90 days without a visa."),
    ("US", "france"):      (VisaRequirement.visa_free,      "US citizens can stay up to 90 days without a visa."),
    ("US", "japan"):       (VisaRequirement.visa_free,      "US citizens can stay up to 90 days without a visa."),
    ("US", "indonesia"):   (VisaRequirement.visa_on_arrival,"US citizens receive a 30-day visa on arrival, extendable once."),
    ("US", "india"):       (VisaRequirement.visa_required,  "US citizens must apply for an e-Visa before travel."),
    ("IN", "indonesia"):   (VisaRequirement.visa_on_arrival,"Indian citizens receive a 30-day visa on arrival."),
    ("IN", "thailand"):    (VisaRequirement.visa_free,      "Indian citizens can stay up to 30 days without a visa."),
    ("IN", "united states"): (VisaRequirement.visa_required,"Indian citizens must apply for a B1/B2 visa before travel."),
    ("GB", "indonesia"):   (VisaRequirement.visa_free,      "UK citizens can stay up to 30 days without a visa."),
    ("GB", "united states"): (VisaRequirement.visa_free,   "UK citizens enter under ESTA (Visa Waiver Program)."),
}


@router.get("/visa-check", response_model=VisaInfo)
async def visa_check(
    destination_country: str = Query(..., description="Country name, e.g. Indonesia"),
    nationality: str = Query(..., description="ISO 3166-1 alpha-2 code, e.g. US"),
):
    key = (nationality.upper(), destination_country.lower())
    if key in _VISA_TABLE:
        requirement, notes = _VISA_TABLE[key]
    else:
        requirement, notes = VisaRequirement.unknown, "Visa requirements not available. Check your government's travel advisory."

    return VisaInfo(
        destination_country=destination_country,
        nationality=nationality.upper(),
        requirement=requirement,
        notes=notes,
    )
