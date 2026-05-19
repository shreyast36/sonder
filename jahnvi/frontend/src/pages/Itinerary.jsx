import { useState, useEffect, useRef, useMemo } from 'react'
import { motion, AnimatePresence, useMotionValue, useTransform, useSpring, useMotionTemplate } from 'framer-motion'
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

  // ── Phone behaviour: power-on, autoscale, wheel routing ────────────────────
  // Phone starts asleep. User taps the screen (or the right-side power
  // button) → boot animation (~1.7s) → app reveals + destination photo
  // fades onto the page background. Mirrors the real "press to wake".
  const [booted, setBooted] = useState(false)
  const [booting, setBooting] = useState(false)
  const powerOn = () => {
    if (booted || booting) return
    setBooting(true)
    setTimeout(() => { setBooted(true); setBooting(false) }, 1700)
  }

  // Scale the phone down on short viewports so it always fits without a page
  // scrollbar. The page itself is locked to 100vh — the phone is the only
  // scroll surface, just like a real device.
  const [phoneScale, setPhoneScale] = useState(1)
  useEffect(() => {
    const compute = () => {
      const navH = 68
      const verticalPadding = 64
      const avail = window.innerHeight - navH - verticalPadding
      setPhoneScale(Math.min(1, avail / (PHONE_H + 24)))
    }
    compute()
    window.addEventListener('resize', compute)
    return () => window.removeEventListener('resize', compute)
  }, [])

  // Route every wheel event into the phone's inner scroll, so the user can
  // mousewheel anywhere on the page and the phone scrolls — like they're
  // looking at a device, not a webpage.
  const phoneScrollRef = useRef(null)
  const bootedRef = useRef(false)
  useEffect(() => { bootedRef.current = booted }, [booted])
  useEffect(() => {
    const onWheel = (e) => {
      if (!bootedRef.current) return
      const el = phoneScrollRef.current
      if (!el) return
      // Don't hijack scroll over the top nav (so its buttons stay usable).
      if (e.clientY < 68) return
      el.scrollTop += e.deltaY
      e.preventDefault()
    }
    window.addEventListener('wheel', onWheel, { passive: false })
    return () => window.removeEventListener('wheel', onWheel)
  }, [])

  // Inject scrollbar-hiding CSS once. Real phones don't show track chrome.
  useEffect(() => {
    if (document.getElementById('sonder-phone-scroll-css')) return
    const s = document.createElement('style')
    s.id = 'sonder-phone-scroll-css'
    s.textContent = `
      .sonder-phone-scroll::-webkit-scrollbar { width: 0 !important; height: 0 !important; }
      .sonder-phone-scroll { scrollbar-width: none !important; -ms-overflow-style: none !important; }
    `
    document.head.appendChild(s)
  }, [])

  return (
    <div style={{ height: '100vh', overflow: 'hidden', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
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

      {/* Bespoke print spread. Page is exactly 100vh; the phone is the only
          surface that scrolls. Mousewheel anywhere is routed into it. */}
      <main style={{
        flex: 1, position: 'relative', zIndex: 1,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 0,
        overflow: 'hidden',
      }}>
        <DestinationBackdrop city={dest?.city} visible={booted && showingItinerary}/>
        <PaperGrain/>
        <GoldVignette/>
        <GhostDestination dest={dest} showingItinerary={showingItinerary}/>
        {isWide && <EditionMark itinerary={itinerary || renderTarget}/>}
        {isWide && <Marginalia firstName={firstName} personaDescriptor={personaDescriptor} showingItinerary={showingItinerary}/>}

        <PhoneStage scale={phoneScale}>
          <PhoneFrame onPowerButton={powerOn} powerButtonGlow={!booted && !booting}>
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
                scrollRef={phoneScrollRef}
              />
            )}
            <PhoneHomeIndicator/>
            <AnimatePresence>
              {!booted && !booting && <PhoneSleepScreen key="sleep" onWake={powerOn}/>}
              {booting && <PhoneBootScreen key="boot"/>}
            </AnimatePresence>
          </PhoneFrame>
        </PhoneStage>

        {isWide && (
          <CuratorNote
            dateRange={dateRange}
            firstName={firstName}
            showingItinerary={showingItinerary}
          />
        )}
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

function DestinationBackdrop({ city, visible }) {
  // Pulls a destination photo from Unsplash (no API key, simple Source URL),
  // preloads it, then fades it onto the page once the phone is awake. The
  // image is heavily darkened so the device + gold typography stay readable.
  // If the image fails to load, the existing gold gradient remains the
  // background — no visible fallback noise.
  const [loadedUrl, setLoadedUrl] = useState(null)

  useEffect(() => {
    if (!city) { setLoadedUrl(null); return }
    let cancelled = false
    const url = `https://source.unsplash.com/1600x900/?${encodeURIComponent(city)},travel,city`
    const img = new Image()
    img.onload  = () => { if (!cancelled) setLoadedUrl(url) }
    img.onerror = () => { if (!cancelled) setLoadedUrl(null) }
    img.src = url
    return () => { cancelled = true }
  }, [city])

  return (
    <AnimatePresence>
      {visible && loadedUrl && (
        <motion.div
          key={loadedUrl}
          initial={{ opacity: 0, scale: 1.04 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.8, ease } }}
          transition={{ duration: 2.4, ease }}
          style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0 }}
        >
          {/* The photograph */}
          <div style={{
            position: 'absolute', inset: 0,
            backgroundImage: `url(${loadedUrl})`,
            backgroundSize: 'cover', backgroundPosition: 'center',
            filter: 'saturate(0.85) brightness(0.85)',
          }}/>
          {/* Tinted vignette so the phone reads clearly against any photo */}
          <div style={{
            position: 'absolute', inset: 0,
            background:
              'radial-gradient(ellipse 60% 70% at 50% 50%, rgba(8,8,7,0.45) 0%, rgba(8,8,7,0.78) 60%, rgba(8,8,7,0.94) 100%)',
          }}/>
          {/* Warm gilt wash on top — keeps the brand temperature */}
          <div style={{
            position: 'absolute', inset: 0,
            background: 'linear-gradient(160deg, rgba(212,182,134,0.06) 0%, transparent 40%, rgba(58,45,24,0.18) 100%)',
            mixBlendMode: 'overlay',
          }}/>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function GhostDestination({ dest, showingItinerary }) {
  // City name behind the phone — gilded text that catches a slow shimmer,
  // like gold leaf on a gallery wall.
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
      <motion.span
        animate={{ backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'] }}
        transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
          fontSize: 'clamp(220px, 28vw, 380px)',
          letterSpacing: '-0.045em', lineHeight: 0.9, whiteSpace: 'nowrap',
          // Gilded gradient — dark gold → bright gold → dark gold, with a
          // slow horizontal shimmer that catches the eye but never demands it.
          backgroundImage: 'linear-gradient(110deg, #3a2d18 0%, #6a4f28 18%, #b89968 38%, #f0dcb0 50%, #b89968 62%, #6a4f28 82%, #3a2d18 100%)',
          backgroundSize: '200% 100%',
          WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
          opacity: 0.18,
          filter: `drop-shadow(0 0 32px ${GOLD}22)`,
        }}
      >
        {dest.city}
      </motion.span>
    </motion.div>
  )
}

function GoldVignette() {
  // Soft, rich gold radial that surrounds the phone — gives the page
  // depth without screaming "neon glow".
  return (
    <>
      <motion.div
        animate={{ opacity: [0.55, 0.85, 0.55] }}
        transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%,-50%)',
          width: 1100, height: 1100, borderRadius: '50%',
          background: 'radial-gradient(ellipse, rgba(240,220,176,0.13) 0%, rgba(212,182,134,0.06) 30%, transparent 65%)',
          filter: 'blur(20px)', pointerEvents: 'none', zIndex: 0,
        }}
      />
      {/* Corner gilding */}
      <div style={{ position: 'absolute', top: -120, right: -120, width: 480, height: 480, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(240,220,176,0.10) 0%, transparent 65%)', pointerEvents: 'none', zIndex: 0 }}/>
      <div style={{ position: 'absolute', bottom: -160, left: -120, width: 520, height: 520, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(184,150,104,0.09) 0%, transparent 65%)', pointerEvents: 'none', zIndex: 0 }}/>
    </>
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
  // Gilded gradient applied via background-clip so it reads as real
  // metal, not flat gold colour.
  const goldText = {
    backgroundImage: 'linear-gradient(180deg, #f0dcb0 0%, #d4b686 35%, #8a6f4a 80%, #5a4628 100%)',
    WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
    WebkitTextFillColor: 'transparent',
    filter: 'drop-shadow(0 0 14px rgba(240,220,176,0.32))',
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.9, ease, delay: 0.4 }}
      style={{
        position: 'absolute', top: 32, right: 56,
        display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6,
        zIndex: 2, pointerEvents: 'none', textAlign: 'right',
      }}
    >
      <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 13, letterSpacing: '0.08em', lineHeight: 1, ...goldText }}>N°</span>
      <motion.span
        animate={{ filter: ['drop-shadow(0 0 14px rgba(240,220,176,0.32))', 'drop-shadow(0 0 34px rgba(240,220,176,0.58))', 'drop-shadow(0 0 14px rgba(240,220,176,0.32))'] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
          fontSize: 64, lineHeight: 1, letterSpacing: '-0.025em',
          ...goldText,
        }}
      >
        {num}
      </motion.span>
      <div style={{ width: 44, height: 1, background: 'linear-gradient(to right, transparent, #f0dcb0, transparent)', marginTop: 8, marginBottom: 6, opacity: 0.85 }}/>
      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.48em', textTransform: 'uppercase', ...goldText }}>
        Bespoke · One of one
      </span>
      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.38em', textTransform: 'uppercase', color: MUTE, marginTop: 2 }}>
        Sonder Atelier
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
        position: 'absolute', bottom: 48, left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
        zIndex: 2, pointerEvents: 'none', textAlign: 'center',
      }}
    >
      {/* Two-tone gold filament drop */}
      <div style={{ width: 1, height: 36, background: 'linear-gradient(to bottom, transparent, rgba(240,220,176,0.85))' }}/>
      <p style={{
        fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
        fontSize: 20, margin: 0, letterSpacing: '0.005em',
        backgroundImage: 'linear-gradient(180deg, #f0dcb0 0%, #d4b686 60%, #8a6f4a 100%)',
        WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
        WebkitTextFillColor: 'transparent',
        filter: 'drop-shadow(0 0 14px rgba(240,220,176,0.30))',
      }}>
        — {note}
      </p>
      {/* Decorative gold flourish: thin double rule with a centered diamond */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
        <span style={{ width: 56, height: 1, background: 'linear-gradient(to right, transparent, rgba(240,220,176,0.85))' }}/>
        <span style={{ width: 5, height: 5, transform: 'rotate(45deg)', background: '#f0dcb0', boxShadow: '0 0 10px rgba(240,220,176,0.6)' }}/>
        <span style={{ width: 56, height: 1, background: 'linear-gradient(to left, transparent, rgba(240,220,176,0.85))' }}/>
      </div>
      {dateRange && (
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.42em', textTransform: 'uppercase', color: GOLD, margin: 0 }}>
          {dateRange}
        </p>
      )}
    </motion.div>
  )
}

