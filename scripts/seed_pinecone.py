"""
One-time Pinecone seed. Populates 3 namespaces with integrated embedding:

    hotels       — Travel+Leisure luxury  + TBO 3-5★ + Geoapify accommodations
    restaurants  — Michelin star/bib      + Geoapify catering
    activities   — Geoapify tourism / heritage / nature POIs

Usage:
    $env:PINECONE_API_KEY="..."; $env:PINECONE_INDEX_NAME="sonder-index"
    $env:GEOAPIFY_API_KEY="..."
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
from ali.vector.client import get_pinecone_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("seed")

DATA  = Path("data/seed")
CACHE = Path(".cache/geoapify_activities")
CACHE.mkdir(parents=True, exist_ok=True)

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "")
UA = "Sonder/1.0 (https://discoversonder.com)"

MAX_TBO_HOTELS        = 3000
# Geoapify free tier: 3000 credits/day, 1 credit per request up to 20 results.
# 20 results × 3 categories × 750 cities = 2250 credits — fits with ~25% headroom.
MAX_PER_CITY          = 20
MAX_UNIVERSE          = 750
BATCH_SIZE            = 50
UPSERT_PAUSE_SEC      = 6
UPSERT_RETRY_BACKOFF  = 60
TBO_PER_STAR_CITY_CAP = 15

ACTIVITY_CATS = ",".join([
    # Sightseeing & landmarks
    "tourism.attraction",
    "tourism.sights",
    # Culture & arts (theatres, galleries, arts centres)
    "entertainment.museum",
    "entertainment.culture",
    # Family / playful
    "entertainment.theme_park",
    "entertainment.water_park",
    "entertainment.activity_park",
    "entertainment.aquarium",
    "entertainment.zoo",
    # Outdoor & nature
    "leisure.park",
    "leisure.spa",
    "leisure.picnic",
    "beach",
    "natural.water",
    "natural.forest",
    "natural.mountain",
    "natural.protected_area",
    # Heritage
    "heritage.unesco",
    # Drink-country experiences (wineries, craft brewers, distilleries)
    "production.winery",
    "production.brewery",
])
CATERING_CATS = ",".join([
    "catering.restaurant",
    "catering.cafe",
    "catering.bar",
    "catering.pub",
    "catering.biergarten",
    "catering.ice_cream",
    "catering.taproom",
    "catering.food_court",
])
ACCOMMODATION_CATS = ",".join([
    "accommodation.hotel",
    "accommodation.guest_house",
    "accommodation.hostel",
    "accommodation.chalet",
    "accommodation.apartment",   # serviced apartments / vacation rentals
    "accommodation.hut",         # alpine huts, glamping bases
    "camping.camp_site",         # campgrounds (incl. glamping) — separate Geoapify namespace
])


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
# Aliases built from two data sources, no hardcoded list:
#   1. REST Countries API (restcountries.com) — every common name, official name,
#      ISO 2/3-letter code, altSpelling, and native name → canonical common name.
#      Also generates comma-swapped forms ("South Korea" → "Korea, South") since
#      that's how some datasets format names.
#   2. worldcities.csv admin_name column → country (subdivisions: states, provinces,
#      regions). Catches "South Australia" → "australia" without manual mapping.
# Cached to .cache/country_aliases.json so re-runs skip the API call.

_COUNTRY_ALIASES_CACHE = Path(".cache/country_aliases.json")


def _fetch_country_aliases() -> dict[str, str]:
    if _COUNTRY_ALIASES_CACHE.exists():
        try:
            return json.loads(_COUNTRY_ALIASES_CACHE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    aliases: dict[str, str] = {}

    # 1. REST Countries — official country name database.
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
                # Comma-swap form: "South Korea" → "Korea, South"
                parts = c["name"]["common"].split(" ")
                if len(parts) > 1:
                    variants.append(f"{parts[-1]}, {' '.join(parts[:-1])}")

                for v in variants:
                    if isinstance(v, str) and v.strip():
                        aliases[v.strip().lower()] = canonical
    except Exception as e:
        log.warning("REST Countries fetch failed: %s — continuing with subdivision data only", e)

    # 2. worldcities.csv admin_name → country (handles "South Australia", "Hawaii", etc.)
    try:
        with open(WORLDCITIES_PATH, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                admin   = (row.get("admin_name") or "").strip().lower()
                country = (row.get("country") or "").strip().lower()
                if not admin or not country:
                    continue
                canonical = aliases.get(country, country)
                if admin not in aliases:        # never override a real country (Georgia)
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
    # Punctuation-stripped retry: "U.S.A." → "usa"
    no_punct = c.replace(".", "").strip()
    if no_punct in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[no_punct]
    # Last comma segment: "CA, USA" → "USA" → "united states"
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
    symmetrically at index build and at resolve so the two sides always agree.
    """
    s = (city or "").strip().lower()
    s = re.sub(r"[.\-_/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Common saint abbreviations — algorithmic, not city-specific
    s = re.sub(r"\bst\b", "saint", s)
    s = re.sub(r"\bste\b", "sainte", s)
    s = re.sub(r"\bmt\b", "mount", s)
    return s


# ── World-cities coord index ─────────────────────────────────────────────────
_NOMINATIM_CACHE_PATH = Path(".cache/nominatim_cities.json")


class CityIndex:
    """Coord lookup with progressive fallbacks for messy real-world inputs.

    Fast path: worldcities.csv (1.6M cities, no API call).
    Slow path: Nominatim (OpenStreetMap geocoder) for small vacation towns not
    in worldcities — Interlaken, Hallstatt, Tulum, Positano, Sedona. Cached
    per (city, country) so each small town hits the API at most once.
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

        # State/region embedded in city: "Adelaide, South Australia" → "adelaide"
        if "," in cl:
            head = _norm_city(cl.split(",", 1)[0])
            if (head, ck) in self.by_pair:
                return self.by_pair[(head, ck)]
            if head in self.largest_by_city:
                return self.largest_by_city[head]

        # City IS the country (Aruba, Monaco)
        if cl == ck and (ck in self.capitals or ck in self.largest_in_country):
            return self.capitals.get(ck) or self.largest_in_country.get(ck)

        # Same city name anywhere (Dubai, Hong Kong)
        if cl in self.largest_by_city:
            return self.largest_by_city[cl]

        # Slow path: Nominatim. Handles vacation towns not in worldcities
        # (Interlaken, Hallstatt, Tulum, Positano, Sedona, ...). Cached.
        geo = await self._nominatim(city, country)
        if geo:
            return geo

        # Last resort: country's capital
        return self.capitals.get(ck) or self.largest_in_country.get(ck)

    async def _nominatim(self, city: str, country: str) -> dict | None:
        key = f"{_norm_city(city)}|{_norm_country(country)}"
        if key in self._nominatim_cache:
            return self._nominatim_cache[key]   # may be None (cached miss)

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

        self._nominatim_cache[key] = entry
        self._persist_nominatim_cache()
        return entry

    def _persist_nominatim_cache(self) -> None:
        _NOMINATIM_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _NOMINATIM_CACHE_PATH.write_text(
            json.dumps(self._nominatim_cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ── Loaders ──────────────────────────────────────────────────────────────────
def load_tl_hotels() -> list[dict]:
    out = []
    with open(TL_PATH, encoding="utf-8-sig", errors="replace") as f:
        for idx, row in enumerate(csv.DictReader(f)):
            hotel   = (row.get("Hotel") or "").strip()
            city    = (row.get("Location") or "").strip()
            country = (row.get("Country") or "").strip()
            if not hotel or not city:
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
                "_id": f"tl-hotel-{idx}",
                "text": text,
                "city": city,
                "country": _norm_country(country),
                "category": "hotel",
                "source": "travel_and_leisure_luxury",
                "star_rating": 5,
                "accommodation_type": "hotel",
                "score": _to_float(score),
                "rank":  _to_float(rank),
                "year":  _to_float(year),
                "theme": theme,
            })
    log.info("Loaded %d T+L hotels", len(out))
    return out


_TBO_STARS = {"FiveStar": 5, "FourStar": 4, "ThreeStar": 3}  # 1★/2★ skipped


def _detect_encoding(path: Path) -> str:
    """Sniff first 64 KB. UTF-8 if it decodes cleanly, else CP1252 (Windows Excel)."""
    with open(path, "rb") as f:
        sample = f.read(65536)
    try:
        sample.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


def load_tbo_hotels() -> list[dict]:
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
            # Drop rows whose key fields hit the U+FFFD replacement char — that means
            # an undecodable byte landed in the name/city/country and downstream
            # resolve() will fail. Lossy decoding is worse than skipping the record.
            if "�" in name or "�" in city or "�" in country:
                skipped_mojibake += 1
                continue
            if seen.get((city, stars), 0) >= TBO_PER_STAR_CITY_CAP:
                continue
            code = (row.get("HotelCode") or "").strip() or str(i)
            out.append({
                "_id": f"tbo-hotel-{code}",
                "text": (f"{name} — {stars}-star hotel in {city}, {country}. "
                         f"{desc[:600]} Facilities: {facilities[:300]}"),
                "city": city,
                "country": _norm_country(country),
                "category": "hotel",
                "source": "tbo",
                "star_rating": stars,
                "accommodation_type": "hotel",
                "amenities": facilities[:300],
            })
            seen[(city, stars)] = seen.get((city, stars), 0) + 1
            if i and i % 100_000 == 0:
                log.info("  ...streamed %d TBO rows, kept %d", i, len(out))
    log.info("Loaded %d TBO hotels (3★–5★) — skipped %d mojibake rows",
             len(out), skipped_mojibake)
    return out


_MICHELIN_KEEP = {"3 stars", "2 stars", "1 star", "3 star", "2 star", "bib gourmand"}


def load_michelin() -> list[dict]:
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
            out.append({
                "_id": f"michelin-{i}",
                "text": (f"{name} — {cuisine} restaurant in {city}, {country}. "
                         f"Michelin {award}. Price {price}. {desc[:800]}"),
                "city": city,
                "country": _norm_country(country),
                "category": "restaurant",
                "cuisine": cuisine,
                "award":   award,
                "price":   price,
                "source":  "michelin",
            })
    log.info("Loaded %d Michelin restaurants", len(out))
    return out


# ── Geoapify Places ──────────────────────────────────────────────────────────
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


def _humanize(cat: str) -> str:
    return cat.split(".", 1)[-1].replace("_", " ")


# Geoapify echoes OSM amenity flags as "categories" (internet_access, wheelchair,
# building, access, etc.) alongside the real taxonomy. We only keep namespaces we
# explicitly query so downstream filtering doesn't have to skip junk tags.
_VALID_CAT_PREFIXES = (
    "accommodation", "catering", "tourism", "entertainment",
    "leisure", "natural", "heritage", "production",
    "sport", "commercial", "beach", "camping",
)


def _filter_cats(cats: list[str]) -> list[str]:
    return [c for c in cats if c and c.split(".", 1)[0] in _VALID_CAT_PREFIXES]


def _build_text(props: dict, city: str, country: str) -> str:
    name    = props.get("name") or ""
    cats    = _filter_cats(props.get("categories") or [])
    primary = _humanize(cats[0]) if cats else "place"
    blurb   = ", ".join(_humanize(c) for c in cats[:4])
    address = props.get("address_line2") or props.get("formatted") or ""
    return (f"{name} — {primary} in {city}, {country}. "
            f"Categories: {blurb}. Address: {address}").strip()


class _AuthError(Exception):
    pass


async def _places_call(client: httpx.AsyncClient, lat: float, lon: float,
                       categories: str, limit: int) -> list[dict]:
    """Returns features list. Retries on 429/5xx/network. Raises _AuthError on 401/403."""
    for attempt in range(3):
        try:
            r = await client.get(
                "https://api.geoapify.com/v2/places",
                params={
                    "categories": categories,
                    "filter":     f"circle:{lon},{lat},15000",
                    "limit":      limit,
                    "apiKey":     GEOAPIFY_API_KEY,
                },
            )
            if r.status_code in (401, 403):
                log.error("  Geoapify auth error %d — check GEOAPIFY_API_KEY", r.status_code)
                raise _AuthError()
            if r.status_code == 429 or r.status_code >= 500:
                wait = 2 ** (attempt + 2)
                log.warning("  Geoapify %d — backing off %ds", r.status_code, wait)
                await asyncio.sleep(wait)
                continue
            r.raise_for_status()
            return r.json().get("features", [])
        except _AuthError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            wait = 2 ** (attempt + 2)
            log.warning("  Geoapify network %s — backing off %ds", type(e).__name__, wait)
            await asyncio.sleep(wait)
        except Exception as e:
            log.warning("  Geoapify unexpected: %s", e)
            return []
    return []


async def fetch_geoapify(
    universe: list[dict],
    cities: CityIndex,
    categories: str,
    record_category: str,   # "hotel" | "restaurant" | "activity"
    cache_subdir: str,
) -> list[dict]:
    if not GEOAPIFY_API_KEY:
        log.error("GEOAPIFY_API_KEY not set — cannot fetch %s", record_category)
        return []

    out: list[dict] = []
    seen: set[str] = set()

    async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": UA}) as client:
        for u in universe:
            city, country, reasons = u["city"], u["country"], u["reasons"]
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
                features = await _places_call(client, wc["lat"], wc["lon"], categories, MAX_PER_CITY)
            except _AuthError:
                log.error("Aborted %s fetch due to auth error", record_category)
                break

            city_recs: list[dict] = []
            for f in features:
                props = f.get("properties", {})
                pid = props.get("place_id") or props.get("datasource", {}).get("raw", {}).get("osm_id")
                if not pid or pid in seen or not props.get("name"):
                    continue
                seen.add(pid)
                rec = {
                    "_id":             f"geoapify-{pid}",
                    "text":            _build_text(props, city, country),
                    "city":            city,
                    "country":         country,
                    "category":        record_category,
                    "source":          "geoapify",
                    "place_id":        pid,
                    "name":            props.get("name", ""),
                    "lat":             props.get("lat", wc["lat"]),
                    "lon":             props.get("lon", wc["lon"]),
                    "categories":      ",".join(_filter_cats(props.get("categories") or [])),
                    "address":         props.get("address_line2") or props.get("formatted") or "",
                    "universe_reason": reasons,
                }
                city_recs.append(rec)
                out.append(rec)

            _save_cache(city, country, city_recs, cache_subdir)
            log.info("  Geoapify: %d %s for %s, %s", len(city_recs), record_category, city, country)
            await asyncio.sleep(0.2)

    log.info("Loaded %d Geoapify %s total", len(out), record_category)
    return out


# ── Pinecone upsert ──────────────────────────────────────────────────────────
_TRANSIENT_TOKENS = ("429", "resource_exhausted", "500", "502", "503", "504",
                     "timeout", "connection")


def _is_transient(err: str) -> bool:
    e = err.lower()
    return any(t in e for t in _TRANSIENT_TOKENS)


async def upsert_batched(namespace: str, records: list[dict]) -> None:
    if not records:
        log.info("Skipping %s — nothing to upsert", namespace)
        return
    index = await get_pinecone_index()
    total = len(records)
    for i in range(0, total, BATCH_SIZE):
        chunk = records[i:i + BATCH_SIZE]
        for attempt in range(4):
            try:
                await asyncio.to_thread(lambda: index.upsert_records(namespace=namespace, records=chunk))
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


# ── Destination universe ─────────────────────────────────────────────────────
POPULATION_LAYER_N = 500


def build_universe(cities: CityIndex, hotels: list[dict],
                   restaurants: list[dict]) -> list[dict]:
    """
    Three algorithmic layers, fully data-derived. Each city carries the list of
    layers it qualifies under in `reasons` — runtime can filter by any of them.

      1. editorial   — T+L luxury + Michelin star/bib cities. Always added first.
                       Editors picked these; we don't second-guess.
      2. population  — top POPULATION_LAYER_N worldcities by population.
                       Geographic floor: every major metro gets in.
      3. tbo_supply  — TBO 3-5★ cities ranked by hotel count. Fills the long tail
                       of practical booking destinations.

    Priority order = insertion order. A city that qualifies under multiple layers
    keeps all reasons in its list. Capped at MAX_UNIVERSE.
    """
    def canon(c: str, co: str) -> tuple[str, str]:
        return (c.strip(), _norm_country(co))

    # ── Build per-layer ordered lists ────────────────────────────────────────
    edit_counts: dict[tuple[str, str], int] = {}
    for r in hotels + restaurants:
        if r["source"] in ("travel_and_leisure_luxury", "michelin") and r["city"]:
            p = canon(r["city"], r["country"])
            edit_counts[p] = edit_counts.get(p, 0) + 1
    editorial = [p for p, _ in sorted(edit_counts.items(), key=lambda x: -x[1])]

    unique = list({id(v): v for v in cities.by_pair.values()}.values())
    by_pop = sorted(unique, key=lambda c: -c["population"])
    population = [canon(c["city"], c["country"]) for c in by_pop[:POPULATION_LAYER_N]]

    tbo_counts: dict[tuple[str, str], int] = {}
    for r in hotels:
        if r["source"] == "tbo" and r["city"]:
            p = canon(r["city"], r["country"])
            tbo_counts[p] = tbo_counts.get(p, 0) + 1
    tbo_supply = [p for p, _ in sorted(tbo_counts.items(), key=lambda x: -x[1])]

    # ── Merge — preserve order, accumulate reasons, cap ──────────────────────
    reasons: dict[tuple[str, str], list[str]] = {}
    for p in editorial:
        reasons.setdefault(p, []).append("editorial")
    for p in population:
        reasons.setdefault(p, []).append("population")
    for p in tbo_supply:
        reasons.setdefault(p, []).append("tbo_supply")

    universe: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for p in editorial + population + tbo_supply:
        if p in seen:
            continue
        seen.add(p)
        city, country = p
        universe.append({"city": city, "country": country, "reasons": reasons[p]})
        if len(universe) >= MAX_UNIVERSE:
            break

    n_edit = sum(1 for u in universe if "editorial"  in u["reasons"])
    n_pop  = sum(1 for u in universe if "population" in u["reasons"])
    n_tbo  = sum(1 for u in universe if "tbo_supply" in u["reasons"])
    log.info(
        "=== Universe: %d cities (editorial %d / population %d / tbo_supply %d) ===",
        len(universe), n_edit, n_pop, n_tbo,
    )
    return universe


# ── Main ─────────────────────────────────────────────────────────────────────
async def main(only: set[str]) -> None:
    do_h, do_r, do_a = "hotels" in only, "restaurants" in only, "activities" in only

    hotels      = load_tl_hotels() + load_tbo_hotels() if do_h else []
    restaurants = load_michelin() if do_r else []

    cities   = CityIndex()
    # Universe needs hotel+restaurant POI counts even when only seeding activities.
    h_for_universe = hotels      or (load_tl_hotels() + load_tbo_hotels())
    r_for_universe = restaurants or load_michelin()
    universe = build_universe(cities, h_for_universe, r_for_universe)

    # Tag every curated record with the universe_reason its city qualifies under.
    # Cities outside the capped universe → reason is just the record's own source
    # (T+L/Michelin always count as "editorial"; TBO always counts as "tbo_supply").
    reasons_map = {(u["city"], u["country"]): u["reasons"] for u in universe}
    source_default = {
        "travel_and_leisure_luxury": ["editorial"],
        "michelin":                  ["editorial"],
        "tbo":                       ["tbo_supply"],
    }
    for r in hotels + restaurants:
        key = (r["city"].strip(), r["country"])
        r["universe_reason"] = reasons_map.get(key) or source_default.get(r["source"], [])

    if do_h:
        hotels += await fetch_geoapify(universe, cities, ACCOMMODATION_CATS, "hotel", "hotels")
    activities = (await fetch_geoapify(universe, cities, ACTIVITY_CATS, "activity", "activities")
                  if do_a else [])
    if do_r:
        restaurants += await fetch_geoapify(universe, cities, CATERING_CATS, "restaurant", "restaurants")

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
