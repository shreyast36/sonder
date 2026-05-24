"""
Destination-photo lookup. Used by the itinerary hero on the frontend when
Wikipedia returns a map / location-diagram / coat-of-arms (common for
regions like 'Patagonia') instead of an actual destination photo.

Wraps shared.pixabay.fetch_image_url so the API key stays server-side.

GET /api/destination-photo?city=X&country=Y → {"url": "https://..." | null}
"""
from fastapi import APIRouter, Query

from shared.pixabay import fetch_image_url

router = APIRouter()


@router.get("/destination-photo")
async def destination_photo(
    city: str = Query(..., min_length=1, max_length=120),
    country: str = Query("", max_length=120),
):
    """Public — no auth. Falls through to {url: null} on any error so the
    frontend can fail open instead of erroring on a missing photo."""
    queries = []
    city = (city or "").strip()
    country = (country or "").strip()
    # Most specific first; Pixabay's relevance ranks "Kyoto Japan" > "Kyoto"
    # > generic "travel" — first hit with a result wins.
    if city and country:
        queries.append(f"{city} {country}")
    if city:
        queries.append(city)

    for q in queries:
        try:
            url = await fetch_image_url(q)
        except Exception:
            url = None
        if url:
            return {"url": url, "query": q}
    return {"url": None, "query": None}