function PhoneSleepScreen({ onWake }) {
  // Dark always-on style display: faint gilt power glyph + "tap to wake".
  // Whole screen is the wake target so the user can tap anywhere on the
  // device, the way an iPhone's tap-to-wake gesture works.
  return (
    <motion.div
      key="sleep"
      initial={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.35, ease } }}
      onClick={onWake}
      style={{
        position: 'absolute', inset: 0, background: '#000', zIndex: 20,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        borderRadius: SCREEN_RADIUS, cursor: 'pointer', userSelect: 'none',
      }}
    >
      {/* Pulsing gilt power glyph */}
      <motion.div
        animate={{ opacity: [0.32, 0.85, 0.32], scale: [0.96, 1, 0.96] }}
        transition={{ duration: 3.4, repeat: Infinity, ease: 'easeInOut' }}
        style={{ marginBottom: 22 }}
      >
        <svg width="46" height="46" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="sonderPower" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"  stopColor="#f0dcb0"/>
              <stop offset="55%" stopColor="#d4b686"/>
              <stop offset="100%" stopColor="#8a6f4a"/>
            </linearGradient>
          </defs>
          <path d="M12 3 V12" stroke="url(#sonderPower)" strokeWidth="1.8" strokeLinecap="round"/>
          <path d="M5.5 8 A8 8 0 1 0 18.5 8" stroke="url(#sonderPower)" strokeWidth="1.8" strokeLinecap="round" fill="none"/>
        </svg>
      </motion.div>
      <motion.span
        animate={{ opacity: [0.35, 0.85, 0.35] }}
        transition={{ duration: 2.8, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          fontFamily: '"Inter Tight",sans-serif',
          fontSize: 10, letterSpacing: '0.48em', textTransform: 'uppercase',
          color: GOLD, marginBottom: 6,
        }}
      >
        Tap to wake
      </motion.span>
      <span style={{
        fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
        fontSize: 11, color: 'rgba(212,182,134,0.55)',
      }}>
        — or press the side button
      </span>
    </motion.div>
  )
}

