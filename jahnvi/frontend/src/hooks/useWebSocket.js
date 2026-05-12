import { useState, useEffect, useRef, useCallback } from 'react'
import { auth } from '../lib/firebase'
import { openChatSocket } from '../lib/api'

const RECONNECT_DELAY = 2000
const PING_INTERVAL   = 30_000

export function useWebSocket(sessionId) {
  const [messages, setMessages]     = useState([])
  const [connected, setConnected]   = useState(false)
  const [typingUsers, setTypingUsers] = useState([])
  const wsRef      = useRef(null)
  const pingRef    = useRef(null)
  const mountedRef = useRef(true)

  const connect = useCallback(async () => {
    if (!sessionId || !mountedRef.current) return

    const currentUser = auth.currentUser
    if (!currentUser) return
    const token = await currentUser.getIdToken()

    const ws = openChatSocket(sessionId)
    wsRef.current = ws

    ws.addEventListener('open', () => {
      // First-message auth: send token before any other message.
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
        setTypingUsers(data.users || [])
      } else if (data.type === 'message' || data.type === 'shreyas') {
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

  return { messages, sendMessage, sendTyping, connected, typingUsers }
}
