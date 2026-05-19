import { useState, useEffect, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { onAuthStateChanged } from 'firebase/auth'
import { ArrowLeft, Mail, Check, Bookmark } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import { emailItinerary, saveItineraryAsCurrent, getCurrentItinerary } from '../lib/api'
import { useAuth } from '../hooks/useAuth'
import { useSSE } from '../hooks/useSSE'
import { auth } from '../lib/firebase'

const SKY    = '#38BDF8'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

const stagger    = { show: { transition: { staggerChildren: 0.09 } } }
const cardReveal = { hidden: { opacity: 0, y: 22 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease } } }

// SSE event name → user-facing phase copy. Phases the user shouldn't see (transient)
// are mapped to null and don't replace the current label.
const PHASE_COPY = {
  persona_inferring:      'Reading your persona',
  persona_inferred:       null,
  retrieving:             'Finding your destination',
  retrieval_done:         null,
  ranking:                null,
  ranked:                 null,
  generating:             'Designing your days',
  day_ready:              null,                     // handled separately — renders progressively
  itinerary_generated:    null,                     // handled separately — flips streamingDone
  explaining:             null,
  validating:             'Polishing',
  revision:               'Refining',
  validated:              null,
  matching_cotravellers:  'Looking for companions',
  matched:                null,
}

function formatDateRange(startISO, endISO) {
  if (!startISO || !endISO) return ''
  try {
    const s = new Date(startISO)
    const e = new Date(endISO)
    const fmt = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    const days = Math.round((e - s) / 86400000)
    return `${fmt(s)} – ${fmt(e)} · ${days} day${days === 1 ? '' : 's'}`
  } catch { return '' }
}

