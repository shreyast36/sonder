import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, MapPin, Check, MessageCircle } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import { useAuth } from '../hooks/useAuth'
import { getCurrentItinerary, getCotravellerProfile, startChat } from '../lib/api'
import SynthBadge from '../components/SynthBadge'

// vivid violet — accent for the match-detail screen
const VIOLET = '#8B5CF6'

// ── Helpers ────────────────────────────────────────────────────────────────

const DIM_LABEL = {
  // PULL
  nature_outdoors:   'Nature',
  culture_history:   'Culture',
  food_drink:        'Food',
  nightlife_social:  'Nightlife',
  comfort_luxury:    'Luxury',
  exploration_local: 'Explore',
  // PUSH
  escape_reset:      'Reset',
  adventure_novelty: 'Adventure',
  connection:        'Connection',
  reflection:        'Reflection',
  curiosity:         'Curious',
  prestige_reward:   'Milestone',
}
const PACE_LABEL   = { relaxed: 'Relaxed', moderate: 'Moderate', packed: 'Packed' }
const BUDGET_LABEL = { budget: 'Budget', mid_range: 'Mid-range', luxury: 'Luxury' }
const STYLE_LABEL  = { solo: 'Solo', couple: 'Couple', family: 'Family', friends: 'Friends' }

function _initialsFromName(name) {
  return (name || '').split(/\s+/).map(w => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase()
}

function useCountUp(target, duration = 1000, delay = 400) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    if (target == null) return
    const timer = setTimeout(() => {
      const start = performance.now()
      const tick = now => {
        const p = Math.min((now - start) / duration, 1)
        const e = 1 - Math.pow(1 - p, 3)
        setCount(Math.round(e * target))
        if (p < 1) requestAnimationFrame(tick)
      }
      requestAnimationFrame(tick)
    }, delay)
    return () => clearTimeout(timer)
  }, [target, duration, delay])
  return count
}

