import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Share2, Mail, Download, Users } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import ActivityCard from '../components/ActivityCard'
import { SonderNavLogo } from '../components/SonderLogoSVG'

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
  const [shareOpen, setShare] = useState(false)
  const [addOpen, setAdd]     = useState(false)
  const [newActivity, setNew] = useState('')
  const [feedback, setFb]     = useState([])

  const day = DAYS[activeDay]

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* top nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <button onClick={() => navigate('/dashboard')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Dashboard</span>
        </button>
        <SonderNavLogo markHeight={32}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={() => setShare(true)} style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '8px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Share2 size={11} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD }}>Export</span>
          </button>
          <button style={{ background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 20, padding: '8px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Users size={11} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD }}>You & Priya</span>
          </button>
        </div>
      </nav>

      {/* destination header */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, padding: '36px 48px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 50% 150% at 80% 50%, rgba(212,182,134,0.07) 0%, transparent 65%)', pointerEvents: 'none' }}/>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>Shared itinerary</p>
            <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 48, color: BONE, lineHeight: 1, letterSpacing: '-0.02em' }}>
              Bali, Indonesia
            </h1>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE, marginBottom: 8 }}>Jun 14 – Jun 21 · 7 days</p>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
              <img src="https://i.pravatar.cc/80?img=32" alt="" style={{ width: 26, height: 26, borderRadius: '50%', border: `1.5px solid rgba(212,182,134,0.25)` }}/>
              <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 26, height: 26, borderRadius: '50%', border: `1.5px solid rgba(212,182,134,0.25)`, marginLeft: -10 }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>You & Priya M.</span>
            </div>
          </div>
        </div>
      </div>

      {/* day tab strip */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.6)', backdropFilter: 'blur(12px)' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex' }}>
          {DAYS.map((d, i) => (
            <button key={d.day} onClick={() => setDay(i)} style={{
              padding: '16px 28px', background: 'none', border: 'none', cursor: 'pointer',
              borderBottom: `2px solid ${activeDay === i ? GOLD : 'transparent'}`,
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.14em',
              color: activeDay === i ? GOLD : MUTE, whiteSpace: 'nowrap', transition: 'color 0.2s',
            }}>
              Day {d.day} — {d.theme}
            </button>
          ))}
        </div>
      </div>

      {/* content */}
      <div style={{ flex: 1, maxWidth: 1100, margin: '0 auto', width: '100%', padding: '0 48px' }}>
        <AnimatePresence mode="wait">
          <motion.div key={activeDay} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -14 }} transition={{ duration: 0.32, ease }}>

            <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 0 }}>
              {/* sidebar */}
              <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '48px 40px 48px 0', position: 'sticky', top: 64, alignSelf: 'start' }}>
                <div style={{ position: 'relative' }}>
                  <span style={{
                    fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
                    fontSize: 120, lineHeight: 1, letterSpacing: '-0.04em',
                    background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
                    opacity: 0.15, userSelect: 'none', display: 'block', marginBottom: -20,
                  }}>
                    {day.day}
                  </span>
                  <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 28, color: BONE, lineHeight: 1.2 }}>
                    {day.theme}
                  </h2>
                </div>
                <div style={{ marginTop: 32, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ padding: '12px 0', borderTop: `1px solid ${HAIRLINE}` }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 4 }}>Activities</p>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 14, fontWeight: 500, color: BONE }}>{day.activities.length}</p>
                  </div>
                  <div style={{ padding: '12px 0', borderTop: `1px solid ${HAIRLINE}` }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 4 }}>Added by</p>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 14, fontWeight: 500, color: BONE }}>You & Priya</p>
                  </div>
                </div>
                <button onClick={() => setAdd(true)} style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 6, padding: '10px 16px', background: 'none', border: `1px solid rgba(212,182,134,0.22)`, borderRadius: 10, cursor: 'pointer' }}>
                  <Plus size={12} style={{ color: GOLD }}/>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD }}>Add activity</span>
                </button>
              </div>

              {/* activity list */}
              <div style={{ padding: '48px 0 48px 48px' }}>
                {day.activities.map(act => (
                  <ActivityCard key={act.id} activity={act} time={act.time} whyThis={act.why} addedBy={act.addedBy}
                    onFeedback={fb => setFb(prev => [...prev.filter(f => f.activity_id !== fb.activity_id), fb])}/>
                ))}
                {feedback.length > 0 && (
                  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                    <button style={{ padding: '16px 32px', background: GOLD, border: 'none', borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: BG, boxShadow: '0 0 40px rgba(212,182,134,0.18)', marginTop: 8 }}>
                      Sync changes · {feedback.length}
                    </button>
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* share sheet */}
      <AnimatePresence>
        {shareOpen && (
          <>
            <motion.div key="sb" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShare(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 300 }}/>
            <motion.div key="ss" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', damping: 30, stiffness: 260 }}
              style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 520, zIndex: 301, background: 'rgba(18,17,16,0.99)', borderRadius: '20px 20px 0 0', border: `1px solid rgba(232,212,168,0.10)`, borderBottom: 'none', padding: '12px 0 44px' }}>
              <div style={{ width: 36, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.14)', margin: '0 auto 20px' }}/>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 26, color: BONE, textAlign: 'center', marginBottom: 32 }}>Export itinerary</p>
              {[
                { Icon: Mail, label: 'Send to both emails', sub: 'PDF sent to you and Priya' },
                { Icon: Download, label: 'Download PDF', sub: 'Opens in your browser' },
              ].map(({ Icon, label, sub }) => (
                <button key={label} onClick={() => setShare(false)} style={{ display: 'flex', alignItems: 'center', gap: 16, width: '100%', padding: '18px 32px', background: 'none', border: 'none', cursor: 'pointer', borderBottom: `1px solid rgba(232,212,168,0.07)` }}>
                  <div style={{ width: 40, height: 40, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.20)`, background: 'rgba(212,182,134,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Icon size={16} style={{ color: GOLD }}/>
                  </div>
                  <div style={{ textAlign: 'left' }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 14, color: BONE, marginBottom: 3 }}>{label}</p>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>{sub}</p>
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
              style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 520, zIndex: 301, background: 'rgba(18,17,16,0.99)', borderRadius: '20px 20px 0 0', border: `1px solid rgba(232,212,168,0.10)`, borderBottom: 'none', padding: '12px 32px 44px' }}>
              <div style={{ width: 36, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.14)', margin: '0 auto 20px' }}/>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 26, color: BONE, marginBottom: 28 }}>Add to Day {day.day}</p>
              <input value={newActivity} onChange={e => setNew(e.target.value)} placeholder="Place, activity, or idea…"
                style={{ width: '100%', padding: '0 0 16px', background: 'none', border: 'none', borderBottom: `1px solid rgba(212,182,134,0.35)`, color: BONE, outline: 'none', fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 24, boxSizing: 'border-box', marginBottom: 32 }}/>
              <button onClick={() => { setAdd(false); setNew('') }} style={{ width: '100%', padding: '16px 0', background: newActivity.trim() ? GOLD : 'rgba(212,182,134,0.08)', border: 'none', borderRadius: 12, cursor: newActivity.trim() ? 'pointer' : 'default', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: newActivity.trim() ? BG : MUTE }}>
                Add activity
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
