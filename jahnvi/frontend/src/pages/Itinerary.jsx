import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Users, Mail } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import ActivityCard from '../components/ActivityCard'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import { emailItineraryTest } from '../lib/api'
import { useAuth } from '../hooks/useAuth'

const SKY    = '#38BDF8'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

const DAYS = [
  {
    day: 1, theme: 'Arrival & First Light',
    activities: [
      { id: 'a1', name: 'Alaya Ubud',                 category: 'Accommodation', time: '3:00 PM',  why: 'Boutique resort with wellness focus — matched to your relaxed pace and mid-range budget.' },
      { id: 'a2', name: 'Sacred Monkey Forest',        category: 'Nature',        time: '5:00 PM',  why: 'A 10-minute walk from your hotel. UNESCO-listed and perfect for a gentle first evening.' },
      { id: 'a3', name: 'Locavore NXT',                category: 'Fine Dining',   time: '7:30 PM',  why: "Ubud's most celebrated chef-led tasting menu. Reservations rare — booked ahead for you." },
    ],
  },
  {
    day: 2, theme: 'Culture & Ceremony',
    activities: [
      { id: 'b1', name: 'Tirta Empul Temple',          category: 'Culture',       time: '8:00 AM',  why: 'Best visited early. The ritual purification pools are a once-in-a-lifetime experience.' },
      { id: 'b2', name: 'Tegalalang Rice Terraces',    category: 'Nature',        time: '11:00 AM', why: 'Most photogenic terraces near Ubud — morning light is ideal for this time slot.' },
      { id: 'b3', name: 'Kecak Fire Dance, Uluwatu',   category: 'Culture',       time: '6:00 PM',  why: "Sunset backdrop and traditional Balinese performance — one of Bali's signature experiences." },
    ],
  },
  {
    day: 3, theme: 'Coastline & Calm',
    activities: [
      { id: 'c1', name: 'Uluwatu Temple',              category: 'Culture',       time: '9:00 AM',  why: 'Dramatic 70m cliff views. Aligns with the scenic nature preference you set.' },
      { id: 'c2', name: 'Padang Padang Beach',         category: 'Nature',        time: '11:30 AM', why: 'Hidden cove accessed by carved stone stairs. Worth every step.' },
      { id: 'c3', name: 'Jimbaran Seafood, Beachside', category: 'Dining',        time: '6:30 PM',  why: 'Fresh catch grilled on the beach at sunset. Within your daily budget.' },
    ],
  },
  {
    day: 4, theme: 'Rest & Renewal',
    activities: [
      { id: 'd1', name: 'Balinese Healing Massage',    category: 'Wellness',      time: '10:00 AM', why: 'Your wellness travel flag — 90-min traditional massage at the resort.' },
      { id: 'd2', name: 'Campuhan Ridge Walk',         category: 'Nature',        time: '1:00 PM',  why: 'Quiet 2km jungle ridge trail. Low effort, high reward.' },
      { id: 'd3', name: 'Sari Organik',                category: 'Dining',        time: '6:00 PM',  why: 'Farm-to-table dinner in the rice fields. The most serene setting in Ubud.' },
    ],
  },
]

const stagger    = { show: { transition: { staggerChildren: 0.09 } } }
const cardReveal = { hidden: { opacity: 0, y: 22 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease } } }

export default function Itinerary() {
  const navigate            = useNavigate()
  const { user }            = useAuth()
  const [activeDay, setDay] = useState(0)
  const [feedback, setFb]   = useState([])
  const [emailing, setEmailing] = useState(false)
  const [emailSent, setEmailSent] = useState(false)

  async function handleEmailExport() {
    if (!user?.email) return
    setEmailing(true)
    try {
      await emailItineraryTest(user.email)
      setEmailSent(true)
      setTimeout(() => setEmailSent(false), 3000)
    } catch (err) {
      console.error('Email export failed:', err)
    } finally {
      setEmailing(false)
    }
  }

  const day = DAYS[activeDay]

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent="#38BDF8" />

      {/* nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/dashboard')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8, transition: 'color 0.2s' }}
          onMouseEnter={e => { e.currentTarget.style.color = BONE }}
          onMouseLeave={e => { e.currentTarget.style.color = MUTE }}
        >
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Dashboard</span>
        </motion.button>
        <SonderNav3D markSize={32}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <motion.button
            whileHover={{ borderColor: `${SKY}55`, boxShadow: `0 0 24px ${SKY}22`, scale: 1.04, transition: spring }}
            whileTap={{ scale: 0.96 }}
            onClick={handleEmailExport}
            disabled={emailing}
            style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '8px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 7, transition: 'all 0.2s', opacity: emailing ? 0.6 : 1 }}
          >
            <Mail size={11} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD }}>
              {emailing ? 'Sending…' : emailSent ? 'Sent!' : 'Email itinerary'}
            </span>
          </motion.button>
          <motion.button
            whileHover={{ borderColor: `${SKY}55`, boxShadow: `0 0 24px ${SKY}22`, scale: 1.04, transition: spring }}
            whileTap={{ scale: 0.96 }}
            onClick={() => navigate('/shared/1')}
            style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '8px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 7, transition: 'all 0.2s' }}
          >
            <Users size={11} style={{ color: SKY }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: SKY }}>Shared with Priya</span>
          </motion.button>
        </div>
      </nav>

      {/* destination header */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, padding: '40px 48px', position: 'relative', zIndex: 1, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse 50% 150% at 80% 50%, ${SKY}0D 0%, transparent 65%)`, pointerEvents: 'none' }}/>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>Your itinerary</p>
            <motion.h1
              animate={{ filter: ['drop-shadow(0 0 16px rgba(212,182,134,0.18))', 'drop-shadow(0 0 40px rgba(212,182,134,0.42))', 'drop-shadow(0 0 16px rgba(212,182,134,0.18))'] }}
              transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
              style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 52, color: BONE, lineHeight: 1, letterSpacing: '-0.02em' }}
            >
              Bali, Indonesia
            </motion.h1>
          </div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>Jun 14 – Jun 21 · 7 days</p>
        </div>
      </div>

      {/* day tab strip */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.75)', backdropFilter: 'blur(16px)', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex' }}>
          {DAYS.map((d, i) => (
            <motion.button
              key={d.day}
              whileHover={activeDay !== i ? { color: BONE, transition: { duration: 0.15 } } : {}}
              whileTap={{ scale: 0.97 }}
              onClick={() => setDay(i)}
              style={{
                padding: '18px 28px', background: activeDay === i ? `${SKY}0F` : 'none',
                border: 'none', cursor: 'pointer',
                borderBottom: `2px solid ${activeDay === i ? SKY : 'transparent'}`,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.14em',
                color: activeDay === i ? SKY : MUTE, whiteSpace: 'nowrap', transition: 'all 0.2s',
                boxShadow: activeDay === i ? `inset 0 1px 0 ${SKY}1A` : 'none',
              }}
            >
              Day {d.day} — {d.theme}
            </motion.button>
          ))}
        </div>
      </div>

      {/* content */}
      <div style={{ flex: 1, maxWidth: 1100, margin: '0 auto', width: '100%', padding: '0 48px', position: 'relative', zIndex: 1 }}>
        <AnimatePresence mode="wait">
          <motion.div key={activeDay} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -14 }} transition={{ duration: 0.32, ease }}>
            <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 0 }}>

              {/* sidebar */}
              <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '52px 44px 52px 0', position: 'sticky', top: 68, alignSelf: 'start', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', top: 0, left: -44, right: 0, height: 280, background: `radial-gradient(ellipse 80% 60% at 30% 20%, ${SKY}12 0%, transparent 65%)`, pointerEvents: 'none' }}/>
                <div style={{ position: 'relative' }}>
                  <motion.span
                    animate={{ filter: [`drop-shadow(0 0 20px ${SKY}22)`, `drop-shadow(0 0 60px ${SKY}55)`, `drop-shadow(0 0 20px ${SKY}22)`] }}
                    transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
                    style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 140, lineHeight: 0.9, letterSpacing: '-0.04em', color: SKY, opacity: 0.14, userSelect: 'none', display: 'block', marginBottom: -28 }}
                  >
                    {day.day}
                  </motion.span>
                  <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 30, color: BONE, lineHeight: 1.2, position: 'relative' }}>
                    {day.theme}
                  </h2>
                </div>

                <div style={{ marginTop: 36, display: 'flex', flexDirection: 'column', gap: 0 }}>
                  {[
                    { label: 'Activities', value: String(day.activities.length) },
                    { label: 'Est. spend',  value: '$65 – $90' },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ padding: '14px 0', borderTop: `1px solid ${HAIRLINE}` }}>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 5 }}>{label}</p>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 15, fontWeight: 500, color: BONE }}>{value}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* activity list */}
              <motion.div variants={stagger} initial="hidden" animate="show" style={{ padding: '52px 0 52px 52px' }}>
                {day.activities.map(act => (
                  <motion.div key={act.id} variants={cardReveal}>
                    <ActivityCard activity={act} time={act.time} whyThis={act.why}
                      onFeedback={fb => setFb(prev => [...prev.filter(f => f.activity_id !== fb.activity_id), fb])}/>
                  </motion.div>
                ))}
                {feedback.length > 0 && (
                  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                    <motion.button
                      whileHover={{ y: -3, boxShadow: `0 0 64px ${SKY}55, 0 0 128px ${SKY}22`, transition: spring }}
                      whileTap={{ scale: 0.97 }}
                      style={{ padding: '16px 36px', background: `linear-gradient(135deg, ${SKY} 0%, #0284C7 100%)`, border: 'none', borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: '#fff', boxShadow: `0 0 48px ${SKY}44, 0 0 96px ${SKY}11`, marginTop: 8 }}
                    >
                      Update itinerary · {feedback.length} change{feedback.length > 1 ? 's' : ''}
                    </motion.button>
                  </motion.div>
                )}
              </motion.div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
