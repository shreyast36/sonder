import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, Plus, Zap } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import MatchCard from '../components/MatchCard'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import { useAuth } from '../hooks/useAuth'
import { storage } from '../lib/firebase'
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage'
import { updateProfile } from 'firebase/auth'
import { auth } from '../lib/firebase'

// vivid amber — Dashboard accent
const AMBER = '#F59E0B'

function useCountUp(target, duration = 1200, delay = 300) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    const timer = setTimeout(() => {
      const start = performance.now()
      const tick = now => {
        const p = Math.min((now - start) / duration, 1)
        const ease = 1 - Math.pow(1 - p, 3)
        setCount(Math.round(ease * target))
        if (p < 1) requestAnimationFrame(tick)
      }
      requestAnimationFrame(tick)
    }, delay)
    return () => clearTimeout(timer)
  }, [target, duration, delay])
  return count
}

const MOCK_MATCHES = [
  { id: '1', display_name: 'Priya Mehta',  location: 'Mumbai, India',    match_score: 92, tags: ['Relaxed', 'Culture', 'Mid-range'],  avatar_url: 'https://i.pravatar.cc/80?img=47' },
  { id: '2', display_name: 'Arjun Nair',   location: 'Bangalore, India', match_score: 87, tags: ['Adventure', 'Mid-range', 'Foodie'], avatar_url: 'https://i.pravatar.cc/80?img=12' },
]

const spring = { type: 'spring', stiffness: 280, damping: 22 }
const stagger = { show: { transition: { staggerChildren: 0.10 } } }
const reveal  = { hidden: { opacity: 0, y: 28 }, show: { opacity: 1, y: 0, transition: { duration: 0.7, ease } } }

