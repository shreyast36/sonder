"""
Destination-photo lookup. Used by the itinerary hero on the frontend when
Wikipedia returns a map / location-diagram / coat-of-arms (common for
regions like 'Patagonia') instead of an actual destination photo.

Wraps shared.pixabay.fetch_image_url so the API key stays server-side.

GET /api/destination-photo?city=X&country=Y → {"url": "https://..." | null}
"""
from fastapi import APIRouter, Query

from shared.pixabay import fetch_image_url, fetch_image_urls

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


# Hand-curated lush-exotic-landscape queries powering the dashboard's
# cinematic Pixabay backdrop. NO architecture, NO cityscapes, NO
# hotels — only natural landscapes (rice terraces, jungle waterfalls,
# limestone karsts, lagoons, granite islands). Pixabay's relevance
# engine handles the actual photo pick per query; "aerial" keyword
# keeps the Ken-Burns simulation reading as flyover.
_LUXURY_BACKDROP_QUERIES = [
    # Tropical islands — full-view ground-level landscapes. NO "aerial"
    # keyword so Pixabay surfaces walking-perspective wide shots, not
    # drone footage. Turquoise water + palm coast + lagoons.
    "Maldives island lagoon",
    "Bora Bora island lagoon",
    "Palawan El Nido island",
    "Hawaii Kauai island",
    "Phi Phi Islands Thailand",
    "Seychelles tropical island",
    "Halong Bay Vietnam",
    "Tahiti island",
    "Whitsunday Islands",
    "Fiji islands",
    # Beautiful mountain landscapes — full-view wide shots from the
    # ground / a ridge / a lakeshore. Peaks, alpine lakes, glaciers.
    "Patagonia Torres del Paine",
    "Swiss Alps Matterhorn",
    "Milford Sound New Zealand",
    "Banff Moraine Lake",
    "Dolomites Italy mountains",
    "Iceland mountain landscape",
    "Lofoten Islands mountains",
    "Himalaya peaks",
    "Norway fjord mountains",
]


@router.get("/luxury-backdrops")
async def luxury_backdrops():
    """Curated luxury-destination Pixabay photos for the dashboard's
    cinematic backdrop. One image per query (most popular). Cached
    by query in `shared.pixabay`, so repeated calls are free.

    Public — no auth. Returns whatever subset of queries Pixabay had
    hits for; never errors. Frontend Ken-Burnses through whatever
    comes back.
    """
    urls: list[str] = []
    for q in _LUXURY_BACKDROP_QUERIES:
        try:
            url = await fetch_image_url(q)
        except Exception:
            url = None
        if url:
            urls.append(url)
    return {"urls": urls}


@router.get("/destination-photos")
async def destination_photos(
    city: str = Query(..., min_length=1, max_length=120),
    country: str = Query("", max_length=120),
    count: int = Query(5, ge=1, le=12),
):
    """Multi-photo lookup for the cinematic trip-locked-in reveal.
    Returns up to `count` distinct Pixabay image URLs ranked by
    popularity. Public — no auth, falls through to an empty list
    on any error so the caller can fail open."""
    city = (city or "").strip()
    country = (country or "").strip()
    # Most-specific query first; the multi variant is cached per query
    # so re-asking with the same city is free.
    primary = f"{city} {country}".strip() or city
    try:
        urls = await fetch_image_urls(primary, count=count)
    except Exception:
        urls = []
    if not urls and country:
        # Country-less retry — broader pool when "Patagonia Argentina"
        # comes back empty but "Patagonia" alone has results.
        try:
            urls = await fetch_image_urls(city, count=count)
        except Exception:
            urls = []
    return {"urls": urls, "query": primary if urls else None}
