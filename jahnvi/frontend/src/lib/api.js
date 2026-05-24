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

async function _del(path) {
  let res
  try {
    res = await fetch(`${BASE}${path}`, { method: 'DELETE', headers: await authHeaders() })
  } catch (networkErr) {
    _reportIfServerError(networkErr, 'DELETE', path)
    throw networkErr
  }
  if (!res.ok) {
    const err = Object.assign(new Error(await _readError(res)), { status: res.status })
    _reportIfServerError(err, 'DELETE', path)
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

// `matchScore` is the 0..1 value from CoTravellerMatch — persisted on the
// session so the persona's reciprocal approval can read the same ground
// truth instead of guessing at decision time. Optional for back-compat.
export async function startChat(profileId, itineraryId, matchScore = null) {
  return post('/api/chat/start', {
    profile_id:   profileId,
    itinerary_id: itineraryId,
    match_score:  matchScore,
  })
}

// uid is read from the Auth token on the backend — do not send user_id.
export async function approveMatch(sessionId) {
  return post('/api/chat/approve', { session_id: sessionId })
}

export async function denyMatch(sessionId) {
  return post('/api/chat/deny', { session_id: sessionId })
}

// Approval lifecycle: user explicitly signs off on a draft itinerary,
// locking it and transitioning into the shared-itinerary surface.
export async function approveItinerary(itineraryId) {
  return post(`/api/itineraries/${encodeURIComponent(itineraryId)}/approve`, {})
}

// Request changes on a draft itinerary. Phase-1: logs feedback into
// revision_history; Phase-2 wires the targeted revision pipeline.
export async function reviseItinerary(itineraryId, feedback, targets = null) {
  return post(`/api/itineraries/${encodeURIComponent(itineraryId)}/revise`,
              targets ? { feedback, targets } : { feedback })
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

// Global per-user notification channel. One socket per app session — used by
// the NotificationProvider to receive chat_notification events anywhere.
export function openNotificationSocket() {
  const wsBase = BASE.replace(/^http/, 'ws')
  return new WebSocket(`${wsBase}/api/ws/notifications`)
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

// ── Web Push ───────────────────────────────────────────────────────────────

// Public endpoint that doesn't require auth — the SW needs the VAPID key
// before it can subscribe. Fetch directly (no auth header) and let the
// caller swallow 503 when web push isn't configured server-side.
export async function getVapidPublicKey() {
  const res = await fetch(`${BASE}/api/push/vapid-public-key`)
  if (!res.ok) throw Object.assign(new Error(res.statusText), { status: res.status })
  return res.json()
}

export async function registerPushSubscription(subscription) {
  return post('/api/push/subscribe', subscription)
}

export async function unregisterPushSubscription(endpoint) {
  return post('/api/push/unsubscribe', { endpoint })
}

// ── Discover (open trips + join requests) ─────────────────────────────────

export async function listOpenTrips(limit = 40) {
  return get(`/api/discover/trips?limit=${limit}`)
}

export async function openMyTrip(itineraryId, { joinCapacity = 1, note = '' } = {}) {
  return post(`/api/itineraries/${encodeURIComponent(itineraryId)}/open`, {
    join_capacity: joinCapacity, note,
  })
}

export async function closeMyTrip(itineraryId) {
  return post(`/api/itineraries/${encodeURIComponent(itineraryId)}/close`, {})
}

export async function requestToJoin(itineraryId, message = '') {
  return post(`/api/discover/trips/${encodeURIComponent(itineraryId)}/join-request`, { message })
}

export async function getTripPreview(itineraryId) {
  return get(`/api/discover/trips/${encodeURIComponent(itineraryId)}/preview`)
}

export async function listInbox() {
  return get('/api/inbox')
}

export async function listMyJoinRequests({ asOwner = false } = {}) {
  const q = asOwner ? '?as=owner' : ''
  return get(`/api/discover/join-requests${q}`)
}

export async function respondJoinRequest(requestId, decision) {
  return post(`/api/discover/join-requests/${encodeURIComponent(requestId)}/respond`, { decision })
}

// ── Social feed (posts + comments) ────────────────────────────────────────

export async function listFeed({ limit = 30, before = null } = {}) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (before) params.set('before', before)
  return get(`/api/feed?${params.toString()}`)
}

export async function createPost({ text, linkedTripId = null, imageUrl = null }) {
  return post('/api/feed/posts', {
    text,
    linked_trip_id: linkedTripId,
    image_url: imageUrl,
  })
}

export async function deletePost(postId) {
  return _del(`/api/feed/posts/${encodeURIComponent(postId)}`)
}

export async function listComments(postId) {
  return get(`/api/feed/posts/${encodeURIComponent(postId)}/comments`)
}

export async function addComment(postId, text) {
  return post(`/api/feed/posts/${encodeURIComponent(postId)}/comments`, { text })
}

// ── Shared itinerary (collaborative negotiation) ───────────────────────────

export async function getSharedItinerary(itineraryId) {
  return get(`/api/shared/${encodeURIComponent(itineraryId)}`)
}

export async function proposeChange(itineraryId, {
  kind = 'add', dayNumber, title = '', message = '', replacesActivityId = null, version,
}) {
  return post(`/api/shared/${encodeURIComponent(itineraryId)}/propose`, {
    kind,
    day_number: dayNumber,
    title,
    message,
    replaces_activity_id: replacesActivityId,
    version,
  })
}

export async function respondToChange(itineraryId, { changeId, decision, title = null, message = '', version }) {
  return post(`/api/shared/${encodeURIComponent(itineraryId)}/respond`, {
    change_id: changeId, decision, title, message, version,
  })
}

export async function withdrawChange(itineraryId, { changeId, version }) {
  return post(`/api/shared/${encodeURIComponent(itineraryId)}/withdraw`, {
    change_id: changeId, version,
  })
}

export async function askPersonaSuggest(itineraryId, { version }) {
  return post(`/api/shared/${encodeURIComponent(itineraryId)}/persona-suggest`, { version })
}

export async function finalizeShared(itineraryId, { version }) {
  return post(`/api/shared/${encodeURIComponent(itineraryId)}/finalize`, { version })
}

// ── Voice (ElevenLabs TTS) ─────────────────────────────────────────────────

// Synthesize one chat message into a Firebase-hosted MP3 URL. Same text
// from the same persona is cached, so re-plays cost $0 and load instantly.
// Returns { audio_url, cached, voice_id }.
export async function synthesizeVoice(profileId, text) {
  return post('/api/voice/synthesize', { profile_id: profileId, text })
}
