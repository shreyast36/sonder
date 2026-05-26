import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Inbox as InboxIcon, MessageCircle, Loader2,
  Heart, Clock, Sparkles,
} from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { listInbox } from '../lib/api'
import SynthBadge from './SynthBadge'

const ROSE   = '#F43F5E'
const VIOLET = '#8B5CF6'
const GREEN  = '#10B981'
const AMBER  = '#F59E0B'

// ── helpers ──────────────────────────────────────────────────────────────

function timeAgo(iso) {
  if (!iso) return ''
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 30_000)    return 'just now'
  if (ms < 3600_000)  return `${Math.floor(ms / 60_000)}m`
  if (ms < 86400_000) return `${Math.floor(ms / 3600_000)}h`
  return `${Math.floor(ms / 86400_000)}d`
}

function initials(name) {
  return (name || '?').split(/\s+/).slice(0, 2).map(s => s[0]?.toUpperCase()).join('')
}

// ── Read-state tracking (localStorage; backend last_read field is V2) ───
//
// Per-(uid, session_id) ISO timestamp of when this browser last opened
// the chat. A session counts as unread if last_message_at is newer.
// Storing per-uid means a logged-out / logged-in different account
// doesn't inherit someone else's reads.

const READ_KEY_PREFIX = 'sonder:inbox:lastread'
const ROWS_KEY_PREFIX = 'sonder:inbox:rows'

function readKey(uid) { return `${READ_KEY_PREFIX}:${uid || 'anon'}` }
function rowsKey(uid) { return `${ROWS_KEY_PREFIX}:${uid || 'anon'}` }

function loadRows(uid) {
  try {
    const raw = localStorage.getItem(rowsKey(uid))
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed
    }
  } catch { /* noop */ }
  return []
}

function saveRows(uid, rows) {
  try { localStorage.setItem(rowsKey(uid), JSON.stringify(rows || [])) } catch { /* noop */ }
}

function loadReadMap(uid) {
  try {
    const raw = localStorage.getItem(readKey(uid))
    if (raw) return JSON.parse(raw) || {}
  } catch { /* noop */ }
  return {}
}

function saveReadMap(uid, map) {
  try { localStorage.setItem(readKey(uid), JSON.stringify(map)) } catch { /* noop */ }
}

function isUnread(session, readMap) {
  if (!session?.last_message_at) return false
  // Sessions with zero messages aren't "unread" — there's nothing to read.
  if (!(session.message_count > 0)) return false
  const lastRead = readMap[session.session_id]
  if (!lastRead) return true
  return new Date(session.last_message_at).getTime() > new Date(lastRead).getTime()
}

// ── Category definitions ────────────────────────────────────────────────

const CATEGORIES = [
  { key: 'all',      label: 'All conversations', icon: InboxIcon,     accent: BONE },
  { key: 'unread',   label: 'Unread',            icon: MessageCircle, accent: ROSE  },
  { key: 'matched',  label: 'Matched',           icon: Heart,         accent: GREEN },
  { key: 'pending',  label: 'Awaiting reply',    icon: Clock,         accent: AMBER },
  { key: 'curated',  label: 'Sonder Curated',    icon: Sparkles,      accent: GOLD  },
]

function matchesCategory(session, cat, readMap) {
  switch (cat) {
    case 'all':     return true
    case 'unread':  return isUnread(session, readMap)
    case 'matched': return session.approval_status === 'approved'
    case 'pending': return session.approval_status === 'pending'
    case 'curated': return !!session.other_is_seed
    default:        return true
  }
}

// ── Row ─────────────────────────────────────────────────────────────────

