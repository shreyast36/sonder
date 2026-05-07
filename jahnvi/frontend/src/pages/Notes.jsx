import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, Calendar, MapPin } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'

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
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease }}
      style={{ display: 'flex', flexDirection: 'column', alignItems: isOwn ? 'flex-end' : 'flex-start', marginBottom: 26 }}
    >
      {!isOwn && (
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: MUTE, marginBottom: 6 }}>{author}</span>
      )}
      <div style={{
        maxWidth: '78%', padding: '16px 20px',
        borderRadius: isOwn ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
        background: isOwn
          ? 'linear-gradient(135deg, rgba(224,178,96,0.20) 0%, rgba(212,182,134,0.09) 60%, rgba(180,138,68,0.07) 100%)'
          : 'rgba(255,255,255,0.04)',
        border: `1px solid ${isOwn ? 'rgba(212,182,134,0.22)' : HAIRLINE}`,
        boxShadow: isOwn ? '0 4px 20px rgba(212,182,134,0.07), inset 0 1px 0 rgba(232,212,168,0.08)' : 'none',
      }}>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, lineHeight: 1.75, color: BONE, margin: 0 }}>
          {content}
        </p>
      </div>
      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM, marginTop: 5, paddingLeft: isOwn ? 0 : 2, paddingRight: isOwn ? 2 : 0 }}>
        {dateStr} · {timeStr}
      </span>
    </motion.div>
  )
}

export default function Notes() {
  const navigate            = useNavigate()
  const [notes, setNotes]   = useState(MOCK_NOTES)
  const [input, setInput]   = useState('')
  const bottomRef           = useRef(null)
  const textareaRef         = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [notes])

  function addNote() {
    if (!input.trim()) return
    setNotes(prev => [...prev, { id: String(Date.now()), content: input, timestamp: new Date().toISOString(), author: 'You', isOwn: true }])
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
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
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <img src="https://i.pravatar.cc/80?img=32" alt="" style={{ width: 32, height: 32, borderRadius: '50%', border: `2px solid ${BG}`, objectFit: 'cover', zIndex: 2, boxShadow: '0 0 12px rgba(212,182,134,0.12)' }}/>
          <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 32, height: 32, borderRadius: '50%', border: `2px solid ${BG}`, objectFit: 'cover', marginLeft: -10, boxShadow: '0 0 12px rgba(212,182,134,0.12)' }}/>
        </div>
      </nav>

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '300px 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1, minHeight: 0 }}>

        {/* left sidebar */}
        <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '52px 44px', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 300, background: 'radial-gradient(ellipse 80% 60% at 30% 20%, rgba(212,182,134,0.09) 0%, transparent 65%)', pointerEvents: 'none' }}/>

          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Trip Notes</p>
          <motion.h1
            animate={{ filter: ['drop-shadow(0 0 14px rgba(212,182,134,0.16))', 'drop-shadow(0 0 40px rgba(212,182,134,0.40))', 'drop-shadow(0 0 14px rgba(212,182,134,0.16))'] }}
            transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
            style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 44, color: BONE, lineHeight: 1, marginBottom: 6, letterSpacing: '-0.02em' }}
          >
            Bali
          </motion.h1>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, marginBottom: 36 }}>Indonesia</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {[
              { Icon: Calendar, label: 'Dates',       value: 'Jun 14 – Jun 21' },
              { Icon: MapPin,   label: 'Travellers',   value: 'You & Priya M.' },
            ].map(({ Icon, label, value }) => (
              <div key={label} style={{ padding: '14px 0', borderTop: `1px solid ${HAIRLINE}`, display: 'flex', alignItems: 'center', gap: 12 }}>
                <Icon size={12} style={{ color: GOLD, flexShrink: 0 }}/>
                <div>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 3 }}>{label}</p>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{value}</p>
                </div>
              </div>
            ))}
            <div style={{ padding: '14px 0', borderTop: `1px solid ${HAIRLINE}` }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, marginBottom: 3 }}>Notes</p>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE }}>{notes.length} shared</p>
            </div>
          </div>

          <div style={{ marginTop: 'auto', paddingTop: 24, position: 'relative' }}>
            <motion.span
              animate={{ filter: ['drop-shadow(0 0 16px rgba(212,182,134,0.10))', 'drop-shadow(0 0 48px rgba(212,182,134,0.28))', 'drop-shadow(0 0 16px rgba(212,182,134,0.10))'] }}
              transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
              style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 140, lineHeight: 0.85, letterSpacing: '-0.04em', background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', opacity: 0.12, userSelect: 'none', display: 'block' }}
            >
              {notes.length}
            </motion.span>
          </div>
        </div>

        {/* right — notes + input */}
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 68px)', overflow: 'hidden' }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: '44px 52px 20px', scrollbarWidth: 'thin', scrollbarColor: `${HAIRLINE} transparent` }}>
            {notes.length === 0 && (
              <div style={{ textAlign: 'center', paddingTop: 80 }}>
                <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 28, color: MUTE }}>No notes yet.</p>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: DIM, marginTop: 10 }}>Add the first one below.</p>
              </div>
            )}
            {notes.map(n => <NoteItem key={n.id} note={n}/>)}
            <div ref={bottomRef}/>
          </div>

          <div style={{ borderTop: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.96)', padding: '18px 52px 28px', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 14 }}>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); addNote() } }}
                onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px' }}
                onFocus={e => { e.currentTarget.style.borderColor = 'rgba(212,182,134,0.45)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(212,182,134,0.08)' }}
                onBlur={e => { e.currentTarget.style.borderColor = HAIRLINE; e.currentTarget.style.boxShadow = 'none' }}
                placeholder="Add a note…"
                rows={1}
                style={{ flex: 1, padding: '14px 18px', background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`, borderRadius: 18, color: BONE, outline: 'none', resize: 'none', fontFamily: '"Inter Tight",sans-serif', fontSize: 14, fontWeight: 300, lineHeight: 1.55, overflow: 'hidden', transition: 'border-color 0.2s, box-shadow 0.2s' }}
              />
              <button onClick={addNote} style={{ width: 48, height: 48, borderRadius: '50%', flexShrink: 0, background: input.trim() ? GOLD : 'rgba(212,182,134,0.07)', border: 'none', cursor: input.trim() ? 'pointer' : 'default', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s', marginBottom: 2, boxShadow: input.trim() ? '0 0 24px rgba(212,182,134,0.28)' : 'none' }} onMouseEnter={e => { if (input.trim()) e.currentTarget.style.boxShadow = '0 0 40px rgba(212,182,134,0.48)' }} onMouseLeave={e => { if (input.trim()) e.currentTarget.style.boxShadow = '0 0 24px rgba(212,182,134,0.28)' }}>
                <Send size={16} style={{ color: input.trim() ? BG : MUTE }}/>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
