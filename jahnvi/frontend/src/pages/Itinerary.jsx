import { useState, useEffect, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { onAuthStateChanged } from 'firebase/auth'
import { ArrowLeft, Users, Mail, Check, Bookmark } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import ActivityCard from '../components/ActivityCard'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import { emailItinerary } from '../lib/api'
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
  const [emailing, setEmailing]   = useState(false)
  const [emailSent, setEmailSent] = useState(false)

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
      itinerary_generated: () => setStreamingDone(true),
      done:  (data) => {
        setStreamingDone(true)
        if (data?.itinerary) {
          setItinerary(data.itinerary)
        } else {
          setError('No itinerary returned')
        }
      },
    }
    for (const [evt, copy] of Object.entries(PHASE_COPY)) {
      if (copy) base[evt] = () => setPhase(copy)
    }
    return base
  }, [])

  function handleSave() {
    if (!itinerary) return
    try {
      localStorage.setItem('sonder_last_itinerary', JSON.stringify(itinerary))
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      console.warn('Save failed:', err)
    }
  }

  const { start } = useSSE(handlers)

  useEffect(() => {
    if (startedRef.current) return

    const raw = sessionStorage.getItem('sonder_trip_profile')
    if (!raw) { navigate('/preferences'); return }
    let profile
    try { profile = JSON.parse(raw) } catch { navigate('/preferences'); return }

    const unsub = onAuthStateChanged(auth, (u) => {
      if (!u) { navigate('/signin'); return }
      if (startedRef.current) return
      startedRef.current = true
      start(profile)
    })
    return () => unsub()
  }, [navigate, start])

  async function handleEmailExport() {
    if (!user?.email || !itinerary?.itinerary_id) return
    setEmailing(true)
    try {
      await emailItinerary(itinerary.itinerary_id, [user.email])
      setEmailSent(true)
      setTimeout(() => setEmailSent(false), 3000)
    } catch (err) {
      console.error('Email export failed:', err)
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

  if (!renderTarget) {
    return (
      <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, textAlign: 'center' }}>
        <AppBackground accent={SKY}/>
        <AnimatePresence mode="wait">
          <motion.p
            key={phase}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.4, ease }}
            style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 28, color: `${SKY}cc`, marginBottom: 18, position: 'relative', zIndex: 1 }}
          >
            {phase}…
          </motion.p>
        </AnimatePresence>
        <motion.div
          animate={{ opacity: [0.25, 0.85, 0.25] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          style={{ width: 100, height: 1, background: `linear-gradient(to right, transparent, ${SKY}88, transparent)`, position: 'relative', zIndex: 1 }}
        />
      </div>
    )
  }

  // ── Real itinerary rendering ───────────────────────────────────────────────
  const days = renderTarget.days || []
  const safeActiveDay = Math.min(activeDay, Math.max(days.length - 1, 0))
  const day  = days[safeActiveDay]
  if (!day) {
    return <div style={{ minHeight: '100vh', background: BG }}/>
  }

  // Show the streaming pulse only while days are still arriving — flip off
  // once the orchestrator signals itinerary_generated (or done).
  const isStreaming = !streamingDone && partialDays.length > 0
  const dest = renderTarget.destination || {}
  const dateRange = formatDateRange(tripProfile?.constraints?.start_date, tripProfile?.constraints?.end_date)

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
              whileHover={!saved ? { borderColor: `${SKY}55`, boxShadow: `0 0 24px ${SKY}22`, scale: 1.04, transition: spring } : {}}
              whileTap={!saved ? { scale: 0.96 } : {}}
              onClick={handleSave}
              disabled={saved}
              style={{ background: saved ? `${SKY}14` : 'none', border: `1px solid ${saved ? `${SKY}66` : HAIRLINE}`, borderRadius: 20, padding: '8px 18px', cursor: saved ? 'default' : 'pointer', display: 'flex', alignItems: 'center', gap: 7, transition: 'all 0.25s' }}
            >
              {saved ? <Check size={11} style={{ color: SKY }}/> : <Bookmark size={11} style={{ color: GOLD }}/>}
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: saved ? SKY : GOLD }}>
                {saved ? 'Saved to dashboard' : 'Save itinerary'}
              </span>
            </motion.button>
          )}
          <motion.button
            whileHover={{ borderColor: `${SKY}55`, boxShadow: `0 0 24px ${SKY}22`, scale: 1.04, transition: spring }}
            whileTap={{ scale: 0.96 }}
            onClick={handleEmailExport}
            disabled={emailing || !itinerary}
            style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '8px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 7, transition: 'all 0.2s', opacity: emailing || !itinerary ? 0.6 : 1 }}
          >
            <Mail size={11} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD }}>
              {emailing ? 'Sending…' : emailSent ? 'Sent!' : 'Email itinerary'}
            </span>
          </motion.button>
        </div>
      </nav>

      {/* destination header */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, padding: '40px 48px', position: 'relative', zIndex: 1, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse 50% 150% at 80% 50%, ${SKY}0D 0%, transparent 65%)`, pointerEvents: 'none' }}/>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>Your itinerary</p>
            <motion.h1
              animate={{ filter: ['drop-shadow(0 0 16px rgba(212,182,134,0.18))', 'drop-shadow(0 0 40px rgba(212,182,134,0.42))', 'drop-shadow(0 0 16px rgba(212,182,134,0.18))'] }}
              transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
              style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 52, color: BONE, lineHeight: 1, letterSpacing: '-0.02em' }}
            >
              {dest.city || 'Your trip'}{dest.country ? `, ${dest.country}` : ''}
            </motion.h1>
          </div>
          {dateRange && (
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>{dateRange}</p>
          )}
        </div>
      </div>

      {/* day tab strip */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.75)', backdropFilter: 'blur(16px)', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', overflowX: 'auto' }}>
          {days.map((d, i) => (
            <motion.button
              key={d.day_number}
              whileHover={safeActiveDay !== i ? { color: BONE, transition: { duration: 0.15 } } : {}}
              whileTap={{ scale: 0.97 }}
              onClick={() => setDay(i)}
              style={{
                padding: '18px 28px', background: safeActiveDay === i ? `${SKY}0F` : 'none',
                border: 'none', cursor: 'pointer',
                borderBottom: `2px solid ${safeActiveDay === i ? SKY : 'transparent'}`,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.14em',
                color: safeActiveDay === i ? SKY : MUTE, whiteSpace: 'nowrap', transition: 'all 0.2s',
                boxShadow: safeActiveDay === i ? `inset 0 1px 0 ${SKY}1A` : 'none',
              }}
            >
              Day {d.day_number}{d.theme ? ` — ${d.theme}` : ''}
            </motion.button>
          ))}
          {isStreaming && (
            <motion.div
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
              style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '18px 22px', fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: `${SKY}cc`, whiteSpace: 'nowrap' }}
            >
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: SKY, boxShadow: `0 0 12px ${SKY}` }}/>
              more days coming
            </motion.div>
          )}
        </div>
      </div>

      {/* content */}
      <div style={{ flex: 1, maxWidth: 1100, margin: '0 auto', width: '100%', padding: '0 48px', position: 'relative', zIndex: 1 }}>
        <AnimatePresence mode="wait">
          <motion.div key={safeActiveDay} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -14 }} transition={{ duration: 0.32, ease }}>
            <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 0 }}>

              {/* sidebar */}
              <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '52px 44px 52px 0', position: 'sticky', top: 68, alignSelf: 'start', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', top: 0, left: -44, right: 0, height: 280, background: `radial-gradient(ellipse 80% 60% at 30% 20%, ${SKY}12 0%, transparent 65%)`, pointerEvents: 'none' }}/>
                <div style={{ position: 'relative' }}>
                  <motion.span
                    animate={{ filter: [`drop-shadow(0 0 20px ${SKY}22)`, `drop-shadow(0 0 60px ${SKY}55)`, `drop-shadow(0 0 20px ${SKY}22)`] }}
                    transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
                    style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 140, lineHeight: 0.9, letterSpacing: '-0.04em', color: SKY, opacity: 0.14, userSelect: 'none', display: 'block', marginBottom: -28 }}
                  >
                    {day.day_number}
                  </motion.span>
                  {day.theme && (
                    <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 30, color: BONE, lineHeight: 1.2, position: 'relative' }}>
                      {day.theme}
                    </h2>
                  )}
                </div>

                <div style={{ marginTop: 36, display: 'flex', flexDirection: 'column', gap: 0 }}>
                  {[
                    { label: 'Activities', value: String(day.activities?.length ?? 0) },
                    { label: 'Daily cost', value: day.daily_cost_usd != null ? `$${Math.round(day.daily_cost_usd)}` : '—' },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ padding: '14px 0', borderTop: `1px solid ${HAIRLINE}` }}>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 5 }}>{label}</p>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 15, fontWeight: 500, color: BONE }}>{value}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* activity list */}
              <motion.div variants={stagger} initial="hidden" animate="show" style={{ padding: '52px 0 52px 52px' }}>
                {(day.activities || []).map((ia, j) => (
                  <motion.div key={ia.activity?.activity_id || `${day.day_number}-${j}`} variants={cardReveal}>
                    <ActivityCard
                      activity={ia.activity}
                      time={ia.time}
                      whyThis={ia.why_this}
                      onFeedback={fb => setFb(prev => [...prev.filter(f => f.activity_id !== fb.activity_id), fb])}
                    />
                  </motion.div>
                ))}
                {feedback.length > 0 && (
                  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                    <motion.button
                      whileHover={{ y: -3, boxShadow: `0 0 64px ${SKY}55, 0 0 128px ${SKY}22`, transition: spring }}
                      whileTap={{ scale: 0.97 }}
                      style={{ padding: '16px 36px', background: `linear-gradient(135deg, ${SKY} 0%, #0284C7 100%)`, border: 'none', borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: '#fff', boxShadow: `0 0 48px ${SKY}44, 0 0 96px ${SKY}11`, marginTop: 8 }}
                    >
                      Update itinerary · {feedback.length} change{feedback.length > 1 ? 's' : ''}
                    </motion.button>
                  </motion.div>
                )}
              </motion.div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
