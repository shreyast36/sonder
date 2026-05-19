import { useState, useEffect, useRef, useMemo } from 'react'
import { motion, AnimatePresence, useMotionValue, useTransform, useSpring, useMotionTemplate } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { onAuthStateChanged } from 'firebase/auth'
import { ArrowLeft, Mail, Check, Bookmark } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D, SonderMark3D } from '../components/SonderMark3D'
import { emailItinerary, saveItineraryAsCurrent, getCurrentItinerary } from '../lib/api'
import { useDestinationPhoto } from '../lib/destinationPhoto'
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
  const [showCompanionPrompt, setShowCompanionPrompt] = useState(false)
  const [companionPromptDismissed, setCompanionPromptDismissed] = useState(false)
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
        // button appear immediately even if the rest of the pipeline hangs,
        // and triggers the companion prompt so the user sees it right after
        // the last day lands instead of waiting on validation/matching.
        setStreamingDone(true)
        if (data?.itinerary) {
          setItinerary(data.itinerary)
          // Cache so the user can navigate to /dashboard → "View itinerary"
          // and still see this trip even if they haven't clicked Save yet.
          try { localStorage.setItem('sonder_last_itinerary', JSON.stringify(data.itinerary)) } catch {}
        }
        // Invite them to meet new people for this trip, with a beat so the
        // last day lands first.
        setTimeout(() => setShowCompanionPrompt(true), 1400)
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

  async function handleMeetPeople() {
    if (!itinerary?.itinerary_id) return
    setCompanionPromptDismissed(true)
    // Best-effort save so the trip lands on the dashboard before we navigate.
    if (!saved) {
      try { await saveItineraryAsCurrent(itinerary.itinerary_id) } catch (err) {
        console.warn('save before companions failed:', err?.message || err)
      }
    }
    navigate(`/companions/${itinerary.itinerary_id}`)
  }

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

  // Viewport tracking. Three buckets:
  //   isWide    ≥1180 → side marginalia + edition marks render
  //   isCompact <720  → nav buttons collapse to icons, logo to the mark only
  // Plus a JS-measured viewport height so iOS Safari's 100vh "URL bar"
  // miscalculation doesn't cut the phone off.
  const [vw, setVw] = useState(() => typeof window !== 'undefined' ? window.innerWidth : 1280)
  const [vh, setVh] = useState(() => typeof window !== 'undefined' ? window.innerHeight : 800)
  useEffect(() => {
    const onResize = () => { setVw(window.innerWidth); setVh(window.innerHeight) }
    window.addEventListener('resize', onResize)
    window.addEventListener('orientationchange', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      window.removeEventListener('orientationchange', onResize)
    }
  }, [])
  const isWide    = vw >= 1180
  const isCompact = vw < 720

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

  // Whichever path set itinerary (SSE done, SSE itinerary_generated, or
  // view-mode /current load), make sure the companion prompt eventually
  // shows up. The SSE handlers already arm a delayed prompt; this effect
  // covers view mode where no events fire.
  useEffect(() => {
    if (!itinerary || showCompanionPrompt || companionPromptDismissed) return
    const t = setTimeout(() => setShowCompanionPrompt(true), 1400)
    return () => clearTimeout(t)
  }, [itinerary, showCompanionPrompt, companionPromptDismissed])

  // ── Phone behaviour: power-on, autoscale, wheel routing ────────────────────
  // Phone starts asleep. User taps the screen (or the right-side power
  // button) → boot animation (~1.7s) → app reveals + destination photo
  // fades onto the page background. Mirrors the real "press to wake".
  const [booted, setBooted] = useState(false)
  const [booting, setBooting] = useState(false)
  const bootTimerRef = useRef(null)
  const togglePower = () => {
    if (booted || booting) {
      // Power off — clear any in-flight boot and snap back to sleep.
      if (bootTimerRef.current) { clearTimeout(bootTimerRef.current); bootTimerRef.current = null }
      setBooting(false)
      setBooted(false)
    } else {
      setBooting(true)
      bootTimerRef.current = setTimeout(() => {
        setBooted(true); setBooting(false); bootTimerRef.current = null
      }, 1700)
    }
  }
  // Tapping the dark screen only wakes — never powers off.
  const powerOn = () => { if (!booted && !booting) togglePower() }

  // Phone scales only to fit HORIZONTALLY. Vertical overflow becomes a
  // page scroll instead of a tiny phone — keeps the in-screen text
  // readable at all zoom levels.
  const phoneScale = (() => {
    const pad = isCompact ? 12 : 24
    const availW = Math.max(0, vw - pad * 2)
    return Math.min(1, availW / (PHONE_W + 12))
  })()

  // Route wheel events into the phone's inner scroll when the page itself
  // has nowhere to go vertically. If the viewport is too short to fit the
  // phone (high zoom, short laptops), the page scrolls naturally — wheel
  // hijack stays out of the way so the user can reach the whole device.
  const phoneScrollRef = useRef(null)
  const mainRef = useRef(null)
  const bootedRef = useRef(false)
  useEffect(() => { bootedRef.current = booted }, [booted])
  useEffect(() => {
    const onWheel = (e) => {
      if (!bootedRef.current) return
      const main = mainRef.current
      // Page can scroll? Let it.
      if (main && main.scrollHeight - main.clientHeight > 4) return
      // Don't hijack scroll over the top nav.
      if (e.clientY < 68) return
      const el = phoneScrollRef.current
      if (!el) return
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
    <div style={{ height: vh, overflow: 'hidden', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      {/* nav — responsive: compact icons-only at <720px */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 50,
        borderBottom: `1px solid ${HAIRLINE}`,
        background: 'rgba(10,8,5,0.88)',
        backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
        padding: isCompact ? '0 16px' : '0 48px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        height: isCompact ? 56 : 68, flexShrink: 0,
      }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/dashboard')}
          title="Dashboard"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8, transition: 'color 0.2s' }}
          onMouseEnter={e => { e.currentTarget.style.color = BONE }}
          onMouseLeave={e => { e.currentTarget.style.color = MUTE }}
        >
          <ArrowLeft size={isCompact ? 16 : 18}/>
          {!isCompact && (
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Dashboard</span>
          )}
        </motion.button>
        {isCompact ? <SonderMark3D size={30}/> : <SonderNav3D markSize={32}/>}
        <div style={{ display: 'flex', alignItems: 'center', gap: isCompact ? 6 : 10 }}>
          {itinerary && (
            <motion.button
              whileHover={!saved && !saving ? { borderColor: `${SKY}55`, boxShadow: `0 0 24px ${SKY}22`, scale: 1.04, transition: spring } : {}}
              whileTap={!saved && !saving ? { scale: 0.96 } : {}}
              onClick={handleSave}
              disabled={saved || saving}
              title={saveError || (saved ? 'Saved to dashboard' : saving ? 'Saving…' : 'Save itinerary')}
              style={{
                background: saved ? `${SKY}14` : 'none',
                border: `1px solid ${saved ? `${SKY}66` : HAIRLINE}`,
                borderRadius: isCompact ? '50%' : 20,
                padding: isCompact ? 0 : '8px 18px',
                width: isCompact ? 36 : 'auto', height: isCompact ? 36 : 'auto',
                cursor: saved ? 'default' : saving ? 'wait' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                transition: 'all 0.25s', opacity: saving ? 0.6 : 1,
              }}
            >
              {saved ? <Check size={isCompact ? 14 : 11} style={{ color: SKY }}/> : <Bookmark size={isCompact ? 14 : 11} style={{ color: GOLD }}/>}
              {!isCompact && (
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: saved ? SKY : saveError ? '#E89B7C' : GOLD }}>
                  {saving ? 'Saving…' : saved ? 'Saved to dashboard' : saveError ? 'Try again' : 'Save itinerary'}
                </span>
              )}
            </motion.button>
          )}
          <motion.button
            whileHover={{ borderColor: `${SKY}55`, boxShadow: `0 0 24px ${SKY}22`, scale: 1.04, transition: spring }}
            whileTap={{ scale: 0.96 }}
            onClick={handleEmailExport}
            disabled={emailing || !itinerary}
            title={emailError || (emailSent ? 'Sent!' : emailing ? 'Sending…' : 'Email itinerary')}
            style={{
              background: 'none',
              border: `1px solid ${emailError ? '#E89B7C66' : HAIRLINE}`,
              borderRadius: isCompact ? '50%' : 20,
              padding: isCompact ? 0 : '8px 18px',
              width: isCompact ? 36 : 'auto', height: isCompact ? 36 : 'auto',
              cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
              transition: 'all 0.2s', opacity: emailing || !itinerary ? 0.6 : 1,
            }}
          >
            <Mail size={isCompact ? 14 : 11} style={{ color: emailError ? '#E89B7C' : GOLD }}/>
            {!isCompact && (
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: emailError ? '#E89B7C' : GOLD }}>
                {emailing ? 'Sending…' : emailSent ? 'Sent!' : emailError ? 'Email failed' : 'Email itinerary'}
              </span>
            )}
          </motion.button>
        </div>
      </nav>

      {/* Bespoke print spread. Phone stays at a comfortable readable size;
          when the viewport is too short to show all of it (high zoom, short
          laptops), main scrolls vertically. The wheel hijack yields to that
          natural page scroll automatically. */}
      <main ref={mainRef} style={{
        flex: 1, position: 'relative', zIndex: 1,
        display: 'flex', alignItems: 'safe center', justifyContent: 'safe center',
        padding: isCompact ? '20px 0' : '32px 0',
        overflowX: 'hidden', overflowY: 'auto',
      }}>
        <DestinationBackdrop city={dest?.city} visible={booted && showingItinerary}/>
        <QuietBackdrop/>
        <AtmosphericScene/>
        <GoldDust count={isCompact ? 6 : 12}/>
        <PaperGrain/>
        {isWide && <EditionMark itinerary={itinerary || renderTarget}/>}

        <PhoneStage scale={phoneScale}>
          <PhoneFrame onPowerButton={togglePower} powerButtonGlow={!booted && !booting}>
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

      </main>

      {/* Companion prompt — slides up when the pipeline 'done' event fires,
          asks Yes/No to meeting new people for this trip. Non-blocking. */}
      <AnimatePresence>
        {showCompanionPrompt && !companionPromptDismissed && itinerary && (
          <motion.div
            key="companion-prompt"
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 60, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 240, damping: 26 }}
            style={{
              position: 'fixed',
              bottom: 24, left: '50%', transform: 'translateX(-50%)',
              zIndex: 100,
              maxWidth: 'min(480px, calc(100vw - 32px))',
              padding: '18px 22px',
              background: 'rgba(20,16,11,0.96)',
              border: `1px solid rgba(212,182,134,0.30)`,
              borderRadius: 16,
              backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
              boxShadow: '0 20px 60px rgba(0,0,0,0.55), 0 0 32px rgba(212,182,134,0.10)',
              display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap',
            }}
          >
            <span style={{
              flex: '1 1 220px',
              fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
              fontSize: 16, color: BONE, lineHeight: 1.35,
            }}>
              Would you like to meet new people on this trip?
            </span>
            <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
              <motion.button
                whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}
                onClick={() => setCompanionPromptDismissed(true)}
                style={{
                  padding: '9px 18px', background: 'none',
                  border: `1px solid ${HAIRLINE}`, borderRadius: 18,
                  cursor: 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em',
                  textTransform: 'uppercase', color: MUTE,
                }}
              >
                No
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.04, boxShadow: `0 0 18px ${GOLD}55` }}
                whileTap={{ scale: 0.97 }}
                onClick={handleMeetPeople}
                style={{
                  padding: '9px 22px',
                  background: `linear-gradient(135deg, ${GOLD} 0%, #B89464 100%)`,
                  border: 'none', borderRadius: 18, cursor: 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.20em',
                  textTransform: 'uppercase', color: '#0a0807', fontWeight: 500,
                }}
              >
                Yes
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Bespoke print surround ───────────────────────────────────────────────────

