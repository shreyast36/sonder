import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Send } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import BottomNav from '../components/BottomNav'

const MOCK_NOTES = [
  { id: '1', content: 'Locavore NXT fills up 3+ weeks ahead. Already have a reservation.', timestamp: '2025-05-28T10:00:00', author: 'Priya', isOwn: false },
  { id: '2', content: 'Budget check: accommodation is $85/night — keep activities under $60/day each to stay on track.', timestamp: '2025-05-28T10:22:00', author: 'You', isOwn: true },
  { id: '3', content: 'Kecak dance at Uluwatu — best view from row 3. Arrive 40 min early.', timestamp: '2025-05-29T09:14:00', author: 'Priya', isOwn: false },
  { id: '4', content: 'Visa on arrival for Indian passports: 30 days, free. Confirmed.', timestamp: '2025-05-30T14:05:00', author: 'You', isOwn: true },
]

function NoteItem({ note }) {
  const { content, timestamp, author, isOwn } = note
  const date = new Date(timestamp)
  const dateStr = date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
  const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: isOwn ? 'flex-end' : 'flex-start', marginBottom: 22 }}>
      {!isOwn && (
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>{author}</span>
      )}
      <div style={{
        maxWidth: '84%',
        padding: '15px 17px',
        borderRadius: isOwn ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        background: isOwn
          ? 'linear-gradient(135deg,rgba(212,182,134,0.16) 0%,rgba(212,182,134,0.06) 100%)'
          : 'rgba(255,255,255,0.04)',
        border: `1px solid ${isOwn ? 'rgba(212,182,134,0.18)' : HAIRLINE}`,
      }}>
        <p style={{
          fontFamily: '"Inter Tight",sans-serif', fontWeight: 300,
          fontSize: 13, lineHeight: 1.75, color: BONE, margin: 0,
        }}>
          {content}
        </p>
      </div>
      <span style={{
        fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM,
        marginTop: 5, paddingLeft: isOwn ? 0 : 2, paddingRight: isOwn ? 2 : 0,
      }}>
        {dateStr} · {timeStr}
      </span>
    </div>
  )
}

export default function Notes() {
  const navigate            = useNavigate()
  const [notes, setNotes]   = useState(MOCK_NOTES)
  const [input, setInput]   = useState('')
  const [activeTab, setTab] = useState('notes')
  const bottomRef           = useRef(null)
  const textareaRef         = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [notes])

  function addNote() {
    if (!input.trim()) return
    setNotes(prev => [...prev, {
      id: String(Date.now()), content: input,
      timestamp: new Date().toISOString(), author: 'You', isOwn: true,
    }])
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', height: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* header */}
      <div style={{ padding: '52px 24px 20px', background: 'rgba(8,8,7,0.94)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', borderBottom: `1px solid ${HAIRLINE}`, flexShrink: 0, position: 'relative', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0 }}>
            <ArrowLeft size={20}/>
          </button>
          <div style={{ flex: 1 }}>
            <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 22, color: BONE, lineHeight: 1 }}>Trip Notes</h1>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, marginTop: 3 }}>Bali · You & Priya</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <img src="https://i.pravatar.cc/80?img=32" alt="" style={{ width: 28, height: 28, borderRadius: '50%', border: `2px solid ${BG}`, objectFit: 'cover' }}/>
            <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 28, height: 28, borderRadius: '50%', border: `2px solid ${BG}`, marginLeft: -10, objectFit: 'cover' }}/>
          </div>
        </div>
      </div>

      {/* notes feed */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px 12px', scrollbarWidth: 'none', position: 'relative', zIndex: 10 }}>
        {notes.length === 0 && (
          <div style={{ textAlign: 'center', paddingTop: 60 }}>
            <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: MUTE }}>No notes yet.</p>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, color: DIM, marginTop: 8 }}>Add the first one below.</p>
          </div>
        )}
        {notes.map(n => <NoteItem key={n.id} note={n}/>)}
        <div ref={bottomRef}/>
      </div>

      {/* input */}
      <div style={{ borderTop: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.96)', flexShrink: 0, position: 'relative', zIndex: 10, paddingBottom: 80 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, padding: '12px 16px' }}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); addNote() } }}
            onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px' }}
            placeholder="Add a note…"
            rows={1}
            style={{
              flex: 1, padding: '12px 14px',
              background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
              borderRadius: 18, color: BONE, outline: 'none', resize: 'none',
              fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300,
              lineHeight: 1.55, overflow: 'hidden',
            }}
          />
          <button onClick={addNote} style={{
            width: 40, height: 40, borderRadius: '50%', flexShrink: 0,
            background: input.trim() ? GOLD : 'rgba(212,182,134,0.08)',
            border: 'none', cursor: input.trim() ? 'pointer' : 'default',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'background 0.2s', marginBottom: 2,
            boxShadow: input.trim() ? '0 0 20px rgba(212,182,134,0.20)' : 'none',
          }}>
            <Send size={15} style={{ color: input.trim() ? BG : MUTE }}/>
          </button>
        </div>
      </div>

      <BottomNav variant="itinerary" activeTab={activeTab} onTabChange={setTab}/>
    </div>
  )
}
