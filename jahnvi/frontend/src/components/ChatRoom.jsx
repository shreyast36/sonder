import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, Check, MapPin, Volume2, Loader2 } from 'lucide-react'
import SynthBadge from './SynthBadge'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import { useWebSocket } from '../hooks/useWebSocket'
import { getCotravellerProfile, getChatSession, getChatMessages, synthesizeVoice } from '../lib/api'

const ROSE   = '#F43F5E'
const VIOLET = '#8B5CF6'

const spring = { type: 'spring', stiffness: 300, damping: 24 }

function Bubble({ message, isOwn, otherName, seenByOther, otherProfileId, canPlayVoice }) {
  const { content, timestamp, message_id } = message
  const timeStr = new Date(timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  // Voice playback state — one Audio element per bubble, fetched on first
  // click. Backend caches by text hash, so replays are instant + free.
  const [playState, setPlayState] = useState('idle')   // idle | loading | playing | error
  const audioRef = useRef(null)

  async function togglePlay() {
    if (playState === 'loading') return
    if (audioRef.current && playState === 'playing') {
      audioRef.current.pause()
      setPlayState('idle')
      return
    }
    if (audioRef.current) {
      audioRef.current.currentTime = 0
      audioRef.current.play().catch(() => setPlayState('error'))
      setPlayState('playing')
      return
    }
    setPlayState('loading')
    try {
      const { audio_url } = await synthesizeVoice(otherProfileId, content)
      const a = new Audio(audio_url)
      a.onended = () => setPlayState('idle')
      a.onerror = () => setPlayState('error')
      audioRef.current = a
      await a.play()
      setPlayState('playing')
    } catch {
      setPlayState('error')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: isOwn ? 24 : -24, y: 8 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration: 0.4, ease }}
      style={{ display: 'flex', flexDirection: 'column', alignItems: isOwn ? 'flex-end' : 'flex-start', marginBottom: 20 }}
    >
      {!isOwn && otherName && (
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: ROSE, marginBottom: 5, opacity: 0.85 }}>{otherName}</span>
      )}
      <div style={{
        maxWidth: '78%', padding: '14px 18px',
        borderRadius: isOwn ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        background: isOwn
          ? 'linear-gradient(135deg, rgba(224,178,96,0.22) 0%, rgba(212,182,134,0.10) 60%, rgba(180,138,68,0.08) 100%)'
          : `linear-gradient(135deg, ${ROSE}12 0%, rgba(255,255,255,0.03) 100%)`,
        border: `1px solid ${isOwn ? 'rgba(212,182,134,0.25)' : `${ROSE}28`}`,
        boxShadow: isOwn ? '0 4px 20px rgba(212,182,134,0.08)' : `0 4px 20px ${ROSE}0A`,
      }}>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, lineHeight: 1.7, color: BONE, margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {content}
        </p>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM }}>{timeStr}</span>
        {isOwn && message_id && seenByOther && (
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: GOLD, opacity: 0.7 }}>Seen</span>
        )}
        {!isOwn && canPlayVoice && (
          <button
            onClick={togglePlay}
            disabled={playState === 'loading'}
            aria-label={playState === 'playing' ? 'Pause voice' : 'Play voice'}
            title={playState === 'error' ? 'Voice unavailable' : 'Play voice'}
            style={{
              background: 'none', border: 'none', padding: 2, cursor: playState === 'loading' ? 'default' : 'pointer',
              color: playState === 'playing' ? ROSE : playState === 'error' ? DIM : MUTE,
              display: 'flex', alignItems: 'center',
            }}
          >
            {playState === 'loading'
              ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, ease: 'linear', repeat: Infinity }} style={{ display: 'inline-flex' }}><Loader2 size={11}/></motion.span>
              : <Volume2 size={11}/>}
          </button>
        )}
      </div>
    </motion.div>
  )
}

function OnlineDot({ online }) {
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
      background: online ? '#22C55E' : '#64748B',
      boxShadow: online ? '0 0 10px rgba(34,197,94,0.55)' : 'none',
      transition: 'background 0.2s, box-shadow 0.2s',
    }}/>
  )
}

/**
 * ChatRoom renders a chat session for the signed-in user. The synthetic
 * co-traveller replies automatically server-side — no second window.
 */
