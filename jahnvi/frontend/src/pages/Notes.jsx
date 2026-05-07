import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, StickyNote } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GRAIN, ease } from '../lib/tokens'
import BottomNav from '../components/BottomNav'

const MOCK_NOTES = [
  { id: '1', content: 'Locavore NXT — book ahead, fills up 3+ weeks in advance.', timestamp: '2025-05-28T10:00:00', author: 'Priya', isOwn: false },
  { id: '2', content: 'Budget note: accommodation is $85/night so we should keep activities under $60/day each to stay on track.', timestamp: '2025-05-28T10:22:00', author: 'You', isOwn: true },
  { id: '3', content: 'Heard the Kecak dance at Uluwatu is best from row 3 — arrive 40 min early.', timestamp: '2025-05-29T09:14:00', author: 'Priya', isOwn: false },
  { id: '4', content: 'Also — check visa on arrival rules for Bali. Should be fine for Indian passports (30 days free) but let\'s confirm.', timestamp: '2025-05-30T14:05:00', author: 'You', isOwn: true },
]

function NoteItem({ note }) {
  const { content, timestamp, author, isOwn } = note
  const date = new Date(timestamp)
  const formatted = date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) + ' · ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: isOwn ? 'flex-end' : 'flex-start', marginBottom: 18 }}>
      {!isOwn && (
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.12em', color: MUTE, marginBottom: 5 }}>
          {author}
        </span>
      )}
      <div style={{
        maxWidth: '82%',
        padding: '13px 15px',
        borderRadius: isOwn ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
        background: isOwn
          ? 'linear-gradient(135deg,rgba(212,182,134,0.18) 0%,rgba(212,182,134,0.07) 100%)'
          : 'rgba(255,255,255,0.04)',
        border: `1px solid ${isOwn ? 'rgba(212,182,134,0.20)' : HAIRLINE}`,
      }}>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, lineHeight: 1.7, color: BONE, margin: 0 }}>
          {content}
        </p>
      </div>
      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM, marginTop: 4, paddingLeft: isOwn ? 0 : 2, paddingRight: isOwn ? 2 : 0 }}>
        {formatted}
      </span>
    </div>
  )
}

export default function Notes() {
  const navigate             = useNavigate()
  const [notes, setNotes]    = useState(MOCK_NOTES)
  const [input, setInput]    = useState('')
  const [activeTab, setTab]  = useState('notes')
  const bottomRef            = useRef(null)

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
  }

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', height: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14,
        padding: '52px 20px 16px',
        background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        borderBottom: `1px solid ${HAIRLINE}`, flexShrink: 0, position: 'relative', zIndex: 10,
      }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0 }}>
          <ArrowLeft size={20}/>
        </button>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 20, color: BONE, lineHeight: 1 }}>Notes</h1>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, marginTop: 2 }}>Bali · You & Priya</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 24, height: 24, borderRadius: '50%', border: `1.5px solid rgba(212,182,134,0.20)` }}/>
          <img src="https://i.pravatar.cc/80?img=32" alt="" style={{ width: 24, height: 24, borderRadius: '50%', border: `1.5px solid rgba(212,182,134,0.20)`, marginLeft: -8 }}/>
        </div>
      </div>

      {/* notes feed */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 20px 0', scrollbarWidth: 'none', position: 'relative', zIndex: 10 }}>
        {notes.length === 0 && (
          <div style={{ textAlign: 'center', paddingTop: 60 }}>
            <StickyNote size={28} style={{ color: MUTE, marginBottom: 12 }}/>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE }}>No notes yet. Add the first one.</p>
          </div>
        )}
        {notes.map(n => <NoteItem key={n.id} note={n}/>)}
        <div ref={bottomRef} style={{ height: 20 }}/>
      </div>

      {/* input */}
      <div style={{
        display: 'flex', alignItems: 'flex-end', gap: 10,
        padding: '12px 16px 80px',
        borderTop: `1px solid ${HAIRLINE}`,
        background: 'rgba(8,8,7,0.95)',
        flexShrink: 0, position: 'relative', zIndex: 10,
      }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); addNote() } }}
          placeholder="Add a note for your trip…"
          rows={1}
          style={{
            flex: 1, padding: '12px 14px',
            background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
            borderRadius: 16, color: BONE, outline: 'none', resize: 'none',
            fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300,
            lineHeight: 1.5, overflow: 'hidden',
          }}
          onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px' }}
        />
        <button
          onClick={addNote}
          style={{
            width: 40, height: 40, borderRadius: '50%', flexShrink: 0,
            background: input.trim() ? GOLD : 'rgba(212,182,134,0.08)',
            border: 'none', cursor: input.trim() ? 'pointer' : 'default',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'background 0.2s', marginBottom: 2,
          }}
        >
          <Send size={15} style={{ color: input.trim() ? BG : MUTE }}/>
        </button>
      </div>

      <BottomNav variant="itinerary" activeTab={activeTab} onTabChange={setTab}/>
    </div>
  )
}
