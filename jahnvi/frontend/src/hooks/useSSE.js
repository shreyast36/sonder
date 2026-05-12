import { useState, useRef, useCallback } from 'react'
import { planTrip } from '../lib/api'

export function useSSE(handlers) {
  const [status, setStatus] = useState('idle')
  const abortRef = useRef(null)

  const start = useCallback(async (userProfile) => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setStatus('streaming')

    try {
      const res = await planTrip(userProfile)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer    = ''
      let eventName = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() // keep incomplete line

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventName = line.slice(6).trim()
          } else if (line.startsWith('data:')) {
            const raw     = line.slice(5).trim()
            const handler = handlers[eventName]
            if (handler) {
              try { handler(raw ? JSON.parse(raw) : undefined) } catch { /* malformed data */ }
            }
            eventName = null
          } else if (line === '') {
            eventName = null // reset between SSE blocks
          }
        }
      }

      setStatus('done')
    } catch (err) {
      if (err.name === 'AbortError') return
      setStatus('error')
      handlers.error?.({ step: 'stream', message: err.message })
    }
  }, [handlers])

  const abort = useCallback(() => {
    abortRef.current?.abort()
    setStatus('idle')
  }, [])

  return { status, start, abort }
}
