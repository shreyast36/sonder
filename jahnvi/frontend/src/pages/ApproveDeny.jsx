import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, MapPin } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'

const VIOLET = '#8B5CF6'
const GREEN  = '#10B981'

function useCountUp(target, duration = 1000, delay = 500) {
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

function ScoreRing({ score, size = 160 }) {
  const r = (size / 2) - 12
  const circumference = 2 * Math.PI * r
  const [offset, setOffset] = useState(circumference)
  useEffect(() => {
    const t = setTimeout(() => setOffset(circumference - (score / 100) * circumference), 600)
    return () => clearTimeout(t)
  }, [score, circumference])
  return (
    <svg width={size} height={size} style={{ display: 'block' }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={HAIRLINE} strokeWidth="3"/>
      <circle cx={size/2} cy={size/2} r={r} fill="none"
        stroke={`url(#vg-approve)`} strokeWidth="3" strokeLinecap="round"
        strokeDasharray={circumference} strokeDashoffset={offset}
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.34,1.56,0.64,1)' }}
      />
      <defs>
        <linearGradient id="vg-approve" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={VIOLET}/>
          <stop offset="100%" stopColor="#D4B686"/>
        </linearGradient>
      </defs>
    </svg>
  )
}

const MOCK_MATCH = {
  display_name: 'Priya Mehta',
  avatar_url: 'https://i.pravatar.cc/400?img=47',
  location: 'Mumbai, India',
  match_score: 92,
  bio: "Slow traveller. Museum crawler. Eats where there's no menu in English.",
  tags: ['Relaxed Pace', 'Mid-range', 'Culture', 'Foodie'],
}

const STATS = [
  { label: 'Travel style',  you: 'Culture',   them: 'Culture'   },
  { label: 'Pace',          you: 'Relaxed',   them: 'Relaxed'   },
  { label: 'Budget',        you: 'Mid-range', them: 'Mid-range' },
  { label: 'Trip length',   you: '6–10 days', them: '7–14 days' },
  { label: 'Travel window', you: 'Jun – Aug', them: 'Flexible'  },
]

const spring  = { type: 'spring', stiffness: 280, damping: 22 }
const reveal  = { hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0, transition: { duration: 0.65, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.08 } } }