// Paper-grain noise overlay. Reused from Welcome; inlined here so the
// itinerary page doesn't depend on its layout.
const _grainSvg = `<svg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="4" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>`
const _grainBg = `url("data:image/svg+xml,${encodeURIComponent(_grainSvg)}")`

// One quiet velvet field with a single soft warm glow centred behind the
// phone. No animation, no decoration — the room the device sits in.
function QuietBackdrop() {
  return (
    <>
      <div style={{
        position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 110% 90% at 50% 45%, #14110b 0%, #0c0a07 55%, #050402 100%)',
      }}/>
      <div style={{
        position: 'fixed', top: '48%', left: '50%',
        transform: 'translate(-50%, -50%)',
        width: 'min(960px, 86vw)', height: 'min(720px, 72vh)',
        background: 'radial-gradient(ellipse, rgba(212,182,134,0.09) 0%, rgba(184,150,104,0.035) 38%, transparent 72%)',
        filter: 'blur(28px)',
        pointerEvents: 'none', zIndex: 0,
      }}/>
    </>
  )
}

function PaperGrain() {
  return (
    <div style={{
      position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
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
          style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0 }}
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
  // The destination as a framed gallery centerpiece. Eyebrow + city name in
  // shimmering gold leaf + gilt ornament + country, layered behind the phone
  // so what you see in the gaps reads as exhibit signage, not just a label.
  if (!showingItinerary || !dest?.city) return null
  return (
    <motion.div
      key={dest.city}
      initial={{ opacity: 0, scale: 1.04 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 1.6, ease, delay: 0.2 }}
      style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        pointerEvents: 'none', zIndex: 0, userSelect: 'none', overflow: 'hidden',
        gap: '2vh',
      }}
    >
      {/* Eyebrow */}
      <motion.span
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 0.55, y: 0 }}
        transition={{ duration: 1.2, delay: 0.5 }}
        style={{
          fontFamily: '"Inter Tight",sans-serif', fontWeight: 400,
          fontSize: 11, letterSpacing: '0.6em', textIndent: '0.6em',
          textTransform: 'uppercase',
          backgroundImage: 'linear-gradient(180deg, #f0dcb0 0%, #8a6f4a 100%)',
          WebkitBackgroundClip: 'text', backgroundClip: 'text',
          color: 'transparent', WebkitTextFillColor: 'transparent',
        }}
      >
        The Destination
      </motion.span>

      {/* City name — massive gilt with slow shimmer */}
      <motion.span
        animate={{ backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'] }}
        transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
          fontSize: 'clamp(180px, 24vw, 320px)',
          letterSpacing: '-0.045em', lineHeight: 0.85, whiteSpace: 'nowrap',
          backgroundImage: 'linear-gradient(110deg, #2a1f12 0%, #5a4628 14%, #b89968 36%, #f0dcb0 50%, #b89968 64%, #5a4628 86%, #2a1f12 100%)',
          backgroundSize: '220% 100%',
          WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
          WebkitTextFillColor: 'transparent',
          opacity: 0.32,
          filter: `drop-shadow(0 0 48px ${GOLD}30) drop-shadow(0 8px 32px rgba(0,0,0,0.6))`,
        }}
      >
        {dest.city}
      </motion.span>

      {/* Gilt ornament: thin double rule with a diamond + sun-burst tick marks */}
      <motion.div
        initial={{ opacity: 0, scaleX: 0.6 }}
        animate={{ opacity: 0.65, scaleX: 1 }}
        transition={{ duration: 1.2, delay: 0.6 }}
        style={{ display: 'flex', alignItems: 'center', gap: 16 }}
      >
        <span style={{ width: 'clamp(80px, 10vw, 160px)', height: 1, background: 'linear-gradient(to right, transparent, rgba(240,220,176,0.8))' }}/>
        <svg width="22" height="22" viewBox="0 0 22 22">
          <defs>
            <linearGradient id="orn" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f0dcb0"/>
              <stop offset="100%" stopColor="#8a6f4a"/>
            </linearGradient>
          </defs>
          <path d="M11 2 L13 11 L22 11 L13 11 L11 20 L9 11 L0 11 L9 11 Z" fill="url(#orn)" opacity="0.85"/>
        </svg>
        <span style={{ width: 'clamp(80px, 10vw, 160px)', height: 1, background: 'linear-gradient(to left, transparent, rgba(240,220,176,0.8))' }}/>
      </motion.div>

      {/* Country */}
      {dest.country && (
        <motion.span
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 0.55, y: 0 }}
          transition={{ duration: 1.2, delay: 0.7 }}
          style={{
            fontFamily: '"Inter Tight",sans-serif', fontWeight: 400,
            fontSize: 13, letterSpacing: '0.52em', textIndent: '0.52em',
            textTransform: 'uppercase',
            backgroundImage: 'linear-gradient(180deg, #f0dcb0 0%, #8a6f4a 100%)',
            WebkitBackgroundClip: 'text', backgroundClip: 'text',
            color: 'transparent', WebkitTextFillColor: 'transparent',
          }}
        >
          {dest.country}
        </motion.span>
      )}
    </motion.div>
  )
}

