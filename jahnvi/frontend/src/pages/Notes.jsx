import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, MapPin, Calendar } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import { SonderNavLogo } from '../components/SonderLogoSVG'

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
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: isOwn ? 'flex-end' : 'flex-start', marginBottom: 24 }}>
      {!isOwn && (
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>{author}</span>
      )}
      <div style={{
        maxWidth: '80%',
        padding: '16px 20px',
        borderRadius: isOwn ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        background: isOwn
          ? 'linear-gradient(135deg,rgba(212,182,134,0.16) 0%,rgba(212,182,134,0.06) 100%)'
          : 'rgba(255,255,255,0.04)',
        border: `1px solid ${isOwn ? 'rgba(212,182,134,0.18)' : HAIRLINE}`,
      }}>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, lineHeight: 1.75, color: BONE, margin: 0 }}>
          {content}
        </p>
      </div>
      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM, marginTop: 5, paddingLeft: isOwn ? 0 : 2, paddingRight: isOwn ? 2 : 0 }}>
        {dateStr} · {timeStr}
      </span>
    </div>
  )
}

export default function Notes() {
  const navigate            = useNavigate()
  const [notes, setNotes]   = useState(MOCK_NOTES)
  const [input, setInput]   = useState('')
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
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* top nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </button>
        <SonderNavLogo markHeight={32}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: -6 }}>
          <img src="https://i.pravatar.cc/80?img=32" alt="" style={{ width: 30, height: 30, borderRadius: '50%', border: `2px solid ${BG}`, objectFit: 'cover', zIndex: 2 }}/>
          <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 30, height: 30, borderRadius: '50%', border: `2px solid ${BG}`, objectFit: 'cover', marginLeft: -10 }}/>
        </div>
      </nav>

      {/* 2-column layout */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '300px 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', minHeight: 0 }}>

        {/* left sidebar — trip context */}
        <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '48px 40px', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 280, background: 'radial-gradient(ellipse 80% 60% at 30% 20%, rgba(212,182,134,0.08) 0%, transparent 65%)', pointerEvents: 'none' }}/>

          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>Trip Notes</p>
          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 40, color: BONE, lineHeight: 1, marginBottom: 6, letterSpacing: '-0.02em' }}>
            Bali
          </h1>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.20em', textTransform: 'uppercase', color: MUTE, marginBottom: 32 }}>Indonesia</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            <div style={{ padding: '14px 0', borderTop: `1px solid ${HAIRLINE}`, display: 'flex', alignItems: 'center', gap: 10 }}>
              <Calendar size={12} style={{ color: GOLD, flexShrink: 0 }}/>
              <div>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 2 }}>Dates</p>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>Jun 14 – Jun 21</p>
              </div>
            </div>
            <div style={{ padding: '14px 0', borderTop: `1px solid ${HAIRLINE}`, display: 'flex', alignItems: 'center', gap: 10 }}>
              <MapPin size={12} style={{ color: GOLD, flexShrink: 0 }}/>
              <div>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 2 }}>Travellers</p>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>You & Priya M.</p>
              </div>
            </div>
            <div style={{ padding: '14px 0', borderTop: `1px solid ${HAIRLINE}` }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 2 }}>Notes</p>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{notes.length} shared</p>
            </div>
          </div>

          {/* note stats decorative */}
          <div style={{ marginTop: 'auto', paddingTop: 32 }}>
            <span style={{
              fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
              fontSize: 120, lineHeight: 0.85, letterSpacing: '-0.04em',
              background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
              opacity: 0.10, userSelect: 'none', display: 'block',
            }}>
              {notes.length}
            </span>
          </div>
        </div>

        {/* right — notes feed + input */}
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
          {/* notes feed */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '40px 48px 20px', scrollbarWidth: 'thin', scrollbarColor: `${HAIRLINE} transparent` }}>
            {notes.length === 0 && (
              <div style={{ textAlign: 'center', paddingTop: 80 }}>
                <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 26, color: MUTE }}>No notes yet.</p>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: DIM, marginTop: 8 }}>Add the first one below.</p>
              </div>
            )}
            {notes.map(n => <NoteItem key={n.id} note={n}/>)}
            <div ref={bottomRef}/>
          </div>

          {/* input */}
          <div style={{ borderTop: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.96)', padding: '16px 48px 24px', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12 }}>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); addNote() } }}
                onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px' }}
                placeholder="Add a note…"
                rows={1}
                style={{
                  flex: 1, padding: '14px 18px',
                  background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
                  borderRadius: 18, color: BONE, outline: 'none', resize: 'none',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 14, fontWeight: 300,
                  lineHeight: 1.55, overflow: 'hidden',
                }}
              />
              <button onClick={addNote} style={{
                width: 46, height: 46, borderRadius: '50%', flexShrink: 0,
                background: input.trim() ? GOLD : 'rgba(212,182,134,0.08)',
                border: 'none', cursor: input.trim() ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'background 0.2s', marginBottom: 2,
                boxShadow: input.trim() ? '0 0 20px rgba(212,182,134,0.20)' : 'none',
              }}>
                <Send size={16} style={{ color: input.trim() ? BG : MUTE }}/>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
