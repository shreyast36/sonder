import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, MapPin, Loader2, Sparkles, MessageCircle, RefreshCw } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import SynthBadge from '../components/SynthBadge'
import { useAuth } from '../hooks/useAuth'
import {
  getCurrentItinerary, getCotravellers, regenerateCotravellers,
} from '../lib/api'

const VIOLET = '#8B5CF6'
const ROSE   = '#F43F5E'
const GREEN  = '#10B981'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

// ── Helpers ───────────────────────────────────────────────────────────────

function useCountUp(target, duration = 600, delay = 200) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    if (!Number.isFinite(target)) return
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

function ScoreRing({ score, size = 88 }) {
  const r = (size / 2) - 7
  const circ = 2 * Math.PI * r
  const [offset, setOffset] = useState(circ)
  useEffect(() => {
    const t = setTimeout(() => setOffset(circ - (score / 100) * circ), 350)
    return () => clearTimeout(t)
  }, [score, circ])
  const uid = `ring-${score}-${size}-${Math.random().toString(36).slice(2, 6)}`
  return (
    <svg width={size} height={size} style={{ display: 'block', flexShrink: 0 }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={HAIRLINE} strokeWidth="2.5"/>
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={`url(#${uid})`} strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray={circ} strokeDashoffset={offset}
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: 'stroke-dashoffset 1.1s cubic-bezier(0.34,1.56,0.64,1)' }}
      />
      <defs>
        <linearGradient id={uid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={VIOLET}/>
          <stop offset="100%" stopColor="#D4B686"/>
        </linearGradient>
      </defs>
      <text x={size/2} y={size/2 + 4}
            textAnchor="middle" fontFamily='"Cormorant Garamond",serif'
            fontStyle="italic" fontSize={size * 0.32} fill={BONE}>
        {score}
      </text>
      <text x={size/2} y={size/2 + (size * 0.22)}
            textAnchor="middle" fontFamily='"Inter Tight",sans-serif'
            fontSize={size * 0.08} fill={`${VIOLET}AA`}
            letterSpacing="0.2em" textTransform="uppercase">
        % MATCH
      </text>
    </svg>
  )
}

// ── Match card (rich detail) ─────────────────────────────────────────────

