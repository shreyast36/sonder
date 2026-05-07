import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, Plus } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import MatchCard from '../components/MatchCard'
import BottomNav from '../components/BottomNav'
import { SonderNavLogo } from '../components/SonderLogoSVG'

const reveal  = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 1, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.12 } } }

const MOCK_MATCHES = [
  { id: '1', display_name: 'Priya Mehta',  location: 'Mumbai, India',    match_score: 92, tags: ['Relaxed', 'Culture', 'Mid-range'],  avatar_url: 'https://i.pravatar.cc/80?img=47' },
  { id: '2', display_name: 'Arjun Nair',   location: 'Bangalore, India', match_score: 87, tags: ['Adventure', 'Mid-range', 'Foodie'], avatar_url: 'https://i.pravatar.cc/80?img=12' },
]

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* nav bar */}
      <div style={{ padding: '52px 24px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative', zIndex: 10 }}>
        <SonderNavLogo markHeight={28}/>
        <img src="https://i.pravatar.cc/80?img=32" alt="You" style={{ width: 34, height: 34, borderRadius: '50%', objectFit: 'cover', border: `1.5px solid rgba(212,182,134,0.25)` }}/>
      </div>

      <motion.div variants={stagger} initial="hidden" animate="show" style={{ position: 'relative', zIndex: 10 }}>

        {/* greeting hero */}
        <motion.div variants={reveal} style={{ padding: '32px 24px 40px', position: 'relative' }}>
          {/* glow */}
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 200, background: 'radial-gradient(ellipse 80% 100% at 30% 50%, rgba(212,182,134,0.10) 0%, transparent 65%)', pointerEvents: 'none' }}/>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>
            Good morning
          </p>
          <h1 style={{
            fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
            fontSize: 52, lineHeight: 1.0, letterSpacing: '-0.02em',
            background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
            display: 'inline-block',
          }}>
            Shreya
          </h1>
        </motion.div>

        {/* upcoming trip card */}
        <motion.div variants={reveal} style={{ padding: '0 20px 36px' }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Upcoming Trip</p>
          <div
            onClick={() => navigate('/itinerary')}
            style={{ padding: 1, borderRadius: 22, cursor: 'pointer', background: 'linear-gradient(145deg,rgba(232,212,168,0.22) 0%,rgba(8,8,7,0) 50%,rgba(232,212,168,0.08) 100%)' }}
          >
            <div style={{ background: 'linear-gradient(160deg,rgba(20,18,14,0.99) 0%,rgba(12,11,9,1) 100%)', borderRadius: 21, padding: '28px 24px 22px', position: 'relative', overflow: 'hidden' }}>
              {/* inner glow */}
              <div style={{ position: 'absolute', top: -40, right: -40, width: 200, height: 200, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(212,182,134,0.12) 0%, transparent 65%)', pointerEvents: 'none' }}/>

              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.45)', marginBottom: 6 }}>Destination</p>
              <h2 style={{
                fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
                fontSize: 58, lineHeight: 0.95, letterSpacing: '-0.02em',
                background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
                display: 'block', marginBottom: 4,
              }}>
                Bali
              </h2>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 24 }}>Indonesia</p>

              <div style={{ height: 1, background: HAIRLINE, marginBottom: 20 }}/>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0 }}>
                {[
                  { label: 'Departs',  value: 'Jun 14' },
                  { label: 'Returns',  value: 'Jun 21' },
                  { label: 'Duration', value: '7 days' },
                ].map(({ label, value }, i) => (
                  <div key={label} style={{ borderRight: i < 2 ? `1px solid ${HAIRLINE}` : 'none', paddingRight: 16, paddingLeft: i > 0 ? 16 : 0 }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 4 }}>{label}</p>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{value}</p>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 20, paddingTop: 16, borderTop: `1px solid ${HAIRLINE}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 22, height: 22, borderRadius: '50%', border: `1.5px solid rgba(212,182,134,0.25)` }}/>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>With Priya M.</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: GOLD }}>Itinerary</span>
                  <ChevronRight size={11} style={{ color: GOLD }}/>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* divider */}
        <div style={{ height: 1, background: HAIRLINE, margin: '0 20px 32px' }}/>

        {/* matches */}
        <motion.div variants={reveal} style={{ padding: '0 20px 32px' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 20 }}>
            <div>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 4 }}>Curated for you</p>
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
        </motion.div>

        {/* new trip */}
        <motion.div variants={reveal} style={{ padding: '0 20px 120px' }}>
          <button onClick={() => navigate('/preferences')} style={{
            width: '100%', padding: '17px 0',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
            background: 'none', border: `1px solid rgba(212,182,134,0.22)`,
            borderRadius: 14, cursor: 'pointer', transition: 'border-color 0.2s',
          }}>
            <Plus size={13} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: GOLD }}>Plan a new trip</span>
          </button>
        </motion.div>

      </motion.div>

      <BottomNav variant="dashboard"/>
    </div>
  )
}
