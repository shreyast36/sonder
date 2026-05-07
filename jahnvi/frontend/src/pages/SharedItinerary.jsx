import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Share2, Mail, Download, X } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GRAIN, ease } from '../lib/tokens'
import ActivityCard from '../components/ActivityCard'
import BottomNav from '../components/BottomNav'

const DAYS = [
  {
    day: 1, theme: 'Arrival & First Light',
    activities: [
      { id: 'a1', name: 'Check in to Alaya Ubud',       category: 'Accommodation', time: '3:00 PM',  addedBy: 'You',   why: 'Boutique resort with wellness focus — matched to your preference.' },
      { id: 'a2', name: 'Sacred Monkey Forest',          category: 'Nature',        time: '5:00 PM',  addedBy: 'Priya', why: 'Priya suggested this based on her culture travel style.' },
      { id: 'a3', name: 'Dinner at Locavore NXT',        category: 'Dining',        time: '7:30 PM',  addedBy: 'You',   why: "Ubud's most celebrated chef-led tasting menu." },
    ],
  },
  {
    day: 2, theme: 'Culture & Ceremony',
    activities: [
      { id: 'b1', name: 'Tirta Empul Temple',            category: 'Culture',       time: '8:00 AM',  addedBy: 'Priya', why: 'Morning visit avoids the midday crowds.' },
      { id: 'b2', name: 'Tegalalang Rice Terraces',      category: 'Nature',        time: '11:00 AM', addedBy: 'You',   why: 'Best light in the late morning for photos.' },
      { id: 'b3', name: 'Kecak Fire Dance at Uluwatu',  category: 'Culture',       time: '6:00 PM',  addedBy: 'Priya', why: 'Sunset backdrop — unmissable.' },
    ],
  },
  {
    day: 3, theme: 'Coastline & Calm',
    activities: [
      { id: 'c1', name: 'Uluwatu Temple Walk',           category: 'Culture',       time: '9:00 AM',  addedBy: 'You',   why: 'Dramatic 70m cliff views.' },
      { id: 'c2', name: 'Padang Padang Beach',           category: 'Nature',        time: '11:30 AM', addedBy: 'Priya', why: 'Hidden cove — worth the carved stair descent.' },
      { id: 'c3', name: 'Jimbaran Seafood Dinner',       category: 'Dining',        time: '6:30 PM',  addedBy: 'You',   why: 'Fresh catch grilled on the beach at sunset.' },
    ],
  },
]

