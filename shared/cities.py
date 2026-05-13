"""
On-demand city context via free public APIs (no key, no signup).

Used by the itinerary generator to enrich a destination with country, climate,
currency, and Wikipedia-sourced description before passing context to the LLM.

Cached to disk so repeat lookups are instant and we never re-hit the APIs.
"""

import asyncio
import json
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_CACHE_FILE = Path(".cache/cities.json")
_cache: dict = {}

if _CACHE_FILE.exists():
    try:
        _cache = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _cache = {}

_UA = "Sonder/1.0 (https://discoversonder.com; hello@discoversonder.com)"


async def get_city_context(city: str, country: str | None = None) -> dict:
    """Return rich city context. Hits cache first; falls back to public APIs."""
    key = f"{city.strip().lower()}|{(country or '').strip().lower()}"
    if key in _cache:
        return _cache[key]

    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": _UA}) as client:
        geo = await _nominatim(client, city, country)
        if not geo or not geo.get("lat"):
            ctx = _stub(city, country)
            _cache[key] = ctx
            _persist()
            return ctx

        wiki, country_data, climate = await asyncio.gather(
            _wikipedia(client, city),
            _rest_countries(client, geo.get("country_code")),
            _open_meteo_climate(client, geo["lat"], geo["lon"]),
            return_exceptions=True,
        )

    ctx = {
        "city":         city,
        "country":      geo.get("country"),
        "country_code": geo.get("country_code"),
        "lat":          geo.get("lat"),
        "lon":          geo.get("lon"),
        "description":  _safe(wiki, "extract", ""),
        "wiki_url":     _safe(wiki, "content_url", ""),
        "currency":     _safe(country_data, "currency", ""),
        "languages":    _safe(country_data, "languages", []),
        "capital":      _safe(country_data, "capital", ""),
        "climate":      climate if not isinstance(climate, Exception) else None,
    }
    _cache[key] = ctx
    _persist()
    return ctx


def _stub(city: str, country: str | None) -> dict:
    return {
        "city": city, "country": country, "country_code": None,
        "lat": None, "lon": None, "description": "",
        "currency": "", "languages": [], "capital": "", "climate": None,
    }


def _safe(obj, key, default=None):
    if isinstance(obj, Exception) or obj is None:
        return default
    return obj.get(key, default) if isinstance(obj, dict) else default


def _persist() -> None:
    _CACHE_FILE.parent.mkdir(exist_ok=True, parents=True)
    _CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False, indent=2), encoding="utf-8")


async def _nominatim(client: httpx.AsyncClient, city: str, country: str | None) -> dict:
    q = f"{city}, {country}" if country else city
    try:
        r = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": 1, "addressdetails": 1},
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return {}
        first = data[0]
        addr = first.get("address", {})
        return {
            "lat": float(first["lat"]),
            "lon": float(first["lon"]),
            "country": addr.get("country"),
            "country_code": (addr.get("country_code") or "").upper() or None,
        }
    except Exception as e:
        logger.warning("Nominatim failed for %s: %s", q, e)
        return {}


async def _wikipedia(client: httpx.AsyncClient, title: str) -> dict:
    try:
        r = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}")
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("Wikipedia summary failed for %s: %s", title, e)
        return {}


async def _rest_countries(client: httpx.AsyncClient, country_code: str | None) -> dict:
    if not country_code:
        return {}
    try:
        r = await client.get(f"https://restcountries.com/v3.1/alpha/{country_code}")
        r.raise_for_status()
        d = r.json()[0]
        currencies = d.get("currencies", {})
        currency_name = next(iter(currencies.values()), {}).get("name") if currencies else ""
        return {
            "currency":  currency_name,
            "languages": list(d.get("languages", {}).values()),
            "capital":   (d.get("capital") or [None])[0],
        }
    except Exception as e:
        logger.warning("REST Countries failed for %s: %s", country_code, e)
        return {}


async def _open_meteo_climate(client: httpx.AsyncClient, lat: float, lon: float) -> dict:
    """Returns per-month avg temp + precipitation (1991-2020 normals)."""
    try:
        r = await client.get(
            "https://climate-api.open-meteo.com/v1/climate",
            params={
                "latitude": lat, "longitude": lon,
                "start_date": "1991-01-01", "end_date": "2020-12-31",
                "models": "EC_Earth3P_HR",
                "daily": "temperature_2m_mean,precipitation_sum",
            },
        )
        r.raise_for_status()
        raw = r.json().get("daily", {})
        dates = raw.get("time", [])
        temps = raw.get("temperature_2m_mean", [])
        precs = raw.get("precipitation_sum", [])
        by_month: dict[int, dict] = {m: {"temp": [], "prec": []} for m in range(1, 13)}
        for date, t, p in zip(dates, temps, precs):
            if t is None or p is None:
                continue
            m = int(date.split("-")[1])
            by_month[m]["temp"].append(t)
            by_month[m]["prec"].append(p)
        return {
            str(m): {
                "avg_temp_c":  round(sum(v["temp"]) / len(v["temp"]), 1) if v["temp"] else None,
                "avg_prec_mm": round(sum(v["prec"]) / len(v["prec"]), 1) if v["prec"] else None,
            } for m, v in by_month.items()
        }
    except Exception as e:
        logger.warning("Open-Meteo failed for %s,%s: %s", lat, lon, e)
        return {}