export default function ChatRoom({ sessionId, selfId }) {
  const navigate = useNavigate()
  const [session, setSession] = useState(null)
  const [other,   setOther]   = useState(null)   // CoTravellerMatch
  const [input,   setInput]   = useState('')
  const bottomRef = useRef(null)

  const {
    messages, sendMessage, sendTyping, sendSeen, seedMessages,
    connected, typingUsers, seenIds, presence,
  } = useWebSocket(sessionId)

  // Hydrate session + history + other-side profile on mount.
  useEffect(() => {
    if (!sessionId) return
    let cancelled = false
    ;(async () => {
      try {
        const s = await getChatSession(sessionId)
        if (cancelled) return
        setSession(s)
        const otherId = s.user_id === selfId ? s.profile_id : s.user_id
        if (otherId) {
          try {
            const p = await getCotravellerProfile(otherId)
            if (!cancelled) setOther(p)
          } catch (e) {
            // Real users won't be in Pinecone; that's fine — the panel
            // collapses to a name-only header.
            console.warn('getCotravellerProfile failed:', e?.message || e)
          }
        }
      } catch (e) {
        console.warn('getChatSession failed:', e?.message || e)
      }
      try {
        const { messages: hist } = await getChatMessages(sessionId)
        if (!cancelled) seedMessages(hist || [])
      } catch (e) {
        console.warn('getChatMessages failed:', e?.message || e)
      }
    })()
    return () => { cancelled = true }
  }, [sessionId, selfId, seedMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, typingUsers.length])

  // Auto-emit "seen" for every incoming message from the other side that we
  // haven't acknowledged yet. Read receipts only mean anything for the
  // message's author, so we only ack messages we did NOT send.
  const ackedRef = useRef(new Set())
  useEffect(() => {
    for (const m of messages) {
      if (!m?.message_id) continue
      if (m.sender_id === selfId) continue
      if (ackedRef.current.has(m.message_id)) continue
      ackedRef.current.add(m.message_id)
      sendSeen(m.message_id)
    }
  }, [messages, selfId, sendSeen])

  function onChangeInput(v) {
    setInput(v)
    if (v.trim()) sendTyping()
  }

  function send(text) {
    const t = (text ?? input).trim()
    if (!t) return
    sendMessage(t)
    setInput('')
  }

  const otherProfile  = other?.profile
  const otherUserId   = session && (session.user_id === selfId ? session.profile_id : session.user_id)
  const otherName     = otherProfile?.display_name || (otherUserId ? otherUserId.split('_')[0] : 'Companion')
  const otherLocation = otherProfile?.location || ''
  const otherAvatar   = otherProfile?.avatar_url || ''
  const otherIsSeed   = !!otherProfile?.is_seed
  const otherTyping   = otherUserId ? typingUsers.includes(otherUserId) : typingUsers.length > 0
  const otherOnline   = otherUserId ? !!presence[otherUserId] : false
  const matchPct      = other?.match_score ? Math.round(other.match_score * 100) : null

  const compat = useMemo(() => {
    return (other?.match_reasons || []).slice(0, 4)
  }, [other])

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent={VIOLET}/>

      {/* nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => navigate(-1)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </motion.button>
        <SonderNav3D markSize={32}/>
        <motion.button
          whileHover={{ background: `${ROSE}18`, borderColor: `${ROSE}55` }}
          whileTap={{ scale: 0.96 }}
          onClick={() => navigate(`/approve/${sessionId}`)}
          style={{ background: 'none', border: `1px solid ${ROSE}44`, borderRadius: 20, padding: '8px 18px', cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: ROSE }}
        >
          Review match
        </motion.button>
      </nav>

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '320px 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1, minHeight: 0 }}>

        {/* left sidebar */}
        <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '52px 44px', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 320, background: `radial-gradient(ellipse 80% 60% at 30% 20%, ${ROSE}12 0%, transparent 65%)`, pointerEvents: 'none' }}/>

          <div style={{ position: 'relative', width: 88, height: 88, marginBottom: 24 }}>
            <motion.div
              animate={{ boxShadow: [`0 0 0 2px ${ROSE}33, 0 0 28px ${ROSE}12`, `0 0 0 2px ${ROSE}66, 0 0 56px ${ROSE}28`, `0 0 0 2px ${ROSE}33, 0 0 28px ${ROSE}12`] }}
              transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut' }}
              style={{ width: 88, height: 88, borderRadius: '50%', overflow: 'hidden' }}
            >
              {otherAvatar ? (
                <img src={otherAvatar} alt={otherName} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
              ) : (
                <div style={{
                  width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'rgba(212,182,134,0.10)', color: GOLD,
                  fontFamily: '"Cormorant Garamond",serif', fontSize: 34,
                }}>
                  {(otherName || '?').split(/\s+/).slice(0, 2).map(s => s[0]?.toUpperCase()).join('') || '?'}
                </div>
              )}
            </motion.div>
            <span title={otherOnline ? 'Online now' : 'Offline'} style={{
              position: 'absolute', right: 0, bottom: 4,
              width: 14, height: 14, borderRadius: '50%',
              background: otherOnline ? '#22C55E' : '#475569',
              boxShadow: otherOnline ? '0 0 12px rgba(34,197,94,0.6)' : 'none',
              border: `2px solid ${BG}`,
            }}/>
          </div>

          <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 34, color: BONE, lineHeight: 1, marginBottom: 8 }}>{otherName}</h2>
          {otherIsSeed && (
            <div style={{ marginBottom: 8 }}>
              <SynthBadge isSeed={true} variant="default" />
            </div>
          )}
          {otherLocation && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 8 }}>
              <MapPin size={10} style={{ color: ROSE }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>{otherLocation}</span>
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
            <OnlineDot online={otherOnline}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: otherOnline ? '#22C55E' : MUTE, letterSpacing: '0.08em' }}>
              {otherOnline ? 'Online' : 'Offline'}
            </span>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: DIM, marginLeft: 'auto' }}>
              {connected ? 'Connected' : 'Reconnecting…'}
            </span>
          </div>

          {matchPct != null && (
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, marginBottom: 32 }}>
              <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 72, lineHeight: 0.88, color: BONE, letterSpacing: '-0.04em' }}>{matchPct}</span>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: `${VIOLET}88`, paddingBottom: 12 }}>% match</span>
            </div>
          )}

          {compat.length > 0 && <>
            <div style={{ height: 1, background: `linear-gradient(to right, transparent, ${HAIRLINE}, transparent)`, marginBottom: 24 }}/>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.24em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Why you match</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 'auto' }}>
              {compat.map((c, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 20, height: 20, borderRadius: '50%', border: `1px solid ${ROSE}33`, background: `${ROSE}0A`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Check size={9} style={{ color: ROSE }}/>
                  </div>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, color: BONE, lineHeight: 1.5 }}>{c}</span>
                </div>
              ))}
            </div>
          </>}
        </div>

        {/* right — messages + input */}
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 68px)', overflow: 'hidden' }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: '44px 52px 20px' }}>
            {messages.length === 0 && (
              <p style={{ color: MUTE, fontFamily: '"Inter Tight",sans-serif', fontSize: 12, textAlign: 'center', marginTop: 80 }}>
                No messages yet — say hello.
              </p>
            )}
            {messages.map((m) => {
              const isOwn = m.sender_id === selfId
              const seen  = isOwn && m.message_id && seenIds.has(m.message_id)
              return (
                <Bubble
                  key={m.message_id || `${m.sender_id}-${m.timestamp}`}
                  message={m}
                  isOwn={isOwn}
                  otherName={otherName}
                  seenByOther={seen}
                  otherProfileId={otherProfile?.profile_id}
                  canPlayVoice={!!otherProfile?.is_seed}
                />
              )
            })}
            <AnimatePresence>
              {otherTyping && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <div style={{ width: 26, height: 26, borderRadius: '50%', border: `1px solid ${ROSE}44`, overflow: 'hidden' }}>
                    {otherAvatar
                      ? <img src={otherAvatar} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
                      : <div style={{ width: '100%', height: '100%', background: `${ROSE}14` }}/>}
                  </div>
                  <div style={{ display: 'flex', gap: 5, padding: '12px 16px', borderRadius: '18px 18px 18px 4px', border: `1px solid ${ROSE}28`, background: `${ROSE}08` }}>
                    {[0, 1, 2].map(i => (
                      <motion.div key={i} animate={{ y: [0, -5, 0] }} transition={{ duration: 0.7, delay: i * 0.14, repeat: Infinity }} style={{ width: 5, height: 5, borderRadius: '50%', background: ROSE }}/>
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
                onChange={e => onChangeInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') send() }}
                placeholder={`Message ${otherName || 'them'}…`}
                style={{ flex: 1, padding: '14px 20px', background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`, borderRadius: 24, color: BONE, outline: 'none', fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300 }}
                onFocus={e => { e.currentTarget.style.borderColor = `${ROSE}55`; e.currentTarget.style.boxShadow = `0 0 0 3px ${ROSE}0F` }}
                onBlur={e => { e.currentTarget.style.borderColor = HAIRLINE; e.currentTarget.style.boxShadow = 'none' }}
              />
              <motion.button
                whileHover={input.trim() ? { scale: 1.08, boxShadow: `0 0 40px ${ROSE}55` } : {}}
                whileTap={input.trim() ? { scale: 0.92 } : {}}
                transition={spring}
                onClick={() => send()}
                style={{ width: 48, height: 48, borderRadius: '50%', flexShrink: 0, background: input.trim() ? `linear-gradient(135deg, ${ROSE} 0%, #E11D48 100%)` : 'rgba(212,182,134,0.07)', border: 'none', cursor: input.trim() ? 'pointer' : 'default', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: input.trim() ? `0 0 24px ${ROSE}44` : 'none' }}
              >
                <Send size={16} style={{ color: input.trim() ? '#fff' : MUTE }}/>
              </motion.button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
