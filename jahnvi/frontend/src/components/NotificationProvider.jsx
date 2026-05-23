import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useLocation, useNavigate } from 'react-router-dom'
import { MessageCircle, MapPin, Sparkles, X } from 'lucide-react'
import { auth } from '../lib/firebase'
import { openNotificationSocket } from '../lib/api'
import { ensurePushSubscribed, dropPushSubscription, pushSupported } from '../lib/push'
import { BG, BONE, MUTE } from '../lib/tokens'
import SynthBadge from './SynthBadge'

const ROSE   = '#F43F5E'
const VIOLET = '#8B5CF6'
const GOLD   = '#D4B686'
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
    // Real-time fan-out for the new social surfaces. Each event type
    // gets re-dispatched as a window CustomEvent so the relevant page
    // (Dashboard's incoming-requests panel, Discover's Open Trips
    // tab, the Feed's comment threads) can listen independently
    // without coupling to this provider.
    if (data?.type === 'join_request_new' && data.request) {
      window.dispatchEvent(new CustomEvent('sonder:join_request:new', { detail: data.request }))
      return
    }
    if (data?.type === 'join_request_resolved' && data.request) {
      window.dispatchEvent(new CustomEvent('sonder:join_request:resolved', { detail: data.request }))
      return
    }
    if (data?.type === 'comment_new' && data.comment) {
      window.dispatchEvent(new CustomEvent('sonder:comment:new', {
        detail: { post_id: data.post_id, comment: data.comment },
      }))
      return
    }
    if (data?.type === 'discover_trip_open' && data.trip) {
      window.dispatchEvent(new CustomEvent('sonder:discover:trip_open', { detail: data.trip }))
      // Surface a small banner unless the user is already looking at
      // /discover — there the card itself is the notification.
      if (!locRef.current.startsWith('/dashboard')) {
        const trip = data.trip
        const where = trip.destination_city
          ? trip.destination_country
            ? `${trip.destination_city}, ${trip.destination_country}`
            : trip.destination_city
          : 'somewhere'
        setBanner({
          kind:    'trip',
          title:   `${trip.owner_name || 'Someone'} opened a trip`,
          preview: `${where}${trip.note ? ' — ' + trip.note : ''}`,
          link:    '/dashboard',
        })
      }
      return
    }
    if (data?.type === 'discover_trip_close' && data.itinerary_id) {
      window.dispatchEvent(new CustomEvent('sonder:discover:trip_close', { detail: { itinerary_id: data.itinerary_id } }))
      return
    }
    if (data?.type === 'discover_post_new' && data.post) {
      window.dispatchEvent(new CustomEvent('sonder:discover:post_new', { detail: data.post }))
      if (!locRef.current.startsWith('/dashboard')) {
        const post = data.post
        setBanner({
          kind:    'post',
          title:   post.author_name || 'New post',
          preview: (post.text || '').slice(0, 140),
          link:    '/dashboard',
        })
      }
      return
    }
    if (data?.type !== 'chat_notification') return
    const { session_id, sender_name, sender_is_seed, preview } = data
    // Suppress if the user is already on the chat page for this session —
    // they're literally looking at the message arrive.
    if (locRef.current === `/chat/${session_id}`) return

    setBanner({
      kind:        'chat',
      sessionId:   session_id,
      title:       sender_name || 'New message',
      senderIsSeed: !!sender_is_seed,
      preview:     preview || '',
      link:        `/chat/${session_id}`,
    })

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
        {banner && (() => {
          const kind = banner.kind || 'chat'
          const accent = kind === 'trip' ? VIOLET : kind === 'post' ? GOLD : ROSE
          const Icon = kind === 'trip' ? MapPin : kind === 'post' ? Sparkles : MessageCircle
          return (
          <motion.div
            initial={{ opacity: 0, y: -24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -24, scale: 0.96 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            style={{
              position: 'fixed', top: 24, right: 24, zIndex: 9999,
              minWidth: 280, maxWidth: 380,
              background: `linear-gradient(135deg, ${BG}f5 0%, rgba(20,16,12,0.96) 100%)`,
              border: `1px solid ${accent}55`,
              borderRadius: 14,
              boxShadow: `0 24px 56px rgba(0,0,0,0.5), 0 0 32px ${accent}22`,
              padding: '14px 18px',
              display: 'flex', alignItems: 'flex-start', gap: 12,
              cursor: 'pointer', backdropFilter: 'blur(20px)',
            }}
            onClick={() => { navigate(banner.link || '/'); setBanner(null) }}
          >
            <div style={{
              width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
              background: `linear-gradient(135deg, ${accent} 0%, ${accent}cc 100%)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: `0 0 18px ${accent}66`,
            }}>
              <Icon size={16} style={{ color: '#fff' }}/>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                <p style={{
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 11, fontWeight: 500,
                  color: BONE, margin: 0, letterSpacing: '0.04em',
                }}>
                  {banner.title}
                </p>
                {kind === 'chat' && <SynthBadge isSeed={banner.senderIsSeed} variant="inline" />}
              </div>
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
          )
        })()}
      </AnimatePresence>
    </NotificationContext.Provider>
  )
}

