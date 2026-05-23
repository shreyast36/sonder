import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, Plus, Check, X, Send, Loader2, MessageCircle, Users,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import {
  getSharedItinerary, proposeChange, respondToChange,
  getUserProfile,
} from '../lib/api'

const ROSE   = '#F43F5E'
const VIOLET = '#8B5CF6'
const GREEN  = '#10B981'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

// ── Helpers ───────────────────────────────────────────────────────────────

function timeAgo(iso) {
  if (!iso) return ''
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 0)        return 'just now'
  if (ms < 1500)     return 'just now'
  if (ms < 60_000)   return `${Math.floor(ms/1000)}s ago`
  if (ms < 3600_000) return `${Math.floor(ms/60_000)}m ago`
  return `${Math.floor(ms/3600_000)}h ago`
}

// ── Sub-components ────────────────────────────────────────────────────────

function ActivityFeed({ log, selfId, otherName, otherEvaluating }) {
  // Show the last 12 entries, newest at top.
  const entries = useMemo(
    () => (log || []).slice(-12).reverse(),
    [log],
  )
  return (
    <div style={{
      padding: '20px 22px',
      borderRadius: 14,
      border: `1px solid ${HAIRLINE}`,
      background: 'rgba(232,212,168,0.025)',
      display: 'flex', flexDirection: 'column', gap: 10,
      minHeight: 240,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <Users size={11} style={{ color: GOLD }}/>
        <span style={{
          fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500,
          letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE,
        }}>Live activity</span>
      </div>
      {otherEvaluating && (
        <motion.div
          initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
          style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
            background: `${VIOLET}10`, border: `1px solid ${VIOLET}33`, borderRadius: 10,
          }}
        >
          <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.1, ease: 'linear', repeat: Infinity }}>
            <Loader2 size={12} style={{ color: VIOLET }}/>
          </motion.span>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: BONE }}>
            {otherName} is thinking…
          </span>
        </motion.div>
      )}
      {entries.length === 0 && !otherEvaluating && (
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: DIM, margin: 0 }}>
          Nothing yet. Propose something to get started.
        </p>
      )}
      {entries.map((e) => {
        const actor =
          e.actor_id === 'system' ? '—' :
          e.actor_id === selfId   ? 'You' :
                                    otherName
        const verb =
          e.kind === 'proposed'   ? 'proposed' :
          e.kind === 'accepted'   ? 'agreed to' :
          e.kind === 'countered'  ? 'countered with' :
          e.kind === 'evaluating' ? 'is reviewing' :
          e.kind === 'joined'     ? 'joined the trip' :
          e.kind
        const color =
          e.kind === 'accepted'   ? GREEN :
          e.kind === 'countered'  ? ROSE :
          e.kind === 'evaluating' ? VIOLET :
                                    MUTE
        return (
          <div key={e.entry_id} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: color, marginTop: 8, flexShrink: 0 }}/>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: BONE, margin: 0, lineHeight: 1.4 }}>
                <span style={{ color: color, fontWeight: 500 }}>{actor}</span>{' '}
                {verb}
                {e.title ? <span style={{ color: BONE, fontWeight: 400 }}>{' '}"{e.title}"</span> : null}
                {typeof e.day_number === 'number' ? <span style={{ color: DIM }}>{' '}· day {e.day_number}</span> : null}
              </p>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM, margin: '2px 0 0' }}>
                {timeAgo(e.created_at)}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function PendingProposalCard({ change, selfId, otherName, onAccept, onCounterClick, submitting }) {
  const mine = change.proposer_id === selfId
  return (
    <div style={{
      padding: '16px 18px',
      borderRadius: 12,
      border: `1px solid ${mine ? `${GOLD}55` : `${ROSE}55`}`,
      background: mine ? 'rgba(232,212,168,0.04)' : `${ROSE}08`,
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{
          fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500,
          letterSpacing: '0.18em', textTransform: 'uppercase', color: mine ? GOLD : ROSE,
        }}>
          {mine ? `Your proposal · waiting on ${otherName}` : `${otherName} proposed`}
        </span>
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM }}>
          · day {change.day_number}
        </span>
      </div>
      <p style={{ fontFamily: '"Cormorant Garamond",serif', fontSize: 22, lineHeight: 1.15, color: BONE, margin: 0 }}>
        {change.title}
      </p>
      {change.message && (
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE, margin: 0, lineHeight: 1.5 }}>
          "{change.message}"
        </p>
      )}
      {!mine && (
        <div style={{ display: 'flex', gap: 10, marginTop: 6 }}>
          <button
            disabled={submitting}
            onClick={() => onAccept(change)}
            style={{
              padding: '9px 16px', borderRadius: 18,
              background: `linear-gradient(135deg, ${GREEN} 0%, #059669 100%)`,
              border: 'none', cursor: submitting ? 'wait' : 'pointer',
              color: '#fff', fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
              letterSpacing: '0.18em', textTransform: 'uppercase', fontWeight: 500,
              opacity: submitting ? 0.7 : 1, display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            <Check size={11}/> Agree
          </button>
          <button
            disabled={submitting}
            onClick={() => onCounterClick(change)}
            style={{
              padding: '9px 16px', borderRadius: 18,
              background: 'rgba(212,182,134,0.05)', border: `1px solid ${HAIRLINE}`,
              cursor: submitting ? 'wait' : 'pointer', color: MUTE,
              fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em',
              textTransform: 'uppercase', fontWeight: 500,
            }}
          >
            Counter
          </button>
        </div>
      )}
    </div>
  )
}

