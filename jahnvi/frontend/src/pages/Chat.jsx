import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Send } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GRAIN, ease } from '../lib/tokens'
import ChatBubble from '../components/ChatBubble'

const MOCK_MESSAGES = [
  { id: '1', content: "Hey! So excited about the Bali trip — I've been wanting to go for years.", timestamp: '2025-06-01T09:02:00', seen: true,  sender_name: 'Priya', isOwn: false },
  { id: '2', content: "Same!! Have you been to Ubud before? I'm thinking we base ourselves there for the first half.", timestamp: '2025-06-01T09:04:00', seen: true,  sender_name: '',      isOwn: true  },
  { id: '3', content: "No, first time! But Ubud sounds perfect — I love the idea of rice fields and temples over Seminyak beach clubs.", timestamp: '2025-06-01T09:06:00', seen: true,  sender_name: 'Priya', isOwn: false },
  { id: '4', content: "Exactly my vibe. Also the itinerary has us at Locavore NXT on day 1 — I cannot wait.", timestamp: '2025-06-01T09:08:00', seen: false, sender_name: '',      isOwn: true  },
]

const SUGGESTED_TOPICS = [
  'What's on your Bali bucket list?',
  'Are you a morning person or night owl traveller?',
  'Any dietary things I should know about?',
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
    const msg = {
      id: String(Date.now()), content: text,
      timestamp: new Date().toISOString(), seen: false, sender_name: '', isOwn: true,
    }
    setMessages(prev => [...prev, msg])
    setInput('')
    setTv(false)

    // simulate reply
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
    <div style={{ maxWidth: 430, margin: '0 auto', height: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '52px 20px 16px',
        background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(16px)',
        borderBottom: `1px solid ${HAIRLINE}`, flexShrink: 0, position: 'relative', zIndex: 10,
      }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0 }}>
          <ArrowLeft size={20}/>
        </button>
        <img src="https://i.pravatar.cc/80?img=47" alt="Priya" style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover' }}/>
        <div style={{ flex: 1 }}>
          <p style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 17, color: BONE, lineHeight: 1 }}>Priya Mehta</p>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: MUTE, marginTop: 2 }}>Bali trip · 92% match</p>
        </div>
        <button
          onClick={() => navigate('/approve/1')}
          style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD, background: 'none', border: `1px solid rgba(212,182,134,0.25)`, borderRadius: 20, padding: '6px 12px', cursor: 'pointer' }}
        >
          Approve
        </button>
      </div>

      {/* messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 20px 0', position: 'relative', zIndex: 10, scrollbarWidth: 'none' }}>
        {messages.map(m => <ChatBubble key={m.id} message={m} isOwn={m.isOwn}/>)}

        {/* typing indicator */}
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

      {/* suggested topics */}
      <AnimatePresence>
        {topicsVisible && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
            style={{ padding: '12px 20px 0', position: 'relative', zIndex: 10, flexShrink: 0 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, marginBottom: 8 }}>Suggested</p>
            <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 8, scrollbarWidth: 'none' }}>
              {SUGGESTED_TOPICS.map(t => (
                <button key={t} onClick={() => send(t)} style={{
                  flexShrink: 0, padding: '8px 14px', borderRadius: 20, cursor: 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 11, fontWeight: 300, lineHeight: 1.4,
                  background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
                  color: BONE, maxWidth: 200, textAlign: 'left', whiteSpace: 'normal',
                }}>
                  {t}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* input bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '12px 16px 32px',
        borderTop: `1px solid ${HAIRLINE}`,
        background: 'rgba(8,8,7,0.95)',
        flexShrink: 0, position: 'relative', zIndex: 10,
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send(input)}
          placeholder="Message Priya…"
          style={{
            flex: 1, padding: '12px 14px',
            background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
            borderRadius: 22, color: BONE, outline: 'none',
            fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300,
          }}
        />
        <button
          onClick={() => send(input)}
          style={{
            width: 40, height: 40, borderRadius: '50%', flexShrink: 0,
            background: input.trim() ? GOLD : 'rgba(212,182,134,0.08)',
            border: 'none', cursor: input.trim() ? 'pointer' : 'default',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'background 0.2s',
          }}
        >
          <Send size={15} style={{ color: input.trim() ? BG : MUTE }}/>
        </button>
      </div>
    </div>
  )
}
