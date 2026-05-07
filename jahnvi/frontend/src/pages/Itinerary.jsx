import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Users } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import ActivityCard from '../components/ActivityCard'
import BottomNav from '../components/BottomNav'

const DAYS = [
  {
    day: 1, theme: 'Arrival & First Light',
    activities: [
      { id: 'a1', name: 'Alaya Ubud',                  category: 'Accommodation', time: '3:00 PM',  why: 'Boutique resort with wellness focus — matched to your relaxed pace and mid-range budget.' },
      { id: 'a2', name: 'Sacred Monkey Forest',         category: 'Nature',        time: '5:00 PM',  why: 'A 10-minute walk from your hotel. UNESCO-listed and perfect for a gentle first evening.' },
      { id: 'a3', name: 'Locavore NXT',                 category: 'Fine Dining',   time: '7:30 PM',  why: "Ubud's most celebrated chef-led tasting menu. Reservations rare — booked ahead for you." },
    ],
  },
  {
    day: 2, theme: 'Culture & Ceremony',
    activities: [
      { id: 'b1', name: 'Tirta Empul Temple',           category: 'Culture',       time: '8:00 AM',  why: 'Best visited early. The ritual purification pools are a once-in-a-lifetime experience.' },
      { id: 'b2', name: 'Tegalalang Rice Terraces',     category: 'Nature',        time: '11:00 AM', why: 'Most photogenic terraces near Ubud — morning light is ideal for this time slot.' },
      { id: 'b3', name: 'Kecak Fire Dance, Uluwatu',    category: 'Culture',       time: '6:00 PM',  why: 'Sunset backdrop and traditional Balinese performance — one of Bali\'s signature experiences.' },
    ],
  },
  {
    day: 3, theme: 'Coastline & Calm',
    activities: [
      { id: 'c1', name: 'Uluwatu Temple',               category: 'Culture',       time: '9:00 AM',  why: 'Dramatic 70m cliff views. Aligns with the scenic nature preference you set.' },
      { id: 'c2', name: 'Padang Padang Beach',          category: 'Nature',        time: '11:30 AM', why: 'Hidden cove accessed by carved stone stairs. Worth every step.' },
      { id: 'c3', name: 'Jimbaran Seafood, Beachside',  category: 'Dining',        time: '6:30 PM',  why: 'Fresh catch grilled on the beach at sunset. Within your daily budget.' },
    ],
  },
  {
    day: 4, theme: 'Rest & Renewal',
    activities: [
      { id: 'd1', name: 'Balinese Healing Massage',     category: 'Wellness',      time: '10:00 AM', why: 'Your wellness travel flag — 90-min traditional massage at the resort.' },
      { id: 'd2', name: 'Campuhan Ridge Walk',          category: 'Nature',        time: '1:00 PM',  why: 'Quiet 2km jungle ridge trail. Low effort, high reward.' },
      { id: 'd3', name: 'Sari Organik',                 category: 'Dining',        time: '6:00 PM',  why: 'Farm-to-table dinner in the rice fields. The most serene setting in Ubud.' },
    ],
  },
]

export default function Itinerary() {
  const navigate           = useNavigate()
  const [activeDay, setDay]   = useState(0)
  const [activeTab, setTab]   = useState('itinerary')
  const [feedback, setFb]     = useState([])

  const day = DAYS[activeDay]

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* sticky header */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 50,
        background: 'rgba(8,8,7,0.94)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
        borderBottom: `1px solid ${HAIRLINE}`,
      }}>
        <div style={{ padding: '52px 20px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <button onClick={() => navigate('/dashboard')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0 }}>
              <ArrowLeft size={20}/>
            </button>
            <div style={{ flex: 1 }}>
              <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 22, color: BONE, lineHeight: 1 }}>
                Bali, Indonesia
              </h1>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, marginTop: 2 }}>Jun 14 – Jun 21 · 7 days</p>
            </div>
            <button onClick={() => navigate('/shared/1')} style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '7px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5 }}>
              <Users size={11} style={{ color: GOLD }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', color: GOLD }}>Shared</span>
            </button>
          </div>
          {/* day tabs */}
          <div style={{ display: 'flex', overflowX: 'auto', scrollbarWidth: 'none' }}>
            {DAYS.map((d, i) => (
              <button key={d.day} onClick={() => setDay(i)} style={{
                padding: '10px 18px', background: 'none', border: 'none', cursor: 'pointer',
                borderBottom: `2px solid ${activeDay === i ? GOLD : 'transparent'}`,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.12em',
                color: activeDay === i ? GOLD : MUTE, whiteSpace: 'nowrap', transition: 'color 0.2s',
              }}>
                Day {d.day}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* content */}
      <div style={{ padding: '32px 24px 100px', position: 'relative', zIndex: 10 }}>
        <AnimatePresence mode="wait">
          <motion.div key={activeDay} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -14 }} transition={{ duration: 0.32, ease }}>

            {/* day hero */}
            <div style={{ position: 'relative', marginBottom: 36 }}>
              {/* background number */}
              <span style={{
                position: 'absolute', top: -20, right: 0,
                fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
                fontSize: 100, lineHeight: 1, letterSpacing: '-0.04em',
                background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
                opacity: 0.10, userSelect: 'none', pointerEvents: 'none',
              }}>
                {day.day}
              </span>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>
                Day {day.day}
              </p>
              <h2 style={{
                fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
                fontSize: 32, lineHeight: 1.2, color: BONE,
              }}>
                {day.theme}
              </h2>
            </div>

            {/* activities */}
            {day.activities.map(act => (
              <ActivityCard key={act.id} activity={act} time={act.time} whyThis={act.why} onFeedback={fb => setFb(prev => [...prev.filter(f => f.activity_id !== fb.activity_id), fb])}/>
            ))}

            {feedback.length > 0 && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <button style={{
                  width: '100%', padding: '16px 0', marginTop: 8,
                  background: GOLD, border: 'none', borderRadius: 12, cursor: 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
                  textTransform: 'uppercase', fontWeight: 500, color: BG,
                  boxShadow: '0 0 40px rgba(212,182,134,0.18)',
                }}>
                  Update itinerary · {feedback.length} change{feedback.length > 1 ? 's' : ''}
                </button>
              </motion.div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      <BottomNav variant="itinerary" activeTab={activeTab} onTabChange={setTab}/>
    </div>
  )
}
