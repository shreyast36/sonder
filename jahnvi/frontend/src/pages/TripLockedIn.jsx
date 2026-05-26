/**
 * Reveal screen between Itinerary-approve and the next step.
 *
 * After the user hits "I'm happy with the proposed itinerary and approve!"
 * on /itinerary, we route them here. Two phases:
 *
 *   1. REVEAL  — "You're going to {City}" with the hero photo + a quick
 *                summary of the finalized days. Sits long enough to land.
 *   2. PROMPT  — "Want to find someone to travel with?" Yes / No.
 *                Yes → /companions/:id  (cotraveller intake)
 *                No  → save as current trip, /dashboard
 *
 * The itinerary is already finalized + persisted by the time we get
 * here (Itinerary.handleApprove ran approveItinerary + saveItineraryAsCurrent),
 * so this page is purely UX choreography.
 */

import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { BG, BONE, GOLD, MUTE, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import { useDestinationPhoto, useDestinationPhotos } from '../lib/destinationPhoto'
import { getCurrentItinerary, saveItineraryAsCurrent } from '../lib/api'
import { useAuth } from '../hooks/useAuth'

const SKY    = '#38BDF8'
const ORANGE = '#F97316'
const GREEN  = '#10B981'
const spring = { type: 'spring', stiffness: 240, damping: 24 }

function _fmtDateRange(days) {
  if (!days || days.length === 0) return ''
  try {
    const s = days[0]?.trip_date
    const e = days[days.length - 1]?.trip_date
    if (!s || !e) return ''
    const f = (d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    return `${f(s)} – ${f(e)} · ${days.length} day${days.length === 1 ? '' : 's'}`
  } catch { return '' }
}

export default function TripLockedIn() {
  const navigate = useNavigate()
  const { itineraryId } = useParams()
  const { user, loading: authLoading } = useAuth()

  // 'reveal' → showing destination + itinerary
  // 'prompt' → asking about co-travellers
  // 'going'  → user picked yes/no, navigating away
  const [phase, setPhase] = useState('reveal')
  const [itinerary, setItinerary] = useState(null)
  const [error, setError] = useState(null)

  // Pull the just-approved itinerary from the backend (most authoritative).
  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/signin'); return }
    let cancelled = false
    ;(async () => {
      try {
        const { itinerary: cur } = await getCurrentItinerary()
        if (cancelled) return
        if (cur && (!itineraryId || cur.itinerary_id === itineraryId)) {
          setItinerary(cur)
        } else if (cur) {
          // Mismatch — the URL itineraryId isn't the user's current trip.
          // Use whatever the backend says is current; the URL is just for
          // shape and we don't 404 on a stale link.
          setItinerary(cur)
        } else {
          setError("We couldn't find your finalized trip — back to dashboard.")
        }
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Could not load your trip')
      }
    })()
    return () => { cancelled = true }
  }, [authLoading, user, itineraryId, navigate])

  // Cinematic reveal needs more breathing room — the Ken-Burns montage
  // cuts every ~1.2s and the typographic build runs ~3.6s before the
  // city title settles. 7s is the read-and-breathe window before the
  // page flips to the co-traveller prompt. "Continue" lets eager users
  // skip ahead.
  useEffect(() => {
    if (phase !== 'reveal' || !itinerary) return
    const t = setTimeout(() => setPhase('prompt'), 7200)
    return () => clearTimeout(t)
  }, [phase, itinerary])

  const dest = itinerary?.destination || {}
  // Multi-photo for the reveal montage. Falls back to the single-
  // photo helper (Wikipedia path) when Pixabay returns nothing usable
  // so the screen always has at least one background image.
  const photos = useDestinationPhotos(dest.city, dest.country, 5)
  const fallbackPhoto = useDestinationPhoto(dest.city, dest.country)
  const montagePhotos = useMemo(() => {
    if (photos.length > 0) return photos
    return fallbackPhoto ? [fallbackPhoto] : []
  }, [photos, fallbackPhoto])

  // Rotate through the montage every 1.2s during the reveal phase.
  // Pauses on the prompt screen so the user isn't visually distracted
  // when reading the question.
  const [photoIdx, setPhotoIdx] = useState(0)
  useEffect(() => {
    if (phase !== 'reveal' || montagePhotos.length < 2) return
    const t = setInterval(() => {
      setPhotoIdx(i => (i + 1) % montagePhotos.length)
    }, 1200)
    return () => clearInterval(t)
  }, [phase, montagePhotos.length])

  const days  = itinerary?.days || []
  const dateRange = _fmtDateRange(days)

  async function handleWantsCompanion() {
    if (!itinerary?.itinerary_id) return
    setPhase('going')
    // Best-effort: make sure the trip is the user's current one before we
    // route into the cotraveller flow. Approve handler already does this
    // but a refresh between approve + prompt could lose it.
    try { await saveItineraryAsCurrent(itinerary.itinerary_id) } catch { /* noop */ }
    navigate(`/companions/${encodeURIComponent(itinerary.itinerary_id)}`)
  }

  async function handleSoloDashboard() {
    if (!itinerary?.itinerary_id) {
      navigate('/dashboard')
      return
    }
    setPhase('going')
    try { await saveItineraryAsCurrent(itinerary.itinerary_id) } catch { /* noop */ }
    navigate('/dashboard')
  }

  return (
    <div style={{
      minHeight: '100vh', background: BG, color: BONE,
      display: 'flex', flexDirection: 'column',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* CINEMATIC MONTAGE — Ken-Burns slideshow.
          Rapid 1.2s cuts give the page a trailer cadence. Each slide
          zooms slightly and crossfades into the next so the transition
          feels deliberate rather than choppy. */}
      <AnimatePresence>
        {phase === 'reveal' && montagePhotos.length > 0 && (
          <motion.div
            key={`slide-${photoIdx}`}
            initial={{ opacity: 0, scale: 1.18 }}
            animate={{ opacity: 1, scale: 1.04 }}
            exit={{ opacity: 0, scale: 1.10 }}
            transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
            style={{
              position: 'absolute', inset: 0, zIndex: 0,
              backgroundImage: `url(${montagePhotos[photoIdx]})`,
              backgroundSize: 'cover', backgroundPosition: 'center',
              filter: 'saturate(0.88) brightness(0.58)',
              willChange: 'transform, opacity',
            }}
          />
        )}
      </AnimatePresence>

      {/* After the reveal phase settles the prompt screen pins on the
          first photo so the background stays calm while the user reads
          the question. */}
      {phase !== 'reveal' && montagePhotos.length > 0 && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 0,
          backgroundImage: `url(${montagePhotos[0]})`,
          backgroundSize: 'cover', backgroundPosition: 'center',
          filter: 'saturate(0.78) brightness(0.45)',
        }}/>
      )}

      {/* Cinematic vignette — dark edges keep focus centre, where the
          type lives. Always rendered (independent of montage) so the
          composition reads as "film frame" not "browser tab". */}
      <div style={{
        position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 120% 90% at 50% 50%, transparent 25%, rgba(0,0,0,0.75) 100%)',
      }}/>

      {/* Top + bottom gradient scrims for type contrast */}
      <div style={{
        position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none',
        background: 'linear-gradient(180deg, rgba(8,8,7,0.55) 0%, rgba(14,11,8,0.30) 30%, rgba(14,11,8,0.30) 70%, rgba(8,8,7,0.85) 100%)',
      }}/>

      {/* Opening flash — quick gold burst on initial reveal so the page
          lands with a visible "stinger" rather than a fade-in. Mounts
          once and gone in 600ms. */}
      <AnimatePresence>
        {phase === 'reveal' && itinerary && (
          <motion.div
            key="stinger"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.45, 0] }}
            transition={{ duration: 0.65, times: [0, 0.3, 1], ease: 'easeOut' }}
            style={{
              position: 'absolute', inset: 0, zIndex: 3, pointerEvents: 'none',
              background: 'radial-gradient(ellipse at 50% 50%, rgba(240,220,176,0.85) 0%, rgba(212,182,134,0.45) 25%, transparent 60%)',
              mixBlendMode: 'screen',
            }}
          />
        )}
      </AnimatePresence>

      {/* Gold dust particles falling from the top — adds visible motion
          during the reveal so the screen never feels static. */}
      {phase === 'reveal' && <GoldDust count={28}/>}

      {/* Top nav — minimal, just the brand mark */}
      <nav style={{
        position: 'relative', zIndex: 5,
        padding: '20px 48px', display: 'flex', justifyContent: 'center',
      }}>
        <SonderNav3D markSize={32}/>
      </nav>

      <div style={{
        flex: 1, position: 'relative', zIndex: 2,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '32px 24px 64px',
        textAlign: 'center',
      }}>
        <AnimatePresence mode="wait">
          {/* ─── ERROR ─── */}
          {error && (
            <motion.div
              key="err"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.35, ease }}
              style={{ maxWidth: 540 }}
            >
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 30, color: BONE, marginBottom: 18 }}>
                Something didn't load.
              </p>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, marginBottom: 30 }}>
                {error}
              </p>
              <button onClick={() => navigate('/dashboard')} style={ctaSecondary}>
                Back to dashboard
              </button>
            </motion.div>
          )}

          {/* ─── LOADING ─── */}
          {!error && !itinerary && (
            <motion.div
              key="load"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.3, ease }}
            >
              <motion.p
                animate={{ opacity: [0.35, 0.9, 0.35] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: `${GOLD}cc` }}
              >
                Pulling up your trip…
              </motion.p>
            </motion.div>
          )}

          {/* ─── REVEAL ─── */}
          {!error && itinerary && phase === 'reveal' && (
            <motion.div
              key="reveal"
              initial={{ opacity: 1 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, scale: 1.08, transition: { duration: 0.5, ease } }}
              style={{ width: '100%', maxWidth: 920 }}
            >
              {/* "LOCKED IN" — track-out animation: starts tight, expands
                  as it lands so it reads as the camera pulling back. */}
              <motion.p
                initial={{ opacity: 0, letterSpacing: '0.20em' }}
                animate={{ opacity: 1, letterSpacing: '0.42em' }}
                transition={{ duration: 1.1, delay: 0.15, ease }}
                style={{
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
                  textTransform: 'uppercase', fontWeight: 600,
                  color: GOLD, marginBottom: 28,
                  textShadow: `0 0 24px ${GOLD}55`,
                }}
              >
                Locked in
              </motion.p>

              {/* COUNTRY — slams in before the city for a "trailer card"
                  feel. Small caps, tracked out, drops a beat before CITY. */}
              {dest.country && (
                <motion.p
                  initial={{ opacity: 0, y: -16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.6, ease }}
                  style={{
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 13,
                    letterSpacing: '0.36em', textTransform: 'uppercase',
                    color: 'rgba(244,237,224,0.85)', marginBottom: 12,
                    textShadow: '0 2px 14px rgba(0,0,0,0.65)',
                  }}
                >
                  {dest.country}
                </motion.p>
              )}

              {/* CITY — the OH SHIT moment. Starts overscaled and blurred
                  at 0.95 then SLAMS to scale 1 with a deep drop-shadow
                  and the gold particle stinger fires behind it (handled
                  above). Pulses gently after settling. */}
              <motion.h1
                initial={{ opacity: 0, scale: 1.55, filter: 'blur(16px)', y: 12 }}
                animate={{
                  opacity: 1, scale: 1, filter: 'blur(0px)', y: 0,
                }}
                transition={{
                  duration: 1.05,
                  delay: 0.95,
                  ease: [0.16, 1, 0.3, 1],
                }}
                style={{
                  fontFamily: '"Cormorant Garamond",serif', fontWeight: 400,
                  fontStyle: 'italic',
                  fontSize: 'clamp(54px, 11vw, 152px)',
                  lineHeight: 0.95, letterSpacing: '-0.025em',
                  color: BONE, marginBottom: 22,
                  textShadow: '0 8px 48px rgba(0,0,0,0.75), 0 0 60px rgba(212,182,134,0.30)',
                  willChange: 'transform, filter, opacity',
                }}
              >
                {dest.city || 'your trip'}
              </motion.h1>

              {/* Underline ornament — a hairline that draws across after
                  the city lands. Telegraphs "this is the title". */}
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 120, opacity: 1 }}
                transition={{ duration: 0.7, delay: 1.7, ease }}
                style={{
                  height: 1, background: `linear-gradient(to right, transparent, ${GOLD}, transparent)`,
                  margin: '0 auto 28px',
                  boxShadow: `0 0 12px ${GOLD}55`,
                }}
              />

              {/* "You're going" — affirmation line in serif, lower-key
                  than the city but warm enough to land. */}
              <motion.p
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 1.9, ease }}
                style={{
                  fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
                  fontSize: 'clamp(22px, 3vw, 32px)',
                  color: `${BONE}d0`, margin: '0 0 14px',
                  letterSpacing: '0.01em',
                }}
              >
                You're going.
              </motion.p>

              {/* DATE — click-in with a tiny x-shake so it reads as a
                  stamped credit. */}
              {dateRange && (
                <motion.p
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: [0, -3, 3, 0] }}
                  transition={{
                    opacity: { duration: 0.5, delay: 2.4, ease },
                    x:       { duration: 0.5, delay: 2.4, times: [0, 0.3, 0.7, 1], ease: 'easeOut' },
                  }}
                  style={{
                    fontFamily: '"Inter Tight",sans-serif',
                    fontSize: 14, color: BONE, marginBottom: 40,
                    letterSpacing: '0.24em', textTransform: 'uppercase',
                    fontWeight: 500,
                  }}
                >
                  {dateRange}
                </motion.p>
              )}

              {/* Day stripe — each pill cascades in left-to-right after
                  the date stamp. Reads like end credits scrolling. */}
              {days.length > 0 && (
                <div style={{
                  display: 'flex', flexWrap: 'wrap', gap: 8,
                  justifyContent: 'center', marginBottom: 40,
                  maxWidth: 720, marginLeft: 'auto', marginRight: 'auto',
                }}>
                  {days.slice(0, 12).map((d, i) => (
                    <motion.span
                      key={d.day_number}
                      initial={{ opacity: 0, y: 10, scale: 0.92 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      transition={{
                        duration: 0.4,
                        delay: 3.0 + i * 0.08,
                        ease: [0.16, 1, 0.3, 1],
                      }}
                      style={{
                        padding: '8px 14px', borderRadius: 999,
                        background: 'rgba(212,182,134,0.10)',
                        border: `1px solid ${GOLD}33`,
                        fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                        letterSpacing: '0.10em', color: `${BONE}e0`,
                        maxWidth: 320, overflow: 'hidden',
                        textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        boxShadow: `0 0 18px ${GOLD}11`,
                      }}
                    >
                      Day {d.day_number}{d.theme ? ` · ${d.theme}` : ''}
                    </motion.span>
                  ))}
                </div>
              )}

              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6, delay: 4.2, ease }}
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => setPhase('prompt')}
                style={ctaSecondary}
              >
                Continue
              </motion.button>
            </motion.div>
          )}

          {/* ─── PROMPT ─── */}
          {!error && itinerary && phase === 'prompt' && (
            <motion.div
              key="prompt"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.5, ease }}
              style={{ width: '100%', maxWidth: 620 }}
            >
              <p style={{
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                letterSpacing: '0.32em', textTransform: 'uppercase',
                color: MUTE, marginBottom: 22,
              }}>
                One more thing
              </p>
              <h2 style={{
                fontFamily: '"Cormorant Garamond",serif', fontWeight: 400,
                fontStyle: 'italic', fontSize: 'clamp(28px, 4.6vw, 44px)',
                lineHeight: 1.18, color: BONE, marginBottom: 18,
                letterSpacing: '-0.01em',
              }}>
                Want to find someone to travel with?
              </h2>
              <p style={{
                fontFamily: '"Inter Tight",sans-serif', fontWeight: 300,
                fontSize: 14, color: `${BONE}b0`, lineHeight: 1.6,
                marginBottom: 44, maxWidth: 480, marginLeft: 'auto', marginRight: 'auto',
              }}>
                We can match you with compatible co-travellers who are heading the same way — or you can keep it solo.
              </p>

              <div style={{
                display: 'flex', flexDirection: 'column', gap: 14,
                alignItems: 'center',
              }}>
                <motion.button
                  whileHover={{ y: -2, boxShadow: `0 0 56px ${SKY}55, 0 0 120px ${SKY}18` }}
                  whileTap={{ scale: 0.97 }}
                  onClick={handleWantsCompanion}
                  style={ctaPrimary(SKY)}
                >
                  Yes — find me a co-traveller
                </motion.button>
                <motion.button
                  whileHover={{ y: -2 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={handleSoloDashboard}
                  style={ctaSecondary}
                >
                  No — I'll travel solo
                </motion.button>
              </div>
            </motion.div>
          )}

          {/* ─── GOING ─── transient state during navigate */}
          {phase === 'going' && (
            <motion.div
              key="going"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ duration: 0.3, ease }}
            >
              <motion.p
                animate={{ opacity: [0.35, 0.9, 0.35] }}
                transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
                style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: `${GOLD}cc` }}
              >
                On your way…
              </motion.p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// Gold-dust particles drifting across the screen during the reveal.