export default function Itinerary() {
  const navigate          = useNavigate()
  const { user }          = useAuth()
  const [activeDay, setDay]       = useState(0)
  const [feedback, setFb]         = useState([])
  const [emailing, setEmailing]     = useState(false)
  const [emailSent, setEmailSent]   = useState(false)
  const [emailError, setEmailError] = useState(null)

  const [phase, setPhase]         = useState('Reading your persona')
  const [itinerary, setItinerary] = useState(null)
  const [partialDays, setPartialDays] = useState([])  // days as they stream in
  const [destination, setDestination] = useState(null)
  const [streamingDone, setStreamingDone] = useState(false)  // flips on itinerary_generated
  const [saved, setSaved]         = useState(false)
  const [error, setError]         = useState(null)
  const startedRef                = useRef(false)

  const handlers = useMemo(() => {
    const base = {
      error: (data) => setError(data?.message || 'Something went wrong'),
      ranked: (data) => {
        // Pick up the destination string for the header before days stream in.
        if (data?.top_destination) setDestination(data.top_destination)
      },
      day_ready: (data) => {
        if (!data?.day) return
        // Append the new day; dedupe by day_number in case the LLM re-emits.
        setPartialDays(prev => {
          const without = prev.filter(d => d.day_number !== data.day.day_number)
          return [...without, data.day].sort((a, b) => a.day_number - b.day_number)
        })
      },
      itinerary_generated: (data) => {
        // Fires as soon as day streaming completes — well before validation
        // and matching run. Surfacing the itinerary here lets the Save
        // button appear immediately even if the rest of the pipeline hangs.
        setStreamingDone(true)
        if (data?.itinerary) {
          setItinerary(data.itinerary)
          // Cache so the user can navigate to /dashboard → "View itinerary"
          // and still see this trip even if they haven't clicked Save yet.
          try { localStorage.setItem('sonder_last_itinerary', JSON.stringify(data.itinerary)) } catch {}
        }
      },
      done:  (data) => {
        setStreamingDone(true)
        // Refinement may have produced a different final itinerary — prefer
        // that over the one emitted at itinerary_generated.
        if (data?.itinerary) {
          setItinerary(data.itinerary)
          try { localStorage.setItem('sonder_last_itinerary', JSON.stringify(data.itinerary)) } catch {}
        }
      },
    }
    for (const [evt, copy] of Object.entries(PHASE_COPY)) {
      if (copy) base[evt] = () => setPhase(copy)
    }
    return base
  }, [])

  const [saving, setSaving]     = useState(false)
  const [saveError, setSaveErr] = useState(null)

  async function handleSave() {
    if (!itinerary?.itinerary_id || saving || saved) return
    setSaving(true)
    setSaveErr(null)
    try {
      await saveItineraryAsCurrent(itinerary.itinerary_id)
      // Mirror to localStorage so the dashboard renders instantly on first
      // load — the GET /itineraries/current call refreshes it from Firestore.
      try {
        localStorage.setItem('sonder_last_itinerary', JSON.stringify(itinerary))
      } catch { /* quota / private-mode — non-fatal */ }
      setSaved(true)
    } catch (err) {
      console.error('Save failed:', err)
      setSaveErr(err?.message || 'Save failed')
      setTimeout(() => setSaveErr(null), 4000)
    } finally {
      setSaving(false)
    }
  }

  const { start } = useSSE(handlers)

  useEffect(() => {
    if (startedRef.current) return

    // One-shot intent flag set by PersonaReveal.handleConfirm. Present →
    // user just confirmed a fresh persona, so we generate. Absent → user
    // is just viewing (e.g. clicked "View itinerary" from Dashboard), so
    // we load the saved trip from Firestore.
    const shouldGenerate = sessionStorage.getItem('sonder_generate_now') === '1'
    if (shouldGenerate) sessionStorage.removeItem('sonder_generate_now')

    const unsub = onAuthStateChanged(auth, async (u) => {
      if (!u) { navigate('/signin'); return }
      if (startedRef.current) return
      startedRef.current = true

      if (!shouldGenerate) {
        // View mode — pull the saved itinerary from Firestore.
        try {
          const res = await getCurrentItinerary()
          if (res?.itinerary) {
            setItinerary(res.itinerary)
            setStreamingDone(true)
            setSaved(true)        // already on the dashboard
            try { localStorage.setItem('sonder_last_itinerary', JSON.stringify(res.itinerary)) } catch {}
            return
          }
        } catch (err) {
          console.warn('Could not load saved itinerary:', err?.message || err)
        }
        // No saved trip yet. If the user generated something earlier this
        // session but didn't click Save, the cache still has it — show that
        // so they can save from here instead of starting over.
        try {
          const cached = JSON.parse(localStorage.getItem('sonder_last_itinerary') || 'null')
          if (cached?.itinerary_id) {
            setItinerary(cached)
            setStreamingDone(true)
            return
          }
        } catch { /* invalid JSON in cache */ }
        navigate('/preferences')
        return
      }

      // Generation mode — need the trip profile from PersonaReveal.
      const raw = sessionStorage.getItem('sonder_trip_profile')
      if (!raw) { navigate('/preferences'); return }
      let profile
      try { profile = JSON.parse(raw) } catch { navigate('/preferences'); return }
      start(profile)
    })
    return () => unsub()
  }, [navigate, start])

  async function handleEmailExport() {
    if (!user?.email || !itinerary?.itinerary_id) return
    setEmailing(true)
    setEmailError(null)
    try {
      await emailItinerary(itinerary.itinerary_id, [user.email])
      setEmailSent(true)
      setTimeout(() => setEmailSent(false), 3000)
    } catch (err) {
      console.error('Email export failed:', err)
      setEmailError(err?.message || 'Email failed')
      setTimeout(() => setEmailError(null), 5000)
    } finally {
      setEmailing(false)
    }
  }

  // ── Loading / error states ─────────────────────────────────────────────────
  if (error) {
    return (
      <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, textAlign: 'center' }}>
        <AppBackground accent={SKY}/>
        <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 32, color: BONE, marginBottom: 16, position: 'relative', zIndex: 1 }}>Something didn't load.</p>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, marginBottom: 32, maxWidth: 480, position: 'relative', zIndex: 1 }}>{error}</p>
        <motion.button
          whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}
          onClick={() => navigate('/persona-reveal')}
          style={{ minWidth: 240, padding: '16px 32px', background: `linear-gradient(135deg, ${SKY} 0%, #0284C7 100%)`, border: 'none', borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: '#fff', position: 'relative', zIndex: 1 }}
        >
          Back to your persona
        </motion.button>
      </div>
    )
  }

  // Build a render target that combines the final itinerary (when ready) with
  // partial days as they stream in. User sees Day 1 within ~15s of submitting
  // rather than waiting for the full ~6-8k token JSON to finish.
  const tripProfileRaw = sessionStorage.getItem('sonder_trip_profile')
  let tripProfile = {}
  try { tripProfile = JSON.parse(tripProfileRaw || '{}') } catch { /* noop */ }

  const renderTarget = itinerary || (partialDays.length > 0 ? {
    destination: (() => {
      const q = tripProfile?.constraints?.destination_query || destination || ''
      const [city, country] = q.includes(',') ? q.split(',').map(s => s.trim()) : [q, '']
      return { city: city || 'Your trip', country: country || '' }
    })(),
    days: partialDays,
    total_budget_usd: 0,
  } : null)

  // ── Real itinerary rendering ───────────────────────────────────────────────
  const showingItinerary = !!renderTarget
  const days = renderTarget?.days || []
  const safeActiveDay = Math.min(activeDay, Math.max(days.length - 1, 0))
  const day = showingItinerary ? days[safeActiveDay] : null
  const isStreaming = !streamingDone && partialDays.length > 0
  const dest = renderTarget?.destination || {}
  const dateRange = formatDateRange(tripProfile?.constraints?.start_date, tripProfile?.constraints?.end_date)

  // Side panels collapse on narrow viewports so the phone stays the focal
  // point rather than getting squeezed by columns.
  const [isWide, setIsWide] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 1180)
  useEffect(() => {
    const onResize = () => setIsWide(window.innerWidth >= 1180)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const firstName = (() => {
    if (user?.displayName) return user.displayName.split(' ')[0]
    if (user?.email) {
      const local = user.email.split('@')[0].split(/[._-]/)[0]
      return local.charAt(0).toUpperCase() + local.slice(1).toLowerCase()
    }
    return 'Traveller'
  })()

  // Cached persona descriptor — adds an editorial flourish on the right.
  let personaDescriptor = null
  try {
    const raw = localStorage.getItem('sonder_persona_v1')
    if (raw) personaDescriptor = JSON.parse(raw)?.persona?.descriptor || null
  } catch { /* noop */ }

  const totalBudget = renderTarget?.total_budget_usd
    || days.reduce((sum, d) => sum + (d.daily_cost_usd || 0), 0)

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent={SKY}/>

      {/* nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/dashboard')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8, transition: 'color 0.2s' }}
          onMouseEnter={e => { e.currentTarget.style.color = BONE }}
          onMouseLeave={e => { e.currentTarget.style.color = MUTE }}
        >
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Dashboard</span>
        </motion.button>
        <SonderNav3D markSize={32}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {itinerary && (
            <motion.button
              whileHover={!saved && !saving ? { borderColor: `${SKY}55`, boxShadow: `0 0 24px ${SKY}22`, scale: 1.04, transition: spring } : {}}
              whileTap={!saved && !saving ? { scale: 0.96 } : {}}
              onClick={handleSave}
              disabled={saved || saving}
              title={saveError || ''}
              style={{ background: saved ? `${SKY}14` : 'none', border: `1px solid ${saved ? `${SKY}66` : HAIRLINE}`, borderRadius: 20, padding: '8px 18px', cursor: saved ? 'default' : saving ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: 7, transition: 'all 0.25s', opacity: saving ? 0.6 : 1 }}
            >
              {saved ? <Check size={11} style={{ color: SKY }}/> : <Bookmark size={11} style={{ color: GOLD }}/>}
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: saved ? SKY : saveError ? '#E89B7C' : GOLD }}>
                {saving ? 'Saving…' : saved ? 'Saved to dashboard' : saveError ? 'Try again' : 'Save itinerary'}
              </span>
            </motion.button>
          )}
          <motion.button
            whileHover={{ borderColor: `${SKY}55`, boxShadow: `0 0 24px ${SKY}22`, scale: 1.04, transition: spring }}
            whileTap={{ scale: 0.96 }}
            onClick={handleEmailExport}
            disabled={emailing || !itinerary}
            title={emailError || ''}
            style={{ background: 'none', border: `1px solid ${emailError ? '#E89B7C66' : HAIRLINE}`, borderRadius: 20, padding: '8px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 7, transition: 'all 0.2s', opacity: emailing || !itinerary ? 0.6 : 1 }}
          >
            <Mail size={11} style={{ color: emailError ? '#E89B7C' : GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: emailError ? '#E89B7C' : GOLD }}>
              {emailing ? 'Sending…' : emailSent ? 'Sent!' : emailError ? 'Email failed' : 'Email itinerary'}
            </span>
          </motion.button>
        </div>
      </nav>

      {/* Bespoke print spread — massive ghosted destination, paper grain,
          edition mark, handwritten curator note. Phone is the artefact. */}
      <main style={{
        flex: 1, position: 'relative', zIndex: 1,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: isWide ? '40px 64px 80px' : '24px 24px 64px',
        overflow: 'hidden',
        minHeight: 920,
      }}>
        <PaperGrain/>
        <GhostDestination dest={dest} showingItinerary={showingItinerary}/>
        <EditionMark itinerary={itinerary || renderTarget}/>
        <Marginalia firstName={firstName} personaDescriptor={personaDescriptor} showingItinerary={showingItinerary}/>

        <PhoneStage>
          <PhoneFrame>
            <PhoneStatusBar/>
            {!showingItinerary ? (
              <PhoneLoading phase={phase}/>
            ) : (
              <PhoneItinerary
                dest={dest}
                dateRange={dateRange}
                days={days}
                safeActiveDay={safeActiveDay}
                setDay={setDay}
                day={day}
                isStreaming={isStreaming}
              />
            )}
            <PhoneHomeIndicator/>
          </PhoneFrame>
        </PhoneStage>

        <CuratorNote
          dateRange={dateRange}
          firstName={firstName}
          showingItinerary={showingItinerary}
        />
      </main>
    </div>
  )
}

