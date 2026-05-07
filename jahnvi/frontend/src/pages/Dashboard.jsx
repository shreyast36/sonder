import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { MapPin, Calendar, ChevronRight, Plus } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import MatchCard from '../components/MatchCard'
import BottomNav from '../components/BottomNav'

const reveal = { hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0, transition: { duration: 0.9, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.1 } } }

const MOCK_TRIP = {
  destination: 'Bali, Indonesia',
  departure: 'Jun 14',
  returnDate: 'Jun 21',
  daysLeft: 18,
  totalDays: 7,
  coTraveller: 'Priya M.',
}

const MOCK_MATCHES = [
  { id: '1', display_name: 'Priya Mehta',  location: 'Mumbai, India',     match_score: 92, tags: ['Relaxed', 'Culture', 'Mid-range'],    avatar_url: 'https://i.pravatar.cc/80?img=47' },
  { id: '2', display_name: 'Arjun Nair',   location: 'Bangalore, India',  match_score: 87, tags: ['Adventure', 'Mid-range', 'Foodie'],   avatar_url: 'https://i.pravatar.cc/80?img=12' },
]

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, position: 'relative', overflowX: 'hidden' }}>
      {/* grain */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* header */}
      <div style={{ padding: '56px 24px 20px', position: 'relative', zIndex: 10 }}>
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>
            Good morning
          </p>
          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 36, lineHeight: 1.1, color: BONE, letterSpacing: '-0.01em' }}>
            Shreya
          </h1>
        </motion.div>
      </div>

      <motion.div variants={stagger} initial="hidden" animate="show" style={{ padding: '0 20px 100px', position: 'relative', zIndex: 10 }}>

        {/* upcoming trip card */}
        <motion.div variants={reveal} style={{ marginBottom: 32 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>
            Upcoming Trip
          </p>
          <div
            onClick={() => navigate('/itinerary')}
            style={{
              padding: 1, borderRadius: 22, cursor: 'pointer',
              background: 'linear-gradient(145deg,rgba(232,212,168,0.22) 0%,rgba(8,8,7,0) 50%,rgba(232,212,168,0.08) 100%)',
            }}
          >
            <div style={{
              background: 'linear-gradient(160deg,rgba(22,20,16,0.98) 0%,rgba(12,11,10,0.99) 100%)',
              borderRadius: 21, padding: '24px 22px',
            }}>
              {/* destination */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 6 }}>
                    <MapPin size={11} style={{ color: GOLD }}/>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase', color: MUTE }}>Destination</span>
                  </div>
                  <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 26, lineHeight: 1.1, color: BONE, letterSpacing: '-0.01em' }}>
                    {MOCK_TRIP.destination}
                  </h2>
                </div>
                <div style={{
                  width: 52, height: 52, borderRadius: '50%',
                  background: 'radial-gradient(ellipse,rgba(212,182,134,0.18) 0%,transparent 70%)',
                  border: `1px solid rgba(212,182,134,0.18)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <span style={{
                    fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
                    fontSize: 13, lineHeight: 1, textAlign: 'center', color: GOLD,
                  }}>
                    {MOCK_TRIP.daysLeft}<br/>
                    <span style={{ fontSize: 8, letterSpacing: '0.10em', textTransform: 'uppercase', fontStyle: 'normal' }}>days</span>
                  </span>
                </div>
              </div>

              {/* divider */}
              <div style={{ height: 1, background: HAIRLINE, marginBottom: 18 }}/>

              {/* meta */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                {[
                  { label: 'Departs', value: MOCK_TRIP.departure },
                  { label: 'Returns', value: MOCK_TRIP.returnDate },
                  { label: 'Duration', value: `${MOCK_TRIP.totalDays} days` },
                  { label: 'With', value: MOCK_TRIP.coTraveller },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 3 }}>{label}</p>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{value}</p>
                  </div>
                ))}
              </div>

              {/* view itinerary link */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 20, paddingTop: 16, borderTop: `1px solid ${HAIRLINE}` }}>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: GOLD }}>View Itinerary</span>
                <ChevronRight size={11} style={{ color: GOLD }}/>
              </div>
            </div>
          </div>
        </motion.div>

        {/* matches */}
        <motion.div variants={reveal} style={{ marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE }}>
              Your Matches
            </p>
            <button
              onClick={() => navigate('/approve/1')}
              style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: GOLD, background: 'none', border: 'none', cursor: 'pointer' }}
            >
              View all
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {MOCK_MATCHES.map(m => (
              <MatchCard key={m.id} match={m} onClick={() => navigate(`/match/${m.id}`)}/>
            ))}
          </div>
        </motion.div>

        {/* start new trip */}
        <motion.div variants={reveal}>
          <button
            onClick={() => navigate('/preferences')}
            style={{
              width: '100%', padding: '18px 0',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
              background: 'none', border: `1px solid rgba(212,182,134,0.22)`,
              borderRadius: 12, cursor: 'pointer',
            }}
          >
            <Plus size={14} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: GOLD }}>
              Plan a new trip
            </span>
          </button>
        </motion.div>

      </motion.div>

      <BottomNav variant="dashboard"/>
    </div>
  )
}
