/**
 * Pull a representative photo for a destination.
 *
 * Order of attempts:
 *   1. Wikipedia REST API (`page/summary/{title}`) — free, no key, fast,
 *      but its infobox image is often a map / location diagram / coat
 *      of arms (especially for regions like "Patagonia" or country-level
 *      queries). We reject anything that looks map-shaped before
 *      accepting it.
 *   2. Backend `/api/destination-photo?city=&country=` — wraps Pixabay
 *      server-side so the API key stays out of the bundle. Returns a
 *      real travel photo for almost every query that has any presence
 *      on Pixabay.
 *
 * Caches the final URL per-destination in localStorage (14d TTL) with
 * negative caching so places with nothing usable don't get retried on
 * every page load.
 */

import { useEffect, useState } from 'react'

// Bumped to v2 so existing users with cached Wikipedia maps (the bug we
// just fixed) refetch fresh on first load instead of waiting 14 days.
const CACHE_KEY = 'sonder_dest_photos_v2'
const TTL_MS    = 1000 * 60 * 60 * 24 * 14  // 14 days

// URL substrings that signal "this is a map / location diagram / flag /
// coat of arms, NOT a destination photo". Wikipedia uses these patterns
// consistently across its infobox images so a simple lowercased
// substring match catches the vast majority of false positives.
const MAP_URL_HINTS = [
  'map',          // 'Patagonia_in_Argentina.svg', 'Location_map_*'
  'karte',        // German Wikipedia ports
  'location',     // 'Argentina_-_Location.svg'
  'locator',      // '*_locator_*'
  'satellite',    // satellite imagery — usually featureless from far up
  'topographic',
  'orthographic',
  'globe',
  'flag_of',
  'coat_of_arms',
  'coatofarms',
  'seal_of',
]

function _looksLikeMap(url) {
  if (!url) return true
  const lower = url.toLowerCase()
  // Wikipedia infobox SVGs are almost always maps, flags, or diagrams.
  // Real destination photos are .jpg/.jpeg/.png/.webp.
  if (lower.endsWith('.svg')) return true
  return MAP_URL_HINTS.some(h => lower.includes(h))
}

function _read() {
  try { return JSON.parse(localStorage.getItem(CACHE_KEY) || '{}') } catch { return {} }
}
function _write(obj) {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(obj)) } catch { /* quota */ }
}
function _key(city, country) {
  return `${(city || '').trim().toLowerCase()}|${(country || '').trim().toLowerCase()}`
}

async function _tryWikiTitle(title) {
  const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}?redirect=true`
  const resp = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!resp.ok) return null
  const data = await resp.json()
  if (data?.type === 'disambiguation') return null
  const candidate = data?.originalimage?.source || data?.thumbnail?.source || null
  // Reject maps / location diagrams / flags before returning. Falling
  // through to the next title (and ultimately to Pixabay) is better
  // than putting a map on the hero card.
  if (_looksLikeMap(candidate)) return null
  return candidate
}

async function _tryPixabay(city, country) {
  const params = new URLSearchParams({ city })
  if (country) params.set('country', country)
  try {
    const resp = await fetch(`/api/destination-photo?${params.toString()}`)
    if (!resp.ok) return null
    const data = await resp.json()
    return data?.url || null
  } catch {
    return null
  }
}

export async function fetchDestinationPhoto(city, country) {
  if (!city) return null
  const key = _key(city, country)
  const cache = _read()
  const hit = cache[key]
  if (hit && Date.now() - (hit.ts || 0) < TTL_MS) return hit.url || null

  // 1. Try Wikipedia (most specific title first), rejecting maps.
  const wikiCandidates = country ? [`${city}, ${country}`, city] : [city]
  let found = null
  for (const t of wikiCandidates) {
    try {
      const u = await _tryWikiTitle(t)
      if (u) { found = u; break }
    } catch { /* try next */ }
  }

  // 2. Pixabay fallback when Wikipedia gave us nothing usable.
  if (!found) {
    found = await _tryPixabay(city, country)
  }

  cache[key] = { url: found, ts: Date.now() }
  _write(cache)
  return found
}

/**
 * Multi-photo lookup for the cinematic trip-locked-in reveal.
 * Backed by /api/destination-photos (Pixabay). 14-day localStorage
 * cache keyed by (city, country, count) so the reveal renders
 * instantly on a refresh.
 */
const MANY_CACHE_KEY = 'sonder_dest_photos_many_v1'

function _readMany() {
  try { return JSON.parse(localStorage.getItem(MANY_CACHE_KEY) || '{}') } catch { return {} }
}
function _writeMany(obj) {
  try { localStorage.setItem(MANY_CACHE_KEY, JSON.stringify(obj)) } catch { /* quota */ }
}

export async function fetchDestinationPhotos(city, country, count = 5) {
  if (!city) return []
  const key = `${_key(city, country)}|${count}`
  const cache = _readMany()
  const hit = cache[key]
  if (hit && Date.now() - (hit.ts || 0) < TTL_MS && Array.isArray(hit.urls)) return hit.urls

  const params = new URLSearchParams({ city, count: String(count) })
  if (country) params.set('country', country)
  let urls = []
  try {
    const resp = await fetch(`/api/destination-photos?${params.toString()}`)
    if (resp.ok) {
      const data = await resp.json()
      urls = Array.isArray(data?.urls) ? data.urls.filter(Boolean) : []
    }
  } catch { /* fall through */ }

  cache[key] = { urls, ts: Date.now() }
  _writeMany(cache)
  return urls
}

export function useDestinationPhotos(city, country, count = 5) {
  const [photos, setPhotos] = useState(() => {
    if (!city) return []
    const cache = _readMany()
    const hit = cache[`${_key(city, country)}|${count}`]
    if (hit && Date.now() - (hit.ts || 0) < TTL_MS && Array.isArray(hit.urls)) return hit.urls
    return []
  })

  useEffect(() => {
    if (!city) { setPhotos([]); return }
    let cancelled = false
    fetchDestinationPhotos(city, country, count).then(urls => {
      if (!cancelled) setPhotos(urls || [])
    })
    return () => { cancelled = true }
  }, [city, country, count])

  return photos
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