// ─── Bespoke print surround ───────────────────────────────────────────────────

// Paper-grain noise overlay. Reused from Welcome; inlined here so the
// itinerary page doesn't depend on its layout.
const _grainSvg = `<svg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="4" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>`
const _grainBg = `url("data:image/svg+xml,${encodeURIComponent(_grainSvg)}")`

function PaperGrain() {
  return (
    <div style={{
      position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0,
      opacity: 0.05, backgroundImage: _grainBg, backgroundSize: '200px 200px',
      mixBlendMode: 'overlay',
    }}/>
  )
}

function GhostDestination({ dest, showingItinerary }) {
  // Show the city name behind the phone at a massive scale, like wall
  // lettering at a private viewing. Hidden during loading.
  if (!showingItinerary || !dest?.city) return null
  return (
    <motion.div
      key={dest.city}
      initial={{ opacity: 0, scale: 1.04 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 1.6, ease, delay: 0.2 }}
      style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        pointerEvents: 'none', zIndex: 0, userSelect: 'none', overflow: 'hidden',
      }}
    >
      <span style={{
        fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
        fontSize: 'clamp(220px, 28vw, 360px)',
        color: BONE, opacity: 0.045,
        letterSpacing: '-0.045em', lineHeight: 0.9, whiteSpace: 'nowrap',
        textShadow: `0 0 64px ${GOLD}11`,
      }}>
        {dest.city}
      </span>
    </motion.div>
  )
}

