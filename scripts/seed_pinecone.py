"""
One-time Pinecone seed script.

Populates 3 namespaces using integrated embedding (llama-text-embed-v2):
    hotels       — T+L luxury list (prestige) + filtered TBO Hotels (main_street)
    restaurants  — Michelin Guide 2021 (prestige)
    activities   — Wikipedia geo-searched POIs near each unique destination

Reads CSVs from data/seed/.

Run from repo root, with env vars set in your shell:
    $env:PINECONE_API_KEY="pcsk_..."
    $env:PINECONE_INDEX_NAME="sonder-index"
    python -m scripts.seed_pinecone
"""

import asyncio
import csv
import logging
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ali.vector.client import get_pinecone_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("seed")

DATA = Path("data/seed")
UA = "Sonder/1.0 (https://discoversonder.com)"

# Caps to keep token + storage reasonable
MAX_TBO_HOTELS          = 3000
MAX_ACTIVITIES_PER_CITY = 30
MAX_CITIES_FOR_WIKI     = 200
BATCH_SIZE              = 90   # Pinecone integrated-embedding upsert limit


# ── Filename resolution (handles spaces / case differences) ──────────────────
def _find(*candidates: str) -> Path:
    for name in candidates:
        p = DATA / name
        if p.exists():
            return p
    raise FileNotFoundError(f"None of these exist in {DATA}: {candidates}")


TL_PATH       = _find("TripAdvisor Luxury Hotels.csv", "tl_worlds_best_hotels.csv")
TBO_PATH      = _find("Hotels.csv", "tbo_hotels.csv")
MICHELIN_PATH = _find("Michelin Guide Restaurants.csv", "michelin_2021.csv")


# ── Hotels: T+L luxury list (prestige tier) ──────────────────────────────────
def load_tl_hotels() -> list[dict]:
    out = []
    with open(TL_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            hotel   = (row.get("Hotel") or "").strip()
            city    = (row.get("Location") or "").strip()
            country = (row.get("Country") or "").strip()
            if not hotel or not city:
                continue
            theme   = (row.get("Theme") or "").strip()
            score   = (row.get("Score") or "").strip()
            company = (row.get("Company") or "").strip()
            rank    = (row.get("Rank") or "0").strip()
            text = (
                f"{hotel} — luxury hotel by {company} in {city}, {country}. "
                f"Theme: {theme}. TripAdvisor luxury score {score}/100. "
                f"Editorial-quality property; one of the world's most acclaimed stays."
            )
            out.append({
                "_id":         f"tl-hotel-{rank}",
                "chunk_text":  text,
                "city":        city,
                "country":     country,
                "tier":        "prestige",
                "category":    "hotel",
                "subcategory": "luxury",
                "source":      "tripadvisor_luxury",
                "score":       _to_float(score, 0.0),
                "theme":       theme,
            })
    log.info("Loaded %d T+L hotels", len(out))
    return out


# ── Hotels: TBO global Hotels.csv (main_street tier — streamed + filtered) ──
def load_tbo_hotels() -> list[dict]:
    """Streams the 2.4 GB Hotels.csv. Keeps only 4-5 star with descriptions."""
    out = []
    seen_cities: dict[str, int] = {}
    PER_CITY_CAP = 30

    with open(TBO_PATH, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if len(out) >= MAX_TBO_HOTELS:
                break

            # CSV has leading spaces in some column names — normalize
            row = {(k or "").strip(): (v or "") for k, v in row.items()}

            name       = row.get("HotelName", "").strip()
            city       = row.get("cityName", "").strip()
            country    = row.get("countyName", "").strip()
            rating     = row.get("HotelRating", "").strip()
            desc       = row.get("Description", "").strip()
            facilities = row.get("HotelFacilities", "").strip()

            if not name or not city or len(desc) < 80:
                continue
            if rating not in ("FourStar", "FiveStar"):
                continue
            if seen_cities.get(city, 0) >= PER_CITY_CAP:
                continue

            tier = "prestige" if rating == "FiveStar" else "main_street"
            text = (
                f"{name} — {rating.replace('Star', '-star')} hotel in {city}, {country}. "
                f"{desc[:600]} Facilities: {facilities[:300]}"
            )
            out.append({
                "_id":          f"tbo-hotel-{row.get('HotelCode', i)}",
                "chunk_text":   text,
                "city":         city,
                "country":      country,
                "tier":         tier,
                "category":     "hotel",
                "subcategory":  rating.lower(),
                "source":       "tbo",
                "hotel_rating": rating,
            })
            seen_cities[city] = seen_cities.get(city, 0) + 1

            if i and i % 100_000 == 0:
                log.info("  ...streamed %d TBO rows, kept %d", i, len(out))

    log.info("Loaded %d TBO hotels (filtered to 4★/5★ with descriptions)", len(out))
    return out


# ── Restaurants: Michelin Guide ───────────────────────────────────────────────
def load_michelin() -> list[dict]:
    out = []
    with open(MICHELIN_PATH, encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            name     = (row.get("Name") or "").strip()
            location = (row.get("Location") or "").strip()
            cuisine  = (row.get("Cuisine") or "").strip()
            award    = (row.get("Award") or "").strip()
            price    = (row.get("Price") or "").strip()
            desc     = (row.get("Description") or "").strip()
            if not name or not location:
                continue
            city, _, country = location.partition(",")
            city, country = city.strip(), (country.strip() or city.strip())
            text = (
                f"{name} — {cuisine} restaurant in {city}, {country}. "
                f"Michelin {award}. Price {price}. {desc[:800]}"
            )
            out.append({
                "_id":        f"michelin-{i}",
                "chunk_text": text,
                "city":       city,
                "country":    country,
                "tier":       "prestige",
                "category":   "restaurant",
                "cuisine":    cuisine,
                "award":      award,
                "price":      price,
                "source":     "michelin",
            })
    log.info("Loaded %d Michelin restaurants", len(out))
    return out


# ── Activities: Wikipedia Geosearch + Summary ────────────────────────────────
EXCLUDE_TERMS = {
    "disaster", "accident", "battle", "earthquake", "tsunami",
    "flood", "massacre", "shooting", "crash", "wreck", "epidemic",
    "pandemic", "outbreak", "born in", "died in",
}


async def fetch_wikipedia_activities(city_country_pairs: list[tuple[str, str]]) -> list[dict]:
    out: list[dict] = []
    seen_titles: set[str] = set()

    async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": UA}) as client:
        for city, country in city_country_pairs:
            geo = await _geocode(client, city, country)
            if not geo:
                continue

            ids = await _wiki_geosearch(client, geo["lat"], geo["lon"])
            kept = 0
            for pageid, title in ids:
                if kept >= MAX_ACTIVITIES_PER_CITY:
                    break
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                summary = await _wiki_summary(client, title)
                if not summary:
                    continue

                extract = summary.get("extract", "")
                if len(extract) < 400 or not summary.get("thumbnail"):
                    continue
                lowered = (title + " " + extract[:300]).lower()
                if any(term in lowered for term in EXCLUDE_TERMS):
                    continue

                out.append({
                    "_id":        f"wiki-{pageid}",
                    "chunk_text": f"{title} — {city}, {country}. {extract}",
                    "city":       city,
                    "country":    country,
                    "tier":       "n/a",
                    "category":   "activity",
                    "source":     "wikipedia",
                    "wiki_title": title,
                    "wiki_url":   (summary.get("content_urls", {}).get("desktop", {}) or {}).get("page", ""),
                })
                kept += 1
                await asyncio.sleep(0.05)

            log.info("  Wikipedia: %d activities for %s, %s", kept, city, country)
            await asyncio.sleep(1.1)   # Nominatim rate-limit: 1 req/sec

    log.info("Loaded %d Wikipedia activities", len(out))
    return out


async def _geocode(client: httpx.AsyncClient, city: str, country: str) -> dict:
    q = f"{city}, {country}" if country else city
    try:
        r = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": 1},
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return {}
        return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}
    except Exception as e:
        log.warning("Geocode failed for %s: %s", q, e)
        return {}


async def _wiki_geosearch(client: httpx.AsyncClient, lat: float, lon: float) -> list[tuple[int, str]]:
    try:
        r = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query", "list": "geosearch",
                "gscoord": f"{lat}|{lon}", "gsradius": 10000, "gslimit": 80,
                "format": "json",
            },
        )
        r.raise_for_status()
        return [(g["pageid"], g["title"]) for g in r.json().get("query", {}).get("geosearch", [])]
    except Exception as e:
        log.warning("Geosearch failed: %s", e)
        return []


