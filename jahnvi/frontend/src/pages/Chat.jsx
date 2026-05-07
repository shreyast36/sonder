import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, Check, MapPin } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'

const MOCK_MESSAGES = [
  { id: '1', content: "Hey! So excited about the Bali trip — I've been wanting to go for years.", timestamp: '2025-06-01T09:02:00', seen: true,  sender_name: 'Priya', isOwn: false },
  { id: '2', content: "Same!! Have you been to Ubud before? I'm thinking we base ourselves there for the first half.", timestamp: '2025-06-01T09:04:00', seen: true,  sender_name: '',      isOwn: true  },
  { id: '3', content: "No, first time! But Ubud sounds perfect — I love the idea of rice fields and temples over Seminyak beach clubs.", timestamp: '2025-06-01T09:06:00', seen: true,  sender_name: 'Priya', isOwn: false },
  { id: '4', content: "Exactly my vibe. Also the itinerary has us at Locavore NXT on day 1 — I cannot wait.", timestamp: '2025-06-01T09:08:00', seen: false, sender_name: '',      isOwn: true  },
]

const SUGGESTED_TOPICS = [
  "What's on your Bali bucket list?",
  'Are you a morning person or night owl traveller?',
  'Any dietary things I should know about?',
]

const COMPAT = [
  'Both prefer relaxed pace',
  'Matching mid-range budget',
  'Culture & food rank highest',
  'Same ideal trip length',
]

function Bubble({ message }) {
  const { content, isOwn, sender_name, timestamp, seen } = message
  const date = new Date(timestamp)
  const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: isOwn ? 'flex-end' : 'flex-start', marginBottom: 20 }}>
      {!isOwn && sender_name && (
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: MUTE, marginBottom: 5 }}>{sender_name}</span>
      )}
      <div style={{
        maxWidth: '78%', padding: '14px 18px',
        borderRadius: isOwn ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        background: isOwn
          ? 'linear-gradient(135deg, rgba(224,178,96,0.22) 0%, rgba(212,182,134,0.10) 60%, rgba(180,138,68,0.08) 100%)'
          : 'rgba(255,255,255,0.045)',
        border: `1px solid ${isOwn ? 'rgba(212,182,134,0.25)' : HAIRLINE}`,
        boxShadow: isOwn ? '0 4px 20px rgba(212,182,134,0.08)' : 'none',
      }}>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, lineHeight: 1.7, color: BONE, margin: 0 }}>
          {content}
        </p>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 4 }}>
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM }}>{timeStr}</span>
        {isOwn && seen && <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: GOLD, opacity: 0.6 }}>Seen</span>}
      </div>
    </div>
  )
}