function ScoreRing({ score, size = 180 }) {
  const r = (size / 2) - 14
  const circumference = 2 * Math.PI * r
  const [offset, setOffset] = useState(circumference)
  useEffect(() => {
    const timer = setTimeout(() => {
      setOffset(circumference - Math.max(0, Math.min(100, score)) / 100 * circumference)
    }, 350)
    return () => clearTimeout(timer)
  }, [score, circumference])
  return (
    <svg width={size} height={size} style={{ display: 'block' }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={HAIRLINE} strokeWidth="3"/>
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke="url(#violet-gold)" strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: 'stroke-dashoffset 1.1s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
      />
      <defs>
        <linearGradient id="violet-gold" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={VIOLET}/>
          <stop offset="100%" stopColor="#D4B686"/>
        </linearGradient>
      </defs>
    </svg>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────

const spring = { type: 'spring', stiffness: 280, damping: 22 }
const stagger = { show: { transition: { staggerChildren: 0.09 } } }
const reveal  = { hidden: { opacity: 0, y: 24 }, show: { opacity: 1, y: 0, transition: { duration: 0.65, ease } } }

export default function MatchDetail() {
  const navigate = useNavigate()
  const { id }    = useParams()
  const { user, loading: authLoading } = useAuth()

  const [data, setData]       = useState(null)   // {profile, match_score, match_reasons, compatibility_breakdown}
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [currentItineraryId, setCurrentItineraryId] = useState(null)
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState(null)

  // Pull whatever current itinerary so the matching call has trip context
  // (companion prefs are scoped per-trip).
  useEffect(() => {
    if (authLoading) return
    if (!user)        { navigate('/signin');   return }
    if (!id)          { navigate('/dashboard'); return }
    let cancelled = false
    ;(async () => {
      try {
        let itineraryId = null
        try {
          const cur = await getCurrentItinerary()
          itineraryId = cur?.itinerary?.itinerary_id || null
        } catch { /* no current trip — that's fine */ }
        const res = await getCotravellerProfile(id, itineraryId)
        if (cancelled) return
        setData(res)
        setCurrentItineraryId(itineraryId)
      } catch (err) {
        if (cancelled) return
        setError(err?.message || 'Could not load this profile')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [authLoading, user?.uid, id, navigate])

  const profile = data?.profile
  const score100 = Math.round((Number(data?.match_score) || 0) * 100)
  const scoreDisp = useCountUp(loading ? null : score100, 1000, 400)

  const tags = useMemo(() => {
    if (!profile) return []
    const dim = (profile.interests || []).map(d => DIM_LABEL[d]).filter(Boolean)
    return [
      ...dim,
      PACE_LABEL[profile.pace],
      BUDGET_LABEL[profile.budget_style],
      STYLE_LABEL[profile.travel_style],
    ].filter(Boolean)
  }, [profile])

  const breakdownItems = useMemo(() => {
    const b = data?.compatibility_breakdown || {}
    return [
      { key: 'interests',    label: 'Shared interests', score: b.interests },
      { key: 'pace',         label: 'Travel pace',      score: b.pace },
      { key: 'travel_style', label: 'Travel style',     score: b.travel_style },
      { key: 'budget',       label: 'Budget range',     score: b.budget },
    ].filter(x => typeof x.score === 'number')
  }, [data])

  // ── Render states ────────────────────────────────────────────────────────

  if (loading) {
    return (
      <PageShell onBack={() => navigate(-1)}>
        <p style={{ textAlign: 'center', marginTop: 80, fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: `${VIOLET}cc` }}>
          Reading their profile…
        </p>
      </PageShell>
    )
  }
  if (error || !profile) {
    return (
      <PageShell onBack={() => navigate(-1)}>
        <div style={{ textAlign: 'center', marginTop: 80 }}>
          <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 28, color: BONE, marginBottom: 14 }}>Something didn't load.</p>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>{error || 'Profile unavailable.'}</p>
        </div>
      </PageShell>
    )
  }

  // ── Real profile ─────────────────────────────────────────────────────────

  return (
    <PageShell onBack={() => navigate(-1)}>
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>

        {/* LEFT — profile */}
        <motion.div
          initial={{ opacity: 0, x: -28 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, ease }}
          style={{ padding: '60px 52px', borderRight: `1px solid ${HAIRLINE}`, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}
        >
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 450, background: `radial-gradient(ellipse 90% 60% at 35% 18%, ${VIOLET}1A 0%, transparent 65%)`, pointerEvents: 'none' }}/>

          {/* Avatar */}
          <div style={{ marginBottom: 24, position: 'relative', display: 'inline-block' }}>
            <motion.div
              animate={{ boxShadow: [`0 0 0 2px ${VIOLET}33, 0 0 32px ${VIOLET}18`, `0 0 0 2px ${VIOLET}77, 0 0 64px ${VIOLET}38`, `0 0 0 2px ${VIOLET}33, 0 0 32px ${VIOLET}18`] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
              style={{ width: 148, height: 148, borderRadius: '50%', overflow: 'hidden', background: 'rgba(232,212,168,0.05)' }}
            >
              {profile.avatar_url ? (
                <img src={profile.avatar_url} alt={profile.display_name} referrerPolicy="no-referrer"
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}/>
              ) : (
                <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 56, color: GOLD }}>
                  {_initialsFromName(profile.display_name)}
                </div>
              )}
            </motion.div>
          </div>

          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 48, color: BONE, lineHeight: 1, marginBottom: 8, letterSpacing: '-0.01em' }}>
            {profile.display_name}
            <span style={{ marginLeft: 12, fontSize: 22, color: MUTE, fontStyle: 'italic' }}>· {profile.age}</span>
          </h1>
          {profile.location && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 14 }}>
              <MapPin size={11} style={{ color: GOLD }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>{profile.location}</span>
            </div>
          )}
          {profile.archetype && (
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.28em', textTransform: 'uppercase', color: VIOLET, marginBottom: 14 }}>
              {profile.archetype}
            </p>
          )}
          {profile.is_seed && (
            <div style={{ marginBottom: 22 }}>
              <SynthBadge isSeed={true} variant="default" />
            </div>
          )}

          {/* Tags */}
          {tags.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 'auto' }}>
              {tags.map((tag, i) => {
                const colors = [VIOLET, '#14B8A6', '#F59E0B', '#E07060', GOLD]
                const c = colors[i % colors.length]
                return (
                  <motion.span
                    key={`${tag}-${i}`}
                    whileHover={{ y: -2, transition: spring }}
                    style={{
                      fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase',
                      color: c, fontFamily: '"Inter Tight",sans-serif',
                      padding: '6px 12px', borderRadius: 20,
                      border: `1px solid ${c}44`, background: `${c}12`,
                    }}
                  >
                    {tag}
                  </motion.span>
                )
              })}
            </div>
          )}

          {/* CTAs */}
          <div style={{ marginTop: 44, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <motion.button
              whileHover={!starting ? { y: -2, boxShadow: `0 12px 32px ${VIOLET}55` } : {}}
              whileTap={!starting ? { scale: 0.98 } : {}}
              disabled={starting}
              onClick={async () => {
                if (starting) return
                setStarting(true)
                setStartError(null)
                try {
                  const { session } = await startChat(profile.profile_id, currentItineraryId || '')
                  navigate(`/chat/${session.session_id}`)
                } catch (e) {
                  setStartError(e?.message || 'Could not start the chat')
                  setStarting(false)
                }
              }}
              style={{ width: '100%', padding: '17px 0',
                background: `linear-gradient(135deg, ${VIOLET} 0%, #6D28D9 100%)`,
                border: 'none', borderRadius: 12, cursor: starting ? 'wait' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
                textTransform: 'uppercase', fontWeight: 500, color: '#fff',
                boxShadow: `0 6px 24px ${VIOLET}44`,
                opacity: starting ? 0.7 : 1 }}
            >
              <MessageCircle size={13}/>
              {starting ? 'Opening chat…' : `Start chat with ${profile.display_name.split(' ')[0]}`}
            </motion.button>
            {startError && (
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: '#F87171', textAlign: 'center', margin: 0 }}>
                {startError}
              </p>
            )}
          </div>
        </motion.div>

        {/* RIGHT — score + compatibility */}
        <motion.div
          variants={stagger} initial="hidden" animate="show"
          style={{ padding: '60px 52px', display: 'flex', flexDirection: 'column' }}
        >
          {/* Score hero */}
          <motion.div variants={reveal} style={{ marginBottom: 44, display: 'flex', alignItems: 'center', gap: 32 }}>
            <div style={{ position: 'relative', flexShrink: 0 }}>
              <ScoreRing score={score100} size={170}/>
              <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <motion.span
                  animate={{ filter: [`drop-shadow(0 0 12px ${VIOLET}88)`, `drop-shadow(0 0 32px ${VIOLET}cc)`, `drop-shadow(0 0 12px ${VIOLET}88)`] }}
                  transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 64, lineHeight: 1, color: BONE, letterSpacing: '-0.04em' }}
                >
                  {scoreDisp}
                </motion.span>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.20em', textTransform: 'uppercase', color: `${VIOLET}BB`, marginTop: 2 }}>% match</span>
              </div>
            </div>
            <div>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>Compatibility</p>
              <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 30, color: BONE, lineHeight: 1.1 }}>
                {score100 >= 85 ? 'Nearly perfect.' : score100 >= 65 ? 'Strong fit.' : score100 >= 45 ? 'Worth exploring.' : 'Different rhythms.'}
              </h2>
            </div>
          </motion.div>

          <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, ${VIOLET}44, ${HAIRLINE})`, marginBottom: 36 }}/>

          {/* Match reasons */}
          {Array.isArray(data?.match_reasons) && data.match_reasons.length > 0 && (
            <motion.div variants={reveal} style={{ marginBottom: 44 }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 24 }}>Why you match</p>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {data.match_reasons.map((reason, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -16 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.4, delay: i * 0.07, ease }}
                    style={{ display: 'flex', alignItems: 'flex-start', gap: 14, padding: '13px 0', borderBottom: `1px solid ${HAIRLINE}` }}
                  >
                    <div style={{ width: 22, height: 22, borderRadius: '50%', border: `1px solid ${VIOLET}44`, background: `${VIOLET}12`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                      <Check size={9} style={{ color: VIOLET }}/>
                    </div>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, lineHeight: 1.6, color: BONE, margin: 0 }}>{reason}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Breakdown bars */}
          {breakdownItems.length > 0 && (
            <motion.div variants={reveal}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 18 }}>Breakdown</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {breakdownItems.map(({ key, label, score }) => {
                  const pct = Math.round(score * 100)
                  return (
                    <div key={key}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: BONE, letterSpacing: '0.04em' }}>{label}</span>
                        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>{pct}%</span>
                      </div>
                      <div style={{ position: 'relative', height: 4, background: 'rgba(232,212,168,0.06)', borderRadius: 2, overflow: 'hidden' }}>
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.9, delay: 0.2, ease }}
                          style={{ position: 'absolute', inset: 0, background: `linear-gradient(90deg, ${VIOLET} 0%, ${GOLD} 100%)`, borderRadius: 2 }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          )}
        </motion.div>
      </div>
    </PageShell>
  )
}

// ── Page chrome ────────────────────────────────────────────────────────────

function PageShell({ children, onBack }) {
  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      {/* gentle ambient — keeps the page from feeling flat without the
          violet-everywhere AppBackground from the old mock version */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, background: `radial-gradient(ellipse 85% 70% at 50% 25%, ${VIOLET}14 0%, transparent 65%)` }}/>

      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', padding: '0 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={onBack}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <ArrowLeft size={16}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </motion.button>
        <SonderNav3D markSize={28}/>
        <div style={{ width: 80 }}/>
      </nav>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', zIndex: 1 }}>
        {children}
      </div>
    </div>
  )
}
