from fastapi import APIRouter, Query
from shared.schemas import VisaInfo, VisaRequirement

router = APIRouter()


@router.get("/visa-check", response_model=VisaInfo)
async def visa_check(
    destination_country: str = Query(..., description="Country name, e.g. Portugal"),
    nationality: str = Query(..., description="ISO 3166-1 alpha-2 code, e.g. US"),
):
    """
    Look up visa requirements for a nationality visiting a destination.

    Expected output:
        VisaInfo(
            destination_country = "Portugal",
            nationality         = "US",
            requirement         = VisaRequirement.visa_free,
            notes               = "US citizens can stay up to 90 days without a visa."
        )
    """
    # TODO: implement static lookup table or integrate a third-party visa API
    raise NotImplementedError
