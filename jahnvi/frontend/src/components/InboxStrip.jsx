import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { MessageCircle, Loader2 } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { listInbox } from '../lib/api'
import SynthBadge from './SynthBadge'

const ROSE = '#F43F5E'
const GREEN = '#10B981'

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

// ── row ──────────────────────────────────────────────────────────────────

function InboxRow({ row, selfUid, onClick, index }) {
  const isMine = row.last_sender_id === selfUid
  const accent =
    row.approval_status === 'approved' ? GREEN :
    row.approval_status === 'denied'   ? MUTE :
                                          ROSE
  return (
    <motion.button
      layout
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.35, delay: 0.05 + index * 0.04, ease }}
      whileHover={{ y: -2, borderColor: `${accent}55` }}
      onClick={onClick}
      style={{
        width: '100%', padding: '14px 16px', borderRadius: 14,
        background: 'rgba(232,212,168,0.025)',
        border: `1px solid ${HAIRLINE}`,
        cursor: 'pointer', textAlign: 'left',
        display: 'flex', alignItems: 'center', gap: 14,
        transition: 'all 0.18s',
      }}
    >
      {/* avatar */}
      <div style={{
        position: 'relative',
        width: 42, height: 42, borderRadius: '50%', flexShrink: 0,
        overflow: 'hidden',
        background: 'linear-gradient(160deg, rgba(212,182,134,0.10) 0%, rgba(20,15,10,1) 100%)',
        border: `1px solid ${accent}55`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {row.other_avatar
          ? <img src={row.other_avatar} alt={row.other_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
          : <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 17, color: accent }}>
              {initials(row.other_name)}
            </span>}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 3 }}>
          <span style={{
            fontFamily: '"Inter Tight",sans-serif', fontSize: 12.5, fontWeight: 500,
            color: BONE, letterSpacing: '0.01em',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {row.other_name}
          </span>
          <SynthBadge isSeed={row.other_is_seed} variant="inline"/>
          <span style={{ flex: 1 }}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9.5, color: DIM, flexShrink: 0 }}>
            {timeAgo(row.last_message_at)}
          </span>
        </div>
        <p style={{
          fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12,
          color: MUTE, margin: 0, lineHeight: 1.45,
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

      {row.approval_status === 'approved' && (
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

// ── section ──────────────────────────────────────────────────────────────

export default function InboxStrip({ selfUid, limit = 8 }) {
  const navigate = useNavigate()
  const [rows, setRows]       = useState([])
  const [loading, setLoading] = useState(true)
  const pollRef = useRef(null)

  const fetchInbox = useCallback(async () => {
    try {
      const res = await listInbox()
      setRows(res?.sessions || [])
    } catch (e) {
      console.warn('listInbox failed:', e?.message || e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchInbox()
    // Mid-frequency poll. The chat_notification WS push also triggers a
    // refetch below so new sessions appear without waiting.
    pollRef.current = setInterval(fetchInbox, 25_000)
    return () => clearInterval(pollRef.current)
  }, [fetchInbox])

  useEffect(() => {
    // The notification socket fans out 'chat_notification' for every
    // inbound chat message — refetch the inbox on any of them so the
    // ordering + preview updates live. NotificationProvider re-dispatches
    // these as a window event we can hook.
    function onInbound() { fetchInbox() }
    window.addEventListener('sonder:inbox:refresh', onInbound)
    return () => window.removeEventListener('sonder:inbox:refresh', onInbound)
  }, [fetchInbox])

  // Always render the section so empty + loaded share the same frame.
  return (
    <div style={{
      padding: '20px 22px', borderRadius: 16,
      background: 'rgba(232,212,168,0.03)',
      border: `1px solid ${HAIRLINE}`,
      display: 'flex', flexDirection: 'column', gap: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
        <motion.span
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
          style={{ width: 6, height: 6, borderRadius: '50%', background: ROSE, boxShadow: `0 0 10px ${ROSE}` }}
        />
        <p style={{
          fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em',
          textTransform: 'uppercase', color: MUTE, margin: 0,
        }}>
          Inbox
        </p>
        <span style={{ flex: 1 }}/>
        {rows.length > 0 && (
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9.5, color: DIM, letterSpacing: '0.04em' }}>
            {rows.length} {rows.length === 1 ? 'conversation' : 'conversations'}
          </span>
        )}
      </div>

      {loading && rows.length === 0 && (
        <div style={{ padding: '14px 4px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.2, ease: 'linear', repeat: Infinity }}>
            <Loader2 size={13} style={{ color: ROSE }}/>
          </motion.span>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE }}>
            Loading inbox…
          </span>
        </div>
      )}

      {!loading && rows.length === 0 && (
        <div style={{ padding: '18px 4px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <MessageCircle size={13} style={{ color: MUTE }}/>
            <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 15, color: BONE, margin: 0 }}>
              Your inbox is quiet for now.
            </p>
          </div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 11, color: MUTE, margin: 0, lineHeight: 1.55 }}>
            New matches start chats here. Travellers exploring your destination might reach out too.
          </p>
        </div>
      )}

      <AnimatePresence initial={false}>
        {rows.slice(0, limit).map((r, i) => (
          <InboxRow
            key={r.session_id}
            row={r}
            selfUid={selfUid}
            index={i}
            onClick={() => navigate(`/chat/${encodeURIComponent(r.session_id)}`)}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}