// Cheap visual motion — keeps the screen alive without a video asset.
// Each particle gets a deterministic seed so positions stay stable
// across re-renders within the same mount.
function GoldDust({ count = 24 }) {
  const particles = useMemo(() => {
    return Array.from({ length: count }, (_, i) => ({
      left:    Math.random() * 100,
      size:    1 + Math.random() * 2.5,
      drift:   -20 + Math.random() * 40,
      delay:   Math.random() * 4,
      dur:     5 + Math.random() * 5,
      opacity: 0.25 + Math.random() * 0.55,
    }))
  }, [count])
  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 2, pointerEvents: 'none',
      overflow: 'hidden',
    }}>
      {particles.map((p, i) => (
        <motion.span
          key={i}
          initial={{ y: '-10vh', x: 0, opacity: 0 }}
          animate={{
            y: '110vh',
            x: p.drift,
            opacity: [0, p.opacity, p.opacity, 0],
          }}
          transition={{
            duration: p.dur,
            delay:    p.delay,
            repeat:   Infinity,
            ease:     'linear',
            times:    [0, 0.15, 0.85, 1],
          }}
          style={{
            position: 'absolute',
            left: `${p.left}%`,
            top: 0,
            width: p.size, height: p.size,
            borderRadius: '50%',
            background: `radial-gradient(circle, rgba(240,220,176,1) 0%, rgba(212,182,134,0.4) 60%, transparent 100%)`,
            boxShadow: '0 0 6px rgba(240,220,176,0.7)',
            willChange: 'transform, opacity',
          }}
        />
      ))}
    </div>
  )
}

function ctaPrimary(accent) {
  return {
    minWidth: 300,
    padding: '18px 32px',
    background: `linear-gradient(135deg, ${accent} 0%, ${accent === SKY ? '#0284C7' : '#059669'} 100%)`,
    border: 'none', borderRadius: 12,
    cursor: 'pointer',
    fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
    letterSpacing: '0.22em', textTransform: 'uppercase',
    fontWeight: 600, color: '#0a0807',
    transition: 'all 0.25s',
    boxShadow: `0 0 40px ${accent}33`,
  }
}

const ctaSecondary = {
  minWidth: 220,
  padding: '14px 28px',
  background: 'rgba(212,182,134,0.04)',
  border: `1px solid ${HAIRLINE}`,
  borderRadius: 12,
  cursor: 'pointer',
  fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
  letterSpacing: '0.20em', textTransform: 'uppercase',
  fontWeight: 400, color: MUTE,
  transition: 'all 0.2s',
}
