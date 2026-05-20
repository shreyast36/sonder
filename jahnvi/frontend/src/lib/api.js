import { auth } from './firebase'
import { Sentry } from './sentry'

const BASE = import.meta.env.VITE_API_BASE_URL || ''

async function authHeaders() {
  const token = await auth.currentUser.getIdToken()
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
}

async function _readError(res) {
  try {
    const ct = res.headers.get('content-type') || ''
    if (ct.includes('application/json')) {
      const data = await res.json()
      return (data && (data.detail || data.message || data.error)) || res.statusText
    }
    const text = await res.text()
    return text.slice(0, 300) || res.statusText
  } catch {
    return res.statusText
  }
}

// Report 5xx + network failures to Sentry while preserving the throw for callers.
// 4xx is left uncaptured: 401/403 are auth state, 404 from /users/profile is a
// normal first-login signal, 422 is client-side input — all expected behavior.
function _reportIfServerError(err, method, path) {
  const status = err?.status
  if (typeof status !== 'number' || status >= 500) {
    Sentry.captureException(err, {
      tags: { api_method: method, api_path: path, http_status: status ?? 'network' },
    })
  }
}

async function get(path) {
  let res
  try {
    res = await fetch(`${BASE}${path}`, { headers: await authHeaders() })
  } catch (networkErr) {
    _reportIfServerError(networkErr, 'GET', path)
    throw networkErr
  }
  if (!res.ok) {
    const err = Object.assign(new Error(await _readError(res)), { status: res.status })
    _reportIfServerError(err, 'GET', path)
    throw err
  }
  return res.json()
}

async function post(path, body) {
  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: await authHeaders(),
      body: JSON.stringify(body),
    })
  } catch (networkErr) {
    _reportIfServerError(networkErr, 'POST', path)
    throw networkErr
  }
  if (!res.ok) {
    const err = Object.assign(new Error(await _readError(res)), { status: res.status })
    _reportIfServerError(err, 'POST', path)
    throw err
  }
  return res.json()
}

export async function createUserProfile(displayName) {
  return post('/api/users/profile', { display_name: displayName })
}

