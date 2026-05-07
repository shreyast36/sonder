import { motion } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, MapPin, Check, MessageCircle } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'

const MOCK_MATCH = {
  id: '1',
  display_name: 'Priya Mehta',
  avatar_url: 'https://i.pravatar.cc/300?img=47',
  location: 'Mumbai, India',
  bio: 'Slow traveller. Museum crawler. Eats where there\'s no menu in English.',
  match_score: 92,
  tags: ['Relaxed Pace', 'Mid-range', 'Culture', 'Foodie'],
  compatibility: [
    'Both prefer relaxed pace over packed schedules',
    'Matching budget range',
    'Culture and food rank highest for both of you',
    'Neither likes group tours',
    'Same ideal trip length: 6–10 days',
  ],
  topics: [
    'Which museum in Bali are you most excited about?',
    'Are you more of a sunrise or a sunset person?',
    'Do you plan everything, or leave room to wander?',
  ],
}

const reveal  = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.8, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.10 } } }

export default function MatchDetail() {
  const navigate = useNavigate()
  const { id }   = useParams()
  const match    = MOCK_MATCH

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* back */}
      <div style={{ position: 'absolute', top: 52, left: 20, zIndex: 20 }}>
        <button onClick={() => navigate(-1)} style={{ width: 38, height: 38, borderRadius: '50%', background: 'rgba(8,8,7,0.6)', backdropFilter: 'blur(10px)', border: `1px solid ${HAIRLINE}`, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
          <ArrowLeft size={16} style={{ color: BONE }}/>
        </button>
      </div>

      {/* profile hero */}
      <div style={{ position: 'relative', padding: '80px 24px 36px', textAlign: 'center' }}>
        {/* glow */}
        <div style={{ position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)', width: 360, height: 320, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(212,182,134,0.11) 0%, transparent 65%)', pointerEvents: 'none' }}/>

        <motion.div initial={{ opacity: 0, scale: 0.90 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.9, ease }}>
          <div style={{ position: 'relative', display: 'inline-block', marginBottom: 20 }}>
            <img src={match.avatar_url} alt={match.display_name} style={{ width: 110, height: 110, borderRadius: '50%', objectFit: 'cover', display: 'block', border: `1.5px solid rgba(212,182,134,0.22)` }}/>
          </div>
          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 34, color: BONE, lineHeight: 1, marginBottom: 8 }}>
            {match.display_name}
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5, marginBottom: 16 }}>
            <MapPin size={10} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>{match.location}</span>
          </div>
          <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 17, lineHeight: 1.65, color: MUTE, maxWidth: 280, margin: '0 auto 22px' }}>
            "{match.bio}"
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 6 }}>
            {match.tags.map(tag => (
              <span key={tag} style={{ fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: GOLD, fontFamily: '"Inter Tight",sans-serif', padding: '4px 11px', borderRadius: 20, border: `1px solid rgba(212,182,134,0.20)`, background: 'rgba(212,182,134,0.04)' }}>
                {tag}
              </span>
            ))}
          </div>
        </motion.div>
      </div>

      {/* match score — hero number */}
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.2, ease }}
        style={{ margin: '0 20px', padding: 1, borderRadius: 22, background: 'linear-gradient(145deg,rgba(232,212,168,0.18) 0%,rgba(8,8,7,0) 55%,rgba(232,212,168,0.06) 100%)' }}>
        <div style={{ background: 'rgba(14,14,13,0.98)', borderRadius: 21, padding: '28px 24px', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', width: 240, height: 180, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(212,182,134,0.10) 0%, transparent 65%)', pointerEvents: 'none' }}/>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 8, position: 'relative' }}>
            Compatibility score
          </p>
          <span style={{
            fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
            fontSize: 88, lineHeight: 1, letterSpacing: '-0.04em',
            background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
            display: 'block', position: 'relative',
          }}>
            {match.match_score}
          </span>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.50)', marginTop: 4, position: 'relative' }}>
            % match
          </p>
        </div>
      </motion.div>

      <motion.div variants={stagger} initial="hidden" animate="show" style={{ padding: '32px 24px 140px', position: 'relative', zIndex: 10 }}>

        {/* compatibility */}
        <motion.div variants={reveal} style={{ marginBottom: 36 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>Why you match</p>
          <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 26, color: BONE, marginBottom: 20 }}>Five things in common</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {match.compatibility.map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '14px 0', borderBottom: `1px solid ${HAIRLINE}` }}>
                <div style={{ width: 20, height: 20, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.22)`, background: 'rgba(212,182,134,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                  <Check size={9} style={{ color: GOLD }}/>
                </div>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, lineHeight: 1.65, color: BONE }}>{item}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* topics */}
        <motion.div variants={reveal}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>Suggested topics</p>
          <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 26, color: BONE, marginBottom: 20 }}>Start the conversation</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {match.topics.map((t, i) => (
              <div key={i} style={{ padding: '16px 18px', borderRadius: 14, border: `1px solid ${HAIRLINE}`, background: 'rgba(232,212,168,0.02)' }}>
                <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 16, lineHeight: 1.55, color: BONE }}>
                  "{t}"
                </p>
              </div>
            ))}
          </div>
        </motion.div>

      </motion.div>

      {/* sticky CTAs */}
      <div style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, padding: '20px 24px 40px', background: `linear-gradient(to top,${BG} 60%,transparent)`, zIndex: 50 }}>
        <button onClick={() => navigate('/chat/session-1')} style={{
          width: '100%', padding: '17px 0', background: GOLD, border: 'none', borderRadius: 12, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
          textTransform: 'uppercase', fontWeight: 500, color: BG,
          boxShadow: '0 0 48px rgba(212,182,134,0.22)',
        }}>
          <MessageCircle size={14}/> Start a conversation
        </button>
        <button onClick={() => navigate('/approve/1')} style={{
          width: '100%', padding: '14px 0', marginTop: 10,
          background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 12, cursor: 'pointer',
          fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
          textTransform: 'uppercase', color: MUTE,
        }}>
          Review match
        </button>
      </div>
    </div>
  )
}