function RichMatchCard({ match, onClick, index }) {
  const p = match?.profile || {}
  const score = Math.round((Number(match?.match_score) || 0) * 100)
  const reasons = (match?.match_reasons || []).slice(0, 3)
  const interests = (p.interests || []).slice(0, 5)
  const isSeed = !!p.is_seed

  return (
    <motion.div
      initial={{ opacity: 0, y: 24, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.55, delay: 0.15 + index * 0.1, ease }}
      whileHover={{ y: -4, boxShadow: `0 32px 80px rgba(0,0,0,0.55), 0 0 0 1px ${VIOLET}33` }}
      onClick={onClick}
      style={{
        cursor: 'pointer',
        padding: 1,
        borderRadius: 22,
        background: 'linear-gradient(145deg,rgba(232,212,168,0.14) 0%,rgba(8,8,7,0) 45%,rgba(212,182,134,0.08) 100%)',
        boxShadow: '0 12px 40px rgba(0,0,0,0.45)',
      }}
    >
      <div style={{
        background: 'linear-gradient(160deg,rgba(20,16,10,0.99) 0%,rgba(12,10,7,1) 100%)',
        borderRadius: 21, padding: '32px 36px',
        position: 'relative', overflow: 'hidden',
        display: 'grid', gridTemplateColumns: '120px 1fr 130px', gap: 32, alignItems: 'center',
      }}>
        {/* radial wash */}
        <div style={{
          position: 'absolute', top: -80, right: -80, width: 280, height: 280,
          borderRadius: '50%',
          background: `radial-gradient(ellipse, ${VIOLET}14 0%, transparent 70%)`,
          pointerEvents: 'none',
        }}/>

        {/* avatar */}
        <motion.div
          animate={{
            boxShadow: [
              `0 0 0 2px ${VIOLET}33, 0 0 28px ${VIOLET}14`,
              `0 0 0 2px ${VIOLET}66, 0 0 56px ${VIOLET}33`,
              `0 0 0 2px ${VIOLET}33, 0 0 28px ${VIOLET}14`,
            ],
          }}
          transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            width: 116, height: 116, borderRadius: '50%', overflow: 'hidden',
            background: 'rgba(212,182,134,0.06)', flexShrink: 0,
          }}
        >
          {p.avatar_url ? (
            <img src={p.avatar_url} alt={p.display_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
          ) : (
            <div style={{
              width: '100%', height: '100%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: '"Cormorant Garamond",serif', fontSize: 36, color: GOLD,
            }}>
              {(p.display_name || '?').split(/\s+/).slice(0, 2).map(s => s[0]?.toUpperCase()).join('')}
            </div>
          )}
        </motion.div>

        {/* middle block — name + meta + reasons + interests */}
        <div style={{ minWidth: 0, position: 'relative' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap', marginBottom: 6 }}>
            <h2 style={{
              fontFamily: '"Cormorant Garamond",serif', fontWeight: 400,
              fontSize: 32, color: BONE, lineHeight: 1, margin: 0,
            }}>{p.display_name || '—'}</h2>
            {isSeed && <SynthBadge isSeed variant="inline"/>}
          </div>
          {p.archetype && (
            <p style={{
              fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
              fontSize: 14, color: MUTE, margin: '0 0 10px',
            }}>{p.archetype}</p>
          )}
          {p.location && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 14 }}>
              <MapPin size={10} style={{ color: GOLD }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>{p.location}</span>
            </div>
          )}

          {reasons.length > 0 && (
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 14px', display: 'flex', flexDirection: 'column', gap: 5 }}>
              {reasons.map((r, i) => (
                <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <span style={{ width: 4, height: 4, borderRadius: '50%', background: VIOLET, marginTop: 7, flexShrink: 0 }}/>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: BONE, lineHeight: 1.5 }}>{r}</span>
                </li>
              ))}
            </ul>
          )}

          {interests.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {interests.map((tag, i) => {
                const palette = [VIOLET, '#14B8A6', '#F59E0B', '#E07060', GOLD]
                const c = palette[i % palette.length]
                return (
                  <span key={tag} style={{
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 8,
                    letterSpacing: '0.18em', textTransform: 'uppercase', color: c,
                    padding: '4px 10px', borderRadius: 12,
                    border: `1px solid ${c}33`, background: `${c}0D`,
                  }}>{tag}</span>
                )
              })}
            </div>
          )}
        </div>

        {/* right — score ring + CTA hint */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, position: 'relative' }}>
          <ScoreRing score={score}/>
          <span style={{
            fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
            letterSpacing: '0.2em', textTransform: 'uppercase', color: VIOLET,
            display: 'flex', alignItems: 'center', gap: 5,
          }}>
            <MessageCircle size={10}/> Open profile
          </span>
        </div>
      </div>
    </motion.div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function Discover() {
  const navigate    = useNavigate()
  const { user }    = useAuth()
  const [itinerary, setItinerary] = useState(null)
  const [matches, setMatches]     = useState([])
  const [activePair, setActivePair] = useState(null)
  const [loading, setLoading]     = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError]         = useState(null)

  // Hydrate current itinerary + matches.
  useEffect(() => {
    if (!user) return
    let cancelled = false
    setLoading(true); setError(null)
    ;(async () => {
      try {
        const itin = await getCurrentItinerary().catch(() => null)
        if (cancelled) return
        setItinerary(itin || null)
        const itinId = itin?.itinerary_id || null
        const res = await getCotravellers(itinId)
        if (cancelled) return
        if (!Array.isArray(res) && res?.active_pair) {
          // Already paired for this trip — bounce to the shared surface.
          navigate(`/shared/${encodeURIComponent(res.active_pair.itinerary_id)}`, { replace: true })
          return
        }
        const arr = Array.isArray(res) ? res : (res?.matches || [])
        setMatches(arr)
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Could not load companions')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [user?.uid, navigate])

  const destinationLabel = useMemo(() => {
    const dest = itinerary?.destination
    if (!dest) return null
    const city = dest.city || ''
    const country = dest.country || ''
    if (city && country) return `${city}, ${country}`
    return city || country || null
  }, [itinerary])

  const scoreDisp = useCountUp(matches.length, 700, 250)

  async function regenerate() {
    setRefreshing(true); setError(null)
    try {
      const excluded = matches.map(m => m?.profile?.profile_id).filter(Boolean)
      const fresh = await regenerateCotravellers(excluded, '')
      const arr = Array.isArray(fresh) ? fresh : (fresh?.matches || [])
      setMatches(arr)
    } catch (e) {
      setError(e?.message || 'Could not refresh')
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent={VIOLET}/>

      {/* nav */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 50,
        borderBottom: `1px solid ${HAIRLINE}`,
        background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)',
        padding: '0 48px', height: 68,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/dashboard')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE,
                   display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Dashboard</span>
        </motion.button>
        <SonderNav3D markSize={32}/>
        <div style={{ width: 80 }}/>
      </nav>

      <div style={{ maxWidth: 1040, margin: '0 auto', width: '100%', padding: '52px 48px 80px' }}>

        {/* hero */}
        <motion.div
          initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.65, ease }}
          style={{ marginBottom: 48 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <Sparkles size={11} style={{ color: VIOLET }}/>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
              Curated companions
            </p>
          </div>
          <motion.h1
            animate={{ filter: [`drop-shadow(0 0 14px ${VIOLET}22)`, `drop-shadow(0 0 36px ${VIOLET}55)`, `drop-shadow(0 0 14px ${VIOLET}22)`] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
            style={{
              fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
              fontSize: 56, color: BONE, lineHeight: 1.05, margin: '0 0 16px',
              letterSpacing: '-0.02em',
            }}
          >
            Travellers whose<br/>rhythm fits yours.
          </motion.h1>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, color: MUTE, margin: 0, maxWidth: 540, lineHeight: 1.7 }}>
            {destinationLabel
              ? <>Three matches picked for your <span style={{ color: BONE }}>{destinationLabel}</span> trip. Open one to vibe-check before deciding.</>
              : <>Plan a trip first and we'll line up three companions whose rhythm fits yours.</>}
          </p>

          {!loading && matches.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 28 }}>
              <span style={{
                fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
                fontSize: 28, color: BONE,
              }}>
                {scoreDisp} {scoreDisp === 1 ? 'match' : 'matches'} ready
              </span>
              <motion.button
                whileHover={!refreshing ? { scale: 1.05 } : {}}
                whileTap={!refreshing ? { scale: 0.96 } : {}}
                onClick={regenerate}
                disabled={refreshing}
                style={{
                  background: 'transparent', border: `1px solid ${VIOLET}55`, borderRadius: 18,
                  padding: '7px 14px', color: VIOLET,
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                  letterSpacing: '0.18em', textTransform: 'uppercase',
                  cursor: refreshing ? 'wait' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: 6,
                  opacity: refreshing ? 0.6 : 1,
                }}
              >
                {refreshing
                  ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, ease: 'linear', repeat: Infinity }}><Loader2 size={11}/></motion.span>
                  : <RefreshCw size={11}/>}
                Fresh batch
              </motion.button>
            </div>
          )}
        </motion.div>

        {/* states */}
        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: '80px 0' }}>
            <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.3, ease: 'linear', repeat: Infinity }}>
              <Loader2 size={20} style={{ color: VIOLET }}/>
            </motion.span>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE }}>
              Finding companions…
            </p>
          </motion.div>
        )}

        {error && !loading && (
          <div style={{ padding: '40px 32px', borderRadius: 14, border: '1px solid rgba(248,113,113,0.35)', background: 'rgba(248,113,113,0.04)', textAlign: 'center' }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, color: '#F87171', margin: 0 }}>{error}</p>
          </div>
        )}

        {!loading && !error && matches.length === 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ textAlign: 'center', padding: '80px 0' }}>
            <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 32, color: MUTE, margin: 0 }}>
              {destinationLabel ? 'No matches yet.' : 'Plan a trip to see companions.'}
            </p>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: DIM, marginTop: 10 }}>
              {destinationLabel
                ? "We'll surface fresher options once you've sat with the matching for a beat."
                : 'Once your itinerary is set we line up three companions automatically.'}
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.96 }}
              onClick={() => navigate(destinationLabel ? '/dashboard' : '/preferences')}
              style={{
                marginTop: 22, padding: '11px 22px', borderRadius: 18,
                background: `linear-gradient(135deg, ${VIOLET} 0%, #6D28D9 100%)`,
                border: 'none', color: '#fff', cursor: 'pointer',
                fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500,
              }}
            >
              {destinationLabel ? 'Back to dashboard' : 'Plan a trip'}
            </motion.button>
          </motion.div>
        )}

        {/* cards */}
        <AnimatePresence>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {matches.map((m, i) => (
              <RichMatchCard
                key={m?.profile?.profile_id || i}
                match={m}
                index={i}
                onClick={() => {
                  const pid = m?.profile?.profile_id
                  if (pid) navigate(`/match/${encodeURIComponent(pid)}`)
                }}
              />
            ))}
          </div>
        </AnimatePresence>
      </div>
    </div>
  )
}