// Stable 4-digit "edition number" derived from the itinerary id so each
// trip has its own print number. Falls back to today's day of year while
// generating, so even the loading state feels numbered.
function _editionNumber(itinerary) {
  const id = itinerary?.itinerary_id || ''
  let n = 0
  for (let i = 0; i < id.length; i++) n = (n * 31 + id.charCodeAt(i)) >>> 0
  if (n === 0) {
    const start = new Date(new Date().getFullYear(), 0, 0)
    n = Math.floor((Date.now() - start.getTime()) / 86400000)
  }
  return String(n % 9999).padStart(4, '0')
}

function EditionMark({ itinerary }) {
  const num = _editionNumber(itinerary)
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.9, ease, delay: 0.4 }}
      style={{
        position: 'absolute', top: 36, right: 56,
        display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4,
        zIndex: 2, pointerEvents: 'none', textAlign: 'right',
      }}
    >
      <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 12, color: MUTE, letterSpacing: '0.04em', lineHeight: 1 }}>N°</span>
      <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 44, color: GOLD, lineHeight: 1, letterSpacing: '-0.02em' }}>
        {num}
      </span>
      <div style={{ width: 28, height: 1, background: GOLD, marginTop: 6, marginBottom: 6 }}/>
      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.42em', textTransform: 'uppercase', color: MUTE }}>
        Bespoke · One of one
      </span>
    </motion.div>
  )
}

