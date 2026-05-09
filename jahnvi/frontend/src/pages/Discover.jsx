import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, MapPin } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'

const PINK   = '#EC4899'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

function useCountUp(target, duration = 600, delay = 200) {
  const [count, setCount] = useState(0)
  useEffect(() => {
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

const ALL_MATCHES = [
  { id: '1', display_name: 'Priya Mehta',   location: 'Mumbai, India',    match_score: 92, tags: ['Relaxed', 'Culture', 'Foodie'],   pace: 'slow',     avatar_url: 'https://i.pravatar.cc/80?img=47' },
  { id: '2', display_name: 'Arjun Nair',    location: 'Bangalore, India', match_score: 87, tags: ['Adventure', 'Foodie'],             pace: 'moderate', avatar_url: 'https://i.pravatar.cc/80?img=12' },
  { id: '3', display_name: 'Zara Khan',     location: 'Delhi, India',     match_score: 84, tags: ['Culture', 'History'],              pace: 'moderate', avatar_url: 'https://i.pravatar.cc/80?img=25' },
  { id: '4', display_name: 'Meera Sharma',  location: 'Pune, India',      match_score: 79, tags: ['Wellness', 'Nature', 'Relaxed'],   pace: 'slow',     avatar_url: 'https://i.pravatar.cc/80?img=31' },
  { id: '5', display_name: 'Rohan Verma',   location: 'Chennai, India',   match_score: 76, tags: ['Adventure', 'Nature'],             pace: 'fast',     avatar_url: 'https://i.pravatar.cc/80?img=18' },
  { id: '6', display_name: 'Kavita Iyer',   location: 'Hyderabad, India', match_score: 73, tags: ['Foodie', 'Nightlife'],             pace: 'fast',     avatar_url: 'https://i.pravatar.cc/80?img=44' },
]

const STYLE_TAGS   = ['Adventure', 'Culture', 'Relaxed', 'Foodie', 'Nature', 'Wellness', 'Nightlife', 'History']
const PACE_OPTIONS = [
  { key: 'all',      label: 'Any pace'  },
  { key: 'slow',     label: 'Slow'      },
  { key: 'moderate', label: 'Moderate'  },
  { key: 'fast',     label: 'Fast'      },
]
const SCORE_OPTIONS = [
  { key: 'all', label: 'All',  min: 0  },
  { key: '70+', label: '70%+', min: 70 },
  { key: '80+', label: '80%+', min: 80 },
  { key: '90+', label: '90%+', min: 90 },
]

const stagger    = { show: { transition: { staggerChildren: 0.07 } } }
const cardReveal = { hidden: { opacity: 0, y: 20, scale: 0.97 }, show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.45, ease } } }

function MiniRing({ score, size = 52 }) {
  const r = (size / 2) - 5
  const circ = 2 * Math.PI * r
  const [offset, setOffset] = useState(circ)
  useEffect(() => {
    const t = setTimeout(() => setOffset(circ - (score / 100) * circ), 600)
    return () => clearTimeout(t)
  }, [score, circ])
  const uid = `ring-${score}-${size}`
  return (
    <svg width={size} height={size} style={{ display: 'block', flexShrink: 0 }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={HAIRLINE} strokeWidth="2"/>
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={`url(#${uid})`} strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray={circ} strokeDashoffset={offset}
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: 'stroke-dashoffset 1.1s cubic-bezier(0.34,1.56,0.64,1)' }}
      />
      <defs>
        <linearGradient id={uid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={PINK}/>
          <stop offset="100%" stopColor="#D4B686"/>
        </linearGradient>
      </defs>
      <text x={size/2} y={size/2 + 5} textAnchor="middle" fontFamily='"Cormorant Garamond",serif' fontSize="13" fill={BONE} fontStyle="italic">{score}</text>
    </svg>
  )
}

function MatchCard({ match, onClick }) {
  return (
    <motion.div
      variants={cardReveal}
      whileHover={{ y: -6, boxShadow: `0 24px 64px rgba(0,0,0,0.55), 0 0 0 1px ${PINK}22`, transition: spring }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      style={{ padding: 1, borderRadius: 20, background: 'linear-gradient(145deg,rgba(232,212,168,0.12) 0%,rgba(8,8,7,0) 50%,rgba(232,212,168,0.06) 100%)', cursor: 'pointer', boxShadow: '0 8px 32px rgba(0,0,0,0.40)' }}
    >
      <div style={{ background: 'linear-gradient(160deg,rgba(20,16,10,0.99) 0%,rgba(12,10,7,1) 100%)', borderRadius: 19, padding: '24px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: -60, right: -60, width: 200, height: 200, borderRadius: '50%', background: `radial-gradient(ellipse, ${PINK}0D 0%, transparent 70%)`, pointerEvents: 'none' }}/>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 18 }}>
          <motion.div
            animate={{ boxShadow: [`0 0 0 2px ${PINK}22, 0 0 16px ${PINK}0D`, `0 0 0 2px ${PINK}55, 0 0 32px ${PINK}22`, `0 0 0 2px ${PINK}22, 0 0 16px ${PINK}0D`] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            style={{ width: 52, height: 52, borderRadius: '50%', overflow: 'hidden', flexShrink: 0 }}
          >
            <img src={match.avatar_url} alt={match.display_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
          </motion.div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 22, color: BONE, lineHeight: 1, marginBottom: 5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{match.display_name}</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <MapPin size={9} style={{ color: GOLD, flexShrink: 0 }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{match.location}</span>
            </div>
          </div>
          <MiniRing score={match.match_score}/>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {match.tags.map((tag, i) => {
            const colors = [PINK, '#14B8A6', '#F59E0B']
            const c = colors[i % colors.length]
            return (
              <span key={tag} style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.14em', textTransform: 'uppercase', color: c, padding: '4px 10px', borderRadius: 12, border: `1px solid ${c}33`, background: `${c}0D` }}>{tag}</span>
            )
          })}
        </div>
      </div>
    </motion.div>
  )
}

export default function Discover() {
  const navigate = useNavigate()
  const [selectedStyles, setStyles] = useState([])
  const [pace, setPace]             = useState('all')
  const [scoreKey, setScore]        = useState('all')

  const scoreMin = SCORE_OPTIONS.find(o => o.key === scoreKey)?.min ?? 0

  const filtered = ALL_MATCHES.filter(m => {
    if (selectedStyles.length > 0 && !selectedStyles.some(s => m.tags.includes(s))) return false
    if (pace !== 'all' && m.pace !== pace) return false
    if (m.match_score < scoreMin) return false
    return true
  })

  const countDisp = useCountUp(filtered.length, 600, 200)
  const toggleStyle = s => setStyles(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])
  const hasFilters = selectedStyles.length > 0 || pace !== 'all' || scoreKey !== 'all'

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent="#EC4899" />

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
        <div style={{ width: 80 }}/>
      </nav>

      {/* 2-column body */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '280px 1fr', maxWidth: 1240, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>

        {/* LEFT — filters */}
        <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '52px 40px', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 320, background: `radial-gradient(ellipse 90% 65% at 30% 20%, ${PINK}14 0%, transparent 65%)`, pointerEvents: 'none' }}/>

          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Discover</p>
          <motion.h1
            animate={{ filter: [`drop-shadow(0 0 14px ${PINK}22)`, `drop-shadow(0 0 40px ${PINK}55)`, `drop-shadow(0 0 14px ${PINK}22)`] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
            style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 40, color: BONE, lineHeight: 1.05, marginBottom: 10, letterSpacing: '-0.02em' }}
          >
            Find your<br/>companion
          </motion.h1>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, lineHeight: 1.75, color: MUTE, marginBottom: 36 }}>
            Matched to your travel style.
          </p>

          <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, ${PINK}33, ${HAIRLINE})`, marginBottom: 28 }}/>

          {/* style filters */}
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>Travel style</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 28 }}>
            {STYLE_TAGS.map(s => {
              const active = selectedStyles.includes(s)
              return (
                <motion.button
                  key={s}
                  whileHover={{ scale: 1.06, transition: { duration: 0.14 } }}
                  whileTap={{ scale: 0.94 }}
                  onClick={() => toggleStyle(s)}
                  style={{ padding: '7px 13px', borderRadius: 20, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.06em', background: active ? `${PINK}18` : 'transparent', border: `1px solid ${active ? `${PINK}66` : HAIRLINE}`, color: active ? PINK : MUTE, transition: 'all 0.18s', boxShadow: active ? `0 0 16px ${PINK}22` : 'none' }}
                >
                  {s}
                </motion.button>
              )
            })}
          </div>

          {/* pace filter */}
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, marginBottom: 10 }}>Pace</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 28 }}>
            {PACE_OPTIONS.map(p => {
              const active = pace === p.key
              return (
                <motion.button
                  key={p.key}
                  whileHover={{ x: 4, transition: { duration: 0.15 } }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => setPace(p.key)}
                  style={{ padding: '10px 14px', borderRadius: 10, cursor: 'pointer', textAlign: 'left', background: active ? `${PINK}12` : 'transparent', border: `1px solid ${active ? `${PINK}44` : 'transparent'}`, fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: active ? BONE : MUTE, transition: 'all 0.18s', boxShadow: active ? `0 0 20px ${PINK}1A` : 'none' }}
                >
                  {p.label}
                </motion.button>
              )
            })}
          </div>

          {/* score filter */}
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>Min. match score</p>
          <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
            {SCORE_OPTIONS.map(o => {
              const active = scoreKey === o.key
              return (
                <motion.button
                  key={o.key}
                  whileHover={{ scale: 1.06, transition: { duration: 0.14 } }}
                  whileTap={{ scale: 0.93 }}
                  onClick={() => setScore(o.key)}
                  style={{ padding: '7px 13px', borderRadius: 20, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.08em', background: active ? `${PINK}18` : 'transparent', border: `1px solid ${active ? `${PINK}55` : HAIRLINE}`, color: active ? PINK : MUTE, transition: 'all 0.18s', boxShadow: active ? `0 0 14px ${PINK}22` : 'none' }}
                >
                  {o.label}
                </motion.button>
              )
            })}
          </div>

          {/* ghost count */}
          <div style={{ marginTop: 'auto', paddingTop: 24 }}>
            <motion.span
              animate={{ filter: [`drop-shadow(0 0 16px ${PINK}22)`, `drop-shadow(0 0 48px ${PINK}55)`, `drop-shadow(0 0 16px ${PINK}22)`] }}
              transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
              style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 140, lineHeight: 0.85, letterSpacing: '-0.04em', color: PINK, opacity: 0.12, userSelect: 'none', display: 'block' }}
            >
              {countDisp}
            </motion.span>
          </div>
        </div>

        {/* RIGHT — match grid */}
        <div style={{ padding: '52px 52px', overflowY: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 36 }}>
            <div>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>Potential companions</p>
              <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 36, color: BONE, lineHeight: 1 }}>
                {filtered.length} match{filtered.length !== 1 ? 'es' : ''} found
              </h2>
            </div>
            <AnimatePresence>
              {hasFilters && (
                <motion.button
                  initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 8 }}
                  whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }}
                  onClick={() => { setStyles([]); setPace('all'); setScore('all') }}
                  style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: PINK, background: 'none', border: 'none', cursor: 'pointer', opacity: 0.8 }}
                >
                  Clear filters
                </motion.button>
              )}
            </AnimatePresence>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={`${selectedStyles.join()}-${pace}-${scoreKey}`}
              variants={stagger} initial="hidden" animate="show"
              style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}
            >
              {filtered.map(m => (
                <MatchCard key={m.id} match={m} onClick={() => navigate(`/match/${m.id}`)}/>
              ))}
            </motion.div>
          </AnimatePresence>

          {filtered.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ textAlign: 'center', paddingTop: 80 }}>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 32, color: MUTE }}>No matches yet.</p>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: DIM, marginTop: 10 }}>Try broadening your filters.</p>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}