export default function SharedItinerary() {
  const navigate          = useNavigate()
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
      <div style={{
        position: 'sticky', top: 0, zIndex: 50,
        background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        borderBottom: `1px solid ${HAIRLINE}`, padding: '52px 20px 0',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <button onClick={() => navigate('/dashboard')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0 }}>
            <ArrowLeft size={20}/>
          </button>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 20, color: BONE, lineHeight: 1 }}>Bali, Indonesia</h1>
              <div style={{ display: 'flex' }}>
                <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 20, height: 20, borderRadius: '50%', border: `1.5px solid ${BG}` }}/>
                <img src="https://i.pravatar.cc/80?img=32" alt="" style={{ width: 20, height: 20, borderRadius: '50%', border: `1.5px solid ${BG}`, marginLeft: -6 }}/>
              </div>
            </div>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, marginTop: 2 }}>Shared with Priya · Jun 14 – Jun 21</p>
          </div>
          <button onClick={() => setShare(true)} style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '7px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5 }}>
            <Share2 size={11} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.12em', color: GOLD }}>Export</span>
          </button>
        </div>

        {/* day tabs */}
        <div style={{ display: 'flex', overflowX: 'auto', scrollbarWidth: 'none' }}>
          {DAYS.map((d, i) => (
            <button key={d.day} onClick={() => setDay(i)} style={{
              padding: '10px 16px', background: 'none', border: 'none', cursor: 'pointer',
              borderBottom: `2px solid ${activeDay === i ? GOLD : 'transparent'}`,
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.12em',
              color: activeDay === i ? GOLD : MUTE, whiteSpace: 'nowrap', transition: 'color 0.2s',
            }}>
              Day {d.day}
            </button>
          ))}
        </div>
      </div>

      {/* content */}
      <div style={{ padding: '24px 20px 100px', position: 'relative', zIndex: 10 }}>
        <AnimatePresence mode="wait">
          <motion.div key={activeDay} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -14 }} transition={{ duration: 0.3, ease }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <div>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 4 }}>Day {day.day}</p>
                <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 22, color: BONE, lineHeight: 1.2 }}>{day.theme}</h2>
              </div>
              <button onClick={() => setAdd(true)} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '8px 14px', background: 'none', border: `1px solid rgba(212,182,134,0.22)`, borderRadius: 20, cursor: 'pointer' }}>
                <Plus size={11} style={{ color: GOLD }}/>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', color: GOLD }}>Add</span>
              </button>
            </div>

            {day.activities.map(act => (
              <ActivityCard key={act.id} activity={act} time={act.time} whyThis={act.why} addedBy={act.addedBy} onFeedback={fb => setFb(prev => [...prev.filter(f => f.activity_id !== fb.activity_id), fb])}/>
            ))}

            {feedback.length > 0 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <button style={{ width: '100%', padding: '15px 0', marginTop: 16, background: GOLD, border: 'none', borderRadius: 10, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: BG }}>
                  Sync Changes ({feedback.length})
                </button>
              </motion.div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* share bottom sheet */}
      <AnimatePresence>
        {shareOpen && (
          <>
            <motion.div key="share-bg" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShare(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 300 }}/>
            <motion.div key="share-sheet" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', damping: 30, stiffness: 260 }}
              style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, zIndex: 301, background: 'rgba(18,17,16,0.99)', borderRadius: '20px 20px 0 0', border: `1px solid rgba(232,212,168,0.10)`, borderBottom: 'none', padding: '12px 0 40px' }}>
              <div style={{ width: 36, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.14)', margin: '0 auto 20px' }}/>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 20, color: BONE, textAlign: 'center', marginBottom: 24 }}>Export itinerary</p>
              {[{ Icon: Mail, label: 'Send to both emails', sub: 'PDF sent to you and Priya' }, { Icon: Download, label: 'Download PDF', sub: 'Opens in your browser' }].map(({ Icon, label, sub }) => (
                <button key={label} onClick={() => setShare(false)} style={{ display: 'flex', alignItems: 'center', gap: 14, width: '100%', padding: '16px 28px', background: 'none', border: 'none', cursor: 'pointer', borderBottom: `1px solid rgba(232,212,168,0.07)` }}>
                  <Icon size={16} style={{ color: GOLD }}/>
                  <div style={{ textAlign: 'left' }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, color: BONE }}>{label}</p>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, marginTop: 2 }}>{sub}</p>
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
            <motion.div key="add-bg" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setAdd(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 300 }}/>
            <motion.div key="add-sheet" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', damping: 30, stiffness: 260 }}
              style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, zIndex: 301, background: 'rgba(18,17,16,0.99)', borderRadius: '20px 20px 0 0', border: `1px solid rgba(232,212,168,0.10)`, borderBottom: 'none', padding: '12px 24px 40px' }}>
              <div style={{ width: 36, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.14)', margin: '0 auto 20px' }}/>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 20, color: BONE, marginBottom: 20 }}>Add to Day {day.day}</p>
              <input value={newActivity} onChange={e => setNew(e.target.value)} placeholder="Activity name or place…" style={{ width: '100%', padding: '14px 16px', background: 'rgba(232,212,168,0.03)', border: `1px solid ${HAIRLINE}`, borderRadius: 10, color: BONE, outline: 'none', fontFamily: '"Inter Tight",sans-serif', fontSize: 14, boxSizing: 'border-box', marginBottom: 16 }}/>
              <button onClick={() => { setAdd(false); setNew('') }} style={{ width: '100%', padding: '15px 0', background: newActivity.trim() ? GOLD : 'rgba(212,182,134,0.08)', border: 'none', borderRadius: 10, cursor: newActivity.trim() ? 'pointer' : 'default', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: newActivity.trim() ? BG : MUTE }}>
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
