"""
Pixabay image search — used to auto-illustrate social posts and
trip-recap cards. Free, no attribution required for the URLs we use.

Single entry point: `fetch_image_url(query)` returns one large image
URL for the best-matching travel photo, or None if Pixabay is
unconfigured / errors / returns no hits.

Results are in-process cached by query (lower-case, trimmed) for the
lifetime of the process so repeated posts about "kyoto" don't burn
quota and don't show 12 different photos for the same destination.

Pixabay docs: https://pixabay.com/api/docs/
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

import httpx

from shared.config import PIXABAY_API_KEY

logger = logging.getLogger(__name__)

_CACHE: dict[str, Optional[str]] = {}
_TIMEOUT_S = 4.0
_API = "https://pixabay.com/api/"


def _normalise(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").lower().strip())


def _best_url(hit: dict) -> Optional[str]:
    """Pick the highest-resolution URL Pixabay returned for a hit.

    Resolution ladder (Pixabay docs):
      - imageURL       → full source resolution (often 4-6K). Only
                         returned to API consumers that have accepted
                         Pixabay's commercial terms.
      - fullHDURL      → 1920x1080 JPEG.
      - largeImageURL  → ~1280px wide JPEG (the legacy default).
      - webformatURL   → ~640px JPEG (fallback for tiny thumbs).

    Prefer the biggest available so the dashboard backdrop renders
    sharp on 4K displays instead of upscaling a 1280px source.
    """
    for k in ("imageURL", "fullHDURL", "largeImageURL", "webformatURL"):
        u = hit.get(k)
        if u:
            return u
    return None


async def fetch_image_urls(query: str, *, count: int = 5, category: str = "travel") -> list[str]:
    """Up to `count` distinct large image URLs for the query, ranked
    by Pixabay's popularity. Cached in-process alongside the single-
    image cache (different key shape) so the destination-photo route
    can ask for a montage without re-paying Pixabay quota.

    `min_width=3840` filters to photos whose source is at least 4K
    wide — so even when Pixabay only exposes a 1920x1080 URL in the
    response, the source it was downscaled from is 4K, giving us the
    sharpest possible JPEG.
    """
    if not PIXABAY_API_KEY:
        return []
    q = _normalise(query)
    if not q:
        return []
    # Cache key includes the 4k bump so the old 1280px-era entries
    # don't bleed through and serve low-res URLs after the upgrade.
    cache_key = f"__many4k__{count}__{q}"
    if cache_key in _CACHE:
        cached = _CACHE.get(cache_key)
        return list(cached) if isinstance(cached, (list, tuple)) else []
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.get(_API, params={
                "key":            PIXABAY_API_KEY,
                "q":              q,
                "image_type":     "photo",
                "orientation":    "horizontal",
                "category":       category,
                "safesearch":     "true",
                "order":          "popular",
                "per_page":       max(3, min(count, 20)),
                "min_width":      3840,
                "min_height":     2160,
            })
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits") or []
            urls: list[str] = []
            for h in hits[:count]:
                u = _best_url(h)
                if u:
                    urls.append(u)
            _CACHE[cache_key] = urls
            return urls
    except Exception as e:
        logger.warning("Pixabay multi-search failed for %r: %s", q, e)
        _CACHE[cache_key] = []
        return []


async def fetch_image_url(query: str, *, category: str = "travel") -> Optional[str]:
    """One large image URL for the given query, or None.

    Caches by normalised query for the process lifetime. category
    defaults to 'travel' to keep results destination-shaped — feed
    posts that mention food / nightlife / etc still land relevant
    images because Pixabay's relevance engine is decent.

    Filtered to 4K-source photos via `min_width=3840`; returns the
    highest-resolution URL Pixabay exposed for the hit.
    """
    if not PIXABAY_API_KEY:
        return None
    q = _normalise(query)
    if not q:
        return None
    # Cache key bumped so post-upgrade calls don't serve pre-upgrade
    # 1280px entries cached before the min_width filter shipped.
    cache_key = f"__one4k__{q}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.get(_API, params={
                "key":            PIXABAY_API_KEY,
                "q":              q,
                "image_type":     "photo",
                "orientation":    "horizontal",
                "category":       category,
                "safesearch":     "true",
                "order":          "popular",
                "per_page":       3,
                "min_width":      3840,
                "min_height":     2160,
            })
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits") or []
            if not hits:
                _CACHE[cache_key] = None
                return None
            url = _best_url(hits[0])
            _CACHE[cache_key] = url
            return url
    except Exception as e:
        logger.warning("Pixabay search failed for %r: %s", q, e)
        return None


async def fetch_image_url_for_post_text(text: str) -> Optional[str]:
    """Best-effort image lookup from arbitrary post text. Strips
    common filler so the query lands on the actual subject of the
    post. Falls back to None when the text is too generic to mine."""
    if not text:
        return None
    cleaned = re.sub(r"[^\w\s]", " ", text).lower()
    # Drop stop-word filler so multi-sentence posts query on the
    # meat ('lisbon coffee golden hour' is better than 'the rain
    # in lisbon was lighter than i expected').
    stop = {
        "the", "and", "a", "an", "is", "are", "was", "were", "of", "to",
        "in", "on", "at", "for", "with", "from", "by", "i", "we", "you",
        "they", "it", "this", "that", "these", "those", "be", "been",
        "as", "if", "but", "or", "so", "than", "then", "just", "really",
        "very", "actually", "like", "still", "even", "much", "more",
        "had", "have", "has", "do", "did", "does", "would", "could",
        "should", "will", "can", "my", "your", "our", "their",
    }
    tokens = [t for t in cleaned.split() if t and t not in stop and len(t) > 2]
    if not tokens:
        return None
    # Use the top 4 most-distinctive tokens. Pixabay's relevance
    # engine works better with a focused query than the full sentence.
    query = " ".join(tokens[:4])
    return await fetch_image_url(query)
