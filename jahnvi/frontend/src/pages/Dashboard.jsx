import { useState, useEffect, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, Plus } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import MatchCard from '../components/MatchCard'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import { useAuth } from '../hooks/useAuth'
import { getCurrentItinerary, getCotravellers, listSavedItineraries, setCurrentItinerary, openMyTrip, closeMyTrip, listMyJoinRequests, respondJoinRequest } from '../lib/api'
import { useDestinationPhoto } from '../lib/destinationPhoto'
import DashboardPulse from '../components/DashboardPulse'
import { storage } from '../lib/firebase'
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage'
import { updateProfile } from 'firebase/auth'
import { auth } from '../lib/firebase'

// vivid amber — Dashboard accent
const AMBER = '#F59E0B'

function useCountUp(target, duration = 1200, delay = 300) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    const timer = setTimeout(() => {
      const start = performance.now()
      const tick = now => {
        const p = Math.min((now - start) / duration, 1)
        const ease = 1 - Math.pow(1 - p, 3)
        setCount(Math.round(ease * target))
        if (p < 1) requestAnimationFrame(tick)
      }
      requestAnimationFrame(tick)
    }, delay)
    return () => clearTimeout(timer)
  }, [target, duration, delay])
  return count
}

function loadStoredItinerary() {
  try {
    const raw = localStorage.getItem('sonder_last_itinerary')
    if (!raw) return null
    return JSON.parse(raw)
  } catch { return null }
}

function fmtShortDate(v) {
  if (!v) return ''
  try {
    const d = new Date(typeof v === 'string' ? v.slice(0, 10) : v)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch { return '' }
}

function deriveTripCard(itinerary) {
  if (!itinerary) return null
  const days = itinerary.days || []
  if (!days.length) return null
  const startRaw = days[0]?.trip_date
  const endRaw   = days[days.length - 1]?.trip_date
  const departs  = fmtShortDate(startRaw) || '—'
  const returns  = fmtShortDate(endRaw)   || '—'
  const duration = `${days.length} day${days.length === 1 ? '' : 's'}`
  let daysAway = null
  if (startRaw) {
    const start = new Date(typeof startRaw === 'string' ? startRaw.slice(0, 10) : startRaw)
    if (!isNaN(start.getTime())) {
      const diff = Math.ceil((start.getTime() - Date.now()) / 86400000)
      daysAway = diff > 0 ? diff : 0
    }
  }
  return {
    city: itinerary.destination?.city || 'Your trip',
    country: itinerary.destination?.country || '',
    departs, returns, duration, daysAway,
  }
}

// Dim id → short human label for MatchCard tags. Lifted from Jahnvi's
// Core 12 PUSH/PULL — covers everything our seed personas + real users emit.
const DIM_TAG = {
  // PULL
  nature_outdoors:   'Nature',
  culture_history:   'Culture',
  food_drink:        'Food',
  nightlife_social:  'Nightlife',
  comfort_luxury:    'Luxury',
  exploration_local: 'Explore',
  // PUSH (occasionally surfaced as a tag)
  escape_reset:      'Reset',
  adventure_novelty: 'Adventure',
  connection:        'Connection',
  reflection:        'Reflection',
  curiosity:         'Curious',
  prestige_reward:   'Milestone',
}
const _PACE_TAG = { relaxed: 'Relaxed', moderate: 'Moderate', packed: 'Packed' }
const _BUDGET_TAG = { budget: 'Budget', mid_range: 'Mid-range', luxury: 'Luxury' }

// ── Past trips carousel ────────────────────────────────────────────────────

function _fmtTripDate(v) {
  if (!v) return ''
  try {
    const d = new Date(typeof v === 'string' ? v.slice(0, 10) : v)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch { return '' }
}

function PastTripsRow({ trips, onSelect, switching }) {
  if (!trips || trips.length === 0) return null
  return (
    <div style={{ marginTop: 36 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 16 }}>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
          Your trips
        </p>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: DIM, margin: 0 }}>
          {trips.length} saved
        </p>
      </div>
      <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 4, scrollbarWidth: 'thin' }}>
        {trips.map((t, i) => {
          const isCurrent = !!t.is_current
          const accent = isCurrent ? '#F59E0B' : 'rgba(245,158,11,0.30)'
          return (
            <motion.button
              key={t.itinerary_id}
              whileHover={!switching && !isCurrent ? { y: -3, borderColor: accent } : {}}
              whileTap={!switching && !isCurrent ? { scale: 0.98 } : {}}
              onClick={() => !isCurrent && onSelect(t.itinerary_id)}
              disabled={switching || isCurrent}
              initial={{ opacity: 0, x: 18 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.05 + i * 0.06, ease }}
              style={{
                position: 'relative',
                flex: '0 0 auto', width: 200, padding: '18px 18px 16px',
                background: isCurrent ? 'rgba(245,158,11,0.06)' : 'rgba(232,212,168,0.04)',
                border: `1px solid ${isCurrent ? 'rgba(245,158,11,0.40)' : HAIRLINE}`,
                borderRadius: 14, cursor: isCurrent ? 'default' : (switching ? 'wait' : 'pointer'),
                transition: 'all 0.25s', textAlign: 'left',
                opacity: switching && !isCurrent ? 0.5 : 1,
              }}
            >
              {isCurrent && (
                <span style={{
                  position: 'absolute', top: 10, right: 10,
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 7.5,
                  letterSpacing: '0.24em', textTransform: 'uppercase',
                  color: '#F59E0B', padding: '3px 7px', borderRadius: 8,
                  background: 'rgba(245,158,11,0.10)', border: '1px solid rgba(245,158,11,0.40)',
                }}>
                  Current
                </span>
              )}
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, margin: '0 0 6px' }}>
                Destination
              </p>
              <h3 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 24, color: BONE, lineHeight: 1, margin: 0, letterSpacing: '-0.01em' }}>
                {t.city}
              </h3>
              {t.country && (
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, margin: '4px 0 12px' }}>
                  {t.country}
                </p>
              )}
              <div style={{ height: 1, background: HAIRLINE, margin: '10px 0' }}/>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>
                  {t.day_count ? `${t.day_count} day${t.day_count === 1 ? '' : 's'}` : '—'}
                </span>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM }}>
                  {_fmtTripDate(t.trip_start) || ''}
                </span>
              </div>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}