function PhoneBootScreen() {
  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.55, ease } }}
      style={{
        position: 'absolute', inset: 0, background: '#000', zIndex: 20,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        borderRadius: SCREEN_RADIUS,
        overflow: 'hidden',
      }}
    >
      {/* Brightness sweep — like the panel actually waking. */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.35, 0.6, 0.3] }}
        transition={{ duration: 1.4, times: [0, 0.5, 0.8, 1], ease: 'easeOut' }}
        style={{
          position: 'absolute', inset: 0,
          background: 'radial-gradient(ellipse 70% 50% at 50% 50%, rgba(240,220,176,0.18) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.82, filter: 'blur(8px)' }}
        animate={{
          opacity: [0, 1, 1, 1],
          scale: [0.82, 1, 1, 0.97],
          filter: ['blur(8px)', 'blur(0px)', 'blur(0px)', 'blur(1px)'],
        }}
        transition={{ duration: 1.5, times: [0, 0.45, 0.78, 1], ease: 'easeOut' }}
        style={{
          fontFamily: '"Cormorant Garamond",serif',
          fontStyle: 'italic', fontWeight: 400,
          fontSize: 132, lineHeight: 1,
          backgroundImage: 'linear-gradient(180deg, #f0dcb0 0%, #d4b686 55%, #8a6f4a 100%)',
          WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
          WebkitTextFillColor: 'transparent',
          filter: 'drop-shadow(0 0 32px rgba(240,220,176,0.55))',
        }}
      >
        S
      </motion.div>
      {/* Subtle "Sonder" wordmark below the S */}
      <motion.span
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: [0, 0.7, 0.7, 0], y: [8, 0, 0, -4] }}
        transition={{ duration: 1.5, times: [0, 0.55, 0.85, 1], ease: 'easeOut' }}
        style={{
          position: 'absolute', bottom: 96,
          fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
          letterSpacing: '0.48em', textTransform: 'uppercase',
          color: GOLD,
        }}
      >
        Sonder
      </motion.span>
    </motion.div>
  )
}