export default function ApproveDeny() {
  const navigate            = useNavigate()
  const [status, setStatus] = useState(null)
  const scoreDisp           = useCountUp(MOCK_MATCH.match_score, 900, 500)

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground />

      {/* nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
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
        <SonderNav3D markSize={32}/>
        <div style={{ width: 80 }}/>
      </nav>

      <AnimatePresence mode="wait">
        {status === null ? (
          <motion.div key="default" style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>

            {/* left — profile */}
            <motion.div
              initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.85, ease }}
              style={{ padding: '60px 52px', borderRight: `1px solid ${HAIRLINE}`, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}
            >
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 450, background: `radial-gradient(ellipse 90% 60% at 35% 18%, ${VIOLET}18 0%, transparent 65%)`, pointerEvents: 'none' }}/>

              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 40 }}>Match Decision</p>

              {/* avatar + score ring */}
              <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 28, marginBottom: 32 }}>
                <motion.div
                  animate={{ boxShadow: [`0 0 0 2px ${VIOLET}33, 0 0 32px ${VIOLET}18`, `0 0 0 2px ${VIOLET}77, 0 0 64px ${VIOLET}38`, `0 0 0 2px ${VIOLET}33, 0 0 32px ${VIOLET}18`] }}
                  transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ width: 116, height: 116, borderRadius: '50%', overflow: 'hidden', flexShrink: 0 }}
                >
                  <img src={MOCK_MATCH.avatar_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
                </motion.div>
                <div style={{ position: 'relative' }}>
                  <ScoreRing score={MOCK_MATCH.match_score} size={130}/>
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                    <motion.span
                      animate={{ filter: [`drop-shadow(0 0 10px ${VIOLET}88)`, `drop-shadow(0 0 28px ${VIOLET}cc)`, `drop-shadow(0 0 10px ${VIOLET}88)`] }}
                      transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                      style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 48, lineHeight: 1, color: BONE, letterSpacing: '-0.03em' }}
                    >
                      {scoreDisp}
                    </motion.span>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: `${VIOLET}99` }}>% match</span>
                  </div>
                </div>
              </div>

              <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 44, color: BONE, lineHeight: 1, marginBottom: 12, letterSpacing: '-0.01em' }}>
                {MOCK_MATCH.display_name}
              </h1>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 20 }}>
                <MapPin size={11} style={{ color: GOLD }}/>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>{MOCK_MATCH.location}</span>
              </div>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 18, lineHeight: 1.65, color: MUTE, marginBottom: 28 }}>
                "{MOCK_MATCH.bio}"
              </p>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 'auto' }}>
                {MOCK_MATCH.tags.map((tag, i) => {
                  const colors = [VIOLET, '#14B8A6', '#F59E0B', '#E07060']
                  const c = colors[i % colors.length]
                  return (
                    <motion.span key={tag} whileHover={{ scale: 1.08, y: -2, transition: spring }} style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: c, fontFamily: '"Inter Tight",sans-serif', padding: '5px 14px', borderRadius: 20, border: `1px solid ${c}44`, background: `${c}12` }}>
                      {tag}
                    </motion.span>
                  )
                })}
              </div>
            </motion.div>

            {/* right — table + decision */}
            <motion.div variants={stagger} initial="hidden" animate="show" style={{ padding: '60px 52px', display: 'flex', flexDirection: 'column' }}>

              <motion.div variants={reveal}>
                <motion.h2
                  animate={{ filter: ['drop-shadow(0 0 12px rgba(244,237,224,0.06))', 'drop-shadow(0 0 28px rgba(244,237,224,0.14))', 'drop-shadow(0 0 12px rgba(244,237,224,0.06))'] }}
                  transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 50, color: BONE, lineHeight: 1.05, marginBottom: 8 }}
                >
                  Travel together?
                </motion.h2>
              </motion.div>

              <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, ${VIOLET}44, ${HAIRLINE})`, margin: '28px 0' }}/>

              <motion.div variants={reveal} style={{ marginBottom: 'auto' }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 18 }}>Compatibility breakdown</p>
                <div style={{ border: `1px solid ${HAIRLINE}`, borderRadius: 18, overflow: 'hidden', boxShadow: '0 12px 40px rgba(0,0,0,0.28), inset 0 1px 0 rgba(232,212,168,0.06)' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '12px 22px', background: 'rgba(232,212,168,0.03)', borderBottom: `1px solid ${HAIRLINE}` }}>
                    {['', 'You', 'Priya'].map(h => (
                      <span key={h} style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE }}>{h}</span>
                    ))}
                  </div>
                  {STATS.map((s, i) => (
                    <motion.div
                      key={s.label}
                      initial={{ opacity: 0, x: 16 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.4, delay: 0.3 + i * 0.07, ease }}
                      style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '15px 22px', alignItems: 'center', borderBottom: i < STATS.length - 1 ? `1px solid ${HAIRLINE}` : 'none', background: s.you === s.them ? `${VIOLET}08` : 'transparent' }}
                    >
                      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>{s.label}</span>
                      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{s.you}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{s.them}</span>
                        {s.you === s.them && (
                          <motion.div
                            initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ ...spring, delay: 0.5 + i * 0.07 }}
                            style={{ width: 16, height: 16, borderRadius: '50%', background: `${VIOLET}18`, border: `1px solid ${VIOLET}44`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                          >
                            <Check size={8} style={{ color: VIOLET }}/>
                          </motion.div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>

                <div style={{ marginTop: 18, padding: '13px 16px', borderRadius: 12, border: `1px solid ${VIOLET}22`, background: `${VIOLET}06`, display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <motion.div animate={{ opacity: [1, 0.4, 1] }} transition={{ duration: 2.5, repeat: Infinity }} style={{ width: 7, height: 7, borderRadius: '50%', background: VIOLET, boxShadow: `0 0 8px ${VIOLET}`, marginTop: 4, flexShrink: 0 }}/>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, lineHeight: 1.7, color: MUTE }}>
                    Both of you need to approve to unlock the shared itinerary. Priya will be notified.
                  </p>
                </div>
              </motion.div>

              <motion.div variants={reveal} style={{ marginTop: 40, display: 'flex', flexDirection: 'column', gap: 12 }}>
                <motion.button
                  whileHover={{ y: -2, boxShadow: `0 0 64px ${GREEN}55, 0 0 128px ${GREEN}22`, transition: spring }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => { setStatus('approved'); setTimeout(() => navigate('/shared/1'), 1800) }}
                  style={{ width: '100%', padding: '18px 0', background: `linear-gradient(135deg, ${GREEN} 0%, #059669 100%)`, border: 'none', borderRadius: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: '#fff', boxShadow: `0 0 48px ${GREEN}33, 0 0 96px ${GREEN}11` }}
                >
                  <Check size={14}/> Approve & travel together
                </motion.button>
                <motion.button
                  whileHover={{ borderColor: 'rgba(232,212,168,0.24)', color: BONE, background: 'rgba(212,182,134,0.06)', transition: { duration: 0.2 } }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => { setStatus('denied'); setTimeout(() => navigate(-1), 1400) }}
                  style={{ width: '100%', padding: '15px 0', background: 'rgba(212,182,134,0.03)', border: `1px solid ${HAIRLINE}`, borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, transition: 'all 0.2s' }}
                >
                  Not a match
                </motion.button>
              </motion.div>
            </motion.div>
          </motion.div>

        ) : (
          <motion.div key={status} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease }} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 1 }}>
            <div style={{ position: 'absolute', inset: 0, background: status === 'approved' ? `radial-gradient(ellipse 40% 40% at 50% 50%, ${GREEN}18 0%, transparent 65%)` : 'radial-gradient(ellipse 40% 40% at 50% 50%, rgba(212,182,134,0.09) 0%, transparent 65%)', pointerEvents: 'none' }}/>
            <div style={{ textAlign: 'center', position: 'relative' }}>
              {status === 'approved' && (
                <motion.div
                  animate={{ boxShadow: [`0 0 0 0 ${GREEN}55`, `0 0 0 28px ${GREEN}00`, `0 0 0 0 ${GREEN}00`] }}
                  transition={{ duration: 1.8, repeat: Infinity }}
                  style={{ width: 80, height: 80, borderRadius: '50%', border: `1px solid ${GREEN}55`, background: `${GREEN}12`, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 36px' }}
                >
                  <Check size={32} style={{ color: GREEN }}/>
                </motion.div>
              )}
              <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 56, color: BONE, marginBottom: 18, lineHeight: 1, filter: 'drop-shadow(0 0 32px rgba(244,237,224,0.12))' }}>
                {status === 'approved' ? "You've approved" : 'Got it'}
              </h2>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, color: MUTE, lineHeight: 1.75, maxWidth: 320, margin: '0 auto' }}>
                {status === 'approved' ? "Waiting for Priya. We'll let you know the moment she confirms." : "We'll keep looking for better matches."}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
