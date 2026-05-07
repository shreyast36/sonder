import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Share2, Mail, Download } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import ActivityCard from '../components/ActivityCard'
import BottomNav from '../components/BottomNav'

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

export default function SharedItinerary() {
  const navigate              = useNavigate()
  const [activeDay, setDay]   = useState(0)
  const [activeTab, setTab]   = useState('itinerary')
  const [shareOpen, setShare] = useState(false)
  const [addOpen, setAdd]     = useState(false)
  const [newActivity, setNew] = useState('')
  const [feedback, setFb]     = useState([])

  const day = DAYS[activeDay]

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* sticky header */}
      <div style={{ position: 'sticky', top: 0, zIndex: 50, background: 'rgba(8,8,7,0.94)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', borderBottom: `1px solid ${HAIRLINE}` }}>
        <div style={{ padding: '52px 20px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <button onClick={() => navigate('/dashboard')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0 }}>
              <ArrowLeft size={20}/>
            </button>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 20, color: BONE, lineHeight: 1 }}>Bali, Indonesia</h1>
                <div style={{ display: 'flex' }}>
                  <img src="https://i.pravatar.cc/80?img=32" alt="" style={{ width: 18, height: 18, borderRadius: '50%', border: `1.5px solid ${BG}`, objectFit: 'cover' }}/>
                  <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 18, height: 18, borderRadius: '50%', border: `1.5px solid ${BG}`, marginLeft: -6, objectFit: 'cover' }}/>
                </div>
              </div>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: MUTE }}>Shared with Priya · Jun 14 – Jun 21</p>
            </div>
            <button onClick={() => setShare(true)} style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '7px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5 }}>
              <Share2 size={10} style={{ color: GOLD }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.12em', color: GOLD }}>Export</span>
            </button>
          </div>
          <div style={{ display: 'flex', overflowX: 'auto', scrollbarWidth: 'none' }}>
            {DAYS.map((d, i) => (
              <button key={d.day} onClick={() => setDay(i)} style={{ padding: '10px 18px', background: 'none', border: 'none', cursor: 'pointer', borderBottom: `2px solid ${activeDay === i ? GOLD : 'transparent'}`, fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.12em', color: activeDay === i ? GOLD : MUTE, whiteSpace: 'nowrap', transition: 'color 0.2s' }}>
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
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 32 }}>
              <div style={{ position: 'relative' }}>
                <span style={{ position: 'absolute', top: -16, left: -4, fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 96, lineHeight: 1, letterSpacing: '-0.04em', background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', opacity: 0.10, userSelect: 'none', pointerEvents: 'none' }}>
                  {day.day}
                </span>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>Day {day.day}</p>
                <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 28, color: BONE, lineHeight: 1.2 }}>{day.theme}</h2>
              </div>
              <button onClick={() => setAdd(true)} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '8px 14px', background: 'none', border: `1px solid rgba(212,182,134,0.22)`, borderRadius: 20, cursor: 'pointer', flexShrink: 0, marginTop: 8 }}>
                <Plus size={11} style={{ color: GOLD }}/>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', color: GOLD }}>Add</span>
              </button>
            </div>

            {day.activities.map(act => (
              <ActivityCard key={act.id} activity={act} time={act.time} whyThis={act.why} addedBy={act.addedBy} onFeedback={fb => setFb(prev => [...prev.filter(f => f.activity_id !== fb.activity_id), fb])}/>
            ))}

            {feedback.length > 0 && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <button style={{ width: '100%', padding: '16px 0', marginTop: 8, background: GOLD, border: 'none', borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: BG, boxShadow: '0 0 40px rgba(212,182,134,0.18)' }}>
                  Sync changes · {feedback.length}
                </button>
              </motion.div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* share sheet */}
      <AnimatePresence>
        {shareOpen && (
          <>
            <motion.div key="sb" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShare(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 300 }}/>
            <motion.div key="ss" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', damping: 30, stiffness: 260 }}
              style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, zIndex: 301, background: 'rgba(18,17,16,0.99)', borderRadius: '20px 20px 0 0', border: `1px solid rgba(232,212,168,0.10)`, borderBottom: 'none', padding: '12px 0 44px' }}>
              <div style={{ width: 36, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.14)', margin: '0 auto 20px' }}/>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: BONE, textAlign: 'center', marginBottom: 28 }}>Export itinerary</p>
              {[{ Icon: Mail, label: 'Send to both emails', sub: 'PDF sent to you and Priya' }, { Icon: Download, label: 'Download PDF', sub: 'Opens in your browser' }].map(({ Icon, label, sub }) => (
                <button key={label} onClick={() => setShare(false)} style={{ display: 'flex', alignItems: 'center', gap: 14, width: '100%', padding: '16px 28px', background: 'none', border: 'none', cursor: 'pointer', borderBottom: `1px solid rgba(232,212,168,0.07)` }}>
                  <div style={{ width: 36, height: 36, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.20)`, background: 'rgba(212,182,134,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Icon size={14} style={{ color: GOLD }}/>
                  </div>
                  <div style={{ textAlign: 'left' }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, color: BONE, marginBottom: 2 }}>{label}</p>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>{sub}</p>
                  </div>
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* add activity sheet */}
      <AnimatePresence>
        {addOpen && (
          <>
            <motion.div key="ab" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setAdd(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 300 }}/>
            <motion.div key="as" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', damping: 30, stiffness: 260 }}
              style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, zIndex: 301, background: 'rgba(18,17,16,0.99)', borderRadius: '20px 20px 0 0', border: `1px solid rgba(232,212,168,0.10)`, borderBottom: 'none', padding: '12px 24px 44px' }}>
              <div style={{ width: 36, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.14)', margin: '0 auto 20px' }}/>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: BONE, marginBottom: 24 }}>Add to Day {day.day}</p>
              <input value={newActivity} onChange={e => setNew(e.target.value)} placeholder="Place, activity, or idea…"
                style={{ width: '100%', padding: '0 0 14px', background: 'none', border: 'none', borderBottom: `1px solid rgba(212,182,134,0.35)`, color: BONE, outline: 'none', fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, boxSizing: 'border-box', marginBottom: 28 }}/>
              <button onClick={() => { setAdd(false); setNew('') }} style={{ width: '100%', padding: '15px 0', background: newActivity.trim() ? GOLD : 'rgba(212,182,134,0.08)', border: 'none', borderRadius: 12, cursor: newActivity.trim() ? 'pointer' : 'default', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: newActivity.trim() ? BG : MUTE }}>
                Add activity
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <BottomNav variant="itinerary" activeTab={activeTab} onTabChange={setTab}/>
    </div>
  )
}
