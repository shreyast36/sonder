import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { auth } from '../lib/firebase'
import { BG, BONE, MUTE, HAIRLINE } from '../lib/tokens'

const ORANGE = '#F97316'
const RED    = '#EF4444'

const BASE = import.meta.env.VITE_API_BASE_URL || ''

function btn(color) {
  return {
    minWidth: 280, padding: '18px 32px',
    background: `linear-gradient(135deg, ${color} 0%, #B91C1C 100%)`,
    border: 'none', borderRadius: 12, cursor: 'pointer',
    fontFamily: '"Inter Tight", sans-serif',
    fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase',
    fontWeight: 500, color: '#fff',
    boxShadow: `0 0 36px ${color}44`,
  }
}

export default function DebugSentry() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('')

  function throwError() {
    setStatus('throwing frontend error…')
    setTimeout(() => { throw new Error('Debug: first frontend error from /debug/sentry') }, 0)
  }

  async function hitBadEndpoint() {
    setStatus('calling /api/plan-trip with bad payload…')
    try {
      const token = auth.currentUser ? await auth.currentUser.getIdToken() : 'no-token'
      const res = await fetch(`${BASE}/api/plan-trip`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        // Empty constraints will pass Pydantic but crash deeper in the pipeline.
        body: JSON.stringify({ constraints: {}, persona_answers: { small_thing: '' } }),
      })
      setStatus(`backend returned ${res.status} — check Sentry for the captured pipeline exception`)
    } catch (err) {
      setStatus(`fetch error: ${err.message}`)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, gap: 18 }}>
      <h1 style={{ fontFamily: '"Cormorant Garamond", serif', fontStyle: 'italic', fontSize: 38, margin: 0 }}>
        Sentry debug
      </h1>
      <p style={{ fontFamily: '"Inter Tight", sans-serif', fontWeight: 300, fontSize: 12, color: MUTE, maxWidth: 480, textAlign: 'center', marginBottom: 12 }}>
        Each button sends a real error to Sentry. After clicking, check the matching Sentry project's Issues tab.
      </p>

      <button onClick={throwError} style={btn(RED)}>
        Throw frontend error
      </button>
      <button onClick={hitBadEndpoint} style={btn(ORANGE)}>
        Trigger backend error
      </button>

      {status && (
        <p style={{ fontFamily: '"Inter Tight", sans-serif', fontSize: 11, color: MUTE, marginTop: 8, maxWidth: 480, textAlign: 'center' }}>
          {status}
        </p>
      )}

      <button
        onClick={() => navigate('/dashboard')}
        style={{ marginTop: 24, padding: '10px 24px', background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 8, color: MUTE, cursor: 'pointer', fontFamily: '"Inter Tight", sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}
      >
        Back to dashboard
      </button>
    </div>
  )
}