function Marginalia({ firstName, personaDescriptor, showingItinerary }) {
  // Tiny left-margin annotations — a serial-feeling editorial sidebar.
  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.9, ease, delay: 0.55 }}
      style={{
        position: 'absolute', top: 'min(48%, 460px)', left: 56,
        transform: 'translateY(-50%)',
        display: 'flex', alignItems: 'center', gap: 14,
        zIndex: 2, pointerEvents: 'none',
      }}
    >
      <div style={{
        writingMode: 'vertical-rl', transform: 'rotate(180deg)',
        fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.42em',
        textTransform: 'uppercase', color: MUTE,
      }}>
        Sonder · Private commission · {showingItinerary ? 'Drawn' : 'Drawing'} for {firstName}
      </div>
      {personaDescriptor && (
        <p style={{
          fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
          fontSize: 12, color: `${GOLD}aa`, margin: 0,
          maxWidth: 160, lineHeight: 1.4, transform: 'translateY(0)',
        }}>
          “{personaDescriptor}”
        </p>
      )}
    </motion.div>
  )
}

function CuratorNote({ dateRange, firstName, showingItinerary }) {
  const note = showingItinerary
    ? `Drawn for ${firstName}, with care.`
    : `Drawing your days, ${firstName}.`
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1, ease, delay: 0.75 }}
      style={{
        position: 'absolute', bottom: 56, left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
        zIndex: 2, pointerEvents: 'none', textAlign: 'center',
      }}
    >
      <div style={{ width: 1, height: 28, background: `linear-gradient(to bottom, transparent, ${GOLD}88)` }}/>
      <p style={{
        fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
        fontSize: 17, color: BONE, margin: 0, letterSpacing: '0.005em',
      }}>
        — {note}
      </p>
      {dateRange && (
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.36em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
          {dateRange}
        </p>
      )}
    </motion.div>
  )
}

function PhoneStage({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1, ease, delay: 0.15 }}
      style={{ position: 'relative', zIndex: 1 }}
    >
      {/* Soft pool of light beneath the phone — object on velvet */}
      <div style={{
        position: 'absolute', bottom: -36, left: '50%', transform: 'translateX(-50%)',
        width: 380, height: 80, borderRadius: '50%',
        background: 'radial-gradient(ellipse, rgba(212,182,134,0.18) 0%, transparent 70%)',
        filter: 'blur(20px)', pointerEvents: 'none', zIndex: 0,
      }}/>
      <motion.div
        animate={{ y: [0, -5, 0] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
      >
        {children}
      </motion.div>
    </motion.div>
  )
}

