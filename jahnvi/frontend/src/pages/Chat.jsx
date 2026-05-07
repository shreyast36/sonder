import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Send, Check, MapPin } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import ChatBubble from '../components/ChatBubble'
import { SonderNavLogo } from '../components/SonderLogoSVG'

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

const COMPATIBILITY = [
  'Both prefer relaxed pace',
  'Matching mid-range budget',
  'Culture & food rank highest',
  'Same ideal trip length',
]

export default function Chat() {
  const navigate       = useNavigate()
  const { sessionId }  = useParams()
  const [messages, setMessages] = useState(MOCK_MESSAGES)
  const [input, setInput]       = useState('')
  const [typing, setTyping]     = useState(false)
  const [topicsVisible, setTv]  = useState(true)
  const bottomRef               = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function send(text) {
    if (!text.trim()) return
    setMessages(prev => [...prev, {
      id: String(Date.now()), content: text,
      timestamp: new Date().toISOString(), seen: false, sender_name: '', isOwn: true,
    }])
    setInput('')
    setTv(false)
    setTyping(true)
    setTimeout(() => {
      setTyping(false)
      setMessages(prev => [...prev, {
        id: String(Date.now() + 1),
        content: "That sounds amazing! Let's plan it.",
        timestamp: new Date().toISOString(),
        seen: false, sender_name: 'Priya', isOwn: false,
      }])
    }, 2200)
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* top nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </button>
        <SonderNavLogo markHeight={32}/>
        <button onClick={() => navigate('/approve/1')} style={{ background: 'none', border: `1px solid rgba(212,182,134,0.28)`, borderRadius: 20, padding: '8px 18px', cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: GOLD }}>
          Review match
        </button>
      </nav>

      {/* 2-column layout */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '320px 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', minHeight: 0 }}>

        {/* left sidebar — profile + context */}
        <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '48px 40px', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 300, background: 'radial-gradient(ellipse 80% 60% at 30% 20%, rgba(212,182,134,0.08) 0%, transparent 65%)', pointerEvents: 'none' }}/>

          <img src="https://i.pravatar.cc/200?img=47" alt="Priya" style={{ width: 80, height: 80, borderRadius: '50%', objectFit: 'cover', border: `1.5px solid rgba(212,182,134,0.22)`, marginBottom: 20 }}/>

          <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 32, color: BONE, lineHeight: 1, marginBottom: 6 }}>Priya Mehta</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 8 }}>
            <MapPin size={10} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>Mumbai, India</span>
          </div>

          {/* match score */}
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, marginBottom: 32 }}>
            <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 64, lineHeight: 0.9, background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent' }}>92</span>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(212,182,134,0.45)', paddingBottom: 10 }}>% match</span>
          </div>

          <div style={{ height: 1, background: HAIRLINE, marginBottom: 28 }}/>

          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.24em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Why you match</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 'auto' }}>
            {COMPATIBILITY.map((c, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 18, height: 18, borderRadius: '50%', border: `1px solid rgba(212,182,134,0.20)`, background: 'rgba(212,182,134,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Check size={9} style={{ color: GOLD }}/>
                </div>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, color: BONE, lineHeight: 1.5 }}>{c}</span>
              </div>
            ))}
          </div>

          {/* suggested topics */}
          <AnimatePresence>
            {topicsVisible && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }} style={{ marginTop: 36 }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>Try asking</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {SUGGESTED_TOPICS.map(t => (
                    <button key={t} onClick={() => send(t)} style={{
                      padding: '10px 14px', borderRadius: 12, cursor: 'pointer', textAlign: 'left',
                      fontFamily: '"Inter Tight",sans-serif', fontSize: 12, fontWeight: 300, lineHeight: 1.5,
                      background: 'rgba(232,212,168,0.03)', border: `1px solid ${HAIRLINE}`, color: BONE,
                      transition: 'border-color 0.2s',
                    }}>
                      {t}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* right — chat feed + input */}
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
          {/* messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '40px 48px 20px', scrollbarWidth: 'thin', scrollbarColor: `${HAIRLINE} transparent` }}>
            {messages.map(m => <ChatBubble key={m.id} message={m} isOwn={m.isOwn}/>)}
            <AnimatePresence>
              {typing && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 24, height: 24, borderRadius: '50%' }}/>
                  <div style={{ display: 'flex', gap: 4, padding: '10px 14px', borderRadius: '18px 18px 18px 4px', border: `1px solid ${HAIRLINE}`, background: 'rgba(255,255,255,0.04)' }}>
                    {[0, 1, 2].map(i => (
                      <motion.div key={i}
                        animate={{ y: [0, -4, 0] }}
                        transition={{ duration: 0.8, delay: i * 0.15, repeat: Infinity }}
                        style={{ width: 5, height: 5, borderRadius: '50%', background: MUTE }}
                      />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <div ref={bottomRef}/>
          </div>

          {/* input bar */}
          <div style={{ borderTop: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.96)', padding: '16px 48px 24px', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && send(input)}
                placeholder="Message Priya…"
                style={{
                  flex: 1, padding: '14px 20px',
                  background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
                  borderRadius: 24, color: BONE, outline: 'none',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300,
                  transition: 'border-color 0.2s',
                }}
              />
              <button
                onClick={() => send(input)}
                style={{
                  width: 46, height: 46, borderRadius: '50%', flexShrink: 0,
                  background: input.trim() ? GOLD : 'rgba(212,182,134,0.08)',
                  border: 'none', cursor: input.trim() ? 'pointer' : 'default',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'background 0.2s',
                  boxShadow: input.trim() ? '0 0 20px rgba(212,182,134,0.20)' : 'none',
                }}
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