// Atmospheric stage: drifting light beams + horizontal mist + floor pool +
// off-center "sun". Cinematic and motion-rich — the kind of thing you'd see
// behind a private auction lot.
// Fully symmetric ambient layer — no diagonal bias, no split-feeling.
// One breathing centred glow + a centred floor pool. That's it.
function AtmosphericScene() {
  return (
    <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
      {/* Centred warm glow, breathing slowly */}
      <motion.div
        animate={{ opacity: [0.7, 0.95, 0.7], scale: [1, 1.03, 1] }}
        transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 'min(1100px, 92vw)', height: 'min(900px, 82vh)',
          background: 'radial-gradient(ellipse, rgba(212,182,134,0.10) 0%, rgba(184,150,104,0.045) 38%, transparent 72%)',
          filter: 'blur(36px)',
        }}
      />
      {/* Floor pool — symmetric warm gilt at the page bottom, gently breathing */}
      <motion.div
        animate={{ opacity: [0.55, 0.85, 0.55] }}
        transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 3 }}
        style={{
          position: 'absolute', bottom: '-22%',
          left: 0, right: 0, height: 520,
          background: 'radial-gradient(ellipse 65% 60% at 50% 100%, rgba(212,182,134,0.14) 0%, rgba(184,150,104,0.06) 35%, transparent 68%)',
          filter: 'blur(44px)',
        }}
      />
    </div>
  )
}