// ─── Phone-frame subcomponents ────────────────────────────────────────────────

const PHONE_W = 392
const PHONE_H = 808
const SCREEN_INSET = 9
const SCREEN_RADIUS = 50

function PhoneFrame({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.7, ease }}
      style={{
        position: 'relative',
        width: PHONE_W, height: PHONE_H,
        borderRadius: SCREEN_RADIUS + SCREEN_INSET,
        // Outer bezel: brushed-black sandwich with gold rim hint.
        background: 'linear-gradient(160deg,#1a1714 0%,#0a0807 45%,#1a1714 100%)',
        padding: SCREEN_INSET,
        boxShadow:
          '0 40px 120px rgba(0,0,0,0.65), ' +
          '0 12px 40px rgba(0,0,0,0.55), ' +
          'inset 0 0 0 1px rgba(212,182,134,0.18), ' +
          'inset 0 0 0 2px rgba(0,0,0,0.6)',
      }}
    >
      {/* Side hardware accents — power + volume buttons */}
      <div style={{ position: 'absolute', right: -2, top: 140, width: 3, height: 78, borderRadius: 2, background: 'linear-gradient(90deg,#0a0807,#1a1714,#0a0807)' }}/>
      <div style={{ position: 'absolute', left: -2, top: 120, width: 3, height: 30, borderRadius: 2, background: 'linear-gradient(90deg,#0a0807,#1a1714,#0a0807)' }}/>
      <div style={{ position: 'absolute', left: -2, top: 168, width: 3, height: 56, borderRadius: 2, background: 'linear-gradient(90deg,#0a0807,#1a1714,#0a0807)' }}/>
      <div style={{ position: 'absolute', left: -2, top: 236, width: 3, height: 56, borderRadius: 2, background: 'linear-gradient(90deg,#0a0807,#1a1714,#0a0807)' }}/>

      {/* Screen */}
      <div style={{
        width: '100%', height: '100%',
        borderRadius: SCREEN_RADIUS,
        background: BG,
        overflow: 'hidden',
        position: 'relative',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Subtle screen reflection */}
        <div style={{ position: 'absolute', inset: 0, borderRadius: SCREEN_RADIUS, background: 'linear-gradient(155deg, rgba(232,212,168,0.05) 0%, transparent 30%, transparent 70%, rgba(232,212,168,0.03) 100%)', pointerEvents: 'none', zIndex: 5 }}/>
        {/* Dynamic island */}
        <div style={{ position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)', width: 112, height: 30, borderRadius: 18, background: '#000', zIndex: 6 }}/>
        {children}
      </div>
    </motion.div>
  )
}

