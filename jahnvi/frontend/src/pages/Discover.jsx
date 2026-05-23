import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, MapPin, Loader2, Sparkles, MessageCircle, Send,
  Users, Plus, Trash2, Calendar, Check, X,
} from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import { useAuth } from '../hooks/useAuth'
import {
  listOpenTrips, requestToJoin,
  listFeed, createPost, deletePost as apiDeletePost,
  listComments, addComment,
} from '../lib/api'

const VIOLET = '#8B5CF6'
const ROSE   = '#F43F5E'
const GREEN  = '#10B981'
const AMBER  = '#F59E0B'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

// ── Helpers ───────────────────────────────────────────────────────────────

function timeAgo(iso) {
  if (!iso) return ''
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 30_000)    return 'just now'
  if (ms < 3600_000)  return `${Math.floor(ms / 60_000)}m`
  if (ms < 86400_000) return `${Math.floor(ms / 3600_000)}h`
  return `${Math.floor(ms / 86400_000)}d`
}

function formatDateRange(start, end) {
  if (!start && !end) return ''
  try {
    const fmt = d => d ? new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''
    if (start && end) return `${fmt(start)} – ${fmt(end)}`
    return fmt(start || end)
  } catch {
    return ''
  }
}

// ── Open Trip card ────────────────────────────────────────────────────────

function OpenTripCard({ trip, index, onRequestJoin }) {
  const status = trip.your_request_status   // null | "proposed" | "approved" | "denied" | "withdrawn"
  const dateRange = formatDateRange(trip.start_date, trip.end_date)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.5, delay: 0.1 + index * 0.06, ease }}
      whileHover={{ y: -3, boxShadow: `0 28px 60px rgba(0,0,0,0.5), 0 0 0 1px ${VIOLET}33` }}
      style={{
        padding: 1, borderRadius: 18,
        background: 'linear-gradient(145deg,rgba(232,212,168,0.10) 0%,rgba(8,8,7,0) 50%,rgba(212,182,134,0.06) 100%)',
        boxShadow: '0 10px 32px rgba(0,0,0,0.4)',
      }}
    >
      <div style={{
        background: 'linear-gradient(160deg,rgba(20,16,10,0.99) 0%,rgba(12,10,7,1) 100%)',
        borderRadius: 17, padding: '24px 28px', position: 'relative', overflow: 'hidden',
        display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        <div style={{ position: 'absolute', top: -60, right: -60, width: 220, height: 220, borderRadius: '50%', background: `radial-gradient(ellipse, ${VIOLET}10 0%, transparent 70%)`, pointerEvents: 'none' }}/>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
          {/* owner avatar */}
          <div style={{
            width: 48, height: 48, borderRadius: '50%', overflow: 'hidden',
            background: 'rgba(212,182,134,0.06)', flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: `1px solid ${VIOLET}33`,
          }}>
            {trip.owner_avatar
              ? <img src={trip.owner_avatar} alt={trip.owner_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
              : <span style={{ fontFamily: '"Cormorant Garamond",serif', fontSize: 22, color: GOLD }}>
                  {(trip.owner_name || '?').split(/\s+/).slice(0, 2).map(s => s[0]?.toUpperCase()).join('')}
                </span>}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontFamily: '"Cormorant Garamond",serif', fontSize: 22, color: BONE, margin: 0, lineHeight: 1.1 }}>
              {trip.destination_city || 'Somewhere'}
              {trip.destination_country ? <span style={{ color: MUTE, fontStyle: 'italic', fontSize: 14 }}>, {trip.destination_country}</span> : null}
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE }}>
                {trip.owner_name}'s trip
              </span>
              {dateRange && (
                <>
                  <span style={{ color: DIM }}>·</span>
                  <Calendar size={9} style={{ color: GOLD }}/>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>{dateRange}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {trip.note && (
          <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 14, color: BONE, lineHeight: 1.55, margin: 0 }}>
            "{trip.note}"
          </p>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Users size={11} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, letterSpacing: '0.04em' }}>
              {trip.confirmed_companions} / {trip.join_capacity} {trip.join_capacity === 1 ? 'companion slot' : 'companion slots'}
            </span>
          </div>
          {status === null && (
            <motion.button
              whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}
              onClick={() => onRequestJoin(trip)}
              style={{
                padding: '8px 16px', borderRadius: 18,
                background: `linear-gradient(135deg, ${VIOLET} 0%, #6D28D9 100%)`,
                border: 'none', cursor: 'pointer', color: '#fff',
                fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500,
                letterSpacing: '0.22em', textTransform: 'uppercase',
              }}
            >
              Request to join
            </motion.button>
          )}
          {status === 'proposed' && (
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: AMBER, padding: '6px 12px', borderRadius: 14, background: `${AMBER}10`, border: `1px solid ${AMBER}55` }}>
              Requested
            </span>
          )}
          {status === 'approved' && (
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: GREEN, padding: '6px 12px', borderRadius: 14, background: `${GREEN}10`, border: `1px solid ${GREEN}55`, display: 'flex', alignItems: 'center', gap: 5 }}>
              <Check size={10}/> Joined
            </span>
          )}
          {status === 'denied' && (
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, padding: '6px 12px', borderRadius: 14, background: 'rgba(212,182,134,0.04)', border: `1px solid ${HAIRLINE}` }}>
              Passed
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// ── Join request modal ───────────────────────────────────────────────────

