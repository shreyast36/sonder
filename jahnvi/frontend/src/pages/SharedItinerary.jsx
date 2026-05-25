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
  withdrawChange, askPersonaSuggest, finalizeShared,
  getUserProfile, getCotravellerProfile,
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

function ActivityFeed({ log, selfId, otherName, otherEvaluating, since }) {
  // Show the last 12 entries, newest at top.
  // Filters that run on the raw log before we render the feed:
  // 1. `since` — drop entries created before the page mounted, so a
  //    reload wipes the visible history. Server-side activity_log is
  //    untouched; this is a UI-only clean slate per session.
  // 2. Strip "evaluating" entries that have a follow-up resolution
  //    from the same actor (accepted / countered / proposed) — those
  //    "is reviewing" rows are noise once the verdict has landed.
  // 3. Also strip "evaluating" entries older than 60s with NO follow-
  //    up — those are orphans from a failed LLM call. They'd
  //    otherwise loiter at the top of the feed forever.
  const entries = useMemo(() => {
    const all = (log || []).filter(e => {
      if (!since) return true
      const ts = new Date(e.created_at || 0).getTime()
      return ts >= since
    })
    const RESOLUTIONS = new Set(['proposed', 'accepted', 'countered', 'withdrawn', 'finalized'])
    const kept = []
    for (let i = 0; i < all.length; i++) {
      const e = all[i]
      if (e.kind === 'evaluating') {
        // Look ahead for a resolution by the same actor within 90s.
        const myTs = new Date(e.created_at || 0).getTime()
        let resolved = false
        for (let j = i + 1; j < all.length; j++) {
          const next = all[j]
          if (next.actor_id === e.actor_id && RESOLUTIONS.has(next.kind)) {
            const dt = new Date(next.created_at || 0).getTime() - myTs
            if (dt >= 0 && dt < 90_000) { resolved = true; break }
          }
        }
        if (resolved) continue
        // Orphan check — older than 60s and no resolution means the
        // LLM call failed. Drop it so the feed stays honest.
        if (Date.now() - myTs > 60_000) continue
      }
      kept.push(e)
    }
    return kept.slice(-12).reverse()
  }, [log])
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
        const isSystem = e.actor_id === 'system'
        const isMine   = e.actor_id === selfId
        const actor    = isSystem ? '' : (isMine ? 'You' : otherName)
        // System entries don't take a subject; we render the verb as a
        // standalone sentence ("Shared itinerary opened").
        const systemVerb =
          e.kind === 'joined'     ? 'Shared itinerary opened' :
          e.kind === 'finalized'  ? 'Itinerary locked in' :
                                    e.kind
        // User/persona verbs — past tense, agreeing with the actor row.
        const subjectVerb =
          e.kind === 'proposed'   ? 'proposed' :
          e.kind === 'accepted'   ? 'agreed to' :
          e.kind === 'countered'  ? 'countered with' :
          e.kind === 'evaluating' ? 'is reviewing' :
          e.kind === 'withdrawn'  ? (isMine ? 'withdrew' : 'withdrew their proposal of') :
          e.kind === 'finalized'  ? 'locked in the trip' :
          e.kind === 'joined'     ? 'joined the trip' :
                                    e.kind
        const verb = isSystem ? systemVerb : subjectVerb
        const color =
          e.kind === 'accepted'   ? GREEN :
          e.kind === 'countered'  ? ROSE :
          e.kind === 'evaluating' ? VIOLET :
          e.kind === 'withdrawn'  ? DIM :
          e.kind === 'finalized'  ? GREEN :
                                    MUTE
        return (
          <div key={e.entry_id} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: color, marginTop: 8, flexShrink: 0 }}/>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: BONE, margin: 0, lineHeight: 1.4 }}>
                {actor && <span style={{ color: color, fontWeight: 500 }}>{actor}{' '}</span>}
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

