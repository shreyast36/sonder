import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, MapPin } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import { SonderNavLogo } from '../components/SonderLogoSVG'

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
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* top nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </button>
        <SonderNavLogo markHeight={32}/>
        <div style={{ width: 80 }}/>
      </nav>

      <AnimatePresence mode="wait">
        {status === null ? (
          <motion.div key="default" style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%' }}>

            {/* left — profile */}
            <motion.div
              initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.9, ease }}
              style={{ padding: '56px 48px', borderRight: `1px solid ${HAIRLINE}`, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}
            >
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 400, background: 'radial-gradient(ellipse 80% 60% at 40% 20%, rgba(212,182,134,0.10) 0%, transparent 65%)', pointerEvents: 'none' }}/>

              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 36 }}>Match Decision</p>

              <img src={MOCK_MATCH.avatar_url} alt={MOCK_MATCH.display_name} style={{ width: 120, height: 120, borderRadius: '50%', objectFit: 'cover', border: `1.5px solid rgba(212,182,134,0.22)`, marginBottom: 24 }}/>

              <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 44, color: BONE, lineHeight: 1, marginBottom: 10, letterSpacing: '-0.01em' }}>
                {MOCK_MATCH.display_name}
              </h1>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 18 }}>
                <MapPin size={11} style={{ color: GOLD }}/>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>{MOCK_MATCH.location}</span>
              </div>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 19, lineHeight: 1.65, color: MUTE, marginBottom: 28 }}>
                "{MOCK_MATCH.bio}"
              </p>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 'auto' }}>
                {MOCK_MATCH.tags.map(tag => (
                  <span key={tag} style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD, fontFamily: '"Inter Tight",sans-serif', padding: '5px 12px', borderRadius: 20, border: `1px solid rgba(212,182,134,0.22)`, background: 'rgba(212,182,134,0.04)' }}>
                    {tag}
                  </span>
                ))}
              </div>

              {/* match score display */}
              <div style={{ marginTop: 40, paddingTop: 32, borderTop: `1px solid ${HAIRLINE}`, display: 'flex', alignItems: 'flex-end', gap: 8 }}>
                <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 80, lineHeight: 0.9, background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent' }}>
                  {MOCK_MATCH.match_score}
                </span>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.45)', paddingBottom: 14 }}>% match</span>
              </div>
            </motion.div>

            {/* right — compatibility + decision */}
            <motion.div
              variants={stagger} initial="hidden" animate="show"
              style={{ padding: '56px 48px', display: 'flex', flexDirection: 'column' }}
            >
              <motion.div variants={reveal} style={{ marginBottom: 10 }}>
                <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 36, color: BONE, lineHeight: 1.1 }}>
                  Travel together?
                </h2>
              </motion.div>

              <div style={{ height: 1, background: HAIRLINE, margin: '28px 0' }}/>

              {/* compatibility table */}
              <motion.div variants={reveal} style={{ marginBottom: 'auto' }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 16 }}>Compatibility breakdown</p>
                <div style={{ border: `1px solid ${HAIRLINE}`, borderRadius: 16, overflow: 'hidden' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '10px 20px', background: 'rgba(232,212,168,0.02)', borderBottom: `1px solid ${HAIRLINE}` }}>
                    {['', 'You', 'Priya'].map(h => (
                      <span key={h} style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE }}>{h}</span>
                    ))}
                  </div>
                  {STATS.map((s, i) => (
                    <div key={s.label} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '15px 20px', alignItems: 'center', borderBottom: i < STATS.length - 1 ? `1px solid ${HAIRLINE}` : 'none', background: s.you === s.them ? 'rgba(212,182,134,0.02)' : 'transparent' }}>
                      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>{s.label}</span>
                      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{s.you}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{s.them}</span>
                        {s.you === s.them && <Check size={10} style={{ color: GOLD }}/>}
                      </div>
                    </div>
                  ))}
                </div>

                {/* pending note */}
                <div style={{ marginTop: 20, padding: '14px 18px', borderRadius: 12, border: `1px solid rgba(212,182,134,0.12)`, background: 'rgba(212,182,134,0.03)', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <div style={{ width: 7, height: 7, borderRadius: '50%', background: GOLD, opacity: 0.7, marginTop: 4, flexShrink: 0 }}/>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, lineHeight: 1.7, color: MUTE }}>
                    Both of you need to approve to unlock the shared itinerary. Priya will be notified.
                  </p>
                </div>
              </motion.div>

              {/* decision buttons */}
              <motion.div variants={reveal} style={{ marginTop: 40, display: 'flex', flexDirection: 'column', gap: 10 }}>
                <button onClick={() => { setStatus('approved'); setTimeout(() => navigate('/shared/1'), 1800) }} style={{
                  width: '100%', padding: '17px 0',
                  background: GOLD, border: 'none', borderRadius: 12, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
                  textTransform: 'uppercase', fontWeight: 500, color: BG,
                  boxShadow: '0 0 48px rgba(212,182,134,0.22)',
                }}>
                  <Check size={14}/> Approve & travel together
                </button>
                <button onClick={() => { setStatus('denied'); setTimeout(() => navigate(-1), 1400) }} style={{
                  width: '100%', padding: '14px 0',
                  background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 12, cursor: 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
                  textTransform: 'uppercase', color: MUTE,
                }}>
                  Not a match
                </button>
              </motion.div>
            </motion.div>
          </motion.div>

        ) : status === 'approved' ? (
          <motion.div key="approved" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease }}
            style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
            <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 40% 40% at 50% 50%, rgba(212,182,134,0.08) 0%, transparent 65%)', pointerEvents: 'none' }}/>
            <div style={{ textAlign: 'center', position: 'relative' }}>
              <div style={{ width: 80, height: 80, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.28)`, background: 'rgba(212,182,134,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 32px' }}>
                <Check size={32} style={{ color: GOLD }}/>
              </div>
              <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 48, color: BONE, marginBottom: 16, lineHeight: 1 }}>
                You've approved
              </h2>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, color: MUTE, lineHeight: 1.75, maxWidth: 320, margin: '0 auto' }}>
                Waiting for Priya. We'll let you know the moment she confirms.
              </p>
            </div>
          </motion.div>
        ) : (
          <motion.div key="denied" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease }}
            style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 48, color: BONE, marginBottom: 16, lineHeight: 1 }}>Got it</h2>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, color: MUTE, lineHeight: 1.75 }}>
                We'll keep looking for better matches.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