// Top-down gold spotlight, like a museum lamp on a private object.
function Spotlight() {
  return (
    <>
      <motion.div
        animate={{ opacity: [0.55, 0.85, 0.55] }}
        transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute', top: -80, left: '50%',
          transform: 'translateX(-50%)',
          width: 'min(1200px, 90vw)', height: 600,
          background: 'radial-gradient(ellipse 45% 70% at 50% 0%, rgba(240,220,176,0.20) 0%, rgba(212,182,134,0.10) 20%, rgba(184,150,104,0.04) 40%, transparent 70%)',
          filter: 'blur(24px)',
          pointerEvents: 'none', zIndex: 0,
        }}
      />
      {/* Floor wash — warm gold pooling at the bottom */}
      <div style={{
        position: 'absolute', bottom: -120, left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(1400px, 95vw)', height: 400,
        background: 'radial-gradient(ellipse 60% 80% at 50% 100%, rgba(212,182,134,0.10) 0%, rgba(184,150,104,0.05) 30%, transparent 65%)',
        filter: 'blur(32px)',
        pointerEvents: 'none', zIndex: 0,
      }}/>
    </>
  )
}

// A single travelling flight arc — origin dot blooms, dashed gold curve
// traces itself between two points, destination dot lights up, then it all
// fades. Loops on a stagger so the canvas always has one or two routes
// drawing themselves like an in-flight map.
function FlightArc({ from, to, delay = 0, dur = 7, repeatDelay = 6 }) {
  const mx = (from.x + to.x) / 2
  const my = Math.min(from.y, to.y) - 60 - Math.random() * 60
  const d = `M ${from.x} ${from.y} Q ${mx} ${my} ${to.x} ${to.y}`
  return (
    <motion.svg
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'visible' }}
      viewBox="0 0 1000 800" preserveAspectRatio="xMidYMid slice"
    >
      <motion.path
        d={d} fill="none"
        stroke="#d4b686" strokeWidth="1.1"
        strokeDasharray="5 6" strokeLinecap="round"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{
          pathLength: [0, 1, 1, 1],
          opacity:    [0, 0.7, 0.7, 0],
        }}
        transition={{ duration: dur, delay, times: [0, 0.45, 0.78, 1], repeat: Infinity, repeatDelay, ease: 'easeInOut' }}
        style={{ filter: 'drop-shadow(0 0 6px rgba(240,220,176,0.5))' }}
      />
      <motion.circle
        cx={from.x} cy={from.y} r="3.5" fill="#f0dcb0"
        animate={{ opacity: [0, 1, 1, 0] }}
        transition={{ duration: dur, delay, times: [0, 0.08, 0.85, 1], repeat: Infinity, repeatDelay, ease: 'easeOut' }}
        style={{ filter: 'drop-shadow(0 0 8px rgba(240,220,176,0.9))' }}
      />
      <motion.circle
        cx={to.x} cy={to.y} r="3.5" fill="#f0dcb0"
        animate={{ opacity: [0, 0, 1, 0], scale: [0.6, 0.6, 1.2, 1] }}
        transition={{ duration: dur, delay, times: [0, 0.42, 0.55, 1], repeat: Infinity, repeatDelay, ease: 'easeOut' }}
        style={{ transformOrigin: `${to.x}px ${to.y}px`, filter: 'drop-shadow(0 0 8px rgba(240,220,176,0.9))' }}
      />
    </motion.svg>
  )
}

