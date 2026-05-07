import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, X } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import MatchCard from '../components/MatchCard'

const MOCK_MATCH = {
  id: '1',
  display_name: 'Priya Mehta',
  avatar_url: 'https://i.pravatar.cc/200?img=47',
  location: 'Mumbai, India',
  match_score: 92,
  tags: ['Relaxed', 'Culture', 'Mid-range'],
}

const STATS = [
  { label: 'Travel style',   you: 'Culture',   them: 'Culture'   },
  { label: 'Pace',           you: 'Relaxed',   them: 'Relaxed'   },
  { label: 'Budget',         you: 'Mid-range', them: 'Mid-range' },
  { label: 'Trip length',    you: '6–10 days', them: '7–14 days' },
  { label: 'Preferred time', you: 'Jun–Aug',   them: 'Any'       },
]

const reveal = { hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0, transition: { duration: 0.7, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.09 } } }

export default function ApproveDeny() {
  const navigate   = useNavigate()
  const [status, setStatus] = useState(null) // null | 'approved' | 'denied'

  function approve() {
    setStatus('approved')
    setTimeout(() => navigate('/shared/1'), 2000)
  }

  function deny() {
    setStatus('denied')
    setTimeout(() => navigate(-1), 1500)
  }

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* header */}
      <div style={{ padding: '52px 24px 20px', display: 'flex', alignItems: 'center', gap: 14, position: 'relative', zIndex: 10 }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0 }}>
          <ArrowLeft size={20}/>
        </button>
        <div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE }}>Match Decision</p>
          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 24, color: BONE, lineHeight: 1.1 }}>Travel together?</h1>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {status === null && (
          <motion.div key="default" variants={stagger} initial="hidden" animate="show" style={{ padding: '0 24px 120px', position: 'relative', zIndex: 10 }}>

            {/* match card */}
            <motion.div variants={reveal} style={{ marginBottom: 28 }}>
              <MatchCard match={MOCK_MATCH} onClick={() => navigate(`/match/${MOCK_MATCH.id}`)}/>
            </motion.div>

            {/* compatibility grid */}
            <motion.div variants={reveal} style={{ marginBottom: 28 }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>
                Compatibility breakdown
              </p>
              <div style={{ border: `1px solid ${HAIRLINE}`, borderRadius: 16, overflow: 'hidden' }}>
                {/* column headers */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '10px 16px', background: 'rgba(232,212,168,0.03)', borderBottom: `1px solid ${HAIRLINE}` }}>
                  {['', 'You', 'Priya'].map(h => (
                    <span key={h} style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE }}>{h}</span>
                  ))}
                </div>
                {STATS.map((s, i) => (
                  <div key={s.label} style={{
                    display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
                    padding: '13px 16px', alignItems: 'center',
                    borderBottom: i < STATS.length - 1 ? `1px solid ${HAIRLINE}` : 'none',
                    background: s.you === s.them ? 'rgba(212,182,134,0.02)' : 'transparent',
                  }}>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>{s.label}</span>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, fontWeight: 500, color: BONE }}>{s.you}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, fontWeight: 500, color: BONE }}>{s.them}</span>
                      {s.you === s.them && <Check size={10} style={{ color: GOLD }}/>}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* pending status note */}
            <motion.div variants={reveal} style={{ marginBottom: 32 }}>
              <div style={{ padding: '14px 16px', borderRadius: 12, border: `1px solid rgba(212,182,134,0.14)`, background: 'rgba(212,182,134,0.03)', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <div className="live-dot" style={{ marginTop: 4 }}/>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, lineHeight: 1.65, color: MUTE }}>
                  Both of you need to approve to unlock the shared itinerary. Priya will be notified of your decision.
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}

        {status === 'approved' && (
          <motion.div key="approved" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ padding: '60px 24px', textAlign: 'center', position: 'relative', zIndex: 10 }}>
            <div style={{ width: 72, height: 72, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.30)`, background: 'rgba(212,182,134,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px' }}>
              <Check size={28} style={{ color: GOLD }}/>
            </div>
            <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 30, color: BONE, marginBottom: 12 }}>You've approved</h2>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, lineHeight: 1.7 }}>
              Waiting for Priya to confirm. We'll notify you the moment she does.
            </p>
          </motion.div>
        )}

        {status === 'denied' && (
          <motion.div key="denied" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ padding: '60px 24px', textAlign: 'center', position: 'relative', zIndex: 10 }}>
            <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 30, color: BONE, marginBottom: 12 }}>Got it</h2>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, lineHeight: 1.7 }}>
              We'll keep looking for better matches for your trip.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* sticky buttons */}
      {status === null && (
        <div style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, padding: '20px 24px 36px', background: `linear-gradient(to top,${BG} 65%,transparent)`, zIndex: 50 }}>
          <button
            onClick={approve}
            style={{
              width: '100%', padding: '17px 0', marginBottom: 10,
              background: GOLD, border: 'none', borderRadius: 12, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
              textTransform: 'uppercase', fontWeight: 500, color: BG,
              boxShadow: '0 0 40px rgba(212,182,134,0.20)',
            }}
          >
            <Check size={14}/> Approve & travel together
          </button>
          <button
            onClick={deny}
            style={{
              width: '100%', padding: '14px 0',
              background: 'none', border: `1px solid ${HAIRLINE}`,
              borderRadius: 12, cursor: 'pointer',
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
              textTransform: 'uppercase', color: MUTE,
            }}
          >
            Not a match
          </button>
        </div>
      )}
    </div>
  )
}