function PhoneStage({ children, scale = 1 }) {
  // Mouse-tracked 3D tilt with spring smoothing — the phone reads as a
  // physical object the cursor is holding. All hooks declared at the top
  // of the component, no hook calls inside JSX (React 18 prod is strict).
  const rawX = useMotionValue(0)
  const rawY = useMotionValue(0)
  const x = useSpring(rawX, { stiffness: 160, damping: 24, mass: 0.6 })
  const y = useSpring(rawY, { stiffness: 160, damping: 24, mass: 0.6 })
  const rotateX = useTransform(y, [-1, 1], [10, -10])
  const rotateY = useTransform(x, [-1, 1], [-12, 12])
  const sheenX  = useTransform(x, [-1, 1], ['0%', '100%'])
  const sheenY  = useTransform(y, [-1, 1], ['0%', '100%'])
  // Compose a CSS background string that reactively follows the cursor.
  const sheenBg = useMotionTemplate`radial-gradient(circle 260px at ${sheenX} ${sheenY}, rgba(240,220,176,0.22) 0%, transparent 60%)`

  function onMove(e) {
    const r = e.currentTarget.getBoundingClientRect()
    rawX.set(((e.clientX - r.left) / r.width  - 0.5) * 2)
    rawY.set(((e.clientY - r.top)  / r.height - 0.5) * 2)
  }
  function onLeave() {
    rawX.set(0); rawY.set(0)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1, ease, delay: 0.15 }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      style={{ position: 'relative', zIndex: 1, perspective: 1600, transform: `scale(${scale})`, transformOrigin: 'center center' }}
    >
      {/* Pool of warm gold light beneath the phone — velvet plinth */}
      <div style={{
        position: 'absolute', bottom: -56, left: '50%', transform: 'translateX(-50%)',
        width: 420, height: 110, borderRadius: '50%',
        background: 'radial-gradient(ellipse, rgba(240,220,176,0.28) 0%, rgba(212,182,134,0.10) 40%, transparent 75%)',
        filter: 'blur(28px)', pointerEvents: 'none', zIndex: 0,
      }}/>
      <motion.div
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        style={{ rotateX, rotateY, transformStyle: 'preserve-3d' }}
      >
        {children}
        {/* Cursor-tracked highlight that glides across the rim */}
        <motion.div
          style={{
            position: 'absolute', inset: 0,
            borderRadius: SCREEN_RADIUS + SCREEN_INSET,
            background: sheenBg,
            pointerEvents: 'none', mixBlendMode: 'screen',
            zIndex: 3,
          }}
        />
      </motion.div>
    </motion.div>
  )
}

