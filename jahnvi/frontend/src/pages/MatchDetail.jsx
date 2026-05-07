import { motion } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, MapPin, Check, MessageCircle } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'

const MOCK_MATCH = {
  id: '1',
  display_name: 'Priya Mehta',
  avatar_url: 'https://i.pravatar.cc/200?img=47',
  location: 'Mumbai, India',
  bio: 'Slow traveller. Museum crawler. Eats where there\'s no menu in English.',
  match_score: 92,
  tags: ['Relaxed Pace', 'Mid-range', 'Culture', 'Foodie'],
  compatibility: [
    'Both prefer relaxed pace over packed schedules',
    'Matching budget range — avoids over-splurging',
    'Culture and food rank highest for both of you',
    'Neither likes group tours',
    'Same ideal trip length: 6–10 days',
  ],
  topics: [
    'Which museum in Bali are you most excited about?',
    'Are you more of a sunrise or sunset person?',
    'Do you prefer planning everything ahead or leaving room to wander?',
  ],
}

function MatchRing({ pct }) {
  const r = 36, c = 2 * Math.PI * r
  return (
    <div style={{ position: 'relative', width: 90, height: 90, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', transform: 'rotate(-90deg)' }} viewBox="0 0 90 90">
        <circle cx="45" cy="45" r={r} fill="none" stroke={HAIRLINE} strokeWidth="2.5"/>
        <circle cx="45" cy="45" r={r} fill="none" stroke={GOLD} strokeWidth="2.5"
          strokeDasharray={c} strokeDashoffset={c - (pct / 100) * c} strokeLinecap="round"/>
      </svg>
      <div style={{ textAlign: 'center', position: 'relative' }}>
        <p style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 22, color: BONE, lineHeight: 1 }}>{pct}%</p>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', color: MUTE, marginTop: 2 }}>MATCH</p>
      </div>
    </div>
  )
}

const reveal = { hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0, transition: { duration: 0.75, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.1 } } }

export default function MatchDetail() {
  const navigate = useNavigate()
  const { id }   = useParams()
  const match    = MOCK_MATCH

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: `url("data:image/svg+xml,${encodeURIComponent('<svg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="4" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>')}")`, backgroundSize: '200px 200px' }}/>

      {/* back button */}
      <div style={{ position: 'absolute', top: 52, left: 20, zIndex: 20 }}>
        <button onClick={() => navigate(-1)} style={{ background: 'rgba(8,8,7,0.5)', backdropFilter: 'blur(10px)', border: `1px solid ${HAIRLINE}`, borderRadius: '50%', width: 38, height: 38, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
          <ArrowLeft size={16} style={{ color: BONE }}/>
        </button>
      </div>

      {/* hero */}
      <div style={{ padding: '80px 24px 32px', textAlign: 'center', position: 'relative', zIndex: 10 }}>
        {/* glow */}
        <div style={{ position: 'absolute', top: 40, left: '50%', transform: 'translateX(-50%)', width: 300, height: 300, borderRadius: '50%', background: 'radial-gradient(ellipse,rgba(212,182,134,0.10) 0%,transparent 65%)', pointerEvents: 'none' }}/>

        <motion.div initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, ease }}>
          <img
            src={match.avatar_url}
            alt={match.display_name}
            style={{ width: 100, height: 100, borderRadius: '50%', objectFit: 'cover', border: `2px solid rgba(212,182,134,0.25)`, marginBottom: 16, display: 'block', margin: '0 auto 16px' }}
          />
          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 30, color: BONE, marginBottom: 6 }}>
            {match.display_name}
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5, marginBottom: 12 }}>
            <MapPin size={10} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>{match.location}</span>
          </div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, lineHeight: 1.75, color: MUTE, maxWidth: 280, margin: '0 auto 24px' }}>
            {match.bio}
          </p>

          {/* tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 6, marginBottom: 28 }}>
            {match.tags.map(tag => (
              <span key={tag} style={{ fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: GOLD, fontFamily: '"Inter Tight",sans-serif', padding: '4px 10px', borderRadius: 20, border: `1px solid rgba(212,182,134,0.22)`, background: 'rgba(212,182,134,0.04)' }}>
                {tag}
              </span>
            ))}
          </div>

          <MatchRing pct={match.match_score}/>
        </motion.div>
      </div>

      {/* divider */}
      <div style={{ height: 1, background: HAIRLINE, margin: '0 24px' }}/>

      <motion.div variants={stagger} initial="hidden" animate="show" style={{ padding: '28px 24px 120px', position: 'relative', zIndex: 10 }}>

        {/* compatibility */}
        <motion.div variants={reveal} style={{ marginBottom: 32 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 16 }}>
            Why you match
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {match.compatibility.map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <div style={{ width: 18, height: 18, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.25)`, background: 'rgba(212,182,134,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                  <Check size={9} style={{ color: GOLD }}/>
                </div>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, lineHeight: 1.65, color: BONE }}>{item}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* topics */}
        <motion.div variants={reveal} style={{ marginBottom: 32 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 16 }}>
            Suggested conversation starters
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {match.topics.map((t, i) => (
              <div key={i} style={{ padding: '14px 16px', borderRadius: 12, border: `1px solid ${HAIRLINE}`, background: 'rgba(232,212,168,0.02)' }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, lineHeight: 1.65, color: BONE }}>{t}</p>
              </div>
            ))}
          </div>
        </motion.div>

      </motion.div>

      {/* sticky CTA */}
      <div style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, padding: '20px 24px 36px', background: `linear-gradient(to top,${BG} 60%,transparent)`, zIndex: 50 }}>
        <button
          onClick={() => navigate('/chat/session-1')}
          style={{
            width: '100%', padding: '17px 0',
            background: GOLD, border: 'none', borderRadius: 12, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
            fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
            textTransform: 'uppercase', fontWeight: 500, color: BG,
          }}
        >
          <MessageCircle size={14}/>
          Start a conversation
        </button>
        <button
          onClick={() => navigate('/approve/1')}
          style={{
            width: '100%', padding: '14px 0', marginTop: 10,
            background: 'none', border: `1px solid ${HAIRLINE}`,
            borderRadius: 12, cursor: 'pointer',
            fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
            textTransform: 'uppercase', color: MUTE,
          }}
        >
          Review match
        </button>
      </div>
    </div>
  )
}