export default function Chat() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState(MOCK_MESSAGES)
  const [input, setInput]       = useState('')
  const [typing, setTyping]     = useState(false)
  const [topicsVisible, setTv]  = useState(true)
  const bottomRef               = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  function send(text) {
    if (!text.trim()) return
    setMessages(prev => [...prev, { id: String(Date.now()), content: text, timestamp: new Date().toISOString(), seen: false, sender_name: '', isOwn: true }])
    setInput('')
    setTv(false)
    setTyping(true)
    setTimeout(() => {
      setTyping(false)
      setMessages(prev => [...prev, { id: String(Date.now() + 1), content: "That sounds amazing! Let's plan it.", timestamp: new Date().toISOString(), seen: false, sender_name: 'Priya', isOwn: false }])
    }, 2200)
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground />

      {/* nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8, transition: 'color 0.2s' }} onMouseEnter={e => { e.currentTarget.style.color = BONE }} onMouseLeave={e => { e.currentTarget.style.color = MUTE }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </button>
        <SonderNav3D markSize={32}/>
        <button onClick={() => navigate('/approve/1')} style={{ background: 'none', border: `1px solid rgba(212,182,134,0.28)`, borderRadius: 20, padding: '8px 18px', cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: GOLD, transition: 'all 0.2s' }} onMouseEnter={e => { e.currentTarget.style.background = 'rgba(212,182,134,0.08)'; e.currentTarget.style.boxShadow = '0 0 20px rgba(212,182,134,0.14)' }} onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.boxShadow = 'none' }}>
          Review match
        </button>
      </nav>

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '320px 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1, minHeight: 0 }}>

        {/* left sidebar */}
        <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '52px 44px', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 320, background: 'radial-gradient(ellipse 80% 60% at 30% 20%, rgba(212,182,134,0.09) 0%, transparent 65%)', pointerEvents: 'none' }}/>

          <motion.div
            animate={{ boxShadow: ['0 0 0 2px rgba(212,182,134,0.18), 0 0 28px rgba(212,182,134,0.08)', '0 0 0 2px rgba(212,182,134,0.38), 0 0 56px rgba(212,182,134,0.24)', '0 0 0 2px rgba(212,182,134,0.18), 0 0 28px rgba(212,182,134,0.08)'] }}
            transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut' }}
            style={{ width: 88, height: 88, borderRadius: '50%', overflow: 'hidden', marginBottom: 24 }}
          >
            <img src="https://i.pravatar.cc/200?img=47" alt="Priya" style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
          </motion.div>

          <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 34, color: BONE, lineHeight: 1, marginBottom: 8 }}>Priya Mehta</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 10 }}>
            <MapPin size={10} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>Mumbai, India</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, marginBottom: 36 }}>
            <motion.span
              animate={{ filter: ['drop-shadow(0 0 10px rgba(212,182,134,0.25))', 'drop-shadow(0 0 40px rgba(212,182,134,0.60))', 'drop-shadow(0 0 10px rgba(212,182,134,0.25))'] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
              style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 72, lineHeight: 0.88, background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent' }}
            >
              92
            </motion.span>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.45)', paddingBottom: 12 }}>% match</span>
          </div>

          <div style={{ height: 1, background: `linear-gradient(to right, transparent, ${HAIRLINE}, transparent)`, marginBottom: 28 }}/>

          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.24em', textTransform: 'uppercase', color: MUTE, marginBottom: 16 }}>In common</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 'auto' }}>
            {COMPAT.map((c, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 20, height: 20, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.22)`, background: 'rgba(212,182,134,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Check size={9} style={{ color: GOLD }}/>
                </div>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, color: BONE, lineHeight: 1.5 }}>{c}</span>
              </div>
            ))}
          </div>

          <AnimatePresence>
            {topicsVisible && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }} style={{ marginTop: 40 }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Try asking</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {SUGGESTED_TOPICS.map(t => (
                    <motion.button key={t} whileHover={{ x: 4, transition: { duration: 0.15 } }} onClick={() => send(t)}
                      style={{ padding: '11px 14px', borderRadius: 12, cursor: 'pointer', textAlign: 'left', fontFamily: '"Inter Tight",sans-serif', fontSize: 12, fontWeight: 300, lineHeight: 1.5, background: 'rgba(232,212,168,0.03)', border: `1px solid ${HAIRLINE}`, color: BONE, transition: 'border-color 0.2s, background 0.2s' }}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(232,212,168,0.22)'; e.currentTarget.style.background = 'rgba(232,212,168,0.06)' }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = HAIRLINE; e.currentTarget.style.background = 'rgba(232,212,168,0.03)' }}
                    >
                      {t}
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* right — messages + input */}
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 68px)', overflow: 'hidden' }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: '44px 52px 20px', scrollbarWidth: 'thin', scrollbarColor: `${HAIRLINE} transparent` }}>
            {messages.map(m => <Bubble key={m.id} message={m}/>)}
            <AnimatePresence>
              {typing && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 26, height: 26, borderRadius: '50%' }}/>
                  <div style={{ display: 'flex', gap: 5, padding: '12px 16px', borderRadius: '18px 18px 18px 4px', border: `1px solid ${HAIRLINE}`, background: 'rgba(255,255,255,0.04)' }}>
                    {[0, 1, 2].map(i => (
                      <motion.div key={i} animate={{ y: [0, -5, 0] }} transition={{ duration: 0.8, delay: i * 0.15, repeat: Infinity }} style={{ width: 5, height: 5, borderRadius: '50%', background: MUTE }}/>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <div ref={bottomRef}/>
          </div>

          <div style={{ borderTop: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.96)', padding: '18px 52px 26px', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && send(input)}
                placeholder="Message Priya…"
                style={{ flex: 1, padding: '14px 20px', background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`, borderRadius: 24, color: BONE, outline: 'none', fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300, transition: 'border-color 0.2s, box-shadow 0.2s' }}
                onFocus={e => { e.currentTarget.style.borderColor = 'rgba(212,182,134,0.45)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(212,182,134,0.08)' }}
                onBlur={e => { e.currentTarget.style.borderColor = HAIRLINE; e.currentTarget.style.boxShadow = 'none' }}
              />
              <button onClick={() => send(input)} style={{ width: 48, height: 48, borderRadius: '50%', flexShrink: 0, background: input.trim() ? GOLD : 'rgba(212,182,134,0.07)', border: 'none', cursor: input.trim() ? 'pointer' : 'default', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s', boxShadow: input.trim() ? '0 0 24px rgba(212,182,134,0.28)' : 'none' }}
                onMouseEnter={e => { if (input.trim()) e.currentTarget.style.boxShadow = '0 0 40px rgba(212,182,134,0.48)' }}
                onMouseLeave={e => { if (input.trim()) e.currentTarget.style.boxShadow = '0 0 24px rgba(212,182,134,0.28)' }}
              >
                <Send size={16} style={{ color: input.trim() ? BG : MUTE }}/>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