// Soft gold wash + scattered twinkling lights cascading down each flank.
// Fills the vertical strips between the phone and the page edges so they
// don't read as dead space, without adding any more typography.
function FlankGlows({ isCompact }) {
  const perSide = isCompact ? 6 : 10
  const orbs = useMemo(() => (
    ['left', 'right'].flatMap(side =>
      Array.from({ length: perSide }, (_, i) => ({
        id: `${side}-${i}`,
        side,
        top: 6 + (i / perSide) * 84 + Math.random() * 4,
        offset: 2 + Math.random() * 10,
        size: 1.4 + Math.random() * 2.6,
        delay: -Math.random() * 5,
        duration: 2.8 + Math.random() * 3.4,
      }))
    )
  ), [perSide])

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
      {/* Left gilt wash — like sconce light spilling inward */}
      <div style={{
        position: 'absolute', top: 0, bottom: 0, left: 0,
        width: 'min(26%, 320px)',
        background: 'linear-gradient(90deg, rgba(212,182,134,0.11) 0%, rgba(184,150,104,0.04) 45%, transparent 100%)',
      }}/>
      {/* Right gilt wash */}
      <div style={{
        position: 'absolute', top: 0, bottom: 0, right: 0,
        width: 'min(26%, 320px)',
        background: 'linear-gradient(270deg, rgba(212,182,134,0.11) 0%, rgba(184,150,104,0.04) 45%, transparent 100%)',
      }}/>

      {/* Subtle vertical filament running down each flank */}
      <motion.div
        animate={{ opacity: [0.25, 0.55, 0.25] }}
        transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute', top: '6%', bottom: '6%', left: '6%', width: 1,
          background: 'linear-gradient(180deg, transparent, rgba(240,220,176,0.45) 20%, rgba(240,220,176,0.45) 80%, transparent)',
        }}
      />
      <motion.div
        animate={{ opacity: [0.25, 0.55, 0.25] }}
        transition={{ duration: 7, delay: 3.5, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute', top: '6%', bottom: '6%', right: '6%', width: 1,
          background: 'linear-gradient(180deg, transparent, rgba(240,220,176,0.45) 20%, rgba(240,220,176,0.45) 80%, transparent)',
        }}
      />

      {/* Twinkling distant lights along each flank */}
      {orbs.map(o => (
        <motion.div
          key={o.id}
          animate={{ opacity: [0.2, 0.95, 0.2] }}
          transition={{ duration: o.duration, delay: o.delay, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            position: 'absolute',
            [o.side]: `${o.offset}%`,
            top: `${o.top}%`,
            width: o.size, height: o.size,
            borderRadius: '50%',
            background: '#f8e6c0',
            boxShadow: `0 0 ${o.size * 5}px rgba(240,220,176,0.9), 0 0 ${o.size * 10}px rgba(240,220,176,0.35)`,
          }}
        />
      ))}
    </div>
  )
}