// ── Members card — oxblood + cream + a single gilded seal, no chip ────────

function TravelCard({ firstName, displayName, uid }) {
  // Stable 4-digit member number derived from uid, so it never changes.
  const num = useMemo(() => {
    const id = uid || ''
    if (!id) return '0001'
    let n = 0
    for (let i = 0; i < id.length; i++) n = (n * 31 + id.charCodeAt(i)) >>> 0
    return String((n % 9899) + 100).padStart(4, '0')
  }, [uid])

  const fullName = (displayName || firstName || 'Traveller').trim()

  const CREAM     = '#f4ede0'
  const CREAM_DIM = 'rgba(244,237,224,0.55)'
  const RIM_GOLD  = 'rgba(212,182,134,0.55)'
  const SEAL_LINK = 'sealGrad-' + (uid || 'x').slice(0, 6)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.75, delay: 0.4, ease }}
      style={{
        width: 460, maxWidth: 'calc(100vw - 64px)',
        margin: '36px auto 16px',
        borderRadius: 14,
        // Oxblood-on-oxblood gradient with a faint gilt rim on the perimeter.
        background:
          'radial-gradient(ellipse at 20% 0%, #4a1a22 0%, #2a0d12 55%, #170509 100%)',
        boxShadow:
          '0 30px 70px rgba(0,0,0,0.65), ' +
          '0 0 18px rgba(74,26,34,0.55), ' +
          `inset 0 0 0 1px ${RIM_GOLD}, ` +     // outer gilt thread
          'inset 0 0 0 3px rgba(20,8,10,0.95), ' + // dark inset
          `inset 0 0 0 4px rgba(212,182,134,0.20)`, // second hairline
        position: 'relative', overflow: 'hidden',
      }}
    >
      {/* Subtle leather sheen — barely visible diagonal */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'linear-gradient(160deg, rgba(244,237,224,0.04) 0%, transparent 30%, transparent 70%, rgba(0,0,0,0.20) 100%)',
      }}/>
      {/* Soft warm halo top-right */}
      <div style={{
        position: 'absolute', top: -80, right: -60, width: 260, height: 260,
        background: 'radial-gradient(ellipse, rgba(212,182,134,0.10) 0%, transparent 65%)',
        pointerEvents: 'none',
      }}/>

      <div style={{ position: 'relative', padding: '32px 30px 28px', textAlign: 'center' }}>
        {/* Wordmark */}
        <p style={{
          fontFamily: '"Inter Tight",sans-serif', fontWeight: 500, fontSize: 10,
          letterSpacing: '0.52em', textIndent: '0.52em', textTransform: 'uppercase',
          color: 'rgba(212,182,134,0.85)',
          margin: 0,
        }}>
          Sonder · Members
        </p>

        {/* Gilt seal */}
        <div style={{ display: 'flex', justifyContent: 'center', margin: '20px 0 16px' }}>
          <svg width="46" height="46" viewBox="0 0 46 46">
            <defs>
              <linearGradient id={SEAL_LINK} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"  stopColor="#f0dcb0"/>
                <stop offset="55%" stopColor="#d4b686"/>
                <stop offset="100%" stopColor="#8a6f4a"/>
              </linearGradient>
            </defs>
            <circle cx="23" cy="23" r="21" fill="none" stroke={`url(#${SEAL_LINK})`} strokeWidth="0.8"/>
            <circle cx="23" cy="23" r="15" fill="none" stroke={`url(#${SEAL_LINK})`} strokeWidth="0.5"/>
            <text x="23" y="29" textAnchor="middle" fontSize="22"
              fill={`url(#${SEAL_LINK})`} fontFamily="'Cormorant Garamond',serif" fontStyle="italic">
              S
            </text>
          </svg>
        </div>

        {/* Top hairline */}
        <div style={{
          width: 80, height: 1,
          background: `linear-gradient(to right, transparent, ${RIM_GOLD}, transparent)`,
          margin: '0 auto 18px',
        }}/>

        {/* Name block */}
        <p style={{
          fontFamily: '"Inter Tight",sans-serif', fontSize: 8,
          letterSpacing: '0.42em', textIndent: '0.42em', textTransform: 'uppercase',
          color: CREAM_DIM, margin: '0 0 10px',
        }}>
          In the name of
        </p>
        <h2 style={{
          fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
          fontSize: 'clamp(28px, 4.6vw, 38px)',
          color: CREAM, margin: 0, lineHeight: 1,
          letterSpacing: '-0.01em',
          filter: 'drop-shadow(0 0 16px rgba(244,237,224,0.18))',
        }}>
          {fullName}
        </h2>

        {/* Bottom hairline */}
        <div style={{
          width: 80, height: 1,
          background: `linear-gradient(to right, transparent, ${RIM_GOLD}, transparent)`,
          margin: '22px auto 16px',
        }}/>

        {/* Bottom row: serial + est. */}
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', padding: '0 2px' }}>
          <span style={{
            fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 17,
            letterSpacing: '0.04em',
            background: 'linear-gradient(180deg, #f0dcb0 0%, #b89968 100%)',
            WebkitBackgroundClip: 'text', backgroundClip: 'text',
            color: 'transparent', WebkitTextFillColor: 'transparent',
          }}>
            N°&nbsp;{num}
          </span>
          <span style={{
            fontFamily: '"Inter Tight",sans-serif', fontSize: 8,
            letterSpacing: '0.42em', textIndent: '0.42em', textTransform: 'uppercase',
            color: CREAM_DIM,
          }}>
            Est. {new Date().getFullYear()}
          </span>
        </div>
      </div>
    </motion.div>
  )
}

