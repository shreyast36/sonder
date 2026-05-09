import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, MapPin, Check, MessageCircle } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'

// vivid violet — MatchDetail accent
const VIOLET = '#8B5CF6'

function useCountUp(target, duration = 1000, delay = 400) {
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

const MOCK_MATCH = {
  id: '1',
  display_name: 'Priya Mehta',
  avatar_url: 'https://i.pravatar.cc/400?img=47',
  location: 'Mumbai, India',
  bio: "Slow traveller. Museum crawler. Eats where there's no menu in English.",
  match_score: 92,
  tags: ['Relaxed Pace', 'Mid-range', 'Culture', 'Foodie'],
  compatibility: [
    'Both prefer relaxed pace over packed schedules',
    'Matching budget range — avoids over-splurging',
    'Culture and food rank highest for both of you',
    'Neither likes group tours or all-inclusives',
    'Same ideal trip length: 6–10 days',
  ],
  topics: [
    "Which museum in Bali are you most excited about?",
    "Are you more of a sunrise or a sunset person?",
    "Do you plan everything, or leave room to wander?",
  ],
}

const spring = { type: 'spring', stiffness: 280, damping: 22 }
const stagger = { show: { transition: { staggerChildren: 0.09 } } }
const reveal  = { hidden: { opacity: 0, y: 24 }, show: { opacity: 1, y: 0, transition: { duration: 0.7, ease } } }

// Animated SVG arc ring
function ScoreRing({ score, size = 220 }) {
  const r = (size / 2) - 14
  const circumference = 2 * Math.PI * r
  const [offset, setOffset] = useState(circumference)
  useEffect(() => {
    const timer = setTimeout(() => {
      setOffset(circumference - (score / 100) * circumference)
    }, 500)
    return () => clearTimeout(timer)
  }, [score, circumference])

  return (
    <svg width={size} height={size} style={{ display: 'block' }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={HAIRLINE} strokeWidth="3"/>
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={`url(#violet-gold)`} strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
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

export default function MatchDetail() {
  const navigate  = useNavigate()
  const match     = MOCK_MATCH
  const scoreDisp = useCountUp(match.match_score, 1000, 500)

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent="#8B5CF6" />

      {/* nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', gap: 24, height: 68 }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => navigate(-1)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8, transition: 'color 0.2s' }}
          onMouseEnter={e => { e.currentTarget.style.color = BONE }}
          onMouseLeave={e => { e.currentTarget.style.color = MUTE }}
        >
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </motion.button>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <SonderNav3D markSize={32}/>
        </div>
        <div style={{ width: 80 }}/>
      </nav>

      {/* 2-column body */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>

        {/* LEFT — profile */}
        <motion.div
          initial={{ opacity: 0, x: -28 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, ease }}
          style={{ padding: '60px 52px', borderRight: `1px solid ${HAIRLINE}`, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}
        >
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 450, background: `radial-gradient(ellipse 90% 60% at 35% 18%, ${VIOLET}1A 0%, transparent 65%)`, pointerEvents: 'none' }}/>

          {/* avatar */}
          <div style={{ marginBottom: 32, position: 'relative', display: 'inline-block' }}>
            <motion.div
              animate={{ boxShadow: [`0 0 0 2px ${VIOLET}33, 0 0 32px ${VIOLET}18`, `0 0 0 2px ${VIOLET}77, 0 0 64px ${VIOLET}38`, `0 0 0 2px ${VIOLET}33, 0 0 32px ${VIOLET}18`] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
              style={{ width: 148, height: 148, borderRadius: '50%', overflow: 'hidden' }}
            >
              <img src={match.avatar_url} alt={match.display_name} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}/>
            </motion.div>
          </div>

          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 48, color: BONE, lineHeight: 1, marginBottom: 12, letterSpacing: '-0.01em', filter: 'drop-shadow(0 0 24px rgba(244,237,224,0.10))' }}>
            {match.display_name}
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 22 }}>
            <MapPin size={11} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>{match.location}</span>
          </div>
          <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 20, lineHeight: 1.65, color: MUTE, marginBottom: 32 }}>
            "{match.bio}"
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 'auto' }}>
            {match.tags.map((tag, i) => {
              const colors = [VIOLET, '#14B8A6', '#F59E0B', '#E07060']
              const c = colors[i % colors.length]
              return (
                <motion.span
                  key={tag}
                  whileHover={{ scale: 1.08, y: -2, transition: spring }}
                  whileTap={{ scale: 0.95 }}
                  style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: c, fontFamily: '"Inter Tight",sans-serif', padding: '6px 14px', borderRadius: 20, border: `1px solid ${c}44`, background: `${c}12`, cursor: 'default', display: 'inline-block' }}
                >
                  {tag}
                </motion.span>
              )
            })}
          </div>

          {/* CTAs */}
          <div style={{ marginTop: 52, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <motion.button
              whileHover={{ y: -2, boxShadow: `0 0 64px ${VIOLET}55, 0 0 128px ${VIOLET}22`, transition: spring }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/chat/session-1')}
              style={{ width: '100%', padding: '18px 0', background: `linear-gradient(135deg, ${VIOLET} 0%, #6D28D9 100%)`, border: 'none', borderRadius: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: '#fff', boxShadow: `0 0 48px ${VIOLET}33, 0 0 96px ${VIOLET}11` }}
            >
              <MessageCircle size={14}/> Start a conversation
            </motion.button>
            <motion.button
              whileHover={{ borderColor: `${VIOLET}44`, color: BONE, background: `${VIOLET}0A`, transition: { duration: 0.2 } }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/approve/1')}
              style={{ width: '100%', padding: '15px 0', background: 'rgba(212,182,134,0.04)', border: `1px solid ${HAIRLINE}`, borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, transition: 'all 0.2s' }}
            >
              Review match
            </motion.button>
          </div>
        </motion.div>

        {/* RIGHT — score + compatibility */}
        <motion.div
          variants={stagger} initial="hidden" animate="show"
          style={{ padding: '60px 52px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}
        >
          {/* Score hero */}
          <motion.div variants={reveal} style={{ marginBottom: 52, display: 'flex', alignItems: 'center', gap: 36 }}>
            <div style={{ position: 'relative', flexShrink: 0 }}>
              <ScoreRing score={match.match_score} size={180}/>
              <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <motion.span
                  animate={{ filter: [`drop-shadow(0 0 12px ${VIOLET}88)`, `drop-shadow(0 0 32px ${VIOLET}cc)`, `drop-shadow(0 0 12px ${VIOLET}88)`] }}
                  transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 72, lineHeight: 1, color: BONE, letterSpacing: '-0.04em' }}
                >
                  {scoreDisp}
                </motion.span>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.20em', textTransform: 'uppercase', color: `${VIOLET}BB`, marginTop: 2 }}>% match</span>
              </div>
            </div>
            <div>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 10 }}>Compatibility</p>
              <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 36, color: BONE, lineHeight: 1.1 }}>
                Nearly<br/>perfect.
              </h2>
            </div>
          </motion.div>

          <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, ${VIOLET}44, ${HAIRLINE})`, marginBottom: 44 }}/>

          {/* compatibility list */}
          <motion.div variants={reveal} style={{ marginBottom: 52 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 28 }}>Why you match</p>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {match.compatibility.map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.45, delay: i * 0.08, ease }}
                  whileHover={{ x: 6, transition: { duration: 0.18 } }}
                  style={{ display: 'flex', alignItems: 'flex-start', gap: 16, padding: '14px 0', borderBottom: `1px solid ${HAIRLINE}`, cursor: 'default' }}
                >
                  <div style={{ width: 22, height: 22, borderRadius: '50%', border: `1px solid ${VIOLET}44`, background: `${VIOLET}12`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                    <Check size={9} style={{ color: VIOLET }}/>
                  </div>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, lineHeight: 1.65, color: BONE }}>{item}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, ${VIOLET}44, ${HAIRLINE})`, marginBottom: 44 }}/>

          {/* topics */}
          <motion.div variants={reveal}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 18 }}>Start the conversation</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {match.topics.map((t, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 14 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.07, ease }}
                  whileHover={{ x: 6, borderColor: `${VIOLET}55`, background: `${VIOLET}0A`, transition: { duration: 0.18 } }}
                  whileTap={{ scale: 0.99 }}
                  style={{ padding: '18px 20px', borderRadius: 14, border: `1px solid ${HAIRLINE}`, background: 'rgba(232,212,168,0.02)', cursor: 'pointer', transition: 'border-color 0.2s, background 0.2s' }}
                  onClick={() => navigate('/chat/session-1')}
                >
                  <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 17, lineHeight: 1.5, color: BONE }}>
                    "{t}"
                  </p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}
