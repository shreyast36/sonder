import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useLocation, useNavigate } from 'react-router-dom'
import { MessageCircle, X } from 'lucide-react'
import { auth } from '../lib/firebase'
import { openNotificationSocket } from '../lib/api'
import { ensurePushSubscribed, dropPushSubscription, pushSupported } from '../lib/push'
import { BG, BONE, MUTE } from '../lib/tokens'

const ROSE = '#F43F5E'
const NotificationContext = createContext(null)
export const useNotifications = () => useContext(NotificationContext)

const RECONNECT_DELAY = 3000
const PING_INTERVAL   = 30_000
const BANNER_TTL_MS   = 5500

/**
 * Mounts once at the App root. Opens a global WebSocket to /ws/notifications,
 * shows an in-app banner for incoming chat messages when the user isn't on
 * the matching chat page, and fires a browser Notification when the tab is
 * hidden. Permission is requested lazily on the first inbound event.
 */
export default function NotificationProvider({ children }) {
  const location  = useLocation()
  const navigate  = useNavigate()
  const [banner, setBanner] = useState(null)   // {sessionId, senderName, preview}
  const wsRef     = useRef(null)
  const pingRef   = useRef(null)
  const mountedRef= useRef(true)
  const locRef    = useRef(location.pathname)
  const permRef   = useRef(typeof Notification !== 'undefined' ? Notification.permission : 'denied')
  // True once the service worker has an active push subscription. When true,
  // the SW receives notifications from the push service and shows them — we
  // must NOT also call `new Notification(...)` here or the user sees two.
  const swPushActiveRef = useRef(false)

  useEffect(() => { locRef.current = location.pathname }, [location.pathname])

  const dismiss = useCallback(() => setBanner(null), [])

  const handleEvent = useCallback((data) => {
    if (data?.type !== 'chat_notification') return
    const { session_id, sender_name, preview } = data
    // Suppress if the user is already on the chat page for this session —
    // they're literally looking at the message arrive.
    if (locRef.current === `/chat/${session_id}`) return

    setBanner({ sessionId: session_id, senderName: sender_name || 'New message', preview: preview || '' })

    // OS notification when the tab is hidden — but only when the service
    // worker DIDN'T already get a push for this message. If swPushActive is
    // true, the SW path is firing its own notification and doubling up here
    // would show two.
    if (typeof document !== 'undefined' && document.hidden && !swPushActiveRef.current) {
      const fire = (perm) => {
        if (perm !== 'granted') return
        try {
          const n = new Notification(sender_name || 'New message on Sonder', {
            body: preview || '',
            tag:  `sonder-chat-${session_id}`,
          })
          n.onclick = () => {
            window.focus()
            navigate(`/chat/${session_id}`)
            n.close()
          }
        } catch { /* notifications API unavailable */ }
      }
      if (permRef.current === 'granted') fire('granted')
      else if (permRef.current === 'default' && typeof Notification !== 'undefined') {
        Notification.requestPermission().then(p => {
          permRef.current = p
          fire(p)
          // Permission just flipped — try to upgrade to true Web Push so the
          // user gets notifications even when the tab is closed.
          if (p === 'granted') {
            ensurePushSubscribed().then(sub => { swPushActiveRef.current = !!sub })
          }
        })
      }
    }
  }, [navigate])

  const connect = useCallback(async () => {
    if (!mountedRef.current) return
    const u = auth.currentUser
    if (!u) return
    const token = await u.getIdToken()

    const ws = openNotificationSocket()
    wsRef.current = ws

    ws.addEventListener('open', () => {
      ws.send(JSON.stringify({ type: 'auth', token }))
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }))
      }, PING_INTERVAL)
    })

    ws.addEventListener('message', (e) => {
      let data
      try { data = JSON.parse(e.data) } catch { return }
      handleEvent(data)
    })

    ws.addEventListener('close', () => {
      clearInterval(pingRef.current)
      if (mountedRef.current) setTimeout(connect, RECONNECT_DELAY)
    })
    ws.addEventListener('error', () => ws.close())
  }, [handleEvent])

  useEffect(() => {
    mountedRef.current = true
    const unsub = auth.onAuthStateChanged((u) => {
      if (u) {
        connect()
        // If permission was already granted on a previous visit, attach the
        // service-worker push subscription silently so closed-browser pushes
        // start working immediately — no permission prompt needed.
        if (
          pushSupported() &&
          typeof Notification !== 'undefined' &&
          Notification.permission === 'granted'
        ) {
          ensurePushSubscribed().then(sub => { swPushActiveRef.current = !!sub })
        }
      } else {
        clearInterval(pingRef.current)
        wsRef.current?.close()
        wsRef.current = null
        swPushActiveRef.current = false
        dropPushSubscription()
      }
    })
    return () => {
      mountedRef.current = false
      unsub()
      clearInterval(pingRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  // Auto-dismiss the banner after a few seconds.
  useEffect(() => {
    if (!banner) return
    const t = setTimeout(() => setBanner(null), BANNER_TTL_MS)
    return () => clearTimeout(t)
  }, [banner])

  return (
    <NotificationContext.Provider value={{ dismiss }}>
      {children}
      <AnimatePresence>
        {banner && (
          <motion.div
            initial={{ opacity: 0, y: -24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -24, scale: 0.96 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            style={{
              position: 'fixed', top: 24, right: 24, zIndex: 9999,
              minWidth: 280, maxWidth: 380,
              background: `linear-gradient(135deg, ${BG}f5 0%, rgba(20,16,12,0.96) 100%)`,
              border: `1px solid ${ROSE}55`,
              borderRadius: 14,
              boxShadow: `0 24px 56px rgba(0,0,0,0.5), 0 0 32px ${ROSE}22`,
              padding: '14px 18px',
              display: 'flex', alignItems: 'flex-start', gap: 12,
              cursor: 'pointer', backdropFilter: 'blur(20px)',
            }}
            onClick={() => { navigate(`/chat/${banner.sessionId}`); setBanner(null) }}
          >
            <div style={{
              width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
              background: `linear-gradient(135deg, ${ROSE} 0%, #E11D48 100%)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: `0 0 18px ${ROSE}66`,
            }}>
              <MessageCircle size={16} style={{ color: '#fff' }}/>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{
                fontFamily: '"Inter Tight",sans-serif', fontSize: 11, fontWeight: 500,
                color: BONE, margin: 0, letterSpacing: '0.04em',
              }}>
                {banner.senderName}
              </p>
              <p style={{
                fontFamily: '"Inter Tight",sans-serif', fontSize: 12, fontWeight: 300,
                color: MUTE, margin: '3px 0 0', lineHeight: 1.45,
                overflow: 'hidden', display: '-webkit-box',
                WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
              }}>
                {banner.preview}
              </p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setBanner(null) }}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: MUTE, padding: 4, display: 'flex',
              }}
              aria-label="Dismiss notification"
            >
              <X size={14}/>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </NotificationContext.Provider>
  )
}