function PendingProposalCard({ change, selfId, otherName, onAccept, onCounterClick, onWithdraw, submitting }) {
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
      {!mine ? (
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
      ) : (
        <div style={{ marginTop: 6 }}>
          <button
            disabled={submitting}
            onClick={() => onWithdraw(change)}
            style={{
              background: 'none', border: 'none', padding: 0,
              cursor: submitting ? 'wait' : 'pointer',
              color: DIM, fontFamily: '"Inter Tight",sans-serif',
              fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase',
              textDecoration: 'underline', textDecorationColor: 'rgba(232,212,168,0.2)',
            }}
          >
            Withdraw
          </button>
        </div>
      )}
    </div>
  )
}

function ProposeForm({
  defaultDay, dayCount, onSubmit, onCancel, submitting, error,
  mode = 'propose', replaceTarget = null,
}) {
  // mode:
  //   'propose'  - brand-new add proposal (day pickable + title input)
  //   'counter'  - day locked, title input (replying to a persona counter)
  //   'replace'  - day locked, title input, shows what's being replaced
  //   'move'     - day pickable only, no title input (target locked)
  const [dayNumber, setDayNumber] = useState(defaultDay || 1)
  const [title,     setTitle]     = useState('')
  const [message,   setMessage]   = useState('')
  useEffect(() => { setDayNumber(defaultDay || 1) }, [defaultDay])

  const wantsTitle    = mode === 'propose' || mode === 'counter' || mode === 'replace'
  const wantsDayPick  = mode === 'propose' || mode === 'move'
  const headlineColor = mode === 'replace' || mode === 'move' ? GOLD : VIOLET
  const headlineText  = {
    propose: 'Propose an activity',
    counter: 'Counter with…',
    replace: 'Replace it with…',
    move:    'Move to another day',
  }[mode] || 'Propose an activity'

  const canSubmit = wantsTitle ? title.trim().length > 0 : true

  function send() {
    if (!canSubmit) return
    onSubmit({
      dayNumber,
      title: wantsTitle ? title.trim() : '',
      message: message.trim(),
    })
  }

  return (
    <div style={{
      padding: '20px 22px', borderRadius: 14,
      background: 'rgba(20,16,12,0.96)', border: `1px solid ${headlineColor}44`,
      boxShadow: `0 24px 60px rgba(0,0,0,0.4)`,
      display: 'flex', flexDirection: 'column', gap: 14,
      minWidth: 320, maxWidth: 460,
    }}>
      <p style={{
        fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase', color: headlineColor, margin: 0,
      }}>
        {headlineText}
      </p>
      {replaceTarget && (
        <div style={{
          padding: '8px 12px', borderRadius: 8,
          background: 'rgba(232,212,168,0.04)', border: `1px dashed ${HAIRLINE}`,
        }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: DIM, margin: 0 }}>
            {mode === 'move' ? 'Moving' : 'Replacing'}
          </p>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: BONE, margin: '4px 0 0' }}>
            {replaceTarget.name} <span style={{ color: DIM }}>· day {replaceTarget.from_day}</span>
          </p>
        </div>
      )}
      {wantsDayPick && (
        <div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, margin: '0 0 6px' }}>
            {mode === 'move' ? 'Move to' : 'Day'}
          </p>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {Array.from({ length: dayCount }, (_, i) => i + 1).map(d => {
              const isOrigin = replaceTarget && replaceTarget.from_day === d
              return (
                <button
                  key={d}
                  onClick={() => setDayNumber(d)}
                  disabled={isOrigin}
                  title={isOrigin ? 'Already on this day' : undefined}
                  style={{
                    padding: '6px 12px', borderRadius: 14,
                    background: d === dayNumber ? `${headlineColor}22` : 'transparent',
                    border: `1px solid ${d === dayNumber ? `${headlineColor}88` : HAIRLINE}`,
                    cursor: isOrigin ? 'not-allowed' : 'pointer',
                    color: isOrigin ? DIM : (d === dayNumber ? BONE : MUTE),
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
                    opacity: isOrigin ? 0.4 : 1,
                  }}
                >Day {d}</button>
              )
            })}
          </div>
        </div>
      )}
      {wantsTitle && (
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder={mode === 'replace' ? 'New activity' : 'Activity (e.g. ramen at Ichiran)'}
          autoFocus
          maxLength={140}
          style={{
            padding: '12px 14px', borderRadius: 10,
            background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
            color: BONE, outline: 'none',
            fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300,
          }}
        />
      )}
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
          disabled={submitting || !canSubmit}
          onClick={send}
          style={{
            padding: '10px 18px', borderRadius: 18,
            background: `linear-gradient(135deg, ${headlineColor} 0%, #6D28D9 100%)`,
            border: 'none', cursor: submitting || !canSubmit ? 'not-allowed' : 'pointer',
            color: '#fff', fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
            letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500,
            opacity: submitting || !canSubmit ? 0.5 : 1,
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          {submitting
            ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, ease: 'linear', repeat: Infinity }}><Loader2 size={11}/></motion.span>
            : <Send size={11}/>}
          {mode === 'counter' ? 'Send counter' :
           mode === 'replace' ? 'Send replacement' :
           mode === 'move'    ? 'Send move' :
                                'Send proposal'}
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

