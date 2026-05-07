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
      { id: 'a1', name: 'Check in to Alaya Ubud',       category: 'Accommodation', time: '3:00 PM',  why: 'Rated top boutique resort in Ubud with a wellness focus — matches your relaxed pace preference.' },
      { id: 'a2', name: 'Sacred Monkey Forest Sanctuary',category: 'Nature',        time: '5:00 PM',  why: 'A 10-minute walk from your hotel, this UNESCO-listed site is perfect for a gentle first afternoon.' },
      { id: 'a3', name: 'Dinner at Locavore NXT',        category: 'Dining',        time: '7:30 PM',  why: "Ubud's most lauded chef-led restaurant. Reservations rare — booked ahead for you." },
    ],
  },
  {
    day: 2, theme: 'Culture & Ceremony',
    activities: [
      { id: 'b1', name: 'Tirta Empul Temple',            category: 'Culture',       time: '8:00 AM',  why: 'Best visited early to avoid crowds. The ritual purification pools are a once-in-a-lifetime experience.' },
      { id: 'b2', name: 'Tegalalang Rice Terraces',      category: 'Nature',        time: '11:00 AM', why: 'The most photogenic terraces near Ubud — morning light is ideal.' },
      { id: 'b3', name: 'Kecak Fire Dance at Uluwatu',   category: 'Culture',       time: '6:00 PM',  why: 'Sunset backdrop and traditional Balinese performance — unmissable.' },
    ],
  },
  {
    day: 3, theme: 'Coastline & Calm',
    activities: [
      { id: 'c1', name: 'Uluwatu Temple Clifftop Walk',  category: 'Culture',       time: '9:00 AM',  why: 'The dramatic 70m cliff views align perfectly with the scenic nature preference you set.' },
      { id: 'c2', name: 'Padang Padang Beach',           category: 'Nature',        time: '11:30 AM', why: 'Hidden cove accessed by carved stone stairs — worth the climb.' },
      { id: 'c3', name: 'Jimbaran Seafood Dinner',       category: 'Dining',        time: '6:30 PM',  why: 'Fresh catch grilled on the beach at sunset. Classic Bali experience within your daily budget.' },
    ],
  },
  {
    day: 4, theme: 'Rest & Renewal',
    activities: [
      { id: 'd1', name: 'Balinese Healing Massage',      category: 'Wellness',      time: '10:00 AM', why: 'Your wellness travel style flag — a 90-min traditional massage at the resort.' },
      { id: 'd2', name: 'Campuhan Ridge Walk',           category: 'Nature',        time: '1:00 PM',  why: 'A quiet 2km trail through the jungle ridge. Low effort, high reward.' },
      { id: 'd3', name: 'Sari Organik Farm Dinner',      category: 'Dining',        time: '6:00 PM',  why: 'Farm-to-table in the rice fields. The most peaceful setting in Ubud.' },
    ],
  },
]

const LOAD_STAGES = [
  'Understanding your travel style…',
  'Finding the best destinations…',
  'Ranking options for you…',
  'Building your itinerary…',
  'Explaining your activities…',
  'Checking everything looks right…',
  'Finding your travel companion…',
]

export default function Itinerary() {
  const navigate   = useNavigate()
  const [activeDay, setDay]   = useState(0)
  const [activeTab, setTab]   = useState('itinerary')
  const [feedback, setFb]     = useState([])

  const day = DAYS[activeDay]

  function handleFeedback(fb) {
    setFb(prev => [...prev.filter(f => f.activity_id !== fb.activity_id), fb])
  }

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* sticky header */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 50,
        background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        borderBottom: `1px solid ${HAIRLINE}`, padding: '52px 20px 0',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 18 }}>
          <button onClick={() => navigate('/dashboard')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0 }}>
            <ArrowLeft size={20}/>
          </button>
          <div style={{ flex: 1 }}>
            <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 22, color: BONE, lineHeight: 1.1 }}>
              Bali, Indonesia
            </h1>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, marginTop: 2 }}>Jun 14 – Jun 21 · 7 days</p>
          </div>
          <button onClick={() => navigate('/shared/1')} style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '7px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5 }}>
            <Users size={11} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', color: GOLD }}>Shared</span>
          </button>
        </div>

        {/* day tabs */}
        <div style={{ display: 'flex', gap: 0, overflowX: 'auto', paddingBottom: 0, scrollbarWidth: 'none' }}>
          {DAYS.map((d, i) => (
            <button
              key={d.day}
              onClick={() => setDay(i)}
              style={{
                padding: '10px 16px', background: 'none', border: 'none', cursor: 'pointer',
                borderBottom: `2px solid ${activeDay === i ? GOLD : 'transparent'}`,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.12em',
                color: activeDay === i ? GOLD : MUTE, whiteSpace: 'nowrap',
                transition: 'color 0.2s',
              }}
            >
              Day {d.day}
            </button>
          ))}
        </div>
      </div>

      {/* content */}
      <div style={{ padding: '24px 20px 100px', position: 'relative', zIndex: 10 }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeDay}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -14 }}
            transition={{ duration: 0.35, ease }}
          >
            <div style={{ marginBottom: 20 }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 4 }}>
                Day {day.day}
              </p>
              <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 24, color: BONE, lineHeight: 1.2 }}>
                {day.theme}
              </h2>
            </div>

            {day.activities.map(act => (
              <ActivityCard
                key={act.id}
                activity={act}
                time={act.time}
                whyThis={act.why}
                onFeedback={handleFeedback}
              />
            ))}

            {feedback.length > 0 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <button style={{
                  width: '100%', padding: '15px 0', marginTop: 16,
                  background: GOLD, border: 'none', borderRadius: 10, cursor: 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
                  textTransform: 'uppercase', fontWeight: 500, color: BG,
                }}>
                  Update Itinerary ({feedback.length} change{feedback.length > 1 ? 's' : ''})
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