function PhoneStatusBar() {
  return (
    <div style={{ height: 50, padding: '14px 28px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0, position: 'relative', zIndex: 3 }}>
      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 600, fontSize: 14, color: BONE, letterSpacing: '-0.01em' }}>9:41</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: BONE }}>
        {/* Signal bars */}
        <svg width="16" height="11" viewBox="0 0 16 11" fill="none">
          <rect x="0"  y="7" width="2.5" height="4" rx="0.5" fill="currentColor"/>
          <rect x="4"  y="5" width="2.5" height="6" rx="0.5" fill="currentColor"/>
          <rect x="8"  y="3" width="2.5" height="8" rx="0.5" fill="currentColor"/>
          <rect x="12" y="0" width="2.5" height="11" rx="0.5" fill="currentColor"/>
        </svg>
        {/* Wifi */}
        <svg width="15" height="11" viewBox="0 0 15 11" fill="none">
          <path d="M7.5 2.5 C4.5 2.5 2 4 0.5 5.5 L1.8 6.8 C3 5.6 5 4.5 7.5 4.5 C10 4.5 12 5.6 13.2 6.8 L14.5 5.5 C13 4 10.5 2.5 7.5 2.5 Z" fill="currentColor"/>
          <path d="M7.5 5.6 C5.5 5.6 4 6.4 3 7.4 L4.3 8.7 C4.9 8 6 7.6 7.5 7.6 C9 7.6 10.1 8 10.7 8.7 L12 7.4 C11 6.4 9.5 5.6 7.5 5.6 Z" fill="currentColor"/>
          <circle cx="7.5" cy="9.6" r="1" fill="currentColor"/>
        </svg>
        {/* Battery */}
        <div style={{ position: 'relative', width: 24, height: 11 }}>
          <div style={{ position: 'absolute', inset: 0, border: `1px solid ${BONE}`, opacity: 0.45, borderRadius: 3 }}/>
          <div style={{ position: 'absolute', right: -2.5, top: 3.5, width: 1.5, height: 4, background: BONE, opacity: 0.45, borderRadius: 1 }}/>
          <div style={{ position: 'absolute', left: 1.5, top: 1.5, bottom: 1.5, width: 17, background: BONE, borderRadius: 1.5 }}/>
        </div>
      </div>
    </div>
  )
}

function PhoneHomeIndicator() {
  return (
    <div style={{ position: 'absolute', bottom: 8, left: '50%', transform: 'translateX(-50%)', width: 134, height: 5, borderRadius: 3, background: BONE, opacity: 0.85, zIndex: 6 }}/>
  )
}

function PhoneLoading({ phase }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 40px', textAlign: 'center', position: 'relative' }}>
      <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse 60% 50% at 50% 45%, ${SKY}14 0%, transparent 70%)`, pointerEvents: 'none' }}/>
      <AnimatePresence mode="wait">
        <motion.p
          key={phase}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.4, ease }}
          style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: `${SKY}cc`, marginBottom: 22, position: 'relative', zIndex: 1 }}
        >
          {phase}…
        </motion.p>
      </AnimatePresence>
      <motion.div
        animate={{ opacity: [0.25, 0.85, 0.25] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        style={{ width: 80, height: 1, background: `linear-gradient(to right, transparent, ${SKY}88, transparent)`, position: 'relative', zIndex: 1 }}
      />
    </div>
  )
}

function PhoneItinerary({ dest, dateRange, days, safeActiveDay, setDay, day, isStreaming }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
      {/* Header */}
      <div style={{ padding: '6px 28px 18px', borderBottom: `1px solid ${HAIRLINE}`, position: 'relative' }}>
        <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse 90% 100% at 70% 20%, ${SKY}10 0%, transparent 70%)`, pointerEvents: 'none' }}/>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 6, position: 'relative' }}>Your itinerary</p>
        <motion.h1
          animate={{ filter: ['drop-shadow(0 0 12px rgba(212,182,134,0.18))', 'drop-shadow(0 0 28px rgba(212,182,134,0.42))', 'drop-shadow(0 0 12px rgba(212,182,134,0.18))'] }}
          transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
          style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 32, color: BONE, lineHeight: 1.05, letterSpacing: '-0.02em', position: 'relative' }}
        >
          {dest.city || 'Your trip'}{dest.country ? `, ${dest.country}` : ''}
        </motion.h1>
        {dateRange && (
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE, marginTop: 8, position: 'relative' }}>{dateRange}</p>
        )}
      </div>

      {/* Day pill strip */}
      <div style={{ flexShrink: 0, borderBottom: `1px solid ${HAIRLINE}`, padding: '12px 16px', display: 'flex', gap: 8, overflowX: 'auto', scrollbarWidth: 'none' }}>
        {days.map((d, i) => {
          const active = safeActiveDay === i
          return (
            <motion.button
              key={d.day_number}
              whileTap={{ scale: 0.95 }}
              onClick={() => setDay(i)}
              style={{
                padding: '8px 14px', borderRadius: 16,
                background: active ? `${SKY}1A` : 'rgba(232,212,168,0.04)',
                border: `1px solid ${active ? `${SKY}55` : HAIRLINE}`,
                cursor: 'pointer', flexShrink: 0,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.12em',
                color: active ? SKY : MUTE, whiteSpace: 'nowrap', transition: 'all 0.2s',
              }}
            >
              Day {d.day_number}
            </motion.button>
          )
        })}
        {isStreaming && (
          <motion.div
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 10px', flexShrink: 0 }}
          >
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: SKY, boxShadow: `0 0 10px ${SKY}` }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: `${SKY}cc` }}>loading</span>
          </motion.div>
        )}
      </div>

      {/* Scrollable content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={safeActiveDay}
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -16 }}
          transition={{ duration: 0.28, ease }}
          style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', padding: '0 24px 40px', scrollbarWidth: 'thin' }}
        >
          {day && (
            <>
              {/* Day intro */}
              <div style={{ padding: '22px 0 18px', borderBottom: `1px solid ${HAIRLINE}` }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>Day {day.day_number}</p>
                {day.theme && (
                  <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 24, color: BONE, lineHeight: 1.15, margin: 0 }}>{day.theme}</h2>
                )}
                <div style={{ display: 'flex', gap: 14, marginTop: 12 }}>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>
                    {(day.activities?.length ?? 0)} stops
                  </span>
                  {day.daily_cost_usd != null && (
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>
                      · ${Math.round(day.daily_cost_usd)} budget
                    </span>
                  )}
                </div>
              </div>

              {/* Activity rows */}
              <motion.div variants={stagger} initial="hidden" animate="show">
                {(day.activities || []).map((ia, j) => (
                  <PhoneActivityRow
                    key={ia.activity?.activity_id || `${day.day_number}-${j}`}
                    ia={ia}
                    last={j === (day.activities?.length ?? 1) - 1}
                  />
                ))}
              </motion.div>
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