// ─── Phone-frame subcomponents ────────────────────────────────────────────────

const PHONE_W = 392
const PHONE_H = 808
const SCREEN_INSET = 9
const SCREEN_RADIUS = 50

// Polished-gold rim: dark base + bright gilt highlight band + dark base again.
// Layered as box-shadows so it stays sharp at the rounded corners.
const GOLD_RIM = (
  '0 50px 140px rgba(0,0,0,0.7), ' +
  '0 18px 60px rgba(0,0,0,0.55), ' +
  '0 0 80px rgba(212,182,134,0.18), ' +              // soft gold halo
  'inset 0 0 0 1px rgba(58,45,24,0.95), ' +          // dark outer edge
  'inset 0 0 0 2.5px rgba(240,220,176,0.85), ' +     // bright gilt
  'inset 0 0 0 4px rgba(110,82,42,0.95), ' +         // burnt gold
  'inset 0 0 0 5px rgba(240,220,176,0.55), ' +       // second highlight
  'inset 0 0 0 6.5px rgba(20,16,10,0.95)'            // black just inside the rim
)

function PhoneFrame({ children, onPowerButton, powerButtonGlow }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.7, ease }}
      style={{
        position: 'relative',
        width: PHONE_W, height: PHONE_H,
        borderRadius: SCREEN_RADIUS + SCREEN_INSET,
        // Bezel itself: rich gold-leaf gradient that catches the sheen overlay
        // from the PhoneStage cursor tracker.
        background: 'linear-gradient(135deg, #3a2d18 0%, #8a6f4a 25%, #f0dcb0 48%, #b89968 60%, #6a5028 80%, #2a1f12 100%)',
        padding: SCREEN_INSET,
        boxShadow: GOLD_RIM,
      }}
    >
      {/* Side hardware accents — gilt power + volume buttons */}
      <motion.button
        onClick={onPowerButton}
        animate={powerButtonGlow
          ? { boxShadow: ['0 0 6px rgba(240,220,176,0.4)', '0 0 22px rgba(240,220,176,0.95)', '0 0 6px rgba(240,220,176,0.4)'] }
          : { boxShadow: '0 0 6px rgba(240,220,176,0.4)' }}
        transition={powerButtonGlow ? { duration: 2.4, repeat: Infinity, ease: 'easeInOut' } : { duration: 0.3 }}
        title={onPowerButton && powerButtonGlow ? 'Power on' : ''}
        style={{
          position: 'absolute', right: -3, top: 150,
          width: 3.5, height: 82, borderRadius: 2,
          background: 'linear-gradient(90deg,#3a2d18,#f0dcb0 50%,#3a2d18)',
          border: 'none', padding: 0,
          cursor: onPowerButton ? 'pointer' : 'default',
          zIndex: 4,
        }}
      />
      <div style={{ position: 'absolute', left: -2.5, top: 124, width: 3.5, height: 30, borderRadius: 2, background: 'linear-gradient(90deg,#3a2d18,#f0dcb0 50%,#3a2d18)' }}/>
      <div style={{ position: 'absolute', left: -2.5, top: 174, width: 3.5, height: 58, borderRadius: 2, background: 'linear-gradient(90deg,#3a2d18,#f0dcb0 50%,#3a2d18)' }}/>
      <div style={{ position: 'absolute', left: -2.5, top: 244, width: 3.5, height: 58, borderRadius: 2, background: 'linear-gradient(90deg,#3a2d18,#f0dcb0 50%,#3a2d18)' }}/>

      {/* Screen */}
      <div style={{
        width: '100%', height: '100%',
        borderRadius: SCREEN_RADIUS,
        background: BG,
        overflow: 'hidden',
        position: 'relative',
        display: 'flex', flexDirection: 'column',
        boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.95), inset 0 0 24px rgba(0,0,0,0.6)',
      }}>
        {/* Glass reflection — diagonal warm highlight */}
        <div style={{ position: 'absolute', inset: 0, borderRadius: SCREEN_RADIUS, background: 'linear-gradient(155deg, rgba(240,220,176,0.07) 0%, transparent 30%, transparent 70%, rgba(240,220,176,0.04) 100%)', pointerEvents: 'none', zIndex: 5 }}/>
        {/* Dynamic island */}
        <div style={{ position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)', width: 112, height: 30, borderRadius: 18, background: '#000', boxShadow: 'inset 0 0 0 1px rgba(240,220,176,0.12)', zIndex: 6 }}/>
        {children}
      </div>
    </motion.div>
  )
}

