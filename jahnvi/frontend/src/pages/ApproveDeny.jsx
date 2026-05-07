import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, MapPin } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import { SonderNavLogo } from '../components/SonderLogoSVG'
import AppBackground from '../components/AppBackground'

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

const reveal  = { hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0, transition: { duration: 0.75, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.09 } } }

export default function ApproveDeny() {
  const navigate            = useNavigate()
  const [status, setStatus] = useState(null)

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground />

      {/* nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8, transition: 'color 0.2s' }} onMouseEnter={e => { e.currentTarget.style.color = BONE }} onMouseLeave={e => { e.currentTarget.style.color = MUTE }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </button>
        <SonderNavLogo markHeight={32}/>
        <div style={{ width: 80 }}/>
      </nav>

      <AnimatePresence mode="wait">
        {status === null ? (
          <motion.div key="default" style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>

            {/* left — profile */}
            <motion.div
              initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.9, ease }}
              style={{ padding: '60px 52px', borderRight: `1px solid ${HAIRLINE}`, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}
            >
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 450, background: 'radial-gradient(ellipse 90% 60% at 35% 18%, rgba(212,182,134,0.12) 0%, transparent 65%)', pointerEvents: 'none' }}/>

              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 40 }}>Match Decision</p>

              <motion.div
                animate={{ boxShadow: ['0 0 0 2px rgba(212,182,134,0.18), 0 0 32px rgba(212,182,134,0.08)', '0 0 0 2px rgba(212,182,134,0.38), 0 0 64px rgba(212,182,134,0.24)', '0 0 0 2px rgba(212,182,134,0.18), 0 0 32px rgba(212,182,134,0.08)'] }}
                transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut' }}
                style={{ width: 128, height: 128, borderRadius: '50%', overflow: 'hidden', marginBottom: 28 }}
              >
                <img src={MOCK_MATCH.avatar_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
              </motion.div>

              <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 48, color: BONE, lineHeight: 1, marginBottom: 12, letterSpacing: '-0.01em' }}>
                {MOCK_MATCH.display_name}
              </h1>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 20 }}>
                <MapPin size={11} style={{ color: GOLD }}/>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>{MOCK_MATCH.location}</span>
              </div>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 19, lineHeight: 1.65, color: MUTE, marginBottom: 32 }}>
                "{MOCK_MATCH.bio}"
              </p>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 'auto' }}>
                {MOCK_MATCH.tags.map(tag => (
                  <span key={tag} style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD, fontFamily: '"Inter Tight",sans-serif', padding: '5px 14px', borderRadius: 20, border: `1px solid rgba(212,182,134,0.25)`, background: 'rgba(212,182,134,0.06)' }}>{tag}</span>
                ))}
              </div>

              <div style={{ marginTop: 44, paddingTop: 32, borderTop: `1px solid ${HAIRLINE}`, display: 'flex', alignItems: 'flex-end', gap: 8 }}>
                <motion.span
                  animate={{ filter: ['drop-shadow(0 0 16px rgba(212,182,134,0.28))', 'drop-shadow(0 0 64px rgba(212,182,134,0.70))', 'drop-shadow(0 0 16px rgba(212,182,134,0.28))'] }}
                  transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 88, lineHeight: 0.88, background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent' }}
                >
                  {MOCK_MATCH.match_score}
                </motion.span>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.45)', paddingBottom: 16 }}>% match</span>
              </div>
            </motion.div>

            {/* right — table + decision */}
            <motion.div variants={stagger} initial="hidden" animate="show" style={{ padding: '60px 52px', display: 'flex', flexDirection: 'column' }}>

              <motion.div variants={reveal}>
                <motion.h2
                  animate={{ filter: ['drop-shadow(0 0 12px rgba(244,237,224,0.06))', 'drop-shadow(0 0 28px rgba(244,237,224,0.14))', 'drop-shadow(0 0 12px rgba(244,237,224,0.06))'] }}
                  transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 52, color: BONE, lineHeight: 1.05, marginBottom: 8 }}
                >
                  Travel together?
                </motion.h2>
              </motion.div>

              <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, rgba(232,212,168,0.22), ${HAIRLINE})`, margin: '32px 0' }}/>

              <motion.div variants={reveal} style={{ marginBottom: 'auto' }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 18 }}>Compatibility breakdown</p>
                <div style={{ border: `1px solid ${HAIRLINE}`, borderRadius: 18, overflow: 'hidden', boxShadow: '0 12px 40px rgba(0,0,0,0.28), inset 0 1px 0 rgba(232,212,168,0.06)' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '12px 22px', background: 'rgba(232,212,168,0.03)', borderBottom: `1px solid ${HAIRLINE}` }}>
                    {['', 'You', 'Priya'].map(h => (
                      <span key={h} style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE }}>{h}</span>
                    ))}
                  </div>
                  {STATS.map((s, i) => (
                    <div key={s.label} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '16px 22px', alignItems: 'center', borderBottom: i < STATS.length - 1 ? `1px solid ${HAIRLINE}` : 'none', background: s.you === s.them ? 'rgba(212,182,134,0.025)' : 'transparent', transition: 'background 0.2s' }}>
                      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>{s.label}</span>
                      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{s.you}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{s.them}</span>
                        {s.you === s.them && <div style={{ width: 16, height: 16, borderRadius: '50%', background: 'rgba(212,182,134,0.08)', border: `1px solid rgba(212,182,134,0.25)`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Check size={8} style={{ color: GOLD }}/></div>}
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: 20, padding: '14px 18px', borderRadius: 12, border: `1px solid rgba(212,182,134,0.12)`, background: 'rgba(212,182,134,0.03)', display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <motion.div animate={{ opacity: [1, 0.4, 1] }} transition={{ duration: 2.8, repeat: Infinity, ease: 'easeInOut' }} style={{ width: 7, height: 7, borderRadius: '50%', background: GOLD, boxShadow: '0 0 8px rgba(212,182,134,0.6)', marginTop: 4, flexShrink: 0 }}/>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, lineHeight: 1.7, color: MUTE }}>
                    Both of you need to approve to unlock the shared itinerary. Priya will be notified.
                  </p>
                </div>
              </motion.div>

              <motion.div variants={reveal} style={{ marginTop: 44, display: 'flex', flexDirection: 'column', gap: 12 }}>
                <button
                  onClick={() => { setStatus('approved'); setTimeout(() => navigate('/shared/1'), 1800) }}
                  style={{ width: '100%', padding: '18px 0', background: GOLD, border: 'none', borderRadius: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: BG, boxShadow: '0 0 48px rgba(212,182,134,0.28), 0 0 96px rgba(212,182,134,0.10)', transition: 'all 0.22s' }}
                  onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 0 64px rgba(212,182,134,0.44), 0 0 128px rgba(212,182,134,0.16)' }}
                  onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = '0 0 48px rgba(212,182,134,0.28), 0 0 96px rgba(212,182,134,0.10)' }}
                >
                  <Check size={14}/> Approve & travel together
                </button>
                <button
                  onClick={() => { setStatus('denied'); setTimeout(() => navigate(-1), 1400) }}
                  style={{ width: '100%', padding: '15px 0', background: 'rgba(212,182,134,0.03)', border: `1px solid ${HAIRLINE}`, borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, transition: 'all 0.2s' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(232,212,168,0.24)'; e.currentTarget.style.color = BONE; e.currentTarget.style.background = 'rgba(212,182,134,0.06)' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = HAIRLINE; e.currentTarget.style.color = MUTE; e.currentTarget.style.background = 'rgba(212,182,134,0.03)' }}
                >
                  Not a match
                </button>
              </motion.div>
            </motion.div>
          </motion.div>

        ) : (
          <motion.div key={status} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease }} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 1 }}>
            <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 40% 40% at 50% 50%, rgba(212,182,134,0.09) 0%, transparent 65%)', pointerEvents: 'none' }}/>
            <div style={{ textAlign: 'center', position: 'relative' }}>
              {status === 'approved' && (
                <motion.div animate={{ boxShadow: ['0 0 0 0 rgba(212,182,134,0.3)', '0 0 0 24px rgba(212,182,134,0)', '0 0 0 0 rgba(212,182,134,0)'] }} transition={{ duration: 2, repeat: Infinity }} style={{ width: 80, height: 80, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.30)`, background: 'rgba(212,182,134,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 36px' }}>
                  <Check size={32} style={{ color: GOLD }}/>
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
