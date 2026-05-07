import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, MapPin, Check, MessageCircle } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'

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
      <AppBackground />

      {/* top nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', gap: 24, height: 68 }}>
        <button
          onClick={() => navigate(-1)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8, transition: 'color 0.2s' }}
          onMouseEnter={e => { e.currentTarget.style.color = BONE }}
          onMouseLeave={e => { e.currentTarget.style.color = MUTE }}
        >
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </button>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <SonderNav3D markSize={32}/>
        </div>
        <div style={{ width: 80 }}/>
      </nav>

      {/* 2-column body */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>

        {/* LEFT: profile */}
        <motion.div
          initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.9, ease }}
          style={{ padding: '60px 52px', borderRight: `1px solid ${HAIRLINE}`, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}
        >
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 450, background: 'radial-gradient(ellipse 90% 60% at 35% 18%, rgba(212,182,134,0.13) 0%, transparent 65%)', pointerEvents: 'none' }}/>

          {/* avatar with gold ring glow */}
          <div style={{ marginBottom: 32, position: 'relative', display: 'inline-block' }}>
            <motion.div
              animate={{ boxShadow: ['0 0 0 2px rgba(212,182,134,0.20), 0 0 32px rgba(212,182,134,0.10)', '0 0 0 2px rgba(212,182,134,0.40), 0 0 64px rgba(212,182,134,0.28)', '0 0 0 2px rgba(212,182,134,0.20), 0 0 32px rgba(212,182,134,0.10)'] }}
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
            {match.tags.map(tag => (
              <motion.span
                key={tag}
                whileHover={{ scale: 1.04, transition: { duration: 0.15 } }}
                style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD, fontFamily: '"Inter Tight",sans-serif', padding: '6px 14px', borderRadius: 20, border: `1px solid rgba(212,182,134,0.25)`, background: 'rgba(212,182,134,0.06)', cursor: 'default', display: 'inline-block' }}
              >
                {tag}
              </motion.span>
            ))}
          </div>

          {/* CTAs */}
          <div style={{ marginTop: 52, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <button
              onClick={() => navigate('/chat/session-1')}
              style={{ width: '100%', padding: '18px 0', background: GOLD, border: 'none', borderRadius: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: BG, boxShadow: '0 0 48px rgba(212,182,134,0.28), 0 0 96px rgba(212,182,134,0.10)', transition: 'all 0.22s' }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 0 64px rgba(212,182,134,0.44), 0 0 128px rgba(212,182,134,0.16)' }}
              onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = '0 0 48px rgba(212,182,134,0.28), 0 0 96px rgba(212,182,134,0.10)' }}
            >
              <MessageCircle size={14}/> Start a conversation
            </button>
            <button
              onClick={() => navigate('/approve/1')}
              style={{ width: '100%', padding: '15px 0', background: 'rgba(212,182,134,0.04)', border: `1px solid ${HAIRLINE}`, borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, transition: 'all 0.2s' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(232,212,168,0.28)'; e.currentTarget.style.color = BONE; e.currentTarget.style.background = 'rgba(212,182,134,0.08)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = HAIRLINE; e.currentTarget.style.color = MUTE; e.currentTarget.style.background = 'rgba(212,182,134,0.04)' }}
            >
              Review match
            </button>
          </div>
        </motion.div>

        {/* RIGHT: details */}
        <motion.div
          variants={stagger} initial="hidden" animate="show"
          style={{ padding: '60px 52px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}
        >
          {/* match score — breathing glow */}
          <motion.div variants={reveal} style={{ marginBottom: 56 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>
              Compatibility score
            </p>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10 }}>
              <motion.span
                animate={{ filter: ['drop-shadow(0 0 16px rgba(212,182,134,0.28))', 'drop-shadow(0 0 64px rgba(212,182,134,0.70))', 'drop-shadow(0 0 16px rgba(212,182,134,0.28))'] }}
                transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 128, lineHeight: 0.88, letterSpacing: '-0.04em', background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'block' }}
              >
                {match.match_score}
              </motion.span>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.50)', paddingBottom: 22 }}>
                % match
              </span>
            </div>
          </motion.div>

          <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, rgba(232,212,168,0.22), ${HAIRLINE})`, marginBottom: 44 }}/>

          {/* compatibility */}
          <motion.div variants={reveal} style={{ marginBottom: 52 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>Why you match</p>
            <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 32, color: BONE, marginBottom: 28 }}>Five things in common</h2>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {match.compatibility.map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: 16 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.07, ease }}
                  style={{ display: 'flex', alignItems: 'flex-start', gap: 16, padding: '16px 0', borderBottom: `1px solid ${HAIRLINE}` }}
                >
                  <div style={{ width: 24, height: 24, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.25)`, background: 'rgba(212,182,134,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                    <Check size={10} style={{ color: GOLD }}/>
                  </div>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, lineHeight: 1.65, color: BONE }}>{item}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, rgba(232,212,168,0.22), ${HAIRLINE})`, marginBottom: 44 }}/>

          {/* topics */}
          <motion.div variants={reveal}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>Suggested topics</p>
            <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 32, color: BONE, marginBottom: 28 }}>Start the conversation</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {match.topics.map((t, i) => (
                <motion.div
                  key={i}
                  whileHover={{ x: 6, transition: { duration: 0.18 } }}
                  style={{ padding: '20px 22px', borderRadius: 16, border: `1px solid ${HAIRLINE}`, background: 'rgba(232,212,168,0.025)', cursor: 'pointer', transition: 'border-color 0.2s, background 0.2s' }}
                  onClick={() => navigate('/chat/session-1')}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(232,212,168,0.22)'; e.currentTarget.style.background = 'rgba(232,212,168,0.05)' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = HAIRLINE; e.currentTarget.style.background = 'rgba(232,212,168,0.025)' }}
                >
                  <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 18, lineHeight: 1.55, color: BONE }}>
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
