import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Share2, Mail, Download, Users } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import ActivityCard from '../components/ActivityCard'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'

const CYAN   = '#06B6D4'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

const DAYS = [
  {
    day: 1, theme: 'Arrival & First Light',
    activities: [
      { id: 'a1', name: 'Alaya Ubud',               category: 'Accommodation', time: '3:00 PM',  addedBy: 'You',   why: 'Boutique resort with wellness focus.' },
      { id: 'a2', name: 'Sacred Monkey Forest',      category: 'Nature',        time: '5:00 PM',  addedBy: 'Priya', why: 'Priya added — a short walk from the hotel.' },
      { id: 'a3', name: 'Locavore NXT',              category: 'Fine Dining',   time: '7:30 PM',  addedBy: 'You',   why: "Ubud's most celebrated chef-led tasting menu." },
    ],
  },
  {
    day: 2, theme: 'Culture & Ceremony',
    activities: [
      { id: 'b1', name: 'Tirta Empul Temple',        category: 'Culture',       time: '8:00 AM',  addedBy: 'Priya', why: 'Best visited early to avoid crowds.' },
      { id: 'b2', name: 'Tegalalang Rice Terraces',  category: 'Nature',        time: '11:00 AM', addedBy: 'You',   why: 'Morning light is ideal.' },
      { id: 'b3', name: 'Kecak Fire Dance, Uluwatu', category: 'Culture',       time: '6:00 PM',  addedBy: 'Priya', why: 'Sunset backdrop — unmissable.' },
    ],
  },
  {
    day: 3, theme: 'Coastline & Calm',
    activities: [
      { id: 'c1', name: 'Uluwatu Temple',            category: 'Culture',       time: '9:00 AM',  addedBy: 'You',   why: 'Dramatic 70m cliff views.' },
      { id: 'c2', name: 'Padang Padang Beach',       category: 'Nature',        time: '11:30 AM', addedBy: 'Priya', why: 'Hidden cove — worth the descent.' },
      { id: 'c3', name: 'Jimbaran Seafood',          category: 'Dining',        time: '6:30 PM',  addedBy: 'You',   why: 'Fresh catch on the beach at sunset.' },
    ],
  },
]

const stagger    = { show: { transition: { staggerChildren: 0.09 } } }
const cardReveal = { hidden: { opacity: 0, y: 22 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease } } }

export default function SharedItinerary() {
  const navigate              = useNavigate()
  const [activeDay, setDay]   = useState(0)
  const [shareOpen, setShare] = useState(false)
  const [addOpen, setAdd]     = useState(false)
  const [newActivity, setNew] = useState('')
  const [feedback, setFb]     = useState([])

  const day = DAYS[activeDay]

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground />

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
            whileHover={{ borderColor: `${CYAN}55`, boxShadow: `0 0 20px ${CYAN}22`, scale: 1.04, transition: spring }}
            whileTap={{ scale: 0.96 }}
            onClick={() => setShare(true)}
            style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '8px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.2s' }}
          >
            <Share2 size={11} style={{ color: CYAN }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: CYAN }}>Export</span>
          </motion.button>
          <motion.button
            whileHover={{ borderColor: `${CYAN}44`, scale: 1.04, transition: spring }}
            whileTap={{ scale: 0.96 }}
            style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '8px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.2s' }}
          >
            <Users size={11} style={{ color: CYAN }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: CYAN }}>You & Priya</span>
          </motion.button>
        </div>
      </nav>

      {/* header */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, padding: '40px 48px', position: 'relative', zIndex: 1, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse 50% 150% at 80% 50%, ${CYAN}0D 0%, transparent 65%)`, pointerEvents: 'none' }}/>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>Shared itinerary</p>
            <motion.h1
              animate={{ filter: ['drop-shadow(0 0 14px rgba(212,182,134,0.16))', 'drop-shadow(0 0 40px rgba(212,182,134,0.40))', 'drop-shadow(0 0 14px rgba(212,182,134,0.16))'] }}
              transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
              style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 52, color: BONE, lineHeight: 1, letterSpacing: '-0.02em' }}
            >
              Bali, Indonesia
            </motion.h1>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE, marginBottom: 10 }}>Jun 14 – Jun 21 · 7 days</p>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
              <img src="https://i.pravatar.cc/80?img=32" alt="" style={{ width: 28, height: 28, borderRadius: '50%', border: `1.5px solid rgba(212,182,134,0.28)`, boxShadow: '0 0 14px rgba(212,182,134,0.12)' }}/>
              <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 28, height: 28, borderRadius: '50%', border: `1.5px solid rgba(212,182,134,0.28)`, marginLeft: -10, boxShadow: '0 0 14px rgba(212,182,134,0.12)' }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>You & Priya M.</span>
            </div>
          </div>
        </div>
      </div>

      {/* tabs */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.75)', backdropFilter: 'blur(16px)', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex' }}>
          {DAYS.map((d, i) => (
            <motion.button
              key={d.day}
              whileHover={activeDay !== i ? { color: BONE, transition: { duration: 0.15 } } : {}}
              whileTap={{ scale: 0.97 }}
              onClick={() => setDay(i)}
              style={{
                padding: '18px 28px', background: activeDay === i ? `${CYAN}0F` : 'none',
                border: 'none', cursor: 'pointer',
                borderBottom: `2px solid ${activeDay === i ? CYAN : 'transparent'}`,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.14em',
                color: activeDay === i ? CYAN : MUTE, whiteSpace: 'nowrap', transition: 'all 0.2s',
                boxShadow: activeDay === i ? `inset 0 1px 0 ${CYAN}1A` : 'none',
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
              <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '52px 44px 52px 0', position: 'sticky', top: 68, alignSelf: 'start', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', top: 0, left: -44, right: 0, height: 280, background: `radial-gradient(ellipse 80% 60% at 30% 20%, ${CYAN}12 0%, transparent 65%)`, pointerEvents: 'none' }}/>
                <div style={{ position: 'relative' }}>
                  <motion.span
                    animate={{ filter: [`drop-shadow(0 0 20px ${CYAN}22)`, `drop-shadow(0 0 60px ${CYAN}55)`, `drop-shadow(0 0 20px ${CYAN}22)`] }}
                    transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
                    style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 140, lineHeight: 0.9, letterSpacing: '-0.04em', color: CYAN, opacity: 0.14, userSelect: 'none', display: 'block', marginBottom: -28 }}
                  >
                    {day.day}
                  </motion.span>
                  <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 30, color: BONE, lineHeight: 1.2, position: 'relative' }}>{day.theme}</h2>
                </div>
                <div style={{ marginTop: 36, display: 'flex', flexDirection: 'column', gap: 0 }}>
                  {[{ label: 'Activities', value: String(day.activities.length) }, { label: 'Added by', value: 'You & Priya' }].map(({ label, value }) => (
                    <div key={label} style={{ padding: '14px 0', borderTop: `1px solid ${HAIRLINE}` }}>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 5 }}>{label}</p>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 15, fontWeight: 500, color: BONE }}>{value}</p>
                    </div>
                  ))}
                </div>
                <motion.button
                  whileHover={{ borderColor: `${CYAN}44`, background: `${CYAN}0A`, boxShadow: `0 0 20px ${CYAN}18`, transition: { duration: 0.18 } }}
                  whileTap={{ scale: 0.96 }}
                  onClick={() => setAdd(true)}
                  style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 7, padding: '10px 16px', background: 'rgba(212,182,134,0.04)', border: `1px solid rgba(212,182,134,0.22)`, borderRadius: 10, cursor: 'pointer', transition: 'all 0.2s' }}
                >
                  <Plus size={12} style={{ color: CYAN }}/>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: CYAN }}>Add activity</span>
                </motion.button>
              </div>
              <motion.div variants={stagger} initial="hidden" animate="show" style={{ padding: '52px 0 52px 52px' }}>
                {day.activities.map(act => (
                  <motion.div key={act.id} variants={cardReveal}>
                    <ActivityCard activity={act} time={act.time} whyThis={act.why} addedBy={act.addedBy} onFeedback={fb => setFb(prev => [...prev.filter(f => f.activity_id !== fb.activity_id), fb])}/>
                  </motion.div>
                ))}
                {feedback.length > 0 && (
                  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                    <motion.button
                      whileHover={{ y: -3, boxShadow: `0 0 64px ${CYAN}55, 0 0 128px ${CYAN}22`, transition: spring }}
                      whileTap={{ scale: 0.97 }}
                      style={{ padding: '16px 36px', background: `linear-gradient(135deg, ${CYAN} 0%, #0891B2 100%)`, border: 'none', borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: '#fff', boxShadow: `0 0 48px ${CYAN}44, 0 0 96px ${CYAN}11`, marginTop: 8 }}
                    >
                      Sync changes · {feedback.length}
                    </motion.button>
                  </motion.div>
                )}
              </motion.div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* share sheet */}
      <AnimatePresence>
        {shareOpen && (
          <>
            <motion.div key="sb" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShare(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.60)', zIndex: 300, backdropFilter: 'blur(6px)' }}/>
            <motion.div key="ss" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', damping: 32, stiffness: 280 }} style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 560, zIndex: 301, background: 'rgba(18,14,9,0.98)', borderRadius: '24px 24px 0 0', border: `1px solid rgba(232,212,168,0.12)`, borderBottom: 'none', padding: '12px 0 48px', backdropFilter: 'blur(24px)' }}>
              <div style={{ width: 40, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.16)', margin: '0 auto 24px' }}/>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 28, color: BONE, textAlign: 'center', marginBottom: 32 }}>Export itinerary</p>
              {[{ Icon: Mail, label: 'Send to both emails', sub: 'PDF sent to you and Priya' }, { Icon: Download, label: 'Download PDF', sub: 'Opens in your browser' }].map(({ Icon, label, sub }) => (
                <motion.button
                  key={label}
                  whileHover={{ background: 'rgba(232,212,168,0.04)', transition: { duration: 0.18 } }}
                  whileTap={{ scale: 0.99 }}
                  onClick={() => setShare(false)}
                  style={{ display: 'flex', alignItems: 'center', gap: 18, width: '100%', padding: '20px 32px', background: 'none', border: 'none', cursor: 'pointer', borderTop: `1px solid rgba(232,212,168,0.07)` }}
                >
                  <div style={{ width: 44, height: 44, borderRadius: '50%', border: `1px solid ${CYAN}33`, background: `${CYAN}0A`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Icon size={16} style={{ color: CYAN }}/>
                  </div>
                  <div style={{ textAlign: 'left' }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 14, color: BONE, marginBottom: 3 }}>{label}</p>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>{sub}</p>
                  </div>
                </motion.button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* add sheet */}
      <AnimatePresence>
        {addOpen && (
          <>
            <motion.div key="ab" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setAdd(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.60)', zIndex: 300, backdropFilter: 'blur(6px)' }}/>
            <motion.div key="as" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', damping: 32, stiffness: 280 }} style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 560, zIndex: 301, background: 'rgba(18,14,9,0.98)', borderRadius: '24px 24px 0 0', border: `1px solid rgba(232,212,168,0.12)`, borderBottom: 'none', padding: '12px 36px 52px', backdropFilter: 'blur(24px)' }}>
              <div style={{ width: 40, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.16)', margin: '0 auto 28px' }}/>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 28, color: BONE, marginBottom: 32 }}>Add to Day {day.day}</p>
              <input
                value={newActivity} onChange={e => setNew(e.target.value)}
                placeholder="Place, activity, or idea…"
                onFocus={e => { e.currentTarget.style.borderBottomColor = `${CYAN}66` }}
                onBlur={e => { e.currentTarget.style.borderBottomColor = 'rgba(212,182,134,0.40)' }}
                style={{ width: '100%', padding: '0 0 18px', background: 'none', border: 'none', borderBottom: `1px solid rgba(212,182,134,0.40)`, color: BONE, outline: 'none', fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 24, boxSizing: 'border-box', marginBottom: 36, transition: 'border-color 0.2s' }}
              />
              <motion.button
                whileHover={newActivity.trim() ? { y: -2, boxShadow: `0 0 40px ${CYAN}44`, transition: spring } : {}}
                whileTap={newActivity.trim() ? { scale: 0.97 } : {}}
                onClick={() => { setAdd(false); setNew('') }}
                style={{ width: '100%', padding: '17px 0', background: newActivity.trim() ? `linear-gradient(135deg, ${CYAN} 0%, #0891B2 100%)` : 'rgba(212,182,134,0.06)', border: 'none', borderRadius: 12, cursor: newActivity.trim() ? 'pointer' : 'default', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: newActivity.trim() ? '#fff' : MUTE, boxShadow: newActivity.trim() ? `0 0 40px ${CYAN}33` : 'none', transition: 'all 0.2s' }}
              >
                Add activity
              </motion.button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