function InboxRow({ row, selfUid, unread, onClick, index }) {
  const isMine = row.last_sender_id === selfUid
  const accent =
    unread                                ? ROSE  :
    row.approval_status === 'approved'    ? GREEN :
    row.approval_status === 'denied'      ? MUTE  :
                                             VIOLET
  return (
    <motion.button
      layout
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: 0.04 * index, ease }}
      whileHover={{ x: 2, borderColor: `${accent}66` }}
      onClick={onClick}
      style={{
        width: '100%', padding: '16px 18px', borderRadius: 14,
        background: unread ? 'rgba(244,63,94,0.045)' : 'rgba(232,212,168,0.025)',
        border: `1px solid ${unread ? `${ROSE}33` : HAIRLINE}`,
        cursor: 'pointer', textAlign: 'left',
        display: 'flex', alignItems: 'center', gap: 14,
        transition: 'all 0.16s',
        position: 'relative',
      }}
    >
      {unread && (
        <span style={{
          position: 'absolute', left: 6, top: '50%', transform: 'translateY(-50%)',
          width: 5, height: 5, borderRadius: '50%',
          background: ROSE, boxShadow: `0 0 8px ${ROSE}`,
        }}/>
      )}

      {/* avatar */}
      <div style={{
        width: 44, height: 44, borderRadius: '50%', flexShrink: 0,
        overflow: 'hidden',
        background: 'linear-gradient(160deg, rgba(212,182,134,0.10) 0%, rgba(20,15,10,1) 100%)',
        border: `1px solid ${accent}55`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {row.other_avatar
          ? <img src={row.other_avatar} alt={row.other_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
          : <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 18, color: accent }}>
              {initials(row.other_name)}
            </span>}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 3 }}>
          <span style={{
            fontFamily: '"Inter Tight",sans-serif', fontSize: 13,
            fontWeight: unread ? 600 : 500,
            color: BONE, letterSpacing: '0.01em',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {row.other_name}
          </span>
          <SynthBadge isSeed={row.other_is_seed} variant="inline"/>
          <span style={{ flex: 1 }}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: unread ? ROSE : DIM, flexShrink: 0, fontWeight: unread ? 500 : 400 }}>
            {timeAgo(row.last_message_at)}
          </span>
        </div>
        <p style={{
          fontFamily: '"Inter Tight",sans-serif',
          fontWeight: unread ? 400 : 300,
          fontSize: 12.5, color: unread ? BONE : MUTE,
          margin: 0, lineHeight: 1.45,
          display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical',
          overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {!row.last_message_preview ? (
            <span style={{ fontStyle: 'italic', color: DIM }}>(no messages yet)</span>
          ) : (
            <>
              {isMine && <span style={{ color: DIM }}>you: </span>}
              {row.last_message_preview}
            </>
          )}
        </p>
      </div>

      {row.approval_status === 'approved' && !unread && (
        <span style={{
          fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.24em', textTransform: 'uppercase',
          color: GREEN, padding: '3px 8px', borderRadius: 8,
          background: `${GREEN}10`, border: `1px solid ${GREEN}44`, flexShrink: 0,
        }}>
          Matched
        </span>
      )}
    </motion.button>
  )
}

// ── Layout ──────────────────────────────────────────────────────────────