export default function Dashboard() {
  const navigate  = useNavigate()
  const { user, signOut }  = useAuth()
  const daysAway  = useCountUp(18, 1000, 600)

  const firstName   = user?.displayName?.split(' ')[0] ?? 'Traveller'
  const hour        = new Date().getHours()
  const greeting    = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  const fileInputRef  = useRef(null)
  const [uploading, setUploading]   = useState(false)
  const [photoURL, setPhotoURL]     = useState(user?.photoURL ?? null)
  const [dropdownOpen, setDropdown] = useState(false)

  async function handleAvatarChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const storageRef = ref(storage, `avatars/${auth.currentUser.uid}`)
      await uploadBytes(storageRef, file)
      const url = await getDownloadURL(storageRef)
      await updateProfile(auth.currentUser, { photoURL: url })
      setPhotoURL(url)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent="#F59E0B" />

      {/* nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <SonderNav3D markSize={32}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <motion.button
            whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }}
            onClick={() => navigate('/preferences')}
            style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.20em', textTransform: 'uppercase', color: MUTE, background: 'none', border: 'none', cursor: 'pointer', transition: 'color 0.2s' }}
            onMouseEnter={e => { e.currentTarget.style.color = BONE }}
            onMouseLeave={e => { e.currentTarget.style.color = MUTE }}
          >
            New trip
          </motion.button>
          <div style={{ position: 'relative' }}>
            <div style={{ cursor: 'pointer' }} onClick={() => setDropdown(o => !o)}>
              <motion.img
                whileHover={{ scale: 1.08, boxShadow: '0 0 0 2px rgba(245,158,11,0.50), 0 0 32px rgba(245,158,11,0.28)' }}
                whileTap={{ scale: 0.95 }}
                transition={spring}
                src={photoURL ?? 'https://i.pravatar.cc/80?img=32'} alt="You"
                style={{ width: 34, height: 34, borderRadius: '50%', objectFit: 'cover', border: `1.5px solid rgba(212,182,134,0.30)`, cursor: 'pointer', boxShadow: '0 0 20px rgba(212,182,134,0.12)', opacity: uploading ? 0.5 : 1, transition: 'opacity 0.2s', display: 'block' }}
              />
              {uploading && (
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%' }}>
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                    style={{ width: 14, height: 14, border: '2px solid transparent', borderTopColor: GOLD, borderRadius: '50%' }}/>
                </div>
              )}
            </div>
            <AnimatePresence>
              {dropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ duration: 0.18, ease }}
                  style={{ position: 'absolute', top: 44, right: 0, minWidth: 190, background: 'rgba(18,15,10,0.96)', border: `1px solid ${HAIRLINE}`, borderRadius: 12, overflow: 'hidden', backdropFilter: 'blur(20px)', boxShadow: '0 16px 48px rgba(0,0,0,0.5)', zIndex: 100 }}
                >
                  {[
                    { label: 'Change profile picture', action: () => { setDropdown(false); fileInputRef.current?.click() } },
                    { label: 'Sign out', action: () => { setDropdown(false); signOut().then(() => navigate('/')) } },
                  ].map(({ label, action }) => (
                    <button key={label} onClick={action}
                      style={{ width: '100%', padding: '14px 18px', background: 'none', border: 'none', textAlign: 'left', fontFamily: '"Inter Tight",sans-serif', fontSize: 12, letterSpacing: '0.04em', color: MUTE, cursor: 'pointer', transition: 'all 0.15s', display: 'block' }}
                      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(232,212,168,0.06)'; e.currentTarget.style.color = BONE }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = MUTE }}
                    >
                      {label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
            <input ref={fileInputRef} type="file" accept="image/*" onChange={handleAvatarChange} style={{ display: 'none' }}/>
          </div>
        </div>
      </nav>

      {/* greeting */}
      <div style={{ borderBottom: `1px solid ${HAIRLINE}`, padding: '44px 48px 40px', position: 'relative', zIndex: 1, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'radial-gradient(ellipse 70% 140% at 15% 60%, rgba(212,182,134,0.09) 0%, transparent 65%)', pointerEvents: 'none' }}/>
        <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>{greeting}</p>
          <motion.h1
            animate={{ filter: ['drop-shadow(0 0 24px rgba(212,182,134,0.20))', 'drop-shadow(0 0 56px rgba(212,182,134,0.50))', 'drop-shadow(0 0 24px rgba(212,182,134,0.20))'] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
            style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 68, lineHeight: 0.95, letterSpacing: '-0.02em', background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'inline-block' }}
          >
            {firstName}
          </motion.h1>
        </motion.div>
      </div>

      {/* main grid */}
      <motion.div variants={stagger} initial="hidden" animate="show"
        style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.4fr 1fr', maxWidth: 1240, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>

        {/* LEFT — trip card */}
        <motion.div variants={reveal} style={{ padding: '52px 52px', borderRight: `1px solid ${HAIRLINE}` }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 24 }}>Upcoming Trip</p>

          <motion.div
            onClick={() => navigate('/itinerary')}
            whileHover={{ y: -6, transition: spring }}
            whileTap={{ scale: 0.99 }}
            style={{ cursor: 'pointer', padding: 1, borderRadius: 26, background: 'linear-gradient(145deg,rgba(232,212,168,0.30) 0%,rgba(8,8,7,0) 50%,rgba(232,212,168,0.12) 100%)', boxShadow: '0 24px 72px rgba(0,0,0,0.55), 0 4px 16px rgba(0,0,0,0.30), inset 0 1px 0 rgba(232,212,168,0.10)' }}
          >
            <div style={{ background: 'linear-gradient(160deg,rgba(24,20,13,0.99) 0%,rgba(14,11,8,1) 100%)', borderRadius: 25, padding: '40px 40px 32px', position: 'relative', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', top: -80, right: -80, width: 360, height: 360, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(245,158,11,0.12) 0%, rgba(212,182,134,0.06) 45%, transparent 70%)', pointerEvents: 'none' }}/>
              <div style={{ position: 'absolute', bottom: -40, left: -40, width: 240, height: 240, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(180,138,68,0.08) 0%, transparent 65%)', pointerEvents: 'none' }}/>

              {/* live dot */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 16 }}>
                <motion.div
                  animate={{ opacity: [1, 0.3, 1], scale: [1, 1.3, 1] }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ width: 6, height: 6, borderRadius: '50%', background: AMBER, boxShadow: `0 0 8px ${AMBER}` }}
                />
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'rgba(245,158,11,0.70)' }}>Upcoming</span>
              </div>

              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.50)', marginBottom: 10, position: 'relative' }}>Destination</p>
              <motion.h2
                animate={{ filter: ['drop-shadow(0 0 16px rgba(212,182,134,0.28))', 'drop-shadow(0 0 48px rgba(212,182,134,0.65))', 'drop-shadow(0 0 16px rgba(212,182,134,0.28))'] }}
                transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
                style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 96, lineHeight: 0.85, letterSpacing: '-0.03em', background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'block', marginBottom: 8, position: 'relative' }}
              >
                Bali
              </motion.h2>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.32em', textTransform: 'uppercase', color: MUTE, marginBottom: 36, position: 'relative' }}>Indonesia</p>

              <div style={{ height: 1, background: `linear-gradient(to right, ${HAIRLINE}, rgba(232,212,168,0.20), ${HAIRLINE})`, marginBottom: 28 }}/>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 0, position: 'relative' }}>
                {[
                  { label: 'Departs',   value: 'Jun 14', accent: false },
                  { label: 'Returns',   value: 'Jun 21', accent: false },
                  { label: 'Duration',  value: '7 days', accent: false },
                  { label: 'Days away', value: daysAway, accent: true  },
                ].map(({ label, value, accent }, i) => (
                  <div key={label} style={{ borderRight: i < 3 ? `1px solid ${HAIRLINE}` : 'none', paddingRight: 20, paddingLeft: i > 0 ? 20 : 0 }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>{label}</p>
                    {accent ? (
                      <motion.p
                        animate={{ filter: [`drop-shadow(0 0 8px ${AMBER}88)`, `drop-shadow(0 0 20px ${AMBER}cc)`, `drop-shadow(0 0 8px ${AMBER}88)`] }}
                        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                        style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 28, fontWeight: 400, color: AMBER, lineHeight: 1 }}
                      >
                        {value}
                      </motion.p>
                    ) : (
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 16, fontWeight: 500, color: BONE }}>{value}</p>
                    )}
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 28, paddingTop: 22, borderTop: `1px solid ${HAIRLINE}`, position: 'relative' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 28, height: 28, borderRadius: '50%', border: `1.5px solid rgba(212,182,134,0.30)`, boxShadow: '0 0 12px rgba(212,182,134,0.15)' }}/>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>Travelling with Priya M.</span>
                </div>
                <motion.div whileHover={{ x: 4 }} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: GOLD }}>View itinerary</span>
                  <ChevronRight size={12} style={{ color: GOLD }}/>
                </motion.div>
              </div>
            </div>
          </motion.div>
        </motion.div>

        {/* RIGHT — companions + new trip */}
        <motion.div variants={reveal} style={{ padding: '52px 44px', display: 'flex', flexDirection: 'column', gap: 36 }}>

          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 24 }}>
              <div>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>Curated for you</p>
                <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 30, color: BONE, lineHeight: 1 }}>Your fellow traveller recommendations</h2>
              </div>
              <motion.button
                whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.94 }}
                onClick={() => navigate('/discover')}
                style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.16em', textTransform: 'uppercase', color: GOLD, background: 'none', border: 'none', cursor: 'pointer' }}
              >
                View all
              </motion.button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {MOCK_MATCHES.map((m, i) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, x: 24 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.4 + i * 0.12, ease }}
                >
                  <MatchCard match={m} onClick={() => navigate(`/match/${m.id}`)}/>
                </motion.div>
              ))}
            </div>
          </div>

          <div style={{ height: 1, background: `linear-gradient(to right, transparent, ${HAIRLINE}, transparent)` }}/>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 16 }}>
              <Zap size={12} style={{ color: AMBER }}/>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE }}>Ready for more?</p>
            </div>
            <motion.button
              whileHover={{ y: -3, boxShadow: '0 0 40px rgba(245,158,11,0.18), inset 0 1px 0 rgba(245,158,11,0.12)', borderColor: 'rgba(245,158,11,0.35)', transition: spring }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/preferences')}
              style={{
                width: '100%', padding: '20px 0',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                background: 'rgba(245,158,11,0.04)', border: `1px solid rgba(245,158,11,0.20)`,
                borderRadius: 16, cursor: 'pointer', transition: 'all 0.25s',
              }}
            >
              <Plus size={13} style={{ color: AMBER }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: AMBER }}>Plan a new trip</span>
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}
