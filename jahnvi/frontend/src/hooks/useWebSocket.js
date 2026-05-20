import { useState, useEffect, useRef, useCallback } from 'react'
import { auth } from '../lib/firebase'
import { openChatSocket } from '../lib/api'

const RECONNECT_DELAY = 2000
const PING_INTERVAL   = 30_000

/**
 * Drives a chat WebSocket session for the signed-in user. Handles
 * first-message auth, ping heartbeat, typing/seen/presence events,
 * and exposes setters the chat page can seed with REST history.
 */
export function useWebSocket(sessionId) {
  const [messages,     setMessages]     = useState([])
  const [connected,    setConnected]    = useState(false)
  const [typingUsers,  setTypingUsers]  = useState([])
  const [seenIds,      setSeenIds]      = useState(new Set())
  const [presence,     setPresence]     = useState({})  // { user_id: bool }
  const wsRef       = useRef(null)
  const pingRef     = useRef(null)
  const typingTORef = useRef(null)
  const mountedRef  = useRef(true)

  const connect = useCallback(async () => {
    if (!sessionId || !mountedRef.current) return

    const currentUser = auth.currentUser
    if (!currentUser) return
    const token = await currentUser.getIdToken()

    const ws = openChatSocket(sessionId)
    wsRef.current = ws

    ws.addEventListener('open', () => {
      ws.send(JSON.stringify({ type: 'auth', token }))
      setConnected(true)
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, PING_INTERVAL)
    })

    ws.addEventListener('message', (e) => {
      let data
      try { data = JSON.parse(e.data) } catch { return }

      if (data.type === 'typing') {
        setTypingUsers(prev => prev.includes(data.user_id) ? prev : [...prev, data.user_id])
        clearTimeout(typingTORef.current)
        typingTORef.current = setTimeout(() => setTypingUsers([]), 3500)
      } else if (data.type === 'seen' && data.message_id) {
        setSeenIds(prev => {
          if (prev.has(data.message_id)) return prev
          const next = new Set(prev)
          next.add(data.message_id)
          return next
        })
      } else if (data.type === 'presence') {
        setPresence(prev => ({ ...prev, [data.user_id]: !!data.online }))
      } else if (data.type === 'message') {
        setMessages(prev => [...prev, data])
      }
    })

    ws.addEventListener('close', () => {
      clearInterval(pingRef.current)
      setConnected(false)
      if (mountedRef.current) setTimeout(connect, RECONNECT_DELAY)
    })

    ws.addEventListener('error', () => ws.close())
  }, [sessionId])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      clearInterval(pingRef.current)
      clearTimeout(typingTORef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((content) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', content }))
    }
  }, [])

  const sendTyping = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'typing' }))
    }
  }, [])

  const sendSeen = useCallback((messageId) => {
    if (!messageId) return
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'seen', message_id: messageId }))
    }
  }, [])

  const seedMessages = useCallback((initial) => {
    setMessages(Array.isArray(initial) ? initial : [])
    const preSeen = new Set()
    for (const m of (initial || [])) if (m?.seen && m.message_id) preSeen.add(m.message_id)
    setSeenIds(preSeen)
  }, [])

  return {
    messages, sendMessage, sendTyping, sendSeen,
    seedMessages, connected, typingUsers, seenIds, presence,
  }
}
