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
    # Pristine tropical paradise beaches — NO boats, NO aerials, NO
    # people, NO architecture. Queries lean on "paradise" / "pristine"
    # / "secluded" / "crystal" because those keywords on Pixabay
    # consistently rank empty-beach landscape compositions ahead of
    # the iconic-but-cluttered destination shots (longtail boats off
    # Phi Phi, junks on Halong Bay, overwater bungalows in Maldives).
    "pristine tropical beach turquoise",
    "secluded white sand beach paradise",
    "crystal clear turquoise water beach",
    "Maldives white sand paradise",
    "Bora Bora paradise sunset beach",
    "Whitsunday whitehaven empty beach",
    "Seychelles pristine beach",
    "Bahamas paradise white sand",
    "tropical lagoon paradise",
    "remote tropical beach turquoise",
    # Pristine alpine + snow-peak landscapes. "Alpenglow" / "sunrise"
    # / "winter" bias toward dramatic light + clean compositions, no
    # ski-resort buildings, no boats on alpine lakes.
    "Swiss Alps Matterhorn alpenglow",
    "Patagonia Torres del Paine sunrise",
    "Dolomites Italy sunrise peaks",
    "Moraine Lake Banff alpine",
    "Iceland highlands mountains",
    "Lofoten Islands snowy peaks",
    "Himalaya snow summit",
    "Milford Sound fjord landscape",
    "Norway fjord winter mountains",
]


# Backdrop endpoint uses tighter Pixabay filters than the standard
# destination-photo lookup: category=nature (not travel — keeps
# hotels and resort balconies out) + editors_choice=true (Pixabay's
# curated quality bar, which strips amateur tourist snapshots).
_BACKDROP_CATEGORY = "nature"
_BACKDROP_EDITORS_CHOICE = True


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
            url = await fetch_image_url(
                q,
                category=_BACKDROP_CATEGORY,
                editors_choice=_BACKDROP_EDITORS_CHOICE,
            )
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
