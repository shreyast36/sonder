"""
One-time Pinecone seed.

Universe = data/destinations/top100.json (curated 364 destinations covering
every traveler persona: cities, beaches, mountains, parks, heritage, wellness,
safari, wine country). This file is the single source of truth — no algorithmic
universe layers, no editorial/population/tbo_supply logic.

Three Pinecone namespaces, all filtered to records inside the curated universe:
    hotels       — T+L luxury + TBO 3-5★
    restaurants  — Michelin star/bib + Foursquare top dining (popularity-sorted)
    activities   — Foursquare arts / landmarks / outdoors (popularity-sorted)

Usage:
    $env:PINECONE_API_KEY="..."; $env:PINECONE_INDEX_NAME="sonder-index"
    $env:FOURSQUARE_API_KEY="..."
    python -m scripts.seed_pinecone [--only hotels,restaurants,activities]
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ali.vector.client import get_pinecone_index, embed_texts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("seed")

DATA              = Path("data/seed")
DESTINATIONS_PATH = Path("data/destinations/top100.json")
CACHE             = Path(".cache/foursquare")
CACHE.mkdir(parents=True, exist_ok=True)

FOURSQUARE_API_KEY     = os.getenv("FOURSQUARE_API_KEY", "")
FOURSQUARE_ENDPOINT    = "https://places-api.foursquare.com/places/search"
FOURSQUARE_API_VERSION = "2025-06-17"
UA = "Sonder/1.0 (https://discoversonder.com)"

MAX_TBO_HOTELS        = 5000   # cap on TBO stream (universe filter reduces this naturally)
MAX_PER_CITY          = 30     # Foursquare allows up to 50; 30 keeps signal tight
RADIUS_METERS         = 15_000
BATCH_SIZE            = 50
UPSERT_PAUSE_SEC      = 6
UPSERT_RETRY_BACKOFF  = 60
TBO_PER_STAR_CITY_CAP = 15

# Foursquare category IDs (new Places API uses long-form hex IDs).
#   4d4b7104d754a06370d81259  Arts & Entertainment
#   4d4b7105d754a06377d81259  Outdoors & Recreation
#   4d4b7105d754a06374d81259  Food
#   4bf58dd8d48988d1fa931735  Hotel
#   4bf58dd8d48988d1ee931735  Hostel
#   4bf58dd8d48988d1ed931735  Bed & Breakfast
#   56aa371be4b08b9a8d573535  Vacation Rental
ACTIVITY_CATEGORIES = "4d4b7104d754a06370d81259,4d4b7105d754a06377d81259"
DINING_CATEGORIES   = "4d4b7105d754a06374d81259"
LODGING_CATEGORIES  = "4bf58dd8d48988d1fa931735,4bf58dd8d48988d1ee931735,4bf58dd8d48988d1ed931735,56aa371be4b08b9a8d573535"

# Only drop records whose categories are clearly not-a-destination at any
# persona — pure infrastructure. Religious sites, casinos, nightclubs etc.
# stay in; runtime persona filtering decides what surfaces (kid-friendly
# excludes casinos, secular travelers exclude churches, etc.).
FSQ_CAT_BLOCKLIST = {
    "atm", "gas station", "fuel station", "parking", "baggage claim",
    "airport terminal", "airport gate", "airport lounge",
    "airport food court", "airport tram station", "airport service",
    "convenience store",
}


# ── Paths ────────────────────────────────────────────────────────────────────
def _find(*names: str) -> Path:
    for name in names:
        if (DATA / name).exists():
            return DATA / name
    raise FileNotFoundError(f"None of these exist in {DATA}: {names}")


TL_PATH          = _find("Travel and Leisure World's Best Luxury Hotels.csv",
                         "Travel and Leisure Worlds Best Luxury Hotels.csv")
TBO_PATH         = _find("Hotels.csv")
MICHELIN_PATH    = _find("Michelin Guide Restaurants.csv")
WORLDCITIES_PATH = _find("worldcities.csv")


# ── Country normalization ────────────────────────────────────────────────────
# Aliases built from REST Countries API + worldcities.csv admin_name column.
# Cached to .cache/country_aliases.json so re-runs skip the API call.

_COUNTRY_ALIASES_CACHE = Path(".cache/country_aliases.json")


def _fetch_country_aliases() -> dict[str, str]:
    if _COUNTRY_ALIASES_CACHE.exists():
        try:
            return json.loads(_COUNTRY_ALIASES_CACHE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    aliases: dict[str, str] = {}

    try:
        with httpx.Client(timeout=30.0, headers={"User-Agent": UA}) as client:
            r = client.get(
                "https://restcountries.com/v3.1/all",
                params={"fields": "name,cca2,cca3,altSpellings"},
            )
            r.raise_for_status()
            for c in r.json():
                canonical = c["name"]["common"].lower()
                variants: list[str] = [
                    c["name"]["common"],
                    c["name"].get("official", "") or "",
                    c.get("cca2", "") or "",
                    c.get("cca3", "") or "",
                    *(c.get("altSpellings") or []),
                ]
                for native in (c["name"].get("nativeName") or {}).values():
                    variants += [native.get("common") or "", native.get("official") or ""]
                parts = c["name"]["common"].split(" ")
                if len(parts) > 1:
                    variants.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
                for v in variants:
                    if isinstance(v, str) and v.strip():
                        aliases[v.strip().lower()] = canonical
    except Exception as e:
        log.warning("REST Countries fetch failed: %s — continuing with subdivision data only", e)

    try:
        with open(WORLDCITIES_PATH, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                admin   = (row.get("admin_name") or "").strip().lower()
                country = (row.get("country") or "").strip().lower()
                if not admin or not country:
                    continue
                canonical = aliases.get(country, country)
                if admin not in aliases:
                    aliases[admin] = canonical
    except Exception as e:
        log.warning("worldcities admin_name pass failed: %s", e)

    if aliases:
        _COUNTRY_ALIASES_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _COUNTRY_ALIASES_CACHE.write_text(
            json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log.info("Loaded %d country/subdivision aliases", len(aliases))
    return aliases


_COUNTRY_ALIASES = _fetch_country_aliases()


def _norm_country(country: str) -> str:
    c = (country or "").strip().lower()
    if c in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[c]
    no_punct = c.replace(".", "").strip()
    if no_punct in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[no_punct]
    if "," in c:
        last = c.rsplit(",", 1)[-1].strip()
        return _COUNTRY_ALIASES.get(last, last)
    return c


def _to_float(s, default=0.0):
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def _norm_city(city: str) -> str:
    """Key form for city lookup: lowercased, punctuation collapsed to spaces.

    Matches 'Bora-Bora' to 'Bora Bora', 'St. Petersburg' to 'Saint Petersburg'
    (after the saint expansion below), 'São Paulo' stays accented. Applied
    symmetrically wherever city keys are built or compared.
    """
    s = (city or "").strip().lower()
    s = re.sub(r"[.\-_/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\bst\b", "saint", s)
    s = re.sub(r"\bste\b", "sainte", s)
    s = re.sub(r"\bmt\b", "mount", s)
    return s


# ── World-cities coord index ─────────────────────────────────────────────────
_NOMINATIM_CACHE_PATH = Path(".cache/nominatim_cities.json")


class CityIndex:
    """Coord lookup with progressive fallbacks for messy real-world inputs.

    Fast path: worldcities.csv. Slow path: Nominatim for small vacation towns
    not in worldcities (Interlaken, Zermatt, Tulum, ...). Cached per pair.
    """

    def __init__(self) -> None:
        self.by_pair:   dict[tuple[str, str], dict] = {}
        self.capitals:  dict[str, dict] = {}
        self.largest_in_country: dict[str, dict] = {}
        self.largest_by_city:    dict[str, dict] = {}

        self._nominatim_cache: dict[str, dict | None] = {}
        if _NOMINATIM_CACHE_PATH.exists():
            try:
                self._nominatim_cache = json.loads(_NOMINATIM_CACHE_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        with open(WORLDCITIES_PATH, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                city    = (row.get("city") or "").strip()
                ascii_  = (row.get("city_ascii") or "").strip()
                country = (row.get("country") or "").strip()
                if not city or not country:
                    continue
                try:
                    lat, lon = float(row.get("lat") or 0), float(row.get("lng") or 0)
                except (ValueError, TypeError):
                    continue
                pop = int(_to_float(row.get("population")))
                ck  = _norm_country(country)
                entry = {"city": city, "country": country, "lat": lat, "lon": lon, "population": pop}

                for k in {_norm_city(city), _norm_city(ascii_)}:
                    if not k:
                        continue
                    cur = self.by_pair.get((k, ck))
                    if cur is None or pop > cur["population"]:
                        self.by_pair[(k, ck)] = entry

                if (row.get("capital") or "").strip() == "primary":
                    self.capitals[ck] = entry
                if pop > self.largest_in_country.get(ck, {}).get("population", -1):
                    self.largest_in_country[ck] = entry

        for (city_key, _), entry in self.by_pair.items():
            if entry["population"] > self.largest_by_city.get(city_key, {}).get("population", -1):
                self.largest_by_city[city_key] = entry

        log.info("Loaded %d world-city pairs (%d countries, %d Nominatim cached)",
                 len(self.by_pair), len(self.largest_in_country), len(self._nominatim_cache))

    async def resolve(self, city: str, country: str) -> dict | None:
        ck = _norm_country(country)
        cl = _norm_city(city)

        if (cl, ck) in self.by_pair:
            return self.by_pair[(cl, ck)]

        if "," in cl:
            head = _norm_city(cl.split(",", 1)[0])
            if (head, ck) in self.by_pair:
                return self.by_pair[(head, ck)]
            if head in self.largest_by_city:
                return self.largest_by_city[head]

        if cl == ck and (ck in self.capitals or ck in self.largest_in_country):
            return self.capitals.get(ck) or self.largest_in_country.get(ck)

        if cl in self.largest_by_city:
            return self.largest_by_city[cl]

        geo = await self._nominatim(city, country)
        if geo:
            return geo

        return self.capitals.get(ck) or self.largest_in_country.get(ck)

    async def _nominatim(self, city: str, country: str) -> dict | None:
        key = f"{_norm_city(city)}|{_norm_country(country)}"
        if key in self._nominatim_cache:
            return self._nominatim_cache[key]

        data = None
        try:
            async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": UA}) as client:
                r = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": f"{city}, {country}", "format": "json", "limit": 1},
                )
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log.warning("  Nominatim failed for %s, %s: %s", city, country, e)
            return None
        finally:
            await asyncio.sleep(1.1)  # Nominatim usage policy: ≤1 req/sec

        entry: dict | None = None
        if data:
            first = data[0]
            try:
                entry = {
                    "city":       city,
                    "country":    country,
                    "lat":        float(first["lat"]),
                    "lon":        float(first["lon"]),
                    "population": 0,
                    "source":     "nominatim",
                }
            except (KeyError, ValueError, TypeError):
                entry = None

        # Only cache real hits; transient None responses get retried next run.
        if entry is not None:
            self._nominatim_cache[key] = entry
            self._persist_nominatim_cache()
        return entry

    def _persist_nominatim_cache(self) -> None:
        _NOMINATIM_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _NOMINATIM_CACHE_PATH.write_text(
            json.dumps(self._nominatim_cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ── Universe (single source of truth) ────────────────────────────────────────
def load_destinations() -> list[dict]:
    data = json.loads(DESTINATIONS_PATH.read_text(encoding="utf-8"))
    log.info("Loaded %d curated destinations from %s", len(data), DESTINATIONS_PATH)
    return data


def _destination_keys(destinations: list[dict]) -> set[tuple[str, str]]:
    """Return the set of normalized (city, country) keys for membership tests."""
    return {(_norm_city(d["city"]), _norm_country(d["country"])) for d in destinations}


def _in_universe(city: str, country: str, dest_keys: set[tuple[str, str]]) -> bool:
    return (_norm_city(city), _norm_country(country)) in dest_keys


# ── Loaders (filtered to universe) ───────────────────────────────────────────
def load_tl_hotels(dest_keys: set[tuple[str, str]]) -> list[dict]:
    out = []
    with open(TL_PATH, encoding="utf-8-sig", errors="replace") as f:
        for idx, row in enumerate(csv.DictReader(f)):
            hotel   = (row.get("Hotel") or "").strip()
            city    = (row.get("Location") or "").strip()
            country = (row.get("Country") or "").strip()
            if not hotel or not city:
                continue
            if not _in_universe(city, country, dest_keys):
                continue
            theme   = (row.get("Theme") or "").strip()
            score   = (row.get("Score") or "").strip()
            company = (row.get("Company") or "").strip()
            rank    = (row.get("Rank") or "0").strip()
            year    = (row.get("Year") or "").strip()
            rank_s  = f" #{rank}" if rank and rank != "0" else ""
            year_s  = f" ({year})" if year else ""
            text = (
                f"{hotel} — luxury hotel by {company} in {city}, {country}. "
                f"Theme: {theme}. Travel and Leisure World's Best{rank_s}{year_s}. "
                f"Score {score}/100. Editorial-quality property; one of the world's most acclaimed stays."
            )
            out.append({
                "_id":                f"tl-hotel-{idx}",
                "text":               text,
                "city":               city,
                "country":            _norm_country(country),
                "category":           "hotel",
                "source":             "travel_and_leisure_luxury",
                "star_rating":        5,
                "accommodation_type": "hotel",
                "score":              _to_float(score),
                "rank":               _to_float(rank),
                "year":               _to_float(year),
                "theme":              theme,
            })
    log.info("Loaded %d T+L hotels (filtered to universe)", len(out))
    return out


_TBO_STARS = {"FiveStar": 5, "FourStar": 4, "ThreeStar": 3}


def _detect_encoding(path: Path) -> str:
    """Sniff first 64 KB. UTF-8 if it decodes cleanly, else CP1252 (Windows Excel)."""
    with open(path, "rb") as f:
        sample = f.read(65536)
    try:
        sample.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


def load_tbo_hotels(dest_keys: set[tuple[str, str]]) -> list[dict]:
    """Streams 2.4 GB Hotels.csv. Per-star-per-city cap spreads coverage."""
    out: list[dict] = []
    seen: dict[tuple[str, int], int] = {}
    encoding = _detect_encoding(TBO_PATH)
    log.info("TBO encoding detected: %s", encoding)
    skipped_mojibake = 0
    with open(TBO_PATH, encoding=encoding, errors="replace") as f:
        for i, raw in enumerate(csv.DictReader(f)):
            if len(out) >= MAX_TBO_HOTELS:
                break
            row = {(k or "").strip(): (v or "") for k, v in raw.items()}
            name       = row.get("HotelName", "").strip()
            city       = row.get("cityName", "").strip()
            country    = row.get("countyName", "").strip()
            stars      = _TBO_STARS.get(row.get("HotelRating", "").strip())
            desc       = row.get("Description", "").strip()
            facilities = row.get("HotelFacilities", "").strip()
            if not name or not city or stars is None or len(desc) < 50:
                continue
            if "�" in name or "�" in city or "�" in country:
                skipped_mojibake += 1
                continue
            if not _in_universe(city, country, dest_keys):
                continue
            if seen.get((city, stars), 0) >= TBO_PER_STAR_CITY_CAP:
                continue
            code = (row.get("HotelCode") or "").strip() or str(i)
            out.append({
                "_id":                f"tbo-hotel-{code}",
                "text":               (f"{name} — {stars}-star hotel in {city}, {country}. "
                                       f"{desc[:600]} Facilities: {facilities[:300]}"),
                "city":               city,
                "country":            _norm_country(country),
                "category":           "hotel",
                "source":             "tbo",
                "star_rating":        stars,
                "accommodation_type": "hotel",
                "amenities":          facilities[:300],
            })
            seen[(city, stars)] = seen.get((city, stars), 0) + 1
            if i and i % 100_000 == 0:
                log.info("  ...streamed %d TBO rows, kept %d", i, len(out))
    log.info("Loaded %d TBO hotels (3★–5★, filtered to universe) — skipped %d mojibake rows",
             len(out), skipped_mojibake)
    return out


_MICHELIN_KEEP = {"3 stars", "2 stars", "1 star", "3 star", "2 star", "bib gourmand"}


def load_michelin(dest_keys: set[tuple[str, str]]) -> list[dict]:
    """Star/bib only — skips the long-tail 'Selected Restaurants' tier."""
    out = []
    with open(MICHELIN_PATH, encoding="utf-8-sig", errors="replace") as f:
        for i, row in enumerate(csv.DictReader(f)):
            name     = (row.get("Name") or "").strip()
            location = (row.get("Location") or "").strip()
            award    = (row.get("Award") or "").strip()
            if not name or not location or award.lower() not in _MICHELIN_KEEP:
                continue
            cuisine = (row.get("Cuisine") or "").strip()
            price   = (row.get("Price") or "").strip()
            desc    = (row.get("Description") or "").strip()
            city, _, country = location.partition(",")
            city, country = city.strip(), (country.strip() or city.strip())
            if not _in_universe(city, country, dest_keys):
                continue
            out.append({
                "_id":      f"michelin-{i}",
                "text":     (f"{name} — {cuisine} restaurant in {city}, {country}. "
                             f"Michelin {award}. Price {price}. {desc[:800]}"),
                "city":     city,
                "country":  _norm_country(country),
                "category": "restaurant",
                "cuisine":  cuisine,
                "award":    award,
                "price":    price,
                "source":   "michelin",
            })
    log.info("Loaded %d Michelin restaurants (filtered to universe)", len(out))
    return out


# ── Foursquare ───────────────────────────────────────────────────────────────
def _cache_path(city: str, country: str, subdir: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{city}__{country}").strip("_")
    d = CACHE / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe}.json"


def _load_cache(city: str, country: str, subdir: str) -> list[dict] | None:
    p = _cache_path(city, country, subdir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(city: str, country: str, records: list[dict], subdir: str) -> None:
    _cache_path(city, country, subdir).write_text(
        json.dumps(records, ensure_ascii=False), encoding="utf-8"
    )


def _category_names(place: dict) -> list[str]:
    return [c.get("name", "") for c in (place.get("categories") or []) if c.get("name")]


def _is_blocked(place: dict) -> bool:
    for name in _category_names(place):
        nl = name.lower()
        if any(blocked in nl for blocked in FSQ_CAT_BLOCKLIST):
            return True
    return False


def _build_fsq_text(place: dict, city: str, country: str) -> str:
    name = (place.get("name") or "").strip()
    cats = _category_names(place)
    primary = cats[0] if cats else "place"
    blurb   = ", ".join(cats[:3]) if cats else ""
    description = (place.get("description") or "").strip()
    rating = place.get("rating")
    price  = place.get("price")
    address = (place.get("location") or {}).get("formatted_address", "") or \
              (place.get("location") or {}).get("address", "")

    parts = [f"{name} — {primary} in {city}, {country}."]
    if blurb and blurb != primary:
        parts.append(f"Categories: {blurb}.")
    if description:
        parts.append(description[:400].strip())
    if rating is not None:
        parts.append(f"Rated {rating}/10.")
    if price:
        parts.append(f"Price tier {price}/4.")
    if address:
        parts.append(f"Address: {address}")
    return " ".join(parts).strip()


class _AuthError(Exception):
    pass


async def _fsq_call(client: httpx.AsyncClient, lat: float, lon: float,
                    categories: str, limit: int) -> list[dict]:
    """New Foursquare Places API call. Requests premium fields explicitly —
    these (rating, popularity, price, description) may add to the per-call
    credit cost but power the runtime metadata filters in Pinecone."""
    for attempt in range(3):
        try:
            r = await client.get(
                FOURSQUARE_ENDPOINT,
                params={
                    "ll":               f"{lat},{lon}",
                    "radius":           RADIUS_METERS,
                    "fsq_category_ids": categories,
                    "limit":            limit,
                    "sort":             "POPULARITY",
                    "fields":           "fsq_place_id,name,latitude,longitude,categories,location",
                },
                headers={
                    "Authorization":         f"Bearer {FOURSQUARE_API_KEY}",
                    "Accept":                "application/json",
                    "X-Places-Api-Version":  FOURSQUARE_API_VERSION,
                    "User-Agent":            UA,
                },
            )
            if r.status_code in (401, 403):
                log.error("  Foursquare auth error %d — check FOURSQUARE_API_KEY", r.status_code)
                raise _AuthError()
            if r.status_code == 429 or r.status_code >= 500:
                wait = 2 ** (attempt + 2)
                log.warning("  Foursquare %d — backing off %ds", r.status_code, wait)
                await asyncio.sleep(wait)
                continue
            r.raise_for_status()
            return r.json().get("results", []) or []
        except _AuthError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            wait = 2 ** (attempt + 2)
            log.warning("  Foursquare network %s — backing off %ds", type(e).__name__, wait)
            await asyncio.sleep(wait)
        except Exception as e:
            log.warning("  Foursquare unexpected: %s", e)
            return []
    return []


async def fetch_foursquare(
    destinations: list[dict],
    cities: CityIndex,
    categories: str,
    record_category: str,    # "restaurant" | "activity"
    cache_subdir: str,
) -> list[dict]:
    if not FOURSQUARE_API_KEY:
        log.error("FOURSQUARE_API_KEY not set — cannot fetch %s", record_category)
        return []

    out: list[dict] = []
    seen: set[str] = set()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for d in destinations:
            city, country = d["city"], d["country"]
            cached = _load_cache(city, country, cache_subdir)
            if cached is not None:
                for rec in cached:
                    pid = rec.get("place_id") or rec.get("_id")
                    if pid and pid not in seen:
                        seen.add(pid)
                        out.append(rec)
                log.info("  [cache] %d %s for %s, %s", len(cached), record_category, city, country)
                continue

            wc = await cities.resolve(city, country)
            if not wc:
                log.warning("  no coords for %s, %s — skipping", city, country)
                _save_cache(city, country, [], cache_subdir)
                continue

            try:
                places = await _fsq_call(client, wc["lat"], wc["lon"], categories, MAX_PER_CITY)
            except _AuthError:
                log.error("Aborted %s fetch due to auth error", record_category)
                break

            city_recs: list[dict] = []
            for place in places:
                fsq_id = place.get("fsq_place_id") or place.get("fsq_id")  # new + legacy
                name   = (place.get("name") or "").strip()
                if not fsq_id or not name or fsq_id in seen:
                    continue
                if _is_blocked(place):
                    continue
                seen.add(fsq_id)

                # New API returns lat/lon at top level; legacy nests under geocodes.main
                lat = place.get("latitude")
                lon = place.get("longitude")
                if lat is None or lon is None:
                    geo = (place.get("geocodes") or {}).get("main") or {}
                    lat = geo.get("latitude",  wc["lat"])
                    lon = geo.get("longitude", wc["lon"])

                location = place.get("location") or {}
                rec = {
                    "_id":         f"foursquare-{fsq_id}",
                    "text":        _build_fsq_text(place, city, country),
                    "city":        city,
                    "country":     country,
                    "category":    record_category,
                    "source":      "foursquare",
                    "place_id":    fsq_id,
                    "name":        name,
                    "lat":         lat,
                    "lon":         lon,
                    "categories":  ",".join(_category_names(place)),
                    "address":     location.get("formatted_address", "") or location.get("address", ""),
                }
                # Only include premium fields when present — Pinecone rejects null metadata.
                for src_key, dst_key in [("rating", "rating"), ("popularity", "popularity"),
                                          ("price", "price_tier"), ("website", "website"),
                                          ("tel", "phone")]:
                    v = place.get(src_key)
                    if v is not None and v != "":
                        rec[dst_key] = v
                desc = (place.get("description") or "").strip()
                if desc:
                    rec["description"] = desc[:400]
                city_recs.append(rec)
                out.append(rec)

            _save_cache(city, country, city_recs, cache_subdir)
            log.info("  Foursquare: %d %s for %s, %s", len(city_recs), record_category, city, country)
            await asyncio.sleep(1.0)   # ~1 QPS to stay under trial-tier rate limit

    log.info("Loaded %d Foursquare %s total", len(out), record_category)
    return out


# ── Pinecone upsert ──────────────────────────────────────────────────────────
_TRANSIENT_TOKENS = ("429", "resource_exhausted", "500", "502", "503", "504",
                     "timeout", "connection")
# Hard caps where retrying just burns time
_HARD_LIMIT_TOKENS = ("embedding token limit", "monthly", "upgrade your plan")


def _is_transient(err: str) -> bool:
    e = err.lower()
    if any(t in e for t in _HARD_LIMIT_TOKENS):
        return False
    return any(t in e for t in _TRANSIENT_TOKENS)


def _to_vector_record(rec: dict, embedding: list[float]) -> dict:
    """Build a Pinecone upsert payload. `text` goes into metadata for retrieval debugging."""
    meta = {k: v for k, v in rec.items() if k != "_id" and v is not None and v != ""}
    return {"id": rec["_id"], "values": embedding, "metadata": meta}


async def upsert_batched(namespace: str, records: list[dict]) -> None:
    if not records:
        log.info("Skipping %s — nothing to upsert", namespace)
        return
    index = await get_pinecone_index()
    total = len(records)
    for i in range(0, total, BATCH_SIZE):
        chunk = records[i:i + BATCH_SIZE]
        texts = [r.get("text", "") for r in chunk]
        for attempt in range(4):
            try:
                embeddings = await embed_texts(texts)
                vectors = [_to_vector_record(r, e) for r, e in zip(chunk, embeddings)]
                await asyncio.to_thread(lambda v=vectors: index.upsert(namespace=namespace, vectors=v))
                break
            except Exception as e:
                if _is_transient(str(e)):
                    wait = UPSERT_RETRY_BACKOFF * (attempt + 1)
                    log.warning("  transient error at %d/%d — waiting %ds (%s)", i, total, wait, e)
                    await asyncio.sleep(wait)
                else:
                    log.error("  unrecoverable at batch %d — skipping: %s", i, e)
                    break
        else:
            log.error("  giving up on batch %d after 4 retries", i)
            continue
        log.info("  upserted %d / %d into '%s'", min(i + BATCH_SIZE, total), total, namespace)
        await asyncio.sleep(UPSERT_PAUSE_SEC)


# ── Main ─────────────────────────────────────────────────────────────────────
async def main(only: set[str]) -> None:
    do_h, do_r, do_a = "hotels" in only, "restaurants" in only, "activities" in only

    destinations = load_destinations()
    dest_keys = _destination_keys(destinations)

    hotels      = (load_tl_hotels(dest_keys) + load_tbo_hotels(dest_keys)) if do_h else []
    restaurants = load_michelin(dest_keys) if do_r else []

    cities = CityIndex()

    if do_h:
        hotels += await fetch_foursquare(destinations, cities, LODGING_CATEGORIES,
                                          "hotel", "hotels")
    activities = (await fetch_foursquare(destinations, cities, ACTIVITY_CATEGORIES,
                                          "activity", "activities") if do_a else [])
    if do_r:
        restaurants += await fetch_foursquare(destinations, cities, DINING_CATEGORIES,
                                               "restaurant", "restaurants")

    log.info("=== Upserting to Pinecone ===")
    if do_h: await upsert_batched("hotels", hotels)
    if do_r: await upsert_batched("restaurants", restaurants)
    if do_a: await upsert_batched("activities", activities)

    log.info("=== Done: hotels=%d restaurants=%d activities=%d ===",
             len(hotels), len(restaurants), len(activities))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--only", default="hotels,restaurants,activities",
                   help="Comma-separated namespaces: hotels, restaurants, activities")
    args = p.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    invalid = only - {"hotels", "restaurants", "activities"}
    if invalid:
        p.error(f"Unknown namespace(s): {invalid}")
    asyncio.run(main(only))