function JoinRequestModal({ trip, onClose, onSubmit, submitting, error }) {
  const [message, setMessage] = useState('')
  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      style={{
        position: 'fixed', inset: 0, zIndex: 100,
        background: 'rgba(10,8,5,0.78)', backdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32,
      }}
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, y: 12 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 12 }}
        transition={spring}
        onClick={e => e.stopPropagation()}
        style={{
          padding: '24px 28px', borderRadius: 16,
          background: 'rgba(20,16,12,0.96)', border: `1px solid ${VIOLET}44`,
          boxShadow: `0 24px 60px rgba(0,0,0,0.5)`,
          display: 'flex', flexDirection: 'column', gap: 14,
          minWidth: 360, maxWidth: 480,
        }}
      >
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500, letterSpacing: '0.22em', textTransform: 'uppercase', color: VIOLET, margin: 0 }}>
          Request to join {trip?.owner_name}'s trip
        </p>
        <p style={{ fontFamily: '"Cormorant Garamond",serif', fontSize: 24, color: BONE, margin: 0, lineHeight: 1.15 }}>
          {trip?.destination_city}{trip?.destination_country ? `, ${trip.destination_country}` : ''}
        </p>
        <textarea
          value={message}
          onChange={e => setMessage(e.target.value)}
          placeholder="Why would you be a good companion? (optional)"
          rows={4}
          maxLength={400}
          autoFocus
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
            disabled={submitting}
            onClick={() => onSubmit(message.trim())}
            style={{
              padding: '11px 22px', borderRadius: 18,
              background: `linear-gradient(135deg, ${VIOLET} 0%, #6D28D9 100%)`,
              border: 'none', cursor: submitting ? 'wait' : 'pointer', color: '#fff',
              fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
              letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500,
              opacity: submitting ? 0.7 : 1,
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {submitting
              ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, ease: 'linear', repeat: Infinity }}><Loader2 size={11}/></motion.span>
              : <Send size={11}/>}
            Send request
          </button>
          <button
            onClick={onClose}
            style={{
              padding: '11px 22px', borderRadius: 18,
              background: 'transparent', border: `1px solid ${HAIRLINE}`,
              cursor: 'pointer', color: MUTE,
              fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
              letterSpacing: '0.22em', textTransform: 'uppercase',
            }}
          >Cancel</button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Comment thread ────────────────────────────────────────────────────────

