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

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { BG, BONE, GOLD, MUTE, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import { useDestinationPhoto } from '../lib/destinationPhoto'
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

  // Auto-advance from reveal → prompt after a beat so the user reads the
  // destination name before the question lands. 4s is the read-and-breathe
  // window for "{Destination} · {dates}". User can also skip past with the
  // "Continue" button.
  useEffect(() => {
    if (phase !== 'reveal' || !itinerary) return
    const t = setTimeout(() => setPhase('prompt'), 4200)
    return () => clearTimeout(t)
  }, [phase, itinerary])

  const dest = itinerary?.destination || {}
  const photo = useDestinationPhoto(dest.city, dest.country)
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
      {/* Hero photo as a soft background, with a deep gradient over it so
          the type stays readable. Slow zoom on mount to feel cinematic. */}
      {photo && (
        <motion.div
          initial={{ scale: 1.10, opacity: 0 }}
          animate={{ scale: 1.00, opacity: 1 }}
          transition={{ duration: 2.4, ease }}
          style={{
            position: 'absolute', inset: 0, zIndex: 0,
            backgroundImage: `url(${photo})`,
            backgroundSize: 'cover', backgroundPosition: 'center',
            filter: 'saturate(0.85) brightness(0.55)',
          }}
        />
      )}
      <div style={{
        position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none',
        background: 'linear-gradient(180deg, rgba(8,8,7,0.55) 0%, rgba(14,11,8,0.40) 35%, rgba(8,8,7,0.92) 100%)',
      }}/>

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
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.7, ease }}
              style={{ width: '100%', maxWidth: 780 }}
            >
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.2, ease }}
                style={{
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                  letterSpacing: '0.36em', textTransform: 'uppercase',
                  color: `${GOLD}cc`, marginBottom: 28,
                }}
              >
                Locked in
              </motion.p>

              <motion.h1
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 1.1, delay: 0.35, ease }}
                style={{
                  fontFamily: '"Cormorant Garamond",serif', fontWeight: 400,
                  fontStyle: 'italic', fontSize: 'clamp(36px, 7vw, 84px)',
                  lineHeight: 1.0, letterSpacing: '-0.02em',
                  color: BONE, marginBottom: 14,
                  textShadow: '0 6px 32px rgba(0,0,0,0.55)',
                }}
              >
                You're going to {dest.city || 'your trip'}.
              </motion.h1>

              {dest.country && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.8, delay: 0.9, ease }}
                  style={{
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 12,
                    letterSpacing: '0.32em', textTransform: 'uppercase',
                    color: MUTE, marginBottom: 14,
                  }}
                >
                  {dest.country}
                </motion.p>
              )}

              {dateRange && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.8, delay: 1.1, ease }}
                  style={{
                    fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
                    fontSize: 20, color: `${BONE}c0`, marginBottom: 40,
                  }}
                >
                  {dateRange}
                </motion.p>
              )}

              {/* Day stripe — small per-day pills so the reveal carries the
                  finalized itinerary's actual shape, not just the city name. */}
              {days.length > 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 1.0, delay: 1.4, ease }}
                  style={{
                    display: 'flex', flexWrap: 'wrap', gap: 8,
                    justifyContent: 'center', marginBottom: 40,
                    maxWidth: 680, marginLeft: 'auto', marginRight: 'auto',
                  }}
                >
                  {days.slice(0, 12).map(d => (
                    <span key={d.day_number} style={{
                      padding: '8px 14px', borderRadius: 999,
                      background: 'rgba(212,182,134,0.08)',
                      border: `1px solid ${HAIRLINE}`,
                      fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                      letterSpacing: '0.10em', color: `${BONE}d8`,
                      maxWidth: 320, overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      Day {d.day_number}{d.theme ? ` · ${d.theme}` : ''}
                    </span>
                  ))}
                </motion.div>
              )}

              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6, delay: 1.9, ease }}
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
