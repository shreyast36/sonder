/**
 * Pull a representative photo for a destination via Wikipedia's REST API.
 *
 *   https://en.wikipedia.org/api/rest_v1/page/summary/{title}
 *
 * Free, no API key, permissive CORS. The infobox image surfaced via
 * `originalimage.source` is reliably good for most cities and travel
 * regions. Caches per-destination in localStorage so we don't hammer
 * Wikipedia on every dashboard load, with negative caching for places
 * that don't have an article so we don't retry forever.
 *
 * Tries `City, Country` first (handles ambiguity like Cairo / Springfield),
 * falls back to bare `City`.
 */

import { useEffect, useState } from 'react'

const CACHE_KEY = 'sonder_dest_photos_v1'
const TTL_MS    = 1000 * 60 * 60 * 24 * 14  // 14 days

function _read() {
  try { return JSON.parse(localStorage.getItem(CACHE_KEY) || '{}') } catch { return {} }
}
function _write(obj) {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(obj)) } catch { /* quota */ }
}
function _key(city, country) {
  return `${(city || '').trim().toLowerCase()}|${(country || '').trim().toLowerCase()}`
}

async function _tryTitle(title) {
  const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}?redirect=true`
  const resp = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!resp.ok) return null
  const data = await resp.json()
  // disambiguation pages don't have a useful image
  if (data?.type === 'disambiguation') return null
  return data?.originalimage?.source || data?.thumbnail?.source || null
}

export async function fetchDestinationPhoto(city, country) {
  if (!city) return null
  const key = _key(city, country)
  const cache = _read()
  const hit = cache[key]
  if (hit && Date.now() - (hit.ts || 0) < TTL_MS) return hit.url || null

  const candidates = country ? [`${city}, ${country}`, city] : [city]
  let found = null
  for (const t of candidates) {
    try {
      const u = await _tryTitle(t)
      if (u) { found = u; break }
    } catch { /* try next */ }
  }
  cache[key] = { url: found, ts: Date.now() }
  _write(cache)
  return found
}

export function useDestinationPhoto(city, country) {
  const [photo, setPhoto] = useState(() => {
    if (!city) return null
    const cache = _read()
    const hit = cache[_key(city, country)]
    if (hit && Date.now() - (hit.ts || 0) < TTL_MS) return hit.url || null
    return null
  })

  useEffect(() => {
    if (!city) { setPhoto(null); return }
    let cancelled = false
    fetchDestinationPhoto(city, country).then(url => {
      if (!cancelled) setPhoto(url || null)
    })
    return () => { cancelled = true }
  }, [city, country])

  return photo
}