async def _wiki_summary(client: httpx.AsyncClient, title: str) -> dict:
    try:
        r = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}")
        if r.status_code != 200:
            return {}
        return r.json()
    except Exception:
        return {}


# ── Pinecone upsert ──────────────────────────────────────────────────────────
async def upsert_batched(namespace: str, records: list[dict]) -> None:
    if not records:
        log.info("Skipping %s — nothing to upsert", namespace)
        return
    index = await get_pinecone_index()
    total = len(records)
    for i in range(0, total, BATCH_SIZE):
        chunk = records[i:i + BATCH_SIZE]
        await asyncio.to_thread(lambda: index.upsert_records(namespace, chunk))
        log.info("  upserted %d / %d into '%s'", min(i + BATCH_SIZE, total), total, namespace)
        await asyncio.sleep(0.1)


def _to_float(s, default):
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


# ── Main ─────────────────────────────────────────────────────────────────────
async def main():
    log.info("=== Loading hotels (T+L + TBO) ===")
    tl     = load_tl_hotels()
    tbo    = load_tbo_hotels()
    hotels = tl + tbo

    log.info("=== Loading restaurants (Michelin) ===")
    restaurants = load_michelin()

    # Build the (city, country) coverage map; pick the top N for Wikipedia fetch
    counts: dict[tuple[str, str], int] = {}
    for r in hotels + restaurants:
        if r["city"]:
            k = (r["city"], r["country"])
            counts[k] = counts.get(k, 0) + 1
    top_cities = [c for c, _ in sorted(counts.items(), key=lambda x: -x[1])[:MAX_CITIES_FOR_WIKI]]
    log.info("=== Unique destinations: %d — fetching Wikipedia for top %d ===",
             len(counts), len(top_cities))

    activities = await fetch_wikipedia_activities(top_cities)

    log.info("=== Upserting to Pinecone ===")
    await upsert_batched("hotels", hotels)
    await upsert_batched("restaurants", restaurants)
    await upsert_batched("activities", activities)

    log.info("=== Done ===")
    log.info("  hotels:       %d", len(hotels))
    log.info("  restaurants:  %d", len(restaurants))
    log.info("  activities:   %d", len(activities))


if __name__ == "__main__":
    asyncio.run(main())
