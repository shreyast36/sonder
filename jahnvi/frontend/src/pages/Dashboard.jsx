import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, Plus, MapPin } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import MatchCard from '../components/MatchCard'
import { SonderNavLogo } from '../components/SonderLogoSVG'

const reveal  = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.9, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.12 } } }

const MOCK_MATCHES = [
  { id: '1', display_name: 'Priya Mehta',  location: 'Mumbai, India',    match_score: 92, tags: ['Relaxed', 'Culture', 'Mid-range'],  avatar_url: 'https://i.pravatar.cc/80?img=47' },
  { id: '2', display_name: 'Arjun Nair',   location: 'Bangalore, India', match_score: 87, tags: ['Adventure', 'Mid-range', 'Foodie'], avatar_url: 'https://i.pravatar.cc/80?img=12' },
]

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* top nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <SonderNavLogo markHeight={32}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button onClick={() => navigate('/preferences')} style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.20em', textTransform: 'uppercase', color: MUTE, background: 'none', border: 'none', cursor: 'pointer' }}>New trip</button>
          <img src="https://i.pravatar.cc/80?img=32" alt="You" style={{ width: 34, height: 34, borderRadius: '50%', objectFit: 'cover', border: `1.5px solid rgba(212,182,134,0.25)`, cursor: 'pointer' }}/>
        </div>
      </nav>

      {/* greeting bar */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, padding: '40px 48px 36px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'radial-gradient(ellipse 60% 120% at 20% 50%, rgba(212,182,134,0.08) 0%, transparent 65%)', pointerEvents: 'none' }}/>
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>Good morning</p>
          <h1 style={{
            fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
            fontSize: 60, lineHeight: 0.95, letterSpacing: '-0.02em',
            background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'inline-block',
          }}>
            Shreya
          </h1>
        </motion.div>
      </div>

      {/* main 2-column grid */}
      <motion.div variants={stagger} initial="hidden" animate="show"
        style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.4fr 1fr', maxWidth: 1200, margin: '0 auto', width: '100%', gap: 0 }}>

        {/* ── LEFT: upcoming trip ── */}
        <motion.div variants={reveal} style={{ padding: '48px 48px', borderRight: `1px solid ${HAIRLINE}` }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 20 }}>Upcoming Trip</p>

          <div
            onClick={() => navigate('/itinerary')}
            style={{ padding: 1, borderRadius: 24, cursor: 'pointer', background: 'linear-gradient(145deg,rgba(232,212,168,0.22) 0%,rgba(8,8,7,0) 50%,rgba(232,212,168,0.08) 100%)' }}
          >
            <div style={{ background: 'linear-gradient(160deg,rgba(20,18,14,0.99) 0%,rgba(12,11,9,1) 100%)', borderRadius: 23, padding: '36px 36px 28px', position: 'relative', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', top: -60, right: -60, width: 280, height: 280, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(212,182,134,0.12) 0%, transparent 65%)', pointerEvents: 'none' }}/>

              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.45)', marginBottom: 8 }}>Destination</p>
              <h2 style={{
                fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
                fontSize: 80, lineHeight: 0.9, letterSpacing: '-0.03em',
                background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'block', marginBottom: 6,
              }}>
                Bali
              </h2>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 32 }}>Indonesia</p>

              <div style={{ height: 1, background: HAIRLINE, marginBottom: 24 }}/>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 0 }}>
                {[
                  { label: 'Departs',  value: 'Jun 14' },
                  { label: 'Returns',  value: 'Jun 21' },
                  { label: 'Duration', value: '7 days' },
                  { label: 'Days away', value: '18' },
                ].map(({ label, value }, i) => (
                  <div key={label} style={{ borderRight: i < 3 ? `1px solid ${HAIRLINE}` : 'none', paddingRight: 20, paddingLeft: i > 0 ? 20 : 0 }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 5 }}>{label}</p>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 15, fontWeight: 500, color: BONE }}>{value}</p>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 24, paddingTop: 20, borderTop: `1px solid ${HAIRLINE}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 26, height: 26, borderRadius: '50%', border: `1.5px solid rgba(212,182,134,0.25)` }}/>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>Travelling with Priya M.</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: GOLD }}>View itinerary</span>
                  <ChevronRight size={12} style={{ color: GOLD }}/>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* ── RIGHT: matches + new trip ── */}
        <motion.div variants={reveal} style={{ padding: '48px 40px', display: 'flex', flexDirection: 'column', gap: 32 }}>

          {/* matches */}
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 20 }}>
              <div>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>Curated for you</p>
                <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 28, color: BONE, lineHeight: 1 }}>Your companions</h2>
              </div>
              <button onClick={() => navigate('/approve/1')} style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.16em', textTransform: 'uppercase', color: GOLD, background: 'none', border: 'none', cursor: 'pointer' }}>
                View all
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {MOCK_MATCHES.map(m => (
                <MatchCard key={m.id} match={m} onClick={() => navigate(`/match/${m.id}`)}/>
              ))}
            </div>
          </div>

          {/* divider */}
          <div style={{ height: 1, background: HAIRLINE }}/>

          {/* new trip */}
          <div>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Ready for more?</p>
            <button onClick={() => navigate('/preferences')} style={{
              width: '100%', padding: '18px 0',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
              background: 'none', border: `1px solid rgba(212,182,134,0.22)`,
              borderRadius: 14, cursor: 'pointer', transition: 'border-color 0.2s',
            }}>
              <Plus size={13} style={{ color: GOLD }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: GOLD }}>Plan a new trip</span>
            </button>
          </div>
        </motion.div>

      </motion.div>
    </div>
  )
}