function PhoneActivityRow({ ia, last }) {
  const a = ia?.activity || {}
  const why = ia?.why_this
  return (
    <motion.div
      variants={cardReveal}
      style={{ padding: '20px 0', borderBottom: last ? 'none' : `1px solid ${HAIRLINE}` }}
    >
      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.20em', textTransform: 'uppercase', color: GOLD, marginBottom: 6 }}>
        {ia?.time || ''}
      </p>
      <h3 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 19, color: BONE, lineHeight: 1.25, margin: '0 0 6px' }}>
        {a.name || 'Untitled stop'}
      </h3>
      {why && (
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, lineHeight: 1.5, color: `${BONE}b0`, margin: '0 0 10px', fontStyle: 'italic' }}>
          {why}
        </p>
      )}
      {!why && a.description && (
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, lineHeight: 1.5, color: MUTE, margin: '0 0 10px' }}>
          {a.description}
        </p>
      )}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {a.category && (
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, padding: '3px 8px', borderRadius: 4, background: 'rgba(232,212,168,0.06)', color: MUTE, letterSpacing: '0.06em' }}>
            {a.category}
          </span>
        )}
        {typeof a.cost_usd === 'number' && a.cost_usd > 0 && (
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, padding: '3px 8px', borderRadius: 4, background: 'rgba(232,212,168,0.06)', color: MUTE, letterSpacing: '0.06em' }}>
            ${Math.round(a.cost_usd)}
          </span>
        )}
        {typeof a.duration_hours === 'number' && a.duration_hours > 0 && (
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, padding: '3px 8px', borderRadius: 4, background: 'rgba(232,212,168,0.06)', color: MUTE, letterSpacing: '0.06em' }}>
            {a.duration_hours}h
          </span>
        )}
      </div>
    </motion.div>
  )
}