// Three layered ridge silhouettes receding into haze at the bottom of the
// canvas, with a warm horizon glow and a sparse line of twinkling city
// lights along the nearest range. Reads as the view from a high terrace
// — fills the empty lower canvas without adding more typography.
function HorizonSilhouette() {
  const cityLights = useMemo(() => Array.from({ length: 22 }, (_, i) => ({
    id: i,
    left: 4 + (i / 22) * 92 + Math.random() * 4,
    bottom: 28 + Math.random() * 36,
    size: 1.4 + Math.random() * 1.8,
    delay: -Math.random() * 6,
    duration: 2.6 + Math.random() * 3.4,
  })), [])
  return (
    <div style={{
      position: 'absolute', left: 0, right: 0, bottom: 0,
      height: 'min(34%, 320px)', pointerEvents: 'none', zIndex: 0,
      overflow: 'hidden',
    }}>
      {/* Atmospheric haze layer — soft warm horizon */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: '60%',
        background: 'linear-gradient(180deg, transparent 0%, rgba(184,150,104,0.04) 35%, rgba(212,182,134,0.10) 75%, rgba(240,220,176,0.13) 100%)',
      }}/>

      {/* Back range — far, almost vapor */}
      <svg style={{ position: 'absolute', bottom: '40%', left: 0, width: '100%', height: 120 }}
        viewBox="0 0 1200 120" preserveAspectRatio="none">
        <path d="M 0 120 L 0 90 Q 120 50 220 78 T 420 64 T 640 50 T 860 70 T 1080 56 T 1200 70 L 1200 120 Z"
              fill="rgba(74,58,32,0.35)"/>
      </svg>

      {/* Middle range */}
      <svg style={{ position: 'absolute', bottom: '20%', left: 0, width: '100%', height: 140 }}
        viewBox="0 0 1200 140" preserveAspectRatio="none">
        <path d="M 0 140 L 0 90 Q 80 38 180 70 T 340 50 T 540 84 T 720 46 T 920 70 T 1200 58 L 1200 140 Z"
              fill="rgba(40,30,18,0.55)"/>
      </svg>

      {/* Front range — closest, darkest */}
      <svg style={{ position: 'absolute', bottom: 0, left: 0, width: '100%', height: 160 }}
        viewBox="0 0 1200 160" preserveAspectRatio="none">
        <path d="M 0 160 L 0 100 Q 100 50 240 86 T 460 60 T 700 96 T 900 50 T 1200 80 L 1200 160 Z"
              fill="rgba(14,11,7,0.85)"/>
      </svg>

      {/* Distant city lights twinkling along the front ridge */}
      {cityLights.map(l => (
        <motion.div
          key={l.id}
          animate={{ opacity: [0.25, 0.95, 0.25] }}
          transition={{ duration: l.duration, delay: l.delay, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            position: 'absolute',
            left: `${l.left}%`, bottom: l.bottom,
            width: l.size, height: l.size,
            borderRadius: '50%',
            background: '#f8e6c0',
            boxShadow: `0 0 ${l.size * 4}px rgba(240,220,176,0.85)`,
          }}
        />
      ))}

      {/* Warm glow line at horizon, just above the back range — like sunset afterglow */}
      <div style={{
        position: 'absolute', bottom: '54%', left: '10%', right: '10%', height: 2,
        background: 'radial-gradient(ellipse 60% 100% at 50% 50%, rgba(240,220,176,0.45) 0%, transparent 70%)',
        filter: 'blur(2px)',
      }}/>
    </div>
  )
}

function FlightPaths() {
  // Pre-baked routes that span the canvas at travel-poster angles.
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
      <FlightArc from={{ x:  80, y: 220 }} to={{ x: 880, y: 300 }} delay={0}  dur={7}  repeatDelay={9}/>
      <FlightArc from={{ x: 920, y: 140 }} to={{ x: 220, y: 560 }} delay={4}  dur={8}  repeatDelay={11}/>
      <FlightArc from={{ x: 160, y: 640 }} to={{ x: 840, y: 480 }} delay={9}  dur={7}  repeatDelay={10}/>
      <FlightArc from={{ x: 460, y:  60 }} to={{ x: 720, y: 720 }} delay={14} dur={8}  repeatDelay={12}/>
      <FlightArc from={{ x: 780, y: 620 }} to={{ x:  60, y: 360 }} delay={20} dur={7}  repeatDelay={11}/>
    </div>
  )
}

// Vintage compass rose — tiny gilded dial drifting slowly in a corner,
// like the inset of a travel atlas. The whole thing rotates ~ once per
// four minutes, and the needle has its own faster sway.
function CompassRose() {
  return (
    <div style={{
      position: 'absolute', top: 96, left: 64,
      width: 132, height: 132,
      opacity: 0.22, pointerEvents: 'none', zIndex: 0,
    }}>
      <motion.svg
        viewBox="0 0 120 120" style={{ width: '100%', height: '100%' }}
        animate={{ rotate: 360 }}
        transition={{ duration: 260, repeat: Infinity, ease: 'linear' }}
      >
        <defs>
          <linearGradient id="cr-gold" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor="#f0dcb0"/>
            <stop offset="60%" stopColor="#b89968"/>
            <stop offset="100%" stopColor="#5a4628"/>
          </linearGradient>
        </defs>
        <circle cx="60" cy="60" r="56" fill="none" stroke="url(#cr-gold)" strokeWidth="0.7"/>
        <circle cx="60" cy="60" r="42" fill="none" stroke="url(#cr-gold)" strokeWidth="0.4"/>
        {/* 4 cardinal arrow blades */}
        {[0, 90, 180, 270].map(deg => (
          <g key={deg} transform={`rotate(${deg} 60 60)`}>
            <polygon points="60,6 57,58 60,52 63,58" fill="url(#cr-gold)"/>
          </g>
        ))}
        {/* 4 intercardinal blades, half scale */}
        {[45, 135, 225, 315].map(deg => (
          <g key={deg} transform={`rotate(${deg} 60 60)`}>
            <polygon points="60,18 58.5,56 60,53 61.5,56" fill="url(#cr-gold)" opacity="0.75"/>
          </g>
        ))}
        <circle cx="60" cy="60" r="2.4" fill="#f0dcb0"/>
        {/* N/E/S/W tick labels — counter-rotated below so they stay upright would
            require a second layer; here they spin with the dial like a real
            map inset, which reads correctly enough at low opacity. */}
        <text x="60" y="5" textAnchor="middle" fontSize="5.4" fill="#f0dcb0" fontFamily="'Cormorant Garamond',serif" fontStyle="italic">N</text>
        <text x="117" y="62" textAnchor="middle" fontSize="5.4" fill="#f0dcb0" fontFamily="'Cormorant Garamond',serif" fontStyle="italic">E</text>
        <text x="60" y="119" textAnchor="middle" fontSize="5.4" fill="#f0dcb0" fontFamily="'Cormorant Garamond',serif" fontStyle="italic">S</text>
        <text x="3" y="62" textAnchor="middle" fontSize="5.4" fill="#f0dcb0" fontFamily="'Cormorant Garamond',serif" fontStyle="italic">W</text>
      </motion.svg>
    </div>
  )
}