function CommentThread({ postId, selfUid, initialCount }) {
  const [open, setOpen]         = useState(false)
  const [loading, setLoading]   = useState(false)
  const [comments, setComments] = useState([])
  const [draft, setDraft]       = useState('')
  const [posting, setPosting]   = useState(false)

  async function loadOnce() {
    setLoading(true)
    try {
      const res = await listComments(postId)
      setComments(res?.comments || [])
    } catch { /* surface inline */ }
    finally { setLoading(false) }
  }
  function toggle() {
    const next = !open
    setOpen(next)
    if (next && comments.length === 0 && !loading) loadOnce()
  }
  async function submit() {
    const text = draft.trim()
    if (!text || posting) return
    setPosting(true)
    try {
      const res = await addComment(postId, text)
      setComments(prev => [...prev, res.comment])
      setDraft('')
    } catch { /* noop */ }
    finally { setPosting(false) }
  }

  return (
    <div style={{ marginTop: 8 }}>
      <button
        onClick={toggle}
        style={{
          background: 'none', border: 'none', padding: 0, cursor: 'pointer',
          color: MUTE, fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
          display: 'inline-flex', alignItems: 'center', gap: 6,
        }}
      >
        <MessageCircle size={11}/>
        {open ? 'Hide' : initialCount > 0 ? `${initialCount} ${initialCount === 1 ? 'comment' : 'comments'}` : 'Reply'}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 10, borderLeft: `1px solid ${HAIRLINE}`, paddingLeft: 14 }}>
              {loading && (
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: DIM, margin: 0 }}>
                  Loading comments…
                </p>
              )}
              {comments.map(c => (
                <div key={c.comment_id} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, fontWeight: 500, color: c.author_id === selfUid ? GOLD : BONE }}>
                      {c.author_name}
                    </span>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM }}>{timeAgo(c.created_at)}</span>
                  </div>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, color: BONE, margin: 0, lineHeight: 1.55, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {c.text}
                  </p>
                </div>
              ))}
              <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                <input
                  value={draft}
                  onChange={e => setDraft(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') submit() }}
                  placeholder="Reply…"
                  maxLength={400}
                  style={{
                    flex: 1, padding: '8px 12px', borderRadius: 14,
                    background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
                    color: BONE, outline: 'none',
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 12,
                  }}
                />
                <button
                  onClick={submit}
                  disabled={!draft.trim() || posting}
                  style={{
                    padding: '7px 12px', borderRadius: 14,
                    background: draft.trim() ? VIOLET : 'transparent',
                    border: `1px solid ${draft.trim() ? VIOLET : HAIRLINE}`,
                    cursor: draft.trim() && !posting ? 'pointer' : 'not-allowed',
                    color: draft.trim() ? '#fff' : MUTE,
                    opacity: posting ? 0.6 : 1,
                  }}
                >
                  {posting
                    ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, ease: 'linear', repeat: Infinity }}><Loader2 size={11}/></motion.span>
                    : <Send size={11}/>}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Post card ─────────────────────────────────────────────────────────────