function _formatPhoneTime(date) {
  const h = date.getHours() % 12 || 12
  const m = String(date.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

function PhoneStatusBar() {
  // Live clock — updates each minute on the actual minute boundary.
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const align = 60_000 - (Date.now() % 60_000)
    let interval
    const timeout = setTimeout(() => {
      setNow(new Date())
      interval = setInterval(() => setNow(new Date()), 60_000)
    }, align)
    return () => { clearTimeout(timeout); if (interval) clearInterval(interval) }
  }, [])

  // Battery: real reading when the browser supports it, otherwise a stable 1.0.
  // Wrapped in synchronous try/catch because some mobile browsers (Firefox,
  // Brave on Android) throw on access rather than rejecting the promise.
  const [batteryLevel, setBatteryLevel] = useState(1)
  const [charging, setCharging] = useState(false)
  useEffect(() => {
    if (typeof navigator === 'undefined' || typeof navigator.getBattery !== 'function') return
    let bat
    let cancelled = false
    let sync = null
    try {
      const p = navigator.getBattery()
      if (p && typeof p.then === 'function') {
        p.then(b => {
          if (cancelled) return
          bat = b
          sync = () => { setBatteryLevel(b.level); setCharging(b.charging) }
          sync()
          b.addEventListener('levelchange', sync)
          b.addEventListener('chargingchange', sync)
        }).catch(() => { /* unavailable — keep defaults */ })
      }
    } catch { /* sync throw — keep defaults */ }
    return () => {
      cancelled = true
      if (bat && sync) {
        try { bat.removeEventListener('levelchange', sync); bat.removeEventListener('chargingchange', sync) } catch {}
      }
    }
  }, [])

  const fillWidth = Math.max(2, Math.round(17 * batteryLevel))
  const fillColor = batteryLevel <= 0.18 ? '#E89B7C' : BONE

  return (
    <div style={{ height: 50, padding: '14px 28px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0, position: 'relative', zIndex: 3 }}>
      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 600, fontSize: 14, color: BONE, letterSpacing: '-0.01em', fontVariantNumeric: 'tabular-nums' }}>
        {_formatPhoneTime(now)}
      </span>
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
        {/* Battery — real fill level */}
        <div style={{ position: 'relative', width: 24, height: 11 }}>
          <div style={{ position: 'absolute', inset: 0, border: `1px solid ${BONE}`, opacity: 0.45, borderRadius: 3 }}/>
          <div style={{ position: 'absolute', right: -2.5, top: 3.5, width: 1.5, height: 4, background: BONE, opacity: 0.45, borderRadius: 1 }}/>
          <div style={{ position: 'absolute', left: 1.5, top: 1.5, bottom: 1.5, width: fillWidth, background: fillColor, borderRadius: 1.5, transition: 'width 0.5s ease, background 0.3s' }}/>
          {charging && (
            <span style={{ position: 'absolute', top: -1, left: 8, fontSize: 9, color: '#FFD166', textShadow: '0 0 4px rgba(255,209,102,0.8)' }}>⚡</span>
          )}
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

function PhoneItinerary({ dest, dateRange, days, safeActiveDay, setDay, day, isStreaming, scrollRef }) {
  // Auto-scroll the active day pill into the center of the strip when the
  // selected day changes (e.g. swipe gesture, or click from the Index).
  const stripRef = useRef(null)
  useEffect(() => {
    const strip = stripRef.current
    if (!strip) return
    const target = strip.children[safeActiveDay]
    if (!target) return
    const rect = strip.getBoundingClientRect()
    const tRect = target.getBoundingClientRect()
    const offset = (tRect.left - rect.left) - (rect.width / 2) + (tRect.width / 2)
    strip.scrollTo({ left: strip.scrollLeft + offset, behavior: 'smooth' })
  }, [safeActiveDay])

  // Swipe to change day. Combine offset + velocity into "swipe power" so a
  // quick flick counts even with little distance, like real iOS scrolling.
  function handleDragEnd(_e, info) {
    if (!days || days.length <= 1) return
    const power = info.offset.x + info.velocity.x * 0.25
    if (power < -90 && safeActiveDay < days.length - 1) {
      setDay(safeActiveDay + 1)
    } else if (power > 90 && safeActiveDay > 0) {
      setDay(safeActiveDay - 1)
    }
  }

  const canSwipeLeft  = safeActiveDay > 0
  const canSwipeRight = safeActiveDay < (days?.length ?? 1) - 1

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
      <div ref={stripRef} style={{ flexShrink: 0, borderBottom: `1px solid ${HAIRLINE}`, padding: '12px 16px', display: 'flex', gap: 8, overflowX: 'auto', scrollbarWidth: 'none', WebkitOverflowScrolling: 'touch' }}>
        {days.map((d, i) => {
          const active = safeActiveDay === i
          return (
            <motion.button
              key={d.day_number}
              whileTap={{ scale: 0.94 }}
              whileHover={!active ? { scale: 1.03 } : {}}
              onClick={() => setDay(i)}
              style={{
                padding: '8px 14px', borderRadius: 16,
                background: active ? `${SKY}1A` : 'rgba(232,212,168,0.04)',
                border: `1px solid ${active ? `${SKY}55` : HAIRLINE}`,
                cursor: 'pointer', flexShrink: 0,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.12em',
                color: active ? SKY : MUTE, whiteSpace: 'nowrap', transition: 'all 0.2s',
                boxShadow: active ? `0 0 16px ${SKY}33` : 'none',
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

      {/* Stable scroll container — the page's wheel router targets this ref
          so the phone is the sole scroll surface. Day swap happens inside it
          via AnimatePresence + drag for swipe paging. */}
      <div
        ref={scrollRef}
        className="sonder-phone-scroll"
        style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', WebkitOverflowScrolling: 'touch' }}
      >
        <AnimatePresence mode="wait" custom={{ canSwipeLeft, canSwipeRight }}>
          <motion.div
            key={safeActiveDay}
            drag={(days?.length ?? 1) > 1 ? 'x' : false}
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.22}
            onDragEnd={handleDragEnd}
            initial={{ opacity: 0, x: 28 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -28 }}
            transition={{ duration: 0.32, ease }}
            style={{ padding: '0 24px 40px', cursor: (days?.length ?? 1) > 1 ? 'grab' : 'auto', touchAction: 'pan-y' }}
          >
            {day && (
              <>
              {/* Day intro */}
              <div style={{ padding: '22px 0 18px', borderBottom: `1px solid ${HAIRLINE}` }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>
                  Day {day.day_number}{day.trip_date ? ` · ${_fmtDay(day.trip_date)}` : ''}
                </p>
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

              {/* Subtle swipe hint at the bottom on the first day */}
              {(days?.length ?? 1) > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10, padding: '12px 0 4px', opacity: 0.55 }}>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.32em', textTransform: 'uppercase', color: MUTE }}>
                    Swipe
                  </span>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {days.map((_, i) => (
                      <span key={i} style={{ width: i === safeActiveDay ? 14 : 4, height: 4, borderRadius: 2, background: i === safeActiveDay ? SKY : 'rgba(232,212,168,0.25)', transition: 'all 0.3s' }}/>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </motion.div>
      </AnimatePresence>
      </div>
    </div>
  )
}

function _fmtDay(v) {
  try {
    const d = new Date(typeof v === 'string' ? v.slice(0, 10) : v)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  } catch { return '' }
}

function PhoneActivityRow({ ia, last }) {
  const a = ia?.activity || {}
  const why = ia?.why_this
  return (
    <motion.div
      variants={cardReveal}
      whileHover={{ x: 2, transition: { duration: 0.2 } }}
      whileTap={{ scale: 0.985 }}
      style={{ padding: '20px 0', borderBottom: last ? 'none' : `1px solid ${HAIRLINE}`, cursor: 'pointer' }}
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
