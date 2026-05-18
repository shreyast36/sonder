import { auth } from './firebase'

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

async function get(path) {
  const res = await fetch(`${BASE}${path}`, { headers: await authHeaders() })
  if (!res.ok) throw Object.assign(new Error(await _readError(res)), { status: res.status })
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw Object.assign(new Error(await _readError(res)), { status: res.status })
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
export async function getCotravellers(itineraryId) {
  return post('/api/cotraveller', { itinerary_id: itineraryId })
}

export async function regenerateCotravellers(excludedProfileIds, feedback) {
  return post('/api/cotraveller/regenerate', { excluded_profile_ids: excludedProfileIds, feedback })
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

// Returns a WebSocket — useWebSocket sends auth token as first message (first-message auth pattern).
export function openChatSocket(sessionId) {
  const wsBase = BASE.replace(/^http/, 'ws')
  return new WebSocket(`${wsBase}/ws/chat/${sessionId}`)
}