// Public endpoint — no auth token required. Always resolves successfully
// even if the email doesn't exist (the backend silently swallows errors
// to prevent account enumeration).
export async function requestPasswordReset(email) {
  const res = await fetch(`${BASE}/api/auth/password-reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!res.ok) throw Object.assign(new Error(res.statusText), { status: res.status })
  return res.json()
}

export async function getUserProfile() {
  return get('/api/users/profile')
}

export async function inferPersona(profile) {
  return post('/api/persona-infer', profile)
}

// Returns a raw fetch Response with a ReadableStream body — pass to useSSE.
export async function planTrip(userProfile) {
  const token = await auth.currentUser.getIdToken()
  return fetch(`${BASE}/api/plan-trip`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(userProfile),
  })
}

export async function updateTrip(request) {
  return post('/api/update-trip', request)
}

// uid is read from the Auth token on the backend — do not send it in the body.
// Falls back to passing the cached persona signals so older users whose
// signals never got persisted server-side still get differentiated matches
// instead of the neutral 28% baseline.
export async function getCotravellers(itineraryId) {
  let top_push, top_interests
  try {
    const cached = JSON.parse(localStorage.getItem('sonder_persona_v1') || 'null')
    top_push      = cached?.persona?.top_push
    top_interests = cached?.persona?.top_interests
  } catch { /* noop */ }
  return post('/api/cotraveller', {
    itinerary_id: itineraryId,
    ...(top_push      ? { top_push }      : {}),
    ...(top_interests ? { top_interests } : {}),
  })
}

export async function regenerateCotravellers(excludedProfileIds, feedback) {
  return post('/api/cotraveller/regenerate', { excluded_profile_ids: excludedProfileIds, feedback })
}

// One-shot fetch of a co-traveller's full profile + match score against the
// current user. Falls back to the cached persona signals so existing users
// see real (non-28%) scores immediately.
export async function getCotravellerProfile(profileId, itineraryId) {
  const params = new URLSearchParams()
  if (itineraryId) params.set('itinerary_id', itineraryId)
  try {
    const cached = JSON.parse(localStorage.getItem('sonder_persona_v1') || 'null')
    ;(cached?.persona?.top_push      || []).forEach(v => params.append('top_push', v))
    ;(cached?.persona?.top_interests || []).forEach(v => params.append('top_interests', v))
  } catch { /* noop */ }
  const q = params.toString() ? `?${params.toString()}` : ''
  return get(`/api/cotraveller/profile/${encodeURIComponent(profileId)}${q}`)
}

export async function startChat(profileId, itineraryId) {
  return post('/api/chat/start', { profile_id: profileId, itinerary_id: itineraryId })
}

// uid is read from the Auth token on the backend — do not send user_id.
export async function approveMatch(sessionId) {
  return post('/api/chat/approve', { session_id: sessionId })
}

export async function denyMatch(sessionId) {
  return post('/api/chat/deny', { session_id: sessionId })
}

export async function saveItineraryAsCurrent(itineraryId) {
  return post(`/api/itineraries/${encodeURIComponent(itineraryId)}/save`, {})
}

export async function getCurrentItinerary() {
  return get('/api/itineraries/current')
}

export async function listSavedItineraries() {
  return get('/api/itineraries/list')
}

export async function setCurrentItinerary(itineraryId) {
  return post('/api/itineraries/set-current', { itinerary_id: itineraryId })
}

// ── Journal ────────────────────────────────────────────────────────────────

export async function listTripJournal(itineraryId) {
  return get(`/api/itineraries/${encodeURIComponent(itineraryId)}/journal`)
}

export async function upsertJournalEntry(itineraryId, body) {
  return post(`/api/itineraries/${encodeURIComponent(itineraryId)}/journal`, body)
}

export async function deleteJournalEntry(entryId) {
  const token = await auth.currentUser.getIdToken()
  const res = await fetch(`${BASE}/api/journal/${encodeURIComponent(entryId)}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw Object.assign(new Error(await _readError(res)), { status: res.status })
  return res.json()
}

export async function getDestinationFeed(city, country) {
  const q = country ? `?country=${encodeURIComponent(country)}` : ''
  return get(`/api/destinations/${encodeURIComponent(city)}/journal${q}`)
}

export async function getCompanionPrefs(itineraryId) {
  return get(`/api/itineraries/${encodeURIComponent(itineraryId)}/companion-prefs`)
}

export async function saveCompanionPrefs(itineraryId, prefs) {
  return post(`/api/itineraries/${encodeURIComponent(itineraryId)}/companion-prefs`, prefs)
}

export async function emailItinerary(itineraryId, recipients, includeNotes = true) {
  return post('/api/export/email', {
    itinerary_id: itineraryId,
    recipients,
    include_notes: includeNotes,
  })
}

export async function emailItineraryTest(email) {
  return post('/api/export/email/test', { email })
}

export async function downloadItineraryPdf(itineraryId) {
  const token = await auth.currentUser.getIdToken()
  window.open(`${BASE}/api/export/pdf/${itineraryId}?token=${encodeURIComponent(token)}`)
}

export async function addSharedActivity(itineraryId, activity, dayNumber, version) {
  return post(`/api/shared-itinerary/${itineraryId}/activity`, { activity, day_number: dayNumber, version })
}

export async function addSharedNote(itineraryId, note, version) {
  return post(`/api/shared-itinerary/${itineraryId}/note`, { note, version })
}

// Returns a WebSocket — useWebSocket sends auth token (or impersonation payload)
// as the first message (first-message auth pattern). The /api prefix matches
// chat.router being mounted under prefix="/api" in mushahid/main.py.
export function openChatSocket(sessionId) {
  const wsBase = BASE.replace(/^http/, 'ws')
  return new WebSocket(`${wsBase}/api/ws/chat/${encodeURIComponent(sessionId)}`)
}

export async function getChatSession(sessionId) {
  return get(`/api/chat/session/${encodeURIComponent(sessionId)}`)
}

export async function getChatMessages(sessionId) {
  return get(`/api/chat/${encodeURIComponent(sessionId)}/messages`)
}

export async function getUserPresence(sessionId, userId) {
  return get(`/api/chat/${encodeURIComponent(sessionId)}/presence/${encodeURIComponent(userId)}`)
}