function ProposeForm({ defaultDay, dayCount, onSubmit, onCancel, submitting, error, mode = 'propose' }) {
  // mode: 'propose' = brand-new proposal (day pickable); 'counter' = day locked
  const [dayNumber, setDayNumber] = useState(defaultDay || 1)
  const [title,     setTitle]     = useState('')
  const [message,   setMessage]   = useState('')
  useEffect(() => { setDayNumber(defaultDay || 1) }, [defaultDay])
  return (
    <div style={{
      padding: '20px 22px', borderRadius: 14,
      background: 'rgba(20,16,12,0.96)', border: `1px solid ${VIOLET}44`,
      boxShadow: `0 24px 60px rgba(0,0,0,0.4)`,
      display: 'flex', flexDirection: 'column', gap: 14,
      minWidth: 320, maxWidth: 460,
    }}>
      <p style={{
        fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase', color: VIOLET, margin: 0,
      }}>
        {mode === 'counter' ? 'Counter with…' : 'Propose an activity'}
      </p>
      {mode === 'propose' && (
        <div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, margin: '0 0 6px' }}>Day</p>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {Array.from({ length: dayCount }, (_, i) => i + 1).map(d => (
              <button
                key={d}
                onClick={() => setDayNumber(d)}
                style={{
                  padding: '6px 12px', borderRadius: 14,
                  background: d === dayNumber ? `${VIOLET}22` : 'transparent',
                  border: `1px solid ${d === dayNumber ? `${VIOLET}88` : HAIRLINE}`,
                  cursor: 'pointer', color: d === dayNumber ? BONE : MUTE,
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
                }}
              >Day {d}</button>
            ))}
          </div>
        </div>
      )}
      <input
        value={title}
        onChange={e => setTitle(e.target.value)}
        placeholder="Activity (e.g. ramen at Ichiran)"
        autoFocus
        maxLength={140}
        style={{
          padding: '12px 14px', borderRadius: 10,
          background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
          color: BONE, outline: 'none',
          fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300,
        }}
      />
      <textarea
        value={message}
        onChange={e => setMessage(e.target.value)}
        placeholder="Why? (optional, one line)"
        rows={2}
        maxLength={400}
        style={{
          padding: '12px 14px', borderRadius: 10,
          background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
          color: BONE, outline: 'none', resize: 'none',
          fontFamily: '"Inter Tight",sans-serif', fontSize: 12, fontWeight: 300,
        }}
      />
      {error && <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: '#F87171', margin: 0 }}>{error}</p>}
      <div style={{ display: 'flex', gap: 10 }}>
        <button
          disabled={submitting || !title.trim()}
          onClick={() => onSubmit({ dayNumber, title: title.trim(), message: message.trim() })}
          style={{
            padding: '10px 18px', borderRadius: 18,
            background: `linear-gradient(135deg, ${VIOLET} 0%, #6D28D9 100%)`,
            border: 'none', cursor: submitting || !title.trim() ? 'not-allowed' : 'pointer',
            color: '#fff', fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
            letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500,
            opacity: submitting || !title.trim() ? 0.5 : 1,
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          {submitting
            ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, ease: 'linear', repeat: Infinity }}><Loader2 size={11}/></motion.span>
            : <Send size={11}/>}
          {mode === 'counter' ? 'Send counter' : 'Send proposal'}
        </button>
        <button
          onClick={onCancel}
          style={{
            padding: '10px 18px', borderRadius: 18,
            background: 'transparent', border: `1px solid ${HAIRLINE}`,
            cursor: 'pointer', color: MUTE,
            fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
            letterSpacing: '0.22em', textTransform: 'uppercase',
          }}
        >Cancel</button>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function SharedItinerary() {
  const navigate     = useNavigate()
  const { id }       = useParams()
  const { user }     = useAuth()
  const selfId       = user?.uid

  const [shared, setShared]       = useState(null)
  const [error, setError]         = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [proposeOpen, setProposeOpen] = useState(false)
  const [proposeDay, setProposeDay] = useState(1)
  const [counterTarget, setCounterTarget] = useState(null)    // ProposedChange we're countering
  const [otherDisplayName, setOtherDisplayName] = useState('them')

  const pollRef = useRef(null)
  const refetch = useCallback(async () => {
    try {
      const next = await getSharedItinerary(id)
      setShared(next)
    } catch (e) {
      setError(e?.message || 'Could not load itinerary')
    }
  }, [id])

  // Hydrate + light polling so the user sees the persona's response
  // even when WS isn't connected (e.g. on a fresh tab).
  useEffect(() => {
    if (!id) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await getSharedItinerary(id)
        if (cancelled) return
        setShared(data)
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Could not load itinerary')
      }
    })()
    pollRef.current = setInterval(() => {
      if (cancelled) return
      refetch()
    }, 4000)
    return () => { cancelled = true; clearInterval(pollRef.current) }
  }, [id, refetch])

  // Other side's display name — for synthetic personas we don't have a
  // direct lookup here, so derive from the activity log or fall back.
  useEffect(() => {
    if (!shared || !selfId) return
    const otherId = (shared.user_ids || []).find(u => u !== selfId)
    if (!otherId) return
    // Try to load co-traveller name from the matches cache. If not
    // available, leave the fallback.
    ;(async () => {
      try {
        const me = await getUserProfile()
        // me.display_name is the signed-in user; the other side's name
        // we already get from the chat history if needed. For now, the
        // 'them' fallback is fine until we wire a profile lookup here.
        if (me?.display_name) {
          // no-op; just confirms auth works
        }
      } catch { /* noop */ }
    })()
  }, [shared, selfId])

  if (error && !shared) {
    return (
      <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ color: MUTE, fontSize: 13 }}>{error}</p>
          <button onClick={() => navigate(-1)} style={{ marginTop: 16, color: GOLD, background: 'none', border: 'none', cursor: 'pointer' }}>Go back</button>
        </div>
      </div>
    )
  }
  if (!shared) {
    return (
      <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.2, ease: 'linear', repeat: Infinity }}>
          <Loader2 size={20} style={{ color: VIOLET }}/>
        </motion.span>
      </div>
    )
  }

  const itin       = shared.itinerary
  const days       = itin.days || []
  const dayCount   = Math.max(days.length, 1)
  const otherId    = (shared.user_ids || []).find(u => u !== selfId)
  const otherName  = otherDisplayName

  const pendingChanges = (shared.proposed_changes || []).filter(c => c.status === 'proposed')
  const otherEvaluating = (shared.activity_log || []).some(e =>
    e.kind === 'evaluating' && e.actor_id !== selfId &&
    (Date.now() - new Date(e.created_at || 0).getTime()) < 12000,
  )

  async function submitPropose({ dayNumber, title, message }) {
    setSubmitting(true); setError(null)
    try {
      const res = await proposeChange(id, {
        kind: 'add', dayNumber, title, message, version: shared.version,
      })
      setShared(res.shared)
      setProposeOpen(false)
      setCounterTarget(null)
    } catch (e) {
      setError(e?.message || 'Could not send proposal')
    } finally {
      setSubmitting(false)
    }
  }

  async function submitCounter({ dayNumber, title, message }) {
    if (!counterTarget) return
    setSubmitting(true); setError(null)
    try {
      const res = await respondToChange(id, {
        changeId: counterTarget.change_id, decision: 'counter',
        title, message, version: shared.version,
      })
      setShared(res.shared)
      setCounterTarget(null)
    } catch (e) {
      setError(e?.message || 'Could not send counter')
    } finally {
      setSubmitting(false)
    }
  }

  async function acceptPending(change) {
    setSubmitting(true); setError(null)
    try {
      const res = await respondToChange(id, {
        changeId: change.change_id, decision: 'accept',
        version: shared.version,
      })
      setShared(res.shared)
    } catch (e) {
      setError(e?.message || 'Could not record agreement')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent={VIOLET}/>

      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={() => navigate(-1)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, display: 'flex', alignItems: 'center', gap: 8 }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </motion.button>
        <SonderNav3D markSize={32}/>
        <div style={{ width: 70 }}/>
      </nav>

      <div style={{ flex: 1, maxWidth: 1200, margin: '0 auto', width: '100%', padding: '40px 48px 80px', display: 'grid', gridTemplateColumns: '1fr 360px', gap: 40 }}>

        {/* LEFT — days + pending proposals */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 36 }}>
          <div>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
              Shared itinerary · v{shared.version}
            </p>
            <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 48, lineHeight: 1.1, color: BONE, margin: '8px 0 4px' }}>
              {itin?.destination?.city || 'Your trip'}
            </h1>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE, margin: 0 }}>
              Propose changes, agree or counter — both of you shape the trip.
            </p>
          </div>

          {pendingChanges.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: ROSE, margin: 0 }}>
                Pending · {pendingChanges.length}
              </p>
              {pendingChanges.map(c => (
                <PendingProposalCard
                  key={c.change_id}
                  change={c}
                  selfId={selfId}
                  otherName={otherName}
                  onAccept={acceptPending}
                  onCounterClick={(ch) => { setCounterTarget(ch); setProposeOpen(false) }}
                  submitting={submitting}
                />
              ))}
            </div>
          )}

          {days.map(day => (
            <div key={day.day_number} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 28, color: BONE, margin: 0 }}>
                  Day {day.day_number}{day.theme ? <span style={{ color: MUTE, fontSize: 16 }}> — {day.theme}</span> : null}
                </h2>
                <button
                  onClick={() => { setProposeDay(day.day_number); setProposeOpen(true); setCounterTarget(null) }}
                  style={{
                    background: 'none', border: `1px solid ${VIOLET}55`, borderRadius: 18,
                    padding: '6px 12px', cursor: 'pointer', color: VIOLET,
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                    letterSpacing: '0.18em', textTransform: 'uppercase',
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}
                >
                  <Plus size={11}/> Propose
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {(day.activities || []).map((ia, i) => (
                  <div key={ia?.activity?.activity_id || i} style={{
                    padding: '12px 16px', borderRadius: 10,
                    border: `1px solid ${HAIRLINE}`,
                    background: 'rgba(232,212,168,0.025)',
                    display: 'flex', alignItems: 'center', gap: 12,
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE, margin: 0 }}>
                        {ia?.activity?.name || '—'}
                      </p>
                      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, margin: '2px 0 0' }}>
                        {ia?.time || ''}
                        {ia?.activity?.category && ia.activity.category !== 'proposed' ? <span> · {ia.activity.category}</span> : null}
                        {ia?.activity?.category === 'proposed' ? <span style={{ color: GREEN }}> · added together</span> : null}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* RIGHT — activity feed */}
        <div style={{ position: 'sticky', top: 100, alignSelf: 'flex-start', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <ActivityFeed
            log={shared.activity_log}
            selfId={selfId}
            otherName={otherName}
            otherEvaluating={otherEvaluating}
          />
        </div>
      </div>

      {/* Propose / Counter modal */}
      <AnimatePresence>
        {(proposeOpen || counterTarget) && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{
              position: 'fixed', inset: 0, zIndex: 100,
              background: 'rgba(10,8,5,0.78)', backdropFilter: 'blur(8px)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: 32,
            }}
            onClick={() => { setProposeOpen(false); setCounterTarget(null) }}
          >
            <motion.div
              initial={{ scale: 0.95, y: 12 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 12 }}
              transition={spring}
              onClick={e => e.stopPropagation()}
            >
              {counterTarget ? (
                <ProposeForm
                  mode="counter"
                  defaultDay={counterTarget.day_number}
                  dayCount={dayCount}
                  onSubmit={submitCounter}
                  onCancel={() => setCounterTarget(null)}
                  submitting={submitting}
                  error={error}
                />
              ) : (
                <ProposeForm
                  mode="propose"
                  defaultDay={proposeDay}
                  dayCount={dayCount}
                  onSubmit={submitPropose}
                  onCancel={() => setProposeOpen(false)}
                  submitting={submitting}
                  error={error}
                />
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
