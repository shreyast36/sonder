import { motion } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, MapPin, Check, MessageCircle } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import { SonderNavLogo } from '../components/SonderLogoSVG'

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

const reveal  = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.8, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.10 } } }

export default function MatchDetail() {
  const navigate = useNavigate()
  const match    = MOCK_MATCH

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* top nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', padding: '0 48px', display: 'flex', alignItems: 'center', gap: 24, height: 64 }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </button>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <SonderNavLogo markHeight={32}/>
        </div>
        <div style={{ width: 80 }}/>
      </nav>

      {/* 2-column body */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%' }}>

        {/* ── LEFT: profile ── */}
        <motion.div
          initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.9, ease }}
          style={{ padding: '56px 48px', borderRight: `1px solid ${HAIRLINE}`, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}
        >
          {/* glow */}
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 400, background: 'radial-gradient(ellipse 80% 60% at 40% 20%, rgba(212,182,134,0.10) 0%, transparent 65%)', pointerEvents: 'none' }}/>

          {/* avatar */}
          <div style={{ marginBottom: 28, position: 'relative' }}>
            <img src={match.avatar_url} alt={match.display_name} style={{ width: 140, height: 140, borderRadius: '50%', objectFit: 'cover', border: `1.5px solid rgba(212,182,134,0.22)`, display: 'block' }}/>
          </div>

          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 44, color: BONE, lineHeight: 1, marginBottom: 10, letterSpacing: '-0.01em' }}>
            {match.display_name}
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 20 }}>
            <MapPin size={11} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>{match.location}</span>
          </div>
          <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 20, lineHeight: 1.65, color: MUTE, marginBottom: 28 }}>
            "{match.bio}"
          </p>

          {/* tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 'auto' }}>
            {match.tags.map(tag => (
              <span key={tag} style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD, fontFamily: '"Inter Tight",sans-serif', padding: '5px 12px', borderRadius: 20, border: `1px solid rgba(212,182,134,0.22)`, background: 'rgba(212,182,134,0.04)' }}>
                {tag}
              </span>
            ))}
          </div>

          {/* CTAs */}
          <div style={{ marginTop: 48, display: 'flex', flexDirection: 'column', gap: 10 }}>
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
              width: '100%', padding: '14px 0',
              background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 12, cursor: 'pointer',
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
              textTransform: 'uppercase', color: MUTE,
            }}>
              Review match
            </button>
          </div>
        </motion.div>

        {/* ── RIGHT: details ── */}
        <motion.div
          variants={stagger} initial="hidden" animate="show"
          style={{ padding: '56px 48px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 0 }}
        >
          {/* match score */}
          <motion.div variants={reveal} style={{ marginBottom: 52 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>
              Compatibility score
            </p>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
              <span style={{
                fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
                fontSize: 120, lineHeight: 0.9, letterSpacing: '-0.04em',
                background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
                display: 'block',
              }}>
                {match.match_score}
              </span>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.45)', paddingBottom: 18 }}>
                % match
              </span>
            </div>
          </motion.div>

          <div style={{ height: 1, background: HAIRLINE, marginBottom: 40 }}/>

          {/* compatibility */}
          <motion.div variants={reveal} style={{ marginBottom: 48 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 10 }}>Why you match</p>
            <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 30, color: BONE, marginBottom: 24 }}>Five things in common</h2>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {match.compatibility.map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 14, padding: '15px 0', borderBottom: `1px solid ${HAIRLINE}` }}>
                  <div style={{ width: 22, height: 22, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.22)`, background: 'rgba(212,182,134,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                    <Check size={10} style={{ color: GOLD }}/>
                  </div>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, lineHeight: 1.65, color: BONE }}>{item}</p>
                </div>
              ))}
            </div>
          </motion.div>

          <div style={{ height: 1, background: HAIRLINE, marginBottom: 40 }}/>

          {/* topics */}
          <motion.div variants={reveal}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 10 }}>Suggested topics</p>
            <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 30, color: BONE, marginBottom: 24 }}>Start the conversation</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {match.topics.map((t, i) => (
                <div key={i} style={{ padding: '18px 20px', borderRadius: 14, border: `1px solid ${HAIRLINE}`, background: 'rgba(232,212,168,0.02)', cursor: 'pointer' }}
                  onClick={() => navigate('/chat/session-1')}>
                  <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 18, lineHeight: 1.55, color: BONE }}>
                    "{t}"
                  </p>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}
