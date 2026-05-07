import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'

const MOCK_MATCH = {
  display_name: 'Priya Mehta',
  avatar_url: 'https://i.pravatar.cc/200?img=47',
  location: 'Mumbai, India',
  match_score: 92,
}

const STATS = [
  { label: 'Travel style',   you: 'Culture',   them: 'Culture'   },
  { label: 'Pace',           you: 'Relaxed',   them: 'Relaxed'   },
  { label: 'Budget',         you: 'Mid-range', them: 'Mid-range' },
  { label: 'Trip length',    you: '6–10 days', them: '7–14 days' },
  { label: 'Travel window',  you: 'Jun – Aug', them: 'Flexible'  },
]

const reveal  = { hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0, transition: { duration: 0.75, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.09 } } }

export default function ApproveDeny() {
  const navigate              = useNavigate()
  const [status, setStatus]   = useState(null)

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* header */}
      <div style={{ padding: '52px 24px 28px', position: 'relative', zIndex: 10 }}>
        <div style={{ position: 'absolute', top: 40, left: 0, right: 0, height: 220, background: 'radial-gradient(ellipse 80% 100% at 50% 50%, rgba(212,182,134,0.09) 0%, transparent 65%)', pointerEvents: 'none' }}/>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, marginBottom: 28 }}>
          <ArrowLeft size={20}/>
        </button>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>Match Decision</p>
        <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 40, lineHeight: 1.1, color: BONE }}>
          Travel together?
        </h1>
      </div>

      <AnimatePresence mode="wait">
        {status === null ? (
          <motion.div key="default" variants={stagger} initial="hidden" animate="show" style={{ padding: '0 24px 140px', position: 'relative', zIndex: 10 }}>

            {/* profile card */}
            <motion.div variants={reveal} style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 32, padding: '22px 20px', borderRadius: 20, border: `1px solid ${HAIRLINE}`, background: 'rgba(14,14,13,0.98)' }}>
              <img src={MOCK_MATCH.avatar_url} alt="" style={{ width: 64, height: 64, borderRadius: '50%', objectFit: 'cover', border: `1.5px solid rgba(212,182,134,0.20)`, flexShrink: 0 }}/>
              <div style={{ flex: 1 }}>
                <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 24, color: BONE, lineHeight: 1, marginBottom: 4 }}>{MOCK_MATCH.display_name}</h2>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>{MOCK_MATCH.location}</p>
              </div>
              <div style={{ textAlign: 'center' }}>
                <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 40, lineHeight: 1, background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'block' }}>
                  {MOCK_MATCH.match_score}
                </span>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.14em', textTransform: 'uppercase', color: MUTE }}>% match</span>
              </div>
            </motion.div>

            {/* stats table */}
            <motion.div variants={reveal} style={{ marginBottom: 28 }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Compatibility breakdown</p>
              <div style={{ border: `1px solid ${HAIRLINE}`, borderRadius: 16, overflow: 'hidden' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '10px 16px', background: 'rgba(232,212,168,0.02)', borderBottom: `1px solid ${HAIRLINE}` }}>
                  {['', 'You', 'Priya'].map(h => (
                    <span key={h} style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE }}>{h}</span>
                  ))}
                </div>
                {STATS.map((s, i) => (
                  <div key={s.label} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '13px 16px', alignItems: 'center', borderBottom: i < STATS.length - 1 ? `1px solid ${HAIRLINE}` : 'none', background: s.you === s.them ? 'rgba(212,182,134,0.02)' : 'transparent' }}>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>{s.label}</span>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, fontWeight: 500, color: BONE }}>{s.you}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, fontWeight: 500, color: BONE }}>{s.them}</span>
                      {s.you === s.them && <Check size={10} style={{ color: GOLD }}/>}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* pending note */}
            <motion.div variants={reveal}>
              <div style={{ padding: '14px 16px', borderRadius: 12, border: `1px solid rgba(212,182,134,0.12)`, background: 'rgba(212,182,134,0.03)', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <div className="live-dot" style={{ marginTop: 4 }}/>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, lineHeight: 1.7, color: MUTE }}>
                  Both of you need to approve to unlock the shared itinerary. Priya will be notified.
                </p>
              </div>
            </motion.div>
          </motion.div>
        ) : status === 'approved' ? (
          <motion.div key="approved" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease }} style={{ padding: '40px 24px', textAlign: 'center', position: 'relative', zIndex: 10 }}>
            <div style={{ position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)', width: 300, height: 300, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(212,182,134,0.10) 0%, transparent 65%)', pointerEvents: 'none' }}/>
            <div style={{ width: 72, height: 72, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.28)`, background: 'rgba(212,182,134,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 28px' }}>
              <Check size={28} style={{ color: GOLD }}/>
            </div>
            <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 36, color: BONE, marginBottom: 14 }}>You've approved</h2>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, color: MUTE, lineHeight: 1.75, maxWidth: 280, margin: '0 auto' }}>
              Waiting for Priya. We'll let you know the moment she confirms.
            </p>
          </motion.div>
        ) : (
          <motion.div key="denied" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease }} style={{ padding: '60px 24px', textAlign: 'center', position: 'relative', zIndex: 10 }}>
            <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 36, color: BONE, marginBottom: 14 }}>Got it</h2>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, color: MUTE, lineHeight: 1.75 }}>
              We'll keep looking for better matches.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {status === null && (
        <div style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, padding: '20px 24px 40px', background: `linear-gradient(to top,${BG} 65%,transparent)`, zIndex: 50 }}>
          <button onClick={() => { setStatus('approved'); setTimeout(() => navigate('/shared/1'), 1800) }} style={{
            width: '100%', padding: '17px 0', marginBottom: 10,
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
        </div>
      )}
    </div>
  )
}