export default function InboxLayout({ selfUid }) {
  const navigate = useNavigate()
  // Stale-while-revalidate: hydrate from localStorage synchronously
  // so reload shows last-known conversations immediately, before any
  // network round-trip. Empty API responses never overwrite the
  // cached state (transient backend hiccups / cold deploys preserve
  // your last good view).
  const [rows, setRows]       = useState(() => loadRows(selfUid))
  const [loading, setLoading] = useState(() => loadRows(selfUid).length === 0)
  const [activeCat, setActiveCat] = useState('all')
  const [readMap, setReadMap] = useState(() => loadReadMap(selfUid))
  const pollRef = useRef(null)

  const fetchInbox = useCallback(async () => {
    try {
      const res = await listInbox()
      const next = res?.sessions || []
      // Only overwrite cached state on a NON-empty response so a
      // single 5xx / Firestore cold-start doesn't blank the inbox.
      if (next.length > 0) {
        setRows(next)
        saveRows(selfUid, next)
      }
    } catch (e) {
      console.warn('listInbox failed:', e?.message || e)
    } finally {
      setLoading(false)
    }
  }, [selfUid])

  useEffect(() => {
    fetchInbox()
    pollRef.current = setInterval(fetchInbox, 20_000)
    return () => clearInterval(pollRef.current)
  }, [fetchInbox])

  useEffect(() => {
    // NotificationProvider fires this on every chat_notification.
    function onInbound() { fetchInbox() }
    window.addEventListener('sonder:inbox:refresh', onInbound)
    return () => window.removeEventListener('sonder:inbox:refresh', onInbound)
  }, [fetchInbox])

  // Counts per category for the sidebar — recomputed on rows / readMap change.
  const counts = useMemo(() => {
    const out = {}
    for (const cat of CATEGORIES) {
      out[cat.key] = rows.filter(r => matchesCategory(r, cat.key, readMap)).length
    }
    return out
  }, [rows, readMap])

  const filtered = useMemo(
    () => rows.filter(r => matchesCategory(r, activeCat, readMap)),
    [rows, activeCat, readMap],
  )

  function openRow(row) {
    // Mark read locally, persist, then navigate. State update is
    // synchronous so the unread badge disappears before the route change.
    const next = { ...readMap, [row.session_id]: new Date().toISOString() }
    setReadMap(next)
    saveReadMap(selfUid, next)
    navigate(`/chat/${encodeURIComponent(row.session_id)}`)
  }

  function markAllRead() {
    // Stamp every visible session as read at "now". Drops the unread
    // count to zero for the current category; the All view's unread
    // sub-count drops too because isUnread() reads from the same map.
    const now = new Date().toISOString()
    const next = { ...readMap }
    for (const r of filtered) {
      if (r.session_id) next[r.session_id] = now
    }
    setReadMap(next)
    saveReadMap(selfUid, next)
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'minmax(220px, 260px) 1fr',
      gap: 24, alignItems: 'start',
    }}>
      {/* ───── LEFT — category sidebar ───── */}
      <aside style={{
        position: 'sticky', top: 92,
        display: 'flex', flexDirection: 'column', gap: 4,
        padding: '14px', borderRadius: 16,
        background: 'rgba(232,212,168,0.03)',
        border: `1px solid ${HAIRLINE}`,
      }}>
        <p style={{
          padding: '6px 12px 10px',
          fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em',
          textTransform: 'uppercase', color: MUTE, margin: 0,
        }}>
          Filters
        </p>
        {CATEGORIES.map(cat => {
          const Icon = cat.icon
          const active = cat.key === activeCat
          const count = counts[cat.key] || 0
          const isUnreadCat = cat.key === 'unread' && count > 0
          return (
            <motion.button
              key={cat.key}
              whileHover={!active ? { x: 2 } : {}}
              whileTap={{ scale: 0.98 }}
              onClick={() => setActiveCat(cat.key)}
              style={{
                position: 'relative',
                padding: '11px 14px', borderRadius: 12,
                background: active ? `linear-gradient(135deg, ${cat.accent}18 0%, rgba(232,212,168,0.04) 100%)` : 'transparent',
                border: active ? `1px solid ${cat.accent}44` : '1px solid transparent',
                cursor: 'pointer', textAlign: 'left',
                display: 'flex', alignItems: 'center', gap: 10,
                color: active ? BONE : MUTE,
                transition: 'all 0.16s',
              }}
            >
              <Icon size={14} style={{ color: active ? cat.accent : MUTE, flexShrink: 0 }}/>
              <span style={{
                flex: 1,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 12,
                fontWeight: active ? 500 : 400, letterSpacing: '0.02em',
              }}>
                {cat.label}
              </span>
              {count > 0 && (
                <span style={{
                  minWidth: 22, padding: '2px 7px', borderRadius: 999,
                  background: isUnreadCat
                    ? `linear-gradient(135deg, ${ROSE} 0%, #E11D48 100%)`
                    : active ? `${cat.accent}22` : 'rgba(232,212,168,0.06)',
                  color: isUnreadCat ? '#fff' : active ? cat.accent : MUTE,
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, fontWeight: 600,
                  textAlign: 'center', lineHeight: 1.4,
                  boxShadow: isUnreadCat ? `0 2px 8px ${ROSE}55` : 'none',
                }}>
                  {count}
                </span>
              )}
            </motion.button>
          )
        })}
      </aside>

      {/* ───── RIGHT — message rows for the active category ───── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {/* Category header — labels the active filter + total count */}
        {(() => {
          const cat = CATEGORIES.find(c => c.key === activeCat)
          const Icon = cat.icon
          return (
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, padding: '4px 4px 8px' }}>
              <Icon size={14} style={{ color: cat.accent }}/>
              <p style={{
                fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
                fontSize: 22, color: BONE, margin: 0,
              }}>
                {cat.label}
              </p>
              <span style={{ flex: 1 }}/>
              {filtered.some(r => isUnread(r, readMap)) && (
                <button
                  onClick={markAllRead}
                  style={{
                    background: `${ROSE}10`,
                    border: `1px solid ${ROSE}55`,
                    borderRadius: 999,
                    padding: '6px 12px', cursor: 'pointer',
                    color: ROSE, fontFamily: '"Inter Tight",sans-serif',
                    fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase',
                    fontWeight: 500, marginRight: 12,
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = `${ROSE}1f` }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = `${ROSE}10` }}
                >
                  Mark all read
                </button>
              )}
              <span style={{
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE,
                letterSpacing: '0.22em', textTransform: 'uppercase',
              }}>
                {filtered.length} {filtered.length === 1 ? 'conversation' : 'conversations'}
              </span>
            </div>
          )
        })()}

        {loading && rows.length === 0 && (
          <div style={{ padding: '24px 18px', display: 'flex', alignItems: 'center', gap: 10, color: MUTE }}>
            <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.2, ease: 'linear', repeat: Infinity }}>
              <Loader2 size={14} style={{ color: ROSE }}/>
            </motion.span>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase' }}>
              Loading inbox…
            </span>
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div style={{
            padding: '36px 24px', borderRadius: 14,
            border: `1px dashed ${HAIRLINE}`, textAlign: 'center',
            display: 'flex', flexDirection: 'column', gap: 6,
          }}>
            <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 18, color: BONE, margin: 0 }}>
              {activeCat === 'unread'  ? 'You\'re all caught up.'
              : activeCat === 'matched' ? 'No matched conversations yet.'
              : activeCat === 'pending' ? 'Nobody\'s waiting on you.'
              : activeCat === 'curated' ? 'No curated travellers in your inbox.'
              :                            'Your inbox is quiet for now.'}
            </p>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 11.5, color: MUTE, margin: 0, lineHeight: 1.55 }}>
              {activeCat === 'all'
                ? 'Travellers exploring your destination may reach out soon.'
                : 'Switch to All to see every conversation.'}
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {filtered.map((r, i) => (
            <InboxRow
              key={r.session_id}
              row={r}
              selfUid={selfUid}
              unread={isUnread(r, readMap)}
              index={i}
              onClick={() => openRow(r)}
            />
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