function matchToCard(m) {
  // Backend returns CoTravellerMatch: { profile: {profile_id, display_name,
  // location, interests, pace, budget_style, ...}, match_score: 0..1,
  // match_reasons: [...] }. Flatten + humanise for MatchCard.
  const p = m?.profile || {}
  const dimTags = (p.interests || []).slice(0, 2).map(d => DIM_TAG[d]).filter(Boolean)
  const paceTag = _PACE_TAG[p.pace]
  const budgetTag = _BUDGET_TAG[p.budget_style]
  return {
    id:           p.profile_id || p.display_name,
    display_name: p.display_name || 'Anonymous',
    location:     p.location || '',
    match_score:  Math.round((Number(m?.match_score) || 0) * 100),
    tags:         [...dimTags, paceTag, budgetTag].filter(Boolean).slice(0, 3),
    avatar_url:   p.avatar_url || null,
    is_seed:      Boolean(p.is_seed),
  }
}

const spring = { type: 'spring', stiffness: 280, damping: 22 }
const stagger = { show: { transition: { staggerChildren: 0.10 } } }
const reveal  = { hidden: { opacity: 0, y: 28 }, show: { opacity: 1, y: 0, transition: { duration: 0.7, ease } } }

export default function Dashboard() {
  const navigate  = useNavigate()
  const { user, signOut }  = useAuth()

  // Firestore is the source of truth — orchestrator writes every itinerary
  // to it on `done`, and the Save button on /itinerary marks one as current.
  // localStorage is a same-tab cache so the dashboard renders instantly
  // while the network round-trip catches up.
  const [storedItinerary, setStoredItinerary] = useState(() => loadStoredItinerary())
  const [matches, setMatches] = useState([])
  const [activePair, setActivePair] = useState(null)
  const [matchesLoading, setMatchesLoading] = useState(false)
  // Open-to-companions toggle state for the current trip. Synced from
  // storedItinerary.is_open_to_join when the itinerary loads.
  const [openToggleBusy, setOpenToggleBusy] = useState(false)
  // Incoming join requests on this user's open trips. Pulls
  // ?as=owner once per session; optimistically prunes a request on
  // approve/deny so the panel stays in sync without a re-fetch.
  const [incoming, setIncoming] = useState([])
  const [incomingBusy, setIncomingBusy] = useState({})   // request_id → bool
  const [pastTrips, setPastTrips] = useState([])
  const [switchingTrip, setSwitchingTrip] = useState(false)

  const refresh = async () => {
    try {
      const res = await getCurrentItinerary()
      const it = res?.itinerary ?? null
      if (it) {
        setStoredItinerary(it)
        try { localStorage.setItem('sonder_last_itinerary', JSON.stringify(it)) } catch { /* noop */ }
      }
      // If the server returns null we intentionally DO NOT wipe localStorage:
      // the user may have just generated a trip and not clicked Save yet, or
      // Firestore might be having a brief moment. Cached card stays visible
      // until they explicitly save a different one (or sign out).
    } catch (err) {
      console.warn('getCurrentItinerary failed (keeping cache):', err?.message || err)
    }
    try {
      const res = await listSavedItineraries()
      setPastTrips(Array.isArray(res?.trips) ? res.trips : [])
    } catch (err) {
      console.warn('listSavedItineraries failed:', err?.message || err)
    }
  }

  async function handleSwitchTrip(itineraryId) {
    if (switchingTrip) return
    setSwitchingTrip(true)
    try {
      await setCurrentItinerary(itineraryId)
      await refresh()
    } catch (err) {
      console.error('set current failed:', err)
    } finally {
      setSwitchingTrip(false)
    }
  }

  // Pull real co-traveller matches once we know who the user is.
  useEffect(() => {
    if (!user) return
    let cancelled = false
    const itin = storedItinerary
    const itineraryId = itin?.itinerary_id || null
    setMatchesLoading(true)
    getCotravellers(itineraryId)
      .then(res => {
        if (cancelled) return
        // If the user already has an approved pair for this trip, suppress
        // the new-matches strip entirely — they don't have a slot to fill,
        // they have a co-traveller already.
        const activePair = !Array.isArray(res) ? res?.active_pair : null
        if (activePair) {
          setActivePair(activePair)
          setMatches([])
          return
        }
        setActivePair(null)
        const arr = Array.isArray(res) ? res : (res?.matches || [])
        setMatches(arr.map(matchToCard))
      })
      .catch(err => {
        if (cancelled) return
        console.warn('getCotravellers failed:', err?.message || err)
        setMatches([])
      })
      .finally(() => { if (!cancelled) setMatchesLoading(false) })
    return () => { cancelled = true }
    // Re-fetch when the saved itinerary id changes (different trip → different matches).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.uid, storedItinerary?.itinerary_id])

  // Pull incoming join-requests on this user's open trips. One fetch
  // on mount; the WS listener below appends in real-time on new ones.
  useEffect(() => {
    if (!user) return
    let cancelled = false
    ;(async () => {
      try {
        const res = await listMyJoinRequests({ asOwner: true })
        if (cancelled) return
        const pending = (res?.requests || []).filter(r => r.status === 'proposed')
        setIncoming(pending)
      } catch (err) {
        console.warn('listMyJoinRequests failed:', err?.message || err)
      }
    })()
    return () => { cancelled = true }
  }, [user?.uid])

  // Real-time push: when the backend fires `join_request_new` for this
  // user (because someone just requested to join one of their open
  // trips), NotificationProvider dispatches a CustomEvent we listen for
  // here and append to local state. Dedup by request_id so a brief
  // race between the WS push and a mount-fetch can't double-render.
  useEffect(() => {
    if (!user) return
    function onNewRequest(e) {
      const req = e.detail
      if (!req || req.status !== 'proposed') return
      setIncoming(prev => prev.some(r => r.request_id === req.request_id)
        ? prev
        : [req, ...prev])
    }
    window.addEventListener('sonder:join_request:new', onNewRequest)
    return () => window.removeEventListener('sonder:join_request:new', onNewRequest)
  }, [user?.uid])

  async function decideIncoming(requestId, decision) {
    setIncomingBusy(prev => ({ ...prev, [requestId]: true }))
    try {
      await respondJoinRequest(requestId, decision)
      setIncoming(prev => prev.filter(r => r.request_id !== requestId))
    } catch (err) {
      console.warn('respondJoinRequest failed:', err?.message || err)
    } finally {
      setIncomingBusy(prev => {
        const next = { ...prev }
        delete next[requestId]
        return next
      })
    }
  }

  useEffect(() => {
    if (!user) return
    refresh()
    const reloadLocal = () => setStoredItinerary(loadStoredItinerary())
    const onStorage = (e) => { if (e.key === 'sonder_last_itinerary') reloadLocal() }
    const onVisible = () => {
      if (document.visibilityState !== 'visible') return
      reloadLocal()
      refresh()
    }
    window.addEventListener('storage', onStorage)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.removeEventListener('storage', onStorage)
      document.removeEventListener('visibilitychange', onVisible)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.uid])

  const trip = deriveTripCard(storedItinerary)
  const tripPhoto = useDestinationPhoto(trip?.city, trip?.country)
  const daysAway  = useCountUp(trip?.daysAway ?? 0, 1000, 600)

  // displayName changes via updateProfile don't refire onAuthStateChanged, so
  // we track an in-component override that takes precedence over user.displayName.
  const [displayNameOverride, setDisplayNameOverride] = useState(null)
  useEffect(() => { setDisplayNameOverride(null) }, [user?.uid])
  const effectiveDisplayName = displayNameOverride ?? user?.displayName ?? null

  // Prefer the user's chosen display name. Fall back to the local part of their
  // email (e.g. "ali.khan@gmail.com" → "Ali"), capitalized. Only resort to a
  // generic greeting when neither is available — but post-signup that should
  // never happen.
  const firstName = (() => {
    if (effectiveDisplayName) return effectiveDisplayName.split(' ')[0]
    if (user?.email) {
      const local = user.email.split('@')[0].split(/[._-]/)[0]
      return local.charAt(0).toUpperCase() + local.slice(1).toLowerCase()
    }
    return ''
  })()

  // Inline name editor state
  const [editingName, setEditingName] = useState(false)
  const [nameInput,   setNameInput]   = useState('')
  const [savingName,  setSavingName]  = useState(false)
  const [nameError,   setNameError]   = useState(null)

  function openNameEditor() {
    setNameInput(effectiveDisplayName ?? '')
    setNameError(null)
    setEditingName(true)
  }
  function cancelNameEdit() {
    setEditingName(false)
    setNameError(null)
    setNameInput('')
  }
  async function saveName(e) {
    e?.preventDefault?.()
    const trimmed = nameInput.trim()
    if (!trimmed) { setNameError('Name cannot be empty.'); return }
    if (trimmed.length > 60) { setNameError('Name is too long.'); return }
    setSavingName(true)
    setNameError(null)
    try {
      await updateProfile(auth.currentUser, { displayName: trimmed })
      setDisplayNameOverride(trimmed)
      setEditingName(false)
      setDropdown(false)
      setNameInput('')
    } catch (err) {
      setNameError('Failed to update. Try again.')
    } finally {
      setSavingName(false)
    }
  }
  const hour        = new Date().getHours()
  const greeting    = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  const fileInputRef  = useRef(null)
  const [uploading, setUploading]   = useState(false)
  const [dropdownOpen, setDropdown] = useState(false)
  const [photoURL, setPhotoURL]     = useState(user?.photoURL ?? null)

  useEffect(() => {
    if (!user?.uid) return
    const storageRef = ref(storage, `avatars/${user.uid}`)
    getDownloadURL(storageRef)
      .then(url => setPhotoURL(url))
      .catch(() => setPhotoURL(user.photoURL ?? null))
  }, [user?.uid])

  async function handleAvatarChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const storageRef = ref(storage, `avatars/${auth.currentUser.uid}`)
      await uploadBytes(storageRef, file)
      const url = await getDownloadURL(storageRef)
      setPhotoURL(url)
    } catch (err) {
      console.error('Avatar upload failed:', err.code, err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent="#F59E0B" />

      {/* nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <SonderNav3D markSize={32}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {/* Always-visible Plan-a-trip CTA — primary action from any
              dashboard state, replaces the old bottom-right button. */}
          <motion.button
            whileHover={{ y: -2, boxShadow: `0 8px 24px rgba(245,158,11,0.30)` }}
            whileTap={{ scale: 0.97 }}
            onClick={() => navigate('/preferences')}
            style={{
              padding: '9px 18px', borderRadius: 999,
              background: `linear-gradient(135deg, ${AMBER} 0%, #D97706 100%)`,
              border: 'none', cursor: 'pointer', color: '#0a0807',
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10, fontWeight: 600,
              letterSpacing: '0.20em', textTransform: 'uppercase',
              display: 'inline-flex', alignItems: 'center', gap: 7,
              boxShadow: `0 6px 18px rgba(245,158,11,0.30)`,
              transition: 'all 0.2s',
            }}
          >
            <Plus size={12}/> Plan a trip
          </motion.button>
          <div style={{ position: 'relative' }}>
            <div style={{ cursor: 'pointer' }} onClick={() => setDropdown(o => !o)}>
              <motion.img
                whileHover={{ scale: 1.08, boxShadow: '0 0 0 2px rgba(245,158,11,0.50), 0 0 32px rgba(245,158,11,0.28)' }}
                whileTap={{ scale: 0.95 }}
                transition={spring}
                src={photoURL ?? 'https://i.pravatar.cc/80?img=32'} alt="You"
                style={{ width: 34, height: 34, borderRadius: '50%', objectFit: 'cover', border: `1.5px solid rgba(212,182,134,0.30)`, cursor: 'pointer', boxShadow: '0 0 20px rgba(212,182,134,0.12)', opacity: uploading ? 0.5 : 1, transition: 'opacity 0.2s', display: 'block' }}
              />
              {uploading && (
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%' }}>
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                    style={{ width: 14, height: 14, border: '2px solid transparent', borderTopColor: GOLD, borderRadius: '50%' }}/>
                </div>
              )}
            </div>
            <AnimatePresence onExitComplete={cancelNameEdit}>
              {dropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ duration: 0.18, ease }}
                  style={{ position: 'absolute', top: 44, right: 0, minWidth: editingName ? 260 : 200, background: 'rgba(18,15,10,0.96)', border: `1px solid ${HAIRLINE}`, borderRadius: 12, overflow: 'hidden', backdropFilter: 'blur(20px)', boxShadow: '0 16px 48px rgba(0,0,0,0.5)', zIndex: 100 }}
                >
                  {editingName ? (
                    <form onSubmit={saveName} style={{ padding: '14px 14px 12px' }}>
                      <label style={{ display: 'block', fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>
                        Display name
                      </label>
                      <input
                        autoFocus
                        type="text"
                        value={nameInput}
                        onChange={e => setNameInput(e.target.value)}
                        placeholder="Your name"
                        maxLength={60}
                        style={{
                          width: '100%', boxSizing: 'border-box',
                          padding: '10px 12px',
                          background: 'rgba(232,212,168,0.04)',
                          border: `1px solid ${HAIRLINE}`,
                          borderRadius: 6,
                          outline: 'none',
                          fontFamily: '"Inter Tight",sans-serif', fontSize: 13, color: BONE,
                          letterSpacing: '0.01em',
                        }}
                      />
                      {nameError && (
                        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: '#E89B7C', margin: '8px 2px 0' }}>{nameError}</p>
                      )}
                      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                        <button type="button" onClick={cancelNameEdit}
                          style={{ flex: 1, padding: '9px 0', background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 6, fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, cursor: 'pointer', transition: 'color 0.15s, border-color 0.15s' }}
                          onMouseEnter={e => { e.currentTarget.style.color = BONE }}
                          onMouseLeave={e => { e.currentTarget.style.color = MUTE }}>
                          Cancel
                        </button>
                        <button type="submit" disabled={savingName}
                          style={{ flex: 1, padding: '9px 0', background: GOLD, border: 'none', borderRadius: 6, fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: BG, fontWeight: 600, cursor: savingName ? 'wait' : 'pointer', opacity: savingName ? 0.65 : 1, transition: 'opacity 0.2s' }}>
                          {savingName ? 'Saving…' : 'Save'}
                        </button>
                      </div>
                    </form>
                  ) : [
                    { label: 'Change name',            action: openNameEditor },
                    { label: 'Change profile picture', action: () => { setDropdown(false); fileInputRef.current?.click() } },
                    { label: 'Sign out',               action: () => { setDropdown(false); signOut().then(() => navigate('/')) } },
                  ].map(({ label, action }) => (
                    <button key={label} onClick={action}
                      style={{ width: '100%', padding: '14px 18px', background: 'none', border: 'none', textAlign: 'left', fontFamily: '"Inter Tight",sans-serif', fontSize: 12, letterSpacing: '0.04em', color: MUTE, cursor: 'pointer', transition: 'all 0.15s', display: 'block' }}
                      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(232,212,168,0.06)'; e.currentTarget.style.color = BONE }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = MUTE }}
                    >
                      {label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
            <input ref={fileInputRef} type="file" accept="image/*" onChange={handleAvatarChange} style={{ display: 'none' }}/>
          </div>
        </div>
      </nav>

      {/* greeting */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, padding: '44px 48px 40px', position: 'relative', zIndex: 1, overflow: 'hidden', textAlign: 'center' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'radial-gradient(ellipse 60% 140% at 50% 60%, rgba(212,182,134,0.10) 0%, transparent 65%)', pointerEvents: 'none' }}/>
        <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>{greeting}</p>
          <motion.h1
            animate={{ filter: ['drop-shadow(0 0 24px rgba(212,182,134,0.20))', 'drop-shadow(0 0 56px rgba(212,182,134,0.50))', 'drop-shadow(0 0 24px rgba(212,182,134,0.20))'] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
            style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 68, lineHeight: 0.95, letterSpacing: '-0.02em', background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'inline-block' }}
          >
            {firstName}
          </motion.h1>
        </motion.div>

        <TravelCard
          firstName={firstName}
          displayName={effectiveDisplayName || user?.displayName}
          uid={user?.uid}
        />

        {/* Live stats strip — small glass pill with key signals */}
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease, delay: 0.4 }}
          style={{
            marginTop: 32,
            display: 'inline-flex', alignItems: 'center', gap: 28,
            padding: '12px 26px', borderRadius: 999,
            background: 'rgba(8,8,7,0.55)', backdropFilter: 'blur(20px)',
            border: `1px solid ${HAIRLINE}`,
            boxShadow: `0 10px 30px rgba(0,0,0,0.4)`,
            position: 'relative', zIndex: 1,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: BONE, lineHeight: 1 }}>
              {pastTrips.length}
            </span>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: MUTE, letterSpacing: '0.22em', textTransform: 'uppercase' }}>
              {pastTrips.length === 1 ? 'trip' : 'trips'} planned
            </span>
          </div>
          <span style={{ width: 1, height: 18, background: HAIRLINE }}/>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: BONE, lineHeight: 1 }}>
              {matches.length}
            </span>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: MUTE, letterSpacing: '0.22em', textTransform: 'uppercase' }}>
              curated matches
            </span>
          </div>
          {incoming.length > 0 && (
            <>
              <span style={{ width: 1, height: 18, background: HAIRLINE }}/>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <motion.span
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ width: 7, height: 7, borderRadius: '50%', background: '#8B5CF6', boxShadow: '0 0 10px #8B5CF6' }}
                />
                <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: '#8B5CF6', lineHeight: 1 }}>
                  {incoming.length}
                </span>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: '#8B5CF6', letterSpacing: '0.22em', textTransform: 'uppercase' }}>
                  awaiting you
                </span>
              </div>
            </>
          )}
        </motion.div>
      </div>

      {/* main grid */}
      <motion.div variants={stagger} initial="hidden" animate="show"
        style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.4fr 1fr', maxWidth: 1240, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>

        {/* LEFT — trip card */}
        <motion.div variants={reveal} style={{ padding: '52px 52px', borderRight: `1px solid ${HAIRLINE}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
            <motion.span
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
              style={{ width: 6, height: 6, borderRadius: '50%', background: AMBER, boxShadow: `0 0 10px ${AMBER}` }}
            />
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
              Upcoming trip
            </p>
          </div>

          {trip ? (
            <motion.div
              onClick={() => navigate('/itinerary')}
              whileHover={{ y: -6, transition: spring }}
              whileTap={{ scale: 0.99 }}
              style={{ cursor: 'pointer', padding: 1, borderRadius: 26, background: 'linear-gradient(145deg,rgba(232,212,168,0.30) 0%,rgba(8,8,7,0) 50%,rgba(232,212,168,0.12) 100%)', boxShadow: '0 24px 72px rgba(0,0,0,0.55), 0 4px 16px rgba(0,0,0,0.30), inset 0 1px 0 rgba(232,212,168,0.10)' }}
            >
              <div style={{ background: 'linear-gradient(160deg,rgba(24,20,13,0.99) 0%,rgba(14,11,8,1) 100%)', borderRadius: 25, padding: '40px 40px 32px', position: 'relative', overflow: 'hidden' }}>
                {/* Destination photo background — Wikipedia REST API, falls
                    back invisible when no image is found. */}
                {tripPhoto && (
                  <>
                    <img
                      src={tripPhoto}
                      alt={trip.city}
                      referrerPolicy="no-referrer"
                      style={{
                        position: 'absolute', inset: 0, width: '100%', height: '100%',
                        objectFit: 'cover', objectPosition: 'center',
                        filter: 'saturate(0.85) brightness(0.55)',
                        pointerEvents: 'none',
                      }}
                    />
                    {/* Top-to-bottom darken so the live-dot + Destination
                        eyebrow read cleanly while the bottom still shows photo. */}
                    <div style={{
                      position: 'absolute', inset: 0, pointerEvents: 'none',
                      background: 'linear-gradient(180deg, rgba(8,8,7,0.55) 0%, rgba(14,11,8,0.40) 40%, rgba(14,11,8,0.75) 100%)',
                    }}/>
                    {/* Warm gilt wash overlay for brand cohesion */}
                    <div style={{
                      position: 'absolute', inset: 0, pointerEvents: 'none',
                      mixBlendMode: 'overlay',
                      background: 'linear-gradient(160deg, rgba(212,182,134,0.10) 0%, transparent 50%, rgba(40,28,14,0.20) 100%)',
                    }}/>
                  </>
                )}
                <div style={{ position: 'absolute', top: -80, right: -80, width: 360, height: 360, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(245,158,11,0.12) 0%, rgba(212,182,134,0.06) 45%, transparent 70%)', pointerEvents: 'none' }}/>
                <div style={{ position: 'absolute', bottom: -40, left: -40, width: 240, height: 240, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(180,138,68,0.08) 0%, transparent 65%)', pointerEvents: 'none' }}/>

                {/* live dot */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 16 }}>
                  <motion.div
                    animate={{ opacity: [1, 0.3, 1], scale: [1, 1.3, 1] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                    style={{ width: 6, height: 6, borderRadius: '50%', background: AMBER, boxShadow: `0 0 8px ${AMBER}` }}
                  />
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'rgba(245,158,11,0.70)' }}>Upcoming</span>
                </div>

                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.50)', marginBottom: 10, position: 'relative' }}>Destination</p>
                <motion.h2
                  animate={{ filter: ['drop-shadow(0 0 16px rgba(212,182,134,0.28))', 'drop-shadow(0 0 48px rgba(212,182,134,0.65))', 'drop-shadow(0 0 16px rgba(212,182,134,0.28))'] }}
                  transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 96, lineHeight: 0.85, letterSpacing: '-0.03em', background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'block', marginBottom: 8, position: 'relative' }}
                >
                  {trip.city}
                </motion.h2>
                {trip.country && (
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.32em', textTransform: 'uppercase', color: MUTE, marginBottom: 36, position: 'relative' }}>{trip.country}</p>
                )}

                <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, rgba(232,212,168,0.20), ${HAIRLINE})`, marginBottom: 28 }}/>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 0, position: 'relative' }}>
                  {[
                    { label: 'Departs',   value: trip.departs,  accent: false },
                    { label: 'Returns',   value: trip.returns,  accent: false },
                    { label: 'Duration',  value: trip.duration, accent: false },
                    { label: 'Days away', value: trip.daysAway != null ? daysAway : '—', accent: true  },
                  ].map(({ label, value, accent }, i) => (
                    <div key={label} style={{ borderRight: i < 3 ? `1px solid ${HAIRLINE}` : 'none', paddingRight: 20, paddingLeft: i > 0 ? 20 : 0 }}>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>{label}</p>
                      {accent ? (
                        <motion.p
                          animate={{ filter: [`drop-shadow(0 0 8px ${AMBER}88)`, `drop-shadow(0 0 20px ${AMBER}cc)`, `drop-shadow(0 0 8px ${AMBER}88)`] }}
                          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                          style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 28, fontWeight: 400, color: AMBER, lineHeight: 1 }}
                        >
                          {value}
                        </motion.p>
                      ) : (
                        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 16, fontWeight: 500, color: BONE }}>{value}</p>
                      )}
                    </div>
                  ))}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginTop: 28, paddingTop: 22, borderTop: `1px solid ${HAIRLINE}`, position: 'relative' }}>
                  <motion.div whileHover={{ x: 4 }} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: GOLD }}>View itinerary</span>
                    <ChevronRight size={12} style={{ color: GOLD }}/>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              onClick={() => navigate('/preferences')}
              whileHover={{ y: -4, borderColor: 'rgba(245,158,11,0.35)', transition: spring }}
              whileTap={{ scale: 0.99 }}
              style={{ cursor: 'pointer', padding: '48px 40px', borderRadius: 26, background: 'rgba(245,158,11,0.04)', border: `1px solid rgba(245,158,11,0.18)`, textAlign: 'center', transition: 'all 0.25s' }}
            >
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 32, color: BONE, lineHeight: 1.15, marginBottom: 12 }}>
                Your next trip is one decision away.
              </p>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, marginBottom: 28, lineHeight: 1.6, maxWidth: 360, margin: '0 auto 28px' }}>
                Plan a trip and your itinerary will live here.
              </p>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 22px', borderRadius: 8, background: 'rgba(245,158,11,0.08)', border: `1px solid rgba(245,158,11,0.30)` }}>
                <Plus size={12} style={{ color: AMBER }}/>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: AMBER }}>Plan your first trip</span>
              </div>
            </motion.div>
          )}

          {/* Trip actions row — outside the clickable card so taps never
              accidentally navigate to /itinerary. */}
          {trip && storedItinerary?.itinerary_id && (
            <div style={{ display: 'flex', gap: 10, marginTop: 18, flexWrap: 'wrap' }}>
              <motion.button
                whileHover={{ y: -2, borderColor: 'rgba(212,182,134,0.40)' }} whileTap={{ scale: 0.97 }}
                onClick={() => navigate(`/journal/${storedItinerary.itinerary_id}`)}
                style={{
                  flex: '1 1 180px', padding: '12px 18px',
                  background: 'rgba(232,212,168,0.03)',
                  border: `1px solid ${HAIRLINE}`,
                  borderRadius: 12, cursor: 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                  letterSpacing: '0.22em', textTransform: 'uppercase',
                  color: GOLD, transition: 'all 0.2s',
                }}
              >
                Open journal
              </motion.button>
              {trip.city && (
                <motion.button
                  whileHover={{ y: -2, borderColor: 'rgba(212,182,134,0.40)' }} whileTap={{ scale: 0.97 }}
                  onClick={() => {
                    const q = trip.country ? `?country=${encodeURIComponent(trip.country)}` : ''
                    navigate(`/destination/${encodeURIComponent(trip.city)}${q}`)
                  }}
                  style={{
                    flex: '1 1 180px', padding: '12px 18px',
                    background: 'rgba(232,212,168,0.03)',
                    border: `1px solid ${HAIRLINE}`,
                    borderRadius: 12, cursor: 'pointer',
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                    letterSpacing: '0.22em', textTransform: 'uppercase',
                    color: GOLD, transition: 'all 0.2s',
                  }}
                >
                  Notes from {trip.city}
                </motion.button>
              )}
              {/* Open-to-companions toggle. Surfaces this trip in
                  /discover so other users can request to join. */}
              <motion.button
                whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}
                disabled={openToggleBusy}
                onClick={async () => {
                  if (openToggleBusy) return
                  setOpenToggleBusy(true)
                  try {
                    if (storedItinerary?.is_open_to_join) {
                      await closeMyTrip(storedItinerary.itinerary_id)
                      setStoredItinerary(prev => prev ? { ...prev, is_open_to_join: false } : prev)
                    } else {
                      await openMyTrip(storedItinerary.itinerary_id, { joinCapacity: 1, note: '' })
                      setStoredItinerary(prev => prev ? { ...prev, is_open_to_join: true, join_capacity: 1 } : prev)
                    }
                  } catch (err) {
                    console.warn('open/close trip failed:', err?.message || err)
                  } finally {
                    setOpenToggleBusy(false)
                  }
                }}
                style={{
                  flex: '1 1 180px', padding: '12px 18px',
                  background: storedItinerary?.is_open_to_join
                    ? 'rgba(139,92,246,0.10)'
                    : 'rgba(232,212,168,0.03)',
                  border: `1px solid ${storedItinerary?.is_open_to_join ? 'rgba(139,92,246,0.50)' : HAIRLINE}`,
                  borderRadius: 12, cursor: openToggleBusy ? 'wait' : 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                  letterSpacing: '0.22em', textTransform: 'uppercase',
                  color: storedItinerary?.is_open_to_join ? '#8B5CF6' : GOLD,
                  opacity: openToggleBusy ? 0.6 : 1,
                  transition: 'all 0.2s',
                }}
              >
                {storedItinerary?.is_open_to_join ? '✓ Open to companions' : 'Open to companions'}
              </motion.button>
            </div>
          )}

          {/* Incoming join-requests panel — only renders when the user
              has open requests waiting on their decision. Sits between
              the trip-actions row and past trips so it's visible
              without dominating the column when empty. */}
          {incoming.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }}
              style={{ marginTop: 28, display: 'flex', flexDirection: 'column', gap: 12 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: '#8B5CF6', margin: 0 }}>
                  Join requests
                </p>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: DIM, margin: 0 }}>
                  {incoming.length} pending
                </p>
              </div>
              {incoming.map(req => {
                const busy = !!incomingBusy[req.request_id]
                return (
                  <div key={req.request_id} style={{
                    padding: '16px 18px', borderRadius: 12,
                    background: 'rgba(139,92,246,0.06)',
                    border: '1px solid rgba(139,92,246,0.30)',
                    display: 'flex', alignItems: 'flex-start', gap: 14,
                  }}>
                    <div style={{
                      width: 40, height: 40, borderRadius: '50%', overflow: 'hidden',
                      background: 'rgba(212,182,134,0.06)', flexShrink: 0,
                      border: '1px solid rgba(139,92,246,0.30)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      {req.requester_avatar
                        ? <img src={req.requester_avatar} alt={req.requester_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
                        : <span style={{ fontFamily: '"Cormorant Garamond",serif', fontSize: 16, color: GOLD }}>
                            {(req.requester_name || '?').split(/\s+/).slice(0, 2).map(s => s[0]?.toUpperCase()).join('')}
                          </span>}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE, margin: 0 }}>
                        {req.requester_name || 'Traveller'}
                      </p>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, margin: '3px 0 0', letterSpacing: '0.04em' }}>
                        wants to join your trip
                      </p>
                      {req.message && (
                        <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 13, color: BONE, margin: '10px 0 0', lineHeight: 1.55 }}>
                          "{req.message}"
                        </p>
                      )}
                      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                        <button
                          disabled={busy}
                          onClick={() => decideIncoming(req.request_id, 'approve')}
                          style={{
                            padding: '7px 14px', borderRadius: 16,
                            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                            border: 'none', cursor: busy ? 'wait' : 'pointer',
                            color: '#fff', fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500,
                            letterSpacing: '0.20em', textTransform: 'uppercase',
                            opacity: busy ? 0.7 : 1,
                          }}
                        >
                          Approve
                        </button>
                        <button
                          disabled={busy}
                          onClick={() => decideIncoming(req.request_id, 'deny')}
                          style={{
                            padding: '7px 14px', borderRadius: 16,
                            background: 'rgba(212,182,134,0.03)',
                            border: `1px solid ${HAIRLINE}`,
                            cursor: busy ? 'wait' : 'pointer', color: MUTE,
                            fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500,
                            letterSpacing: '0.20em', textTransform: 'uppercase',
                          }}
                        >
                          Pass
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </motion.div>
          )}

          {/* Past trips moved to its own full-width strip below the grid */}
        </motion.div>

        {/* RIGHT — companions + new trip */}
        <motion.div variants={reveal} style={{ padding: '52px 44px', display: 'flex', flexDirection: 'column', gap: 36 }}>

          <div>
            <div style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <motion.span
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ width: 6, height: 6, borderRadius: '50%', background: GOLD, boxShadow: `0 0 10px ${GOLD}` }}
                />
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
                  Curated for you
                </p>
              </div>
              <motion.h2
                animate={{ filter: [`drop-shadow(0 0 12px rgba(212,182,134,0.18))`, `drop-shadow(0 0 28px rgba(212,182,134,0.45))`, `drop-shadow(0 0 12px rgba(212,182,134,0.18))`] }}
                transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
                style={{
                  fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
                  fontSize: 34, color: BONE, lineHeight: 1.02, margin: 0,
                  letterSpacing: '-0.015em',
                }}
              >
                Travellers tuned to your rhythm.
              </motion.h2>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {activePair && (
                <motion.button
                  initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease }}
                  onClick={() => navigate(`/shared/${encodeURIComponent(activePair.itinerary_id)}`)}
                  style={{
                    textAlign: 'left', padding: '18px 20px', borderRadius: 14,
                    background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.30)',
                    cursor: 'pointer', color: BONE, display: 'flex', flexDirection: 'column', gap: 4,
                  }}
                >
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: '#10B981', fontWeight: 500 }}>
                    You're matched · this trip
                  </span>
                  <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 18, color: BONE }}>
                    Open your shared itinerary →
                  </span>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>
                    Pick up planning together where you left off.
                  </span>
                </motion.button>
              )}
              {!activePair && matches.slice(0, 4).map((m, i) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, x: 24 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.4 + i * 0.12, ease }}
                >
                  <MatchCard match={m} onClick={() => navigate(`/match/${m.id}`)}/>
                </motion.div>
              ))}
              {!matchesLoading && !activePair && matches.length === 0 && (
                <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 14, color: MUTE, padding: '20px 4px', margin: 0 }}>
                  No matches yet — plan a trip and we'll line up companions whose rhythm fits yours.
                </p>
              )}
              {matchesLoading && (
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, padding: '20px 4px', margin: 0 }}>
                  Finding companions…
                </p>
              )}
            </div>
          </div>

        </motion.div>

        {/* Your trips — full-width strip between the main grid and Pulse */}
        {pastTrips.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease, delay: 0.2 }}
            style={{
              gridColumn: '1 / -1',
              padding: '40px 52px 24px',
              borderTop: `1px solid ${HAIRLINE}`,
              position: 'relative',
            }}
          >
            {/* gold gradient hairline ornament */}
            <div style={{
              position: 'absolute', top: -1, left: '50%', transform: 'translateX(-50%)',
              width: 120, height: 1,
              background: `linear-gradient(to right, transparent, ${GOLD}, transparent)`,
            }}/>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 22 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <motion.span
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
                    style={{ width: 6, height: 6, borderRadius: '50%', background: AMBER, boxShadow: `0 0 10px ${AMBER}` }}
                  />
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
                    Your trip vault
                  </p>
                </div>
                <h2 style={{
                  fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
                  fontSize: 30, color: BONE, lineHeight: 1.05, margin: 0,
                  letterSpacing: '-0.015em',
                }}>
                  Every trip you've planned.
                </h2>
              </div>
              <motion.button
                whileHover={{ y: -2, borderColor: 'rgba(245,158,11,0.40)' }} whileTap={{ scale: 0.97 }}
                onClick={() => navigate('/preferences')}
                style={{
                  padding: '11px 20px', borderRadius: 999,
                  background: `linear-gradient(135deg, rgba(245,158,11,0.10) 0%, rgba(245,158,11,0.04) 100%)`,
                  border: `1px solid rgba(245,158,11,0.30)`,
                  cursor: 'pointer', color: AMBER,
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, fontWeight: 500,
                  letterSpacing: '0.22em', textTransform: 'uppercase',
                  display: 'inline-flex', alignItems: 'center', gap: 7,
                  boxShadow: `0 6px 18px rgba(245,158,11,0.18)`,
                  transition: 'all 0.2s',
                }}
              >
                <Plus size={11}/> New trip
              </motion.button>
            </div>
            <PastTripsRow
              trips={pastTrips}
              onSelect={handleSwitchTrip}
              switching={switchingTrip}
            />
          </motion.section>
        )}

        {/* Sonder Pulse — the discovery surface folded inline */}
        <DashboardPulse selfUid={user?.uid}/>
      </motion.div>
    </div>
  )
}