function ActivityRow({ activity, dayNumber, locked = false, onReplace, onMove }) {
  const [hover, setHover] = useState(false)
  const name = activity?.activity?.name || '—'
  const category = activity?.activity?.category
  const proposed = category === 'proposed'
  const showActions = hover && !locked
  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: '12px 16px', borderRadius: 10,
        border: `1px solid ${hover ? `${VIOLET}44` : HAIRLINE}`,
        background: 'rgba(232,212,168,0.025)',
        display: 'flex', alignItems: 'center', gap: 12,
        transition: 'border-color 0.2s',
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: BONE, margin: 0 }}>
          {name}
        </p>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, margin: '2px 0 0' }}>
          {activity?.time || ''}
          {category && !proposed ? <span> · {category}</span> : null}
          {proposed ? <span style={{ color: GREEN }}> · added together</span> : null}
        </p>
      </div>
      <AnimatePresence>
        {showActions && (
          <motion.div
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 8 }}
            transition={{ duration: 0.15 }}
            style={{ display: 'flex', gap: 6 }}
          >
            <button
              onClick={() => onReplace(activity)}
              style={{
                padding: '5px 10px', borderRadius: 14,
                background: 'transparent', border: `1px solid ${HAIRLINE}`,
                cursor: 'pointer', color: MUTE,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                letterSpacing: '0.18em', textTransform: 'uppercase',
              }}
            >Replace</button>
            <button
              onClick={() => onMove(activity)}
              style={{
                padding: '5px 10px', borderRadius: 14,
                background: 'transparent', border: `1px solid ${HAIRLINE}`,
                cursor: 'pointer', color: MUTE,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                letterSpacing: '0.18em', textTransform: 'uppercase',
              }}
            >Move</button>
          </motion.div>
        )}
      </AnimatePresence>
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
  // Celebration modal — surfaces on a successful lockIn so the moment
  // gets a real visual beat instead of just an activity-log row.
  const [showFinalizedModal, setShowFinalizedModal] = useState(false)
  const [proposeOpen, setProposeOpen] = useState(false)
  const [proposeDay, setProposeDay] = useState(1)
  const [counterTarget, setCounterTarget] = useState(null)    // ProposedChange we're countering
  // For per-activity edits — we hold either a "replace" or "move" target.
  // editTarget = { activity_id, name, from_day, mode: 'replace'|'move' }
  const [editTarget, setEditTarget] = useState(null)
  const [otherDisplayName, setOtherDisplayName] = useState('them')

  const pollRef = useRef(null)
  // Timestamp the user opened the page. ActivityFeed uses this to
  // hide entries from earlier sessions — reloading the page gives a
  // clean feed without touching the persisted log.
  const pageOpenedAtRef = useRef(Date.now())
  const [pollErrorCount, setPollErrorCount] = useState(0)
  const refetch = useCallback(async () => {
    try {
      const next = await getSharedItinerary(id)
      setShared(next)
      setPollErrorCount(0)   // any successful fetch clears the error banner
    } catch (e) {
      setPollErrorCount(c => c + 1)
      setError(e?.message || 'Could not load itinerary')
    }
  }, [id])

  // Hydrate on mount; the adaptive-polling effect below handles the
  // refresh cadence so this only runs once per id change.
  useEffect(() => {
    if (!id) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await getSharedItinerary(id)
        if (cancelled) return
        setShared(data)
        setPollErrorCount(0)
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Could not load itinerary')
      }
    })()
    return () => { cancelled = true }
  }, [id])

  // Adaptive polling — fast (1.5s) while the persona is mid-evaluation
  // so the resolution lands quickly in the UI, slow (4s) otherwise.
  // Re-arms on every `otherEvaluating` flip so we don't oversample the
  // backend when nothing's happening.
  const otherEvaluatingDerived = !!shared && (shared.activity_log || []).some(e =>
    e.kind === 'evaluating' && e.actor_id !== selfId &&
    (Date.now() - new Date(e.created_at || 0).getTime()) < 12000,
  )
  useEffect(() => {
    if (!id) return
    const interval = otherEvaluatingDerived ? 1500 : 4000
    pollRef.current = setInterval(() => { refetch() }, interval)
    return () => clearInterval(pollRef.current)
  }, [id, refetch, otherEvaluatingDerived])

  // Resolve the other party's display name. For synthetic personas we
  // hit getCotravellerProfile (Pinecone-backed); for real users we'd
  // need a user-by-id endpoint, which doesn't exist yet — fall back to
  // a friendly placeholder rather than rendering "them" forever.
  useEffect(() => {
    if (!shared || !selfId) return
    const otherId = (shared.user_ids || []).find(u => u !== selfId)
    if (!otherId) { setOtherDisplayName('them'); return }
    let cancelled = false
    ;(async () => {
      // Synthetic profile_ids start with "ct_". Try the cotraveller
      // route first; if that 404s (real user), keep the fallback.
      try {
        const match = await getCotravellerProfile(otherId, shared.itinerary_id || '')
        if (cancelled) return
        const name = match?.profile?.display_name?.split(/\s+/)?.[0]
        if (name) setOtherDisplayName(name)
      } catch {
        if (!cancelled) setOtherDisplayName('your match')
      }
    })()
    return () => { cancelled = true }
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
  const finalized = (shared.activity_log || []).some(e => e.kind === 'finalized')
  const acceptedCount = (shared.proposed_changes || []).filter(c => c.status === 'accepted').length
  const canFinalize = !finalized && pendingChanges.length === 0 && acceptedCount > 0

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

  async function withdrawPending(change) {
    setSubmitting(true); setError(null)
    try {
      const res = await withdrawChange(id, { changeId: change.change_id, version: shared.version })
      setShared(res.shared)
    } catch (e) {
      setError(e?.message || 'Could not withdraw')
    } finally {
      setSubmitting(false)
    }
  }

  async function askToSuggest() {
    setSubmitting(true); setError(null)
    try {
      const res = await askPersonaSuggest(id, { version: shared.version })
      setShared(res.shared)
    } catch (e) {
      setError(e?.message || 'Could not get a suggestion')
    } finally {
      setSubmitting(false)
    }
  }

  async function lockIn() {
    setSubmitting(true); setError(null)
    try {
      const res = await finalizeShared(id, { version: shared.version })
      setShared(res.shared)
      setShowFinalizedModal(true)
    } catch (e) {
      setError(e?.message || 'Could not finalise')
    } finally {
      setSubmitting(false)
    }
  }

  async function submitEdit({ dayNumber, title, message }) {
    if (!editTarget) return
    setSubmitting(true); setError(null)
    try {
      const res = await proposeChange(id, {
        kind: editTarget.mode,                             // 'replace' | 'move'
        dayNumber,                                          // move target / replace stays on origin day
        title,                                              // empty for move
        message,
        replacesActivityId: editTarget.activity_id,
        version: shared.version,
      })
      setShared(res.shared)
      setEditTarget(null)
    } catch (e) {
      setError(e?.message || 'Could not send the edit')
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
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
                Shared itinerary · v{shared.version}{finalized ? ' · locked' : ''}
              </p>
              {pollErrorCount >= 2 && (
                <button
                  onClick={refetch}
                  style={{
                    background: 'rgba(248,113,113,0.08)',
                    border: '1px solid rgba(248,113,113,0.35)',
                    borderRadius: 12, padding: '3px 10px',
                    cursor: 'pointer', color: '#F87171',
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                    letterSpacing: '0.16em', textTransform: 'uppercase',
                  }}
                >
                  Connection issue · tap to retry
                </button>
              )}
            </div>
            <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 48, lineHeight: 1.1, color: BONE, margin: '8px 0 4px' }}>
              {itin?.destination?.city || 'Your trip'}
            </h1>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE, margin: 0 }}>
              {finalized
                ? 'Locked in. No more changes can be made.'
                : 'Propose changes, agree or counter — both of you shape the trip.'}
            </p>
            {!finalized && (
              <div style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
                <button
                  onClick={askToSuggest}
                  disabled={submitting}
                  style={{
                    padding: '8px 14px', borderRadius: 18,
                    background: 'transparent', border: `1px solid ${VIOLET}55`,
                    cursor: submitting ? 'wait' : 'pointer', color: VIOLET,
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                    letterSpacing: '0.18em', textTransform: 'uppercase', fontWeight: 500,
                    display: 'flex', alignItems: 'center', gap: 6,
                    opacity: submitting ? 0.6 : 1,
                  }}
                >
                  <MessageCircle size={11}/> Ask {otherName} for an idea
                </button>
                {canFinalize && (
                  <button
                    onClick={lockIn}
                    disabled={submitting}
                    style={{
                      padding: '8px 14px', borderRadius: 18,
                      background: `linear-gradient(135deg, ${GREEN} 0%, #059669 100%)`,
                      border: 'none', cursor: submitting ? 'wait' : 'pointer',
                      color: '#fff', fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                      letterSpacing: '0.18em', textTransform: 'uppercase', fontWeight: 500,
                      display: 'flex', alignItems: 'center', gap: 6,
                      opacity: submitting ? 0.7 : 1,
                    }}
                  >
                    <Check size={11}/> Lock it in
                  </button>
                )}
              </div>
            )}
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
                  onWithdraw={withdrawPending}
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
                {!finalized && (
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
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {(day.activities || []).map((ia, i) => (
                  <ActivityRow
                    key={ia?.activity?.activity_id || i}
                    activity={ia}
                    dayNumber={day.day_number}
                    locked={finalized}
                    onReplace={(act) => setEditTarget({
                      activity_id: act?.activity?.activity_id,
                      name:        act?.activity?.name || '',
                      from_day:    day.day_number,
                      mode:        'replace',
                    })}
                    onMove={(act) => setEditTarget({
                      activity_id: act?.activity?.activity_id,
                      name:        act?.activity?.name || '',
                      from_day:    day.day_number,
                      mode:        'move',
                    })}
                  />
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
            since={pageOpenedAtRef.current}
          />
        </div>
      </div>

      {/* Propose / Counter / Replace / Move modal */}
      <AnimatePresence>
        {(proposeOpen || counterTarget || editTarget) && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{
              position: 'fixed', inset: 0, zIndex: 100,
              background: 'rgba(10,8,5,0.78)', backdropFilter: 'blur(8px)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: 32,
            }}
            onClick={() => { setProposeOpen(false); setCounterTarget(null); setEditTarget(null) }}
          >
            <motion.div
              initial={{ scale: 0.95, y: 12 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 12 }}
              transition={spring}
              onClick={e => e.stopPropagation()}
            >
              {editTarget ? (
                <ProposeForm
                  mode={editTarget.mode}
                  defaultDay={editTarget.mode === 'move'
                    // For 'move', start on a non-origin day so the picker
                    // has a sensible default. For 'replace', stay put.
                    ? (editTarget.from_day === 1 ? Math.min(2, dayCount) : editTarget.from_day - 1)
                    : editTarget.from_day}
                  dayCount={dayCount}
                  replaceTarget={editTarget}
                  onSubmit={submitEdit}
                  onCancel={() => setEditTarget(null)}
                  submitting={submitting}
                  error={error}
                />
              ) : counterTarget ? (
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

      {/* Lock-in confirmation. Surfaces on a successful finalize so the
          moment lands as a deliberate beat rather than a silent state
          change. The email receipt is fired server-side in parallel. */}
      <AnimatePresence>
        {showFinalizedModal && shared && (
          <motion.div
            key="finalized-modal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            onClick={() => setShowFinalizedModal(false)}
            style={{
              position: 'fixed', inset: 0, zIndex: 200,
              background: 'rgba(2,2,2,0.85)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: 16, cursor: 'pointer',
            }}
          >
            <motion.div
              initial={{ scale: 0.92, y: 18 }}
              animate={{ scale: 1, y: 0 }}
              transition={{ type: 'spring', stiffness: 260, damping: 24 }}
              onClick={(e) => e.stopPropagation()}
              style={{
                cursor: 'default',
                maxWidth: 480, width: '100%',
                padding: '40px 36px',
                borderRadius: 18,
                background: 'linear-gradient(160deg, rgba(22,18,12,0.99) 0%, rgba(14,11,8,1) 100%)',
                border: `1px solid ${GREEN}55`,
                boxShadow: `0 30px 80px rgba(0,0,0,0.7), 0 0 60px ${GREEN}22`,
                textAlign: 'center',
              }}
            >
              <p style={{
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                letterSpacing: '0.32em', textTransform: 'uppercase',
                color: GREEN, marginBottom: 18,
              }}>
                Locked in
              </p>
              <h2 style={{
                fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
                fontWeight: 400, fontSize: 'clamp(28px, 4vw, 38px)',
                color: BONE, lineHeight: 1.15, margin: '0 0 18px',
              }}>
                Your trip is final.
              </h2>
              <p style={{
                fontFamily: '"Inter Tight",sans-serif', fontWeight: 300,
                fontSize: 14, color: `${BONE}c8`, lineHeight: 1.6,
                margin: '0 0 28px',
              }}>
                We've sent a confirmation to your inbox and added it to your shared trips on the dashboard. Time to pack.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
                <motion.button
                  whileHover={{ y: -2, boxShadow: `0 0 36px ${GREEN}55` }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => { setShowFinalizedModal(false); navigate('/dashboard') }}
                  style={{
                    minWidth: 260, padding: '15px 28px',
                    background: `linear-gradient(135deg, ${GREEN} 0%, #059669 100%)`,
                    border: 'none', borderRadius: 12, cursor: 'pointer',
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
                    letterSpacing: '0.22em', textTransform: 'uppercase',
                    fontWeight: 600, color: '#0a0807',
                  }}
                >
                  Back to dashboard
                </motion.button>
                <button
                  onClick={() => setShowFinalizedModal(false)}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    padding: '10px 18px',
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                    letterSpacing: '0.20em', textTransform: 'uppercase',
                    color: MUTE,
                  }}
                >
                  Stay on this page
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