function PostCard({ post, selfUid, onDelete }) {
  const isMine = post.author_id === selfUid
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease }}
      style={{
        padding: '20px 24px', borderRadius: 14,
        background: 'linear-gradient(160deg,rgba(20,16,10,0.95) 0%,rgba(12,10,7,1) 100%)',
        border: `1px solid ${HAIRLINE}`,
        display: 'flex', flexDirection: 'column', gap: 12,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <div style={{
          width: 36, height: 36, borderRadius: '50%', overflow: 'hidden',
          background: 'rgba(212,182,134,0.06)', flexShrink: 0,
          border: `1px solid ${HAIRLINE}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {post.author_avatar
            ? <img src={post.author_avatar} alt={post.author_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
            : <span style={{ fontFamily: '"Cormorant Garamond",serif', fontSize: 14, color: GOLD }}>
                {(post.author_name || '?').split(/\s+/).slice(0, 2).map(s => s[0]?.toUpperCase()).join('')}
              </span>}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: isMine ? GOLD : BONE }}>
              {post.author_name}
            </span>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: DIM }}>{timeAgo(post.created_at)}</span>
          </div>
        </div>
        {isMine && (
          <button
            onClick={() => onDelete(post)}
            title="Delete post"
            style={{
              background: 'none', border: 'none', padding: 2,
              cursor: 'pointer', color: DIM,
              display: 'flex', alignItems: 'center',
            }}
          >
            <Trash2 size={12}/>
          </button>
        )}
      </div>
      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, color: BONE, margin: 0, lineHeight: 1.65, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {post.text}
      </p>
      <CommentThread postId={post.post_id} selfUid={selfUid} initialCount={post.comment_count || 0}/>
    </motion.div>
  )
}

// ── Post composer ─────────────────────────────────────────────────────────

function PostComposer({ onCreated }) {
  const [text, setText]   = useState('')
  const [busy, setBusy]   = useState(false)
  const [error, setError] = useState(null)

  async function submit() {
    const t = text.trim()
    if (!t || busy) return
    setBusy(true); setError(null)
    try {
      const res = await createPost({ text: t })
      onCreated?.(res.post)
      setText('')
    } catch (e) {
      setError(e?.message || 'Could not post')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{
      padding: '20px 24px', borderRadius: 14,
      background: 'rgba(232,212,168,0.025)', border: `1px solid ${HAIRLINE}`,
      display: 'flex', flexDirection: 'column', gap: 12,
    }}>
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="Share something — a trip you're planning, a question, a recommendation…"
        rows={3}
        maxLength={600}
        style={{
          padding: '12px 14px', borderRadius: 12,
          background: 'rgba(20,16,10,0.6)', border: `1px solid ${HAIRLINE}`,
          color: BONE, outline: 'none', resize: 'none',
          fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300,
          lineHeight: 1.6,
        }}
      />
      {error && <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: '#F87171', margin: 0 }}>{error}</p>}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: DIM }}>
          {text.length} / 600
        </span>
        <button
          onClick={submit}
          disabled={!text.trim() || busy}
          style={{
            padding: '8px 18px', borderRadius: 18,
            background: text.trim() ? `linear-gradient(135deg, ${VIOLET} 0%, #6D28D9 100%)` : 'transparent',
            border: `1px solid ${text.trim() ? VIOLET : HAIRLINE}`,
            cursor: text.trim() && !busy ? 'pointer' : 'not-allowed',
            color: text.trim() ? '#fff' : MUTE,
            fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500,
            letterSpacing: '0.2em', textTransform: 'uppercase',
            opacity: busy ? 0.7 : 1,
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          {busy
            ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, ease: 'linear', repeat: Infinity }}><Loader2 size={11}/></motion.span>
            : <Send size={11}/>}
          Post
        </button>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function Discover() {
  const navigate          = useNavigate()
  const { user }          = useAuth()
  const selfUid           = user?.uid
  const [params, setParams] = useSearchParams()
  const initialTab = params.get('tab') === 'feed' ? 'feed' : 'trips'
  const [tab, setTab] = useState(initialTab)

  // Open trips state
  const [trips, setTrips]               = useState([])
  const [tripsLoading, setTripsLoading] = useState(false)
  const [tripsError, setTripsError]     = useState(null)
  const [joinTarget, setJoinTarget]     = useState(null)
  const [joinBusy, setJoinBusy]         = useState(false)
  const [joinErr, setJoinErr]           = useState(null)

  // Feed state
  const [posts, setPosts]               = useState([])
  const [feedLoading, setFeedLoading]   = useState(false)
  const [feedError, setFeedError]       = useState(null)

  const switchTab = useCallback((t) => {
    setTab(t)
    setParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('tab', t)
      return next
    }, { replace: true })
  }, [setParams])

  // Hydrate the active tab on mount + when switched.
  useEffect(() => {
    if (!user) return
    let cancelled = false
    if (tab === 'trips') {
      setTripsLoading(true); setTripsError(null)
      ;(async () => {
        try {
          const res = await listOpenTrips(40)
          if (cancelled) return
          setTrips(res?.trips || [])
        } catch (e) {
          if (!cancelled) setTripsError(e?.message || 'Could not load trips')
        } finally {
          if (!cancelled) setTripsLoading(false)
        }
      })()
    } else {
      setFeedLoading(true); setFeedError(null)
      ;(async () => {
        try {
          const res = await listFeed({ limit: 30 })
          if (cancelled) return
          setPosts(res?.posts || [])
        } catch (e) {
          if (!cancelled) setFeedError(e?.message || 'Could not load feed')
        } finally {
          if (!cancelled) setFeedLoading(false)
        }
      })()
    }
    return () => { cancelled = true }
  }, [tab, user?.uid])

  async function submitJoin(message) {
    if (!joinTarget) return
    setJoinBusy(true); setJoinErr(null)
    try {
      const res = await requestToJoin(joinTarget.itinerary_id, message)
      const newStatus = res?.request?.status || 'proposed'
      setTrips(prev => prev.map(t =>
        t.itinerary_id === joinTarget.itinerary_id
          ? { ...t, your_request_status: newStatus }
          : t,
      ))
      setJoinTarget(null)
    } catch (e) {
      setJoinErr(e?.message || 'Could not send request')
    } finally {
      setJoinBusy(false)
    }
  }

  async function deletePostLocal(post) {
    if (!confirm('Delete this post?')) return
    try {
      await apiDeletePost(post.post_id)
      setPosts(prev => prev.filter(p => p.post_id !== post.post_id))
    } catch (e) {
      alert(e?.message || 'Could not delete')
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent={VIOLET}/>

      <nav style={{
        position: 'sticky', top: 0, zIndex: 50,
        borderBottom: `1px solid ${HAIRLINE}`,
        background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)',
        padding: '0 48px', height: 68,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/dashboard')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE,
                   display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Dashboard</span>
        </motion.button>
        <SonderNav3D markSize={32}/>
        <div style={{ width: 80 }}/>
      </nav>

      <div style={{ maxWidth: 720, margin: '0 auto', width: '100%', padding: '40px 24px 80px' }}>

        {/* hero */}
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, ease }} style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <Sparkles size={11} style={{ color: VIOLET }}/>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
              Discover
            </p>
          </div>
          <motion.h1
            animate={{ filter: [`drop-shadow(0 0 12px ${VIOLET}22)`, `drop-shadow(0 0 30px ${VIOLET}55)`, `drop-shadow(0 0 12px ${VIOLET}22)`] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
            style={{
              fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
              fontSize: 44, color: BONE, lineHeight: 1.05, margin: 0,
            }}
          >
            {tab === 'trips' ? 'Trips you could join.' : 'What travellers are saying.'}
          </motion.h1>
        </motion.div>

        {/* tab bar */}
        <div style={{ display: 'flex', gap: 4, borderBottom: `1px solid ${HAIRLINE}`, marginBottom: 28 }}>
          {[
            { key: 'trips', label: 'Open Trips' },
            { key: 'feed',  label: 'Feed' },
          ].map(t => {
            const active = tab === t.key
            return (
              <button
                key={t.key}
                onClick={() => switchTab(t.key)}
                style={{
                  position: 'relative',
                  padding: '12px 4px', marginRight: 24,
                  background: 'none', border: 'none', cursor: 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
                  letterSpacing: '0.22em', textTransform: 'uppercase',
                  color: active ? BONE : MUTE, fontWeight: active ? 500 : 400,
                  transition: 'color 0.18s',
                }}
              >
                {t.label}
                {active && (
                  <motion.span
                    layoutId="discover-tab-underline"
                    style={{
                      position: 'absolute', left: 0, right: 0, bottom: -1,
                      height: 2, background: VIOLET, borderRadius: 1,
                    }}
                  />
                )}
              </button>
            )
          })}
        </div>

        {/* OPEN TRIPS */}
        {tab === 'trips' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {tripsLoading && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: '40px 0' }}>
                <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.3, ease: 'linear', repeat: Infinity }}>
                  <Loader2 size={20} style={{ color: VIOLET }}/>
                </motion.span>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE }}>
                  Finding open trips…
                </p>
              </div>
            )}
            {tripsError && !tripsLoading && (
              <div style={{ padding: '24px', borderRadius: 12, border: '1px solid rgba(248,113,113,0.35)', background: 'rgba(248,113,113,0.04)', textAlign: 'center' }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: '#F87171', margin: 0 }}>{tripsError}</p>
              </div>
            )}
            {!tripsLoading && !tripsError && trips.length === 0 && (
              <div style={{ textAlign: 'center', padding: '60px 0' }}>
                <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 28, color: MUTE, margin: 0 }}>
                  Nobody's opened a trip yet.
                </p>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: DIM, marginTop: 10 }}>
                  Be first — open your trip to companions from your dashboard.
                </p>
              </div>
            )}
            {trips.map((t, i) => (
              <OpenTripCard
                key={t.itinerary_id}
                trip={t}
                index={i}
                onRequestJoin={(trip) => { setJoinTarget(trip); setJoinErr(null) }}
              />
            ))}
          </div>
        )}

        {/* FEED */}
        {tab === 'feed' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <PostComposer onCreated={(p) => setPosts(prev => [p, ...prev])}/>
            {feedLoading && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: '40px 0' }}>
                <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.3, ease: 'linear', repeat: Infinity }}>
                  <Loader2 size={20} style={{ color: VIOLET }}/>
                </motion.span>
              </div>
            )}
            {feedError && !feedLoading && (
              <div style={{ padding: '24px', borderRadius: 12, border: '1px solid rgba(248,113,113,0.35)', background: 'rgba(248,113,113,0.04)', textAlign: 'center' }}>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: '#F87171', margin: 0 }}>{feedError}</p>
              </div>
            )}
            {!feedLoading && !feedError && posts.length === 0 && (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: MUTE, margin: 0 }}>
                  Be the first to say something.
                </p>
              </div>
            )}
            {posts.map(p => (
              <PostCard
                key={p.post_id}
                post={p}
                selfUid={selfUid}
                onDelete={deletePostLocal}
              />
            ))}
          </div>
        )}
      </div>

      <AnimatePresence>
        {joinTarget && (
          <JoinRequestModal
            trip={joinTarget}
            onClose={() => setJoinTarget(null)}
            onSubmit={submitJoin}
            submitting={joinBusy}
            error={joinErr}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
