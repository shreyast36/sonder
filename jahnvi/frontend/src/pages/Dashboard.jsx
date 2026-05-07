import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, Plus } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import MatchCard from '../components/MatchCard'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'

const reveal  = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.9, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.12 } } }

const MOCK_MATCHES = [
  { id: '1', display_name: 'Priya Mehta',  location: 'Mumbai, India',    match_score: 92, tags: ['Relaxed', 'Culture', 'Mid-range'],  avatar_url: 'https://i.pravatar.cc/80?img=47' },
  { id: '2', display_name: 'Arjun Nair',   location: 'Bangalore, India', match_score: 87, tags: ['Adventure', 'Mid-range', 'Foodie'], avatar_url: 'https://i.pravatar.cc/80?img=12' },
]

const STATS = [
  { label: 'Departs',   value: 'Jun 14' },
  { label: 'Returns',   value: 'Jun 21' },
  { label: 'Duration',  value: '7 days' },
  { label: 'Days away', value: '18'     },
]

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground />

      {/* top nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <SonderNav3D markSize={32}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <button
            onClick={() => navigate('/preferences')}
            style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.20em', textTransform: 'uppercase', color: MUTE, background: 'none', border: 'none', cursor: 'pointer', transition: 'color 0.2s' }}
            onMouseEnter={e => { e.currentTarget.style.color = BONE }}
            onMouseLeave={e => { e.currentTarget.style.color = MUTE }}
          >
            New trip
          </button>
          <img src="https://i.pravatar.cc/80?img=32" alt="You" style={{ width: 34, height: 34, borderRadius: '50%', objectFit: 'cover', border: `1.5px solid rgba(212,182,134,0.30)`, cursor: 'pointer', boxShadow: '0 0 20px rgba(212,182,134,0.12)', transition: 'box-shadow 0.2s' }}
            onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 0 30px rgba(212,182,134,0.28)' }}
            onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 0 20px rgba(212,182,134,0.12)' }}
          />
        </div>
      </nav>

      {/* greeting bar */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, padding: '44px 48px 40px', position: 'relative', zIndex: 1, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'radial-gradient(ellipse 70% 140% at 15% 60%, rgba(212,182,134,0.09) 0%, transparent 65%)', pointerEvents: 'none' }}/>
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>Good morning</p>
          <motion.h1
            animate={{ filter: ['drop-shadow(0 0 24px rgba(212,182,134,0.20))', 'drop-shadow(0 0 56px rgba(212,182,134,0.50))', 'drop-shadow(0 0 24px rgba(212,182,134,0.20))'] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
            style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 68, lineHeight: 0.95, letterSpacing: '-0.02em', background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'inline-block' }}
          >
            Shreya
          </motion.h1>
        </motion.div>
      </div>

      {/* main 2-col grid */}
      <motion.div variants={stagger} initial="hidden" animate="show"
        style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.4fr 1fr', maxWidth: 1240, margin: '0 auto', width: '100%', gap: 0, position: 'relative', zIndex: 1 }}>

        {/* LEFT: trip card */}
        <motion.div variants={reveal} style={{ padding: '52px 52px', borderRight: `1px solid ${HAIRLINE}` }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 24 }}>Upcoming Trip</p>

          <motion.div
            onClick={() => navigate('/itinerary')}
            whileHover={{ y: -4, transition: { duration: 0.25, ease: 'easeOut' } }}
            style={{ cursor: 'pointer', padding: 1, borderRadius: 26, background: 'linear-gradient(145deg,rgba(232,212,168,0.30) 0%,rgba(8,8,7,0) 50%,rgba(232,212,168,0.12) 100%)', boxShadow: '0 24px 72px rgba(0,0,0,0.55), 0 4px 16px rgba(0,0,0,0.30), inset 0 1px 0 rgba(232,212,168,0.10)' }}
          >
            <div style={{ background: 'linear-gradient(160deg,rgba(24,20,13,0.99) 0%,rgba(14,11,8,1) 100%)', borderRadius: 25, padding: '40px 40px 32px', position: 'relative', overflow: 'hidden' }}>
              {/* inner ambient glow */}
              <div style={{ position: 'absolute', top: -80, right: -80, width: 360, height: 360, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(212,182,134,0.16) 0%, transparent 65%)', pointerEvents: 'none' }}/>
              <div style={{ position: 'absolute', bottom: -40, left: -40, width: 240, height: 240, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(180,138,68,0.08) 0%, transparent 65%)', pointerEvents: 'none' }}/>

              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.50)', marginBottom: 10, position: 'relative' }}>Destination</p>
              <motion.h2
                animate={{ filter: ['drop-shadow(0 0 16px rgba(212,182,134,0.28))', 'drop-shadow(0 0 48px rgba(212,182,134,0.65))', 'drop-shadow(0 0 16px rgba(212,182,134,0.28))'] }}
                transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
                style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 96, lineHeight: 0.85, letterSpacing: '-0.03em', background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'block', marginBottom: 8, position: 'relative' }}
              >
                Bali
              </motion.h2>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.32em', textTransform: 'uppercase', color: MUTE, marginBottom: 36, position: 'relative' }}>Indonesia</p>

              <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, rgba(232,212,168,0.20), ${HAIRLINE})`, marginBottom: 28 }}/>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 0, position: 'relative' }}>
                {STATS.map(({ label, value }, i) => (
                  <div key={label} style={{ borderRight: i < 3 ? `1px solid ${HAIRLINE}` : 'none', paddingRight: 20, paddingLeft: i > 0 ? 20 : 0 }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>{label}</p>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 16, fontWeight: 500, color: label === 'Days away' ? GOLD : BONE }}>{value}</p>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 28, paddingTop: 22, borderTop: `1px solid ${HAIRLINE}`, position: 'relative' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 28, height: 28, borderRadius: '50%', border: `1.5px solid rgba(212,182,134,0.30)`, boxShadow: '0 0 12px rgba(212,182,134,0.15)' }}/>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>Travelling with Priya M.</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: GOLD }}>View itinerary</span>
                  <ChevronRight size={12} style={{ color: GOLD }}/>
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>

        {/* RIGHT: matches + new trip */}
        <motion.div variants={reveal} style={{ padding: '52px 44px', display: 'flex', flexDirection: 'column', gap: 36 }}>

          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 24 }}>
              <div>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>Curated for you</p>
                <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 30, color: BONE, lineHeight: 1 }}>Your companions</h2>
              </div>
              <button
                onClick={() => navigate('/approve/1')}
                style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.16em', textTransform: 'uppercase', color: GOLD, background: 'none', border: 'none', cursor: 'pointer', transition: 'opacity 0.2s' }}
                onMouseEnter={e => { e.currentTarget.style.opacity = '0.65' }}
                onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
              >
                View all
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {MOCK_MATCHES.map(m => (
                <MatchCard key={m.id} match={m} onClick={() => navigate(`/match/${m.id}`)}/>
              ))}
            </div>
          </div>

          <div style={{ height: 1, background: `linear-gradient(to right, transparent, ${HAIRLINE}, transparent)` }}/>

          <div>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 16 }}>Ready for more?</p>
            <motion.button
              whileHover={{ y: -2, transition: { duration: 0.2 } }}
              onClick={() => navigate('/preferences')}
              style={{
                width: '100%', padding: '20px 0',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                background: 'rgba(212,182,134,0.04)', border: `1px solid rgba(212,182,134,0.22)`,
                borderRadius: 16, cursor: 'pointer', transition: 'border-color 0.2s, background 0.2s, box-shadow 0.2s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(212,182,134,0.42)'; e.currentTarget.style.background = 'rgba(212,182,134,0.07)'; e.currentTarget.style.boxShadow = '0 0 30px rgba(212,182,134,0.10)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(212,182,134,0.22)'; e.currentTarget.style.background = 'rgba(212,182,134,0.04)'; e.currentTarget.style.boxShadow = 'none' }}
            >
              <Plus size={13} style={{ color: GOLD }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: GOLD }}>Plan a new trip</span>
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}