// Drifting gold dust — slow, sparse, never distracting.
function GoldDust({ count = 28 }) {
  const particles = useMemo(() => Array.from({ length: count }, (_, i) => ({
    id: i,
    left: Math.random() * 100,
    top:  10 + Math.random() * 80,
    size: 1 + Math.random() * 2.5,
    duration: 22 + Math.random() * 28,
    delay: -Math.random() * 30,
    baseOpacity: 0.15 + Math.random() * 0.4,
    drift: 60 + Math.random() * 120,
  })), [count])

  return (
    <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
      {particles.map(p => (
        <motion.div
          key={p.id}
          animate={{ y: [0, -p.drift, 0], opacity: [p.baseOpacity, p.baseOpacity * 0.3, p.baseOpacity] }}
          transition={{ duration: p.duration, delay: p.delay, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            position: 'absolute',
            left: `${p.left}%`, top: `${p.top}%`,
            width: p.size, height: p.size,
            borderRadius: '50%',
            background: '#f0dcb0',
            boxShadow: `0 0 ${p.size * 3}px rgba(240,220,176,0.7)`,
          }}
        />
      ))}
    </div>
  )
}

// Gilded corner brackets — like the corners of an art print frame.
function CornerOrnaments() {
  const bracket = (
    <svg width="64" height="64" viewBox="0 0 64 64" fill="none" style={{ display: 'block' }}>
      <defs>
        <linearGradient id="cornGold" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%"  stopColor="#f0dcb0"/>
          <stop offset="55%" stopColor="#b89968"/>
          <stop offset="100%" stopColor="#5a4628"/>
        </linearGradient>
      </defs>
      <path d="M4 28 V8 H24" stroke="url(#cornGold)" strokeWidth="1.4" strokeLinecap="round"/>
      <path d="M8 8 L12 8 M8 12 L10 12" stroke="url(#cornGold)" strokeWidth="0.7" strokeLinecap="round"/>
      <circle cx="14" cy="14" r="1.2" fill="url(#cornGold)"/>
    </svg>
  )
  const wrap = { position: 'absolute', pointerEvents: 'none', zIndex: 1, opacity: 0.7 }
  return (
    <>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 0.7 }} transition={{ duration: 1.4, delay: 0.5 }} style={{ ...wrap, top: 18, left: 18 }}>{bracket}</motion.div>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 0.7 }} transition={{ duration: 1.4, delay: 0.55 }} style={{ ...wrap, top: 18, right: 18, transform: 'scaleX(-1)' }}>{bracket}</motion.div>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 0.7 }} transition={{ duration: 1.4, delay: 0.6 }} style={{ ...wrap, bottom: 18, left: 18, transform: 'scaleY(-1)' }}>{bracket}</motion.div>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 0.7 }} transition={{ duration: 1.4, delay: 0.65 }} style={{ ...wrap, bottom: 18, right: 18, transform: 'scale(-1, -1)' }}>{bracket}</motion.div>
    </>
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
  // Tiny gilded print number tucked in the corner — fingerprint, not signage.
  const num = _editionNumber(itinerary)
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 0.7, y: 0 }}
      transition={{ duration: 0.9, ease, delay: 0.4 }}
      style={{
        position: 'fixed', top: 28, right: 32,
        display: 'flex', alignItems: 'baseline', gap: 4,
        zIndex: 51, pointerEvents: 'none',
        fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
        backgroundImage: 'linear-gradient(180deg, #f0dcb0 0%, #d4b686 50%, #8a6f4a 100%)',
        WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
        WebkitTextFillColor: 'transparent',
        filter: 'drop-shadow(0 0 10px rgba(240,220,176,0.32))',
      }}
    >
      <span style={{ fontSize: 11, letterSpacing: '0.04em' }}>N°</span>
      <span style={{ fontSize: 24, lineHeight: 1, letterSpacing: '-0.02em' }}>{num}</span>
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
      {/* Real 3D Sonder mark — the actual brand mark, not a gilt letter. */}
      <motion.div
        initial={{ opacity: 0, scale: 0.78, filter: 'blur(10px)' }}
        animate={{
          opacity: [0, 1, 1, 1],
          scale: [0.78, 1.02, 1, 0.99],
          filter: ['blur(10px)', 'blur(0px)', 'blur(0px)', 'blur(0.5px)'],
        }}
        transition={{ duration: 1.5, times: [0, 0.5, 0.85, 1], ease: 'easeOut' }}
        style={{
          filter: 'drop-shadow(0 0 36px rgba(240,220,176,0.55))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
      >
        <SonderMark3D size={180}/>
      </motion.div>
      <motion.span
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: [0, 0.85, 0.85, 0], y: [10, 0, 0, -4] }}
        transition={{ duration: 1.5, times: [0, 0.55, 0.85, 1], ease: 'easeOut' }}
        style={{
          position: 'absolute', bottom: 110,
          fontFamily: '"Inter Tight",sans-serif',
          fontWeight: 400, fontSize: 13,
          letterSpacing: '0.52em', textIndent: '0.52em', textTransform: 'uppercase',
          backgroundImage: 'linear-gradient(180deg, #F0DCB0 0%, #E8D4A8 35%, #D4B686 55%, #B89464 80%, #8A6F4A 100%)',
          WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
          WebkitTextFillColor: 'transparent',
        }}
      >
        Sonder
      </motion.span>
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.55, 0.55, 0] }}
        transition={{ duration: 1.5, times: [0, 0.6, 0.85, 1], ease: 'easeOut' }}
        style={{
          position: 'absolute', bottom: 84,
          fontFamily: '"Inter Tight",sans-serif', fontWeight: 300,
          fontSize: 8, letterSpacing: '0.42em', textIndent: '0.42em',
          textTransform: 'uppercase', color: 'rgba(244,237,224,0.55)',
        }}
      >
        Travel, together
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

  // Wrapper-with-scaled-dimensions: the outer motion.div takes the SCALED
  // box size so flex centering + overflow:hidden treat it as a smaller
  // element. The inner div renders at the natural device size but is
  // visually scaled via transform-origin top-left, so what you see matches
  // what the layout box reserves. Fixes the cropping when the viewport is
  // shorter than PHONE_H (high browser zoom, short laptop screens, etc.).
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1, ease, delay: 0.15 }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      style={{
        position: 'relative', zIndex: 1, perspective: 1600,
        width: PHONE_W * scale, height: PHONE_H * scale,
        // Auto margins make the phone center when there's room and snap to
        // the top of the scroll area when it overflows — fallback for browsers
        // that don't support align-items: safe center.
        margin: 'auto',
      }}
    >
      <div style={{
        position: 'absolute', top: 0, left: 0,
        width: PHONE_W, height: PHONE_H,
        transform: `scale(${scale})`,
        transformOrigin: 'top left',
      }}>
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
      </div>
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
        title={onPowerButton ? (powerButtonGlow ? 'Power on' : 'Power off') : ''}
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

function PhoneDestinationHeader({ dest, dateRange }) {
  // Wikipedia REST API photo for the destination, when we can find one.
  // Falls back to the warm sky-tinted gradient header if Wikipedia 404s or
  // returns nothing usable.
  const photo = useDestinationPhoto(dest?.city, dest?.country)
  if (photo) {
    return (
      <div style={{ position: 'relative', height: 168, overflow: 'hidden', borderBottom: `1px solid ${HAIRLINE}` }}>
        {/* Cover photo */}
        <img
          src={photo}
          alt={dest?.city || ''}
          referrerPolicy="no-referrer"
          style={{
            position: 'absolute', inset: 0, width: '100%', height: '100%',
            objectFit: 'cover', objectPosition: 'center',
            filter: 'saturate(0.92) brightness(0.78)',
          }}
        />
        {/* Bottom-heavy darken so the text below sits on a quiet plate */}
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(180deg, rgba(8,8,7,0.10) 0%, rgba(8,8,7,0.55) 55%, rgba(8,8,7,0.85) 100%)',
        }}/>
        {/* Warm gilt wash so it matches brand temperature on any photo */}
        <div style={{
          position: 'absolute', inset: 0, mixBlendMode: 'overlay',
          background: 'linear-gradient(160deg, rgba(212,182,134,0.10) 0%, transparent 45%, rgba(40,28,14,0.20) 100%)',
        }}/>
        {/* Text */}
        <div style={{ position: 'absolute', left: 26, right: 26, bottom: 14 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.30em', textTransform: 'uppercase', color: 'rgba(244,237,224,0.75)', margin: 0, marginBottom: 4 }}>
            Your itinerary
          </p>
          <h1 style={{
            fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 30,
            color: BONE, lineHeight: 1.05, letterSpacing: '-0.02em', margin: 0,
            textShadow: '0 2px 18px rgba(0,0,0,0.6)',
          }}>
            {dest.city || 'Your trip'}{dest.country ? `, ${dest.country}` : ''}
          </h1>
          {dateRange && (
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: 'rgba(244,237,224,0.85)', margin: '6px 0 0', textShadow: '0 1px 8px rgba(0,0,0,0.7)' }}>
              {dateRange}
            </p>
          )}
        </div>
      </div>
    )
  }
  // Fallback — the original sky-tinted header.
  return (
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
      <PhoneDestinationHeader dest={dest} dateRange={dateRange}/>

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
