import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { onAuthStateChanged } from 'firebase/auth'
import { BG, BONE, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import { auth } from '../lib/firebase'
import { inferPersona } from '../lib/api'

const ORANGE = '#F97316'
const spring = { type: 'spring', stiffness: 280, damping: 22 }
const PERSONA_CACHE_KEY = 'sonder_persona_v1'

// Tiny stable hash so we can auto-invalidate the persona cache when the
// underlying trip answers actually change. Not cryptographic — collision
// resistance doesn't matter, only equality detection.
function _signature(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0
  return h
}

export default function PersonaReveal() {
  const navigate = useNavigate()
  const [state, setState] = useState({ status: 'loading', persona: null, error: null })

  useEffect(() => {
    const raw = sessionStorage.getItem('sonder_trip_profile')
    if (!raw) {
      navigate('/preferences')
      return
    }
    let profile
    try { profile = JSON.parse(raw) } catch { navigate('/preferences'); return }

    const sig = _signature(raw)

    // Reuse the previously inferred persona unless the user actually changed
    // their answers. localStorage so it survives tab close; signature gate so
    // a fresh trip auto-invalidates instead of showing the old persona.
    const cachedRaw = localStorage.getItem(PERSONA_CACHE_KEY)
    if (cachedRaw) {
      try {
        const cached = JSON.parse(cachedRaw)
        if (cached?.signature === sig && cached?.persona?.descriptor) {
          setState({ status: 'ready', persona: cached.persona, error: null })
          return
        }
      } catch { /* fall through and re-infer */ }
    }

    // Wait for Firebase to restore the auth state before calling the endpoint.
    // `auth.currentUser` is null on first mount until onAuthStateChanged fires.
    const unsub = onAuthStateChanged(auth, (user) => {
      if (!user) {
        navigate('/signin')
        return
      }
      inferPersona(profile)
        .then(persona => {
          try {
            localStorage.setItem(PERSONA_CACHE_KEY, JSON.stringify({ signature: sig, persona }))
          } catch { /* quota / private-mode — ignore */ }
          setState({ status: 'ready', persona, error: null })
        })
        .catch(err => setState({ status: 'error', persona: null, error: err.message || 'Could not read your persona' }))
    })
    return () => unsub()
  }, [navigate])

  function handleConfirm() {
    // One-shot flag so /itinerary knows to generate. Without it, /itinerary
    // shows the user's last saved trip (no regeneration loop on navigation).
    sessionStorage.setItem('sonder_generate_now', '1')
    navigate('/itinerary')
  }

  function handleAdjust() {
    localStorage.removeItem(PERSONA_CACHE_KEY)
    navigate('/preferences')
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent={ORANGE}/>

      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'center', height: 68 }}>
        <SonderNav3D markSize={32}/>
      </nav>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '48px', maxWidth: 720, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <AnimatePresence mode="wait">
          {state.status === 'loading' && (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.4, ease }}>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: `${ORANGE}cc`, marginBottom: 14 }}>
                Reading you…
              </p>
              <motion.div
                animate={{ opacity: [0.3, 0.9, 0.3] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                style={{ width: 80, height: 1, background: `linear-gradient(to right, transparent, ${ORANGE}88, transparent)`, margin: '20px auto' }}
              />
            </motion.div>
          )}

          {state.status === 'error' && (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.4, ease }}>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 28, color: BONE, marginBottom: 24 }}>
                Something didn't load.
              </p>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, marginBottom: 36 }}>
                {state.error}
              </p>
              <button onClick={handleAdjust} style={ctaPrimary(true)}>
                Back to your answers
              </button>
            </motion.div>
          )}

          {state.status === 'ready' && state.persona && (
            <motion.div
              key="ready"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -24 }}
              transition={{ duration: 0.55, ease }}
              style={{ width: '100%' }}
            >
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 22 }}>
                {state.persona.softener}
              </p>

              <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 48, lineHeight: 1.2, color: BONE, marginBottom: state.persona.emotional_tone ? 14 : 28 }}>
                {state.persona.descriptor}
              </h1>

              {state.persona.emotional_tone && (
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.30em', textTransform: 'uppercase', color: `${BONE}88`, marginBottom: 28 }}>
                  {state.persona.emotional_tone}
                </p>
              )}

              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 16, lineHeight: 1.7, color: `${BONE}d0`, marginBottom: 44, maxWidth: 560, marginLeft: 'auto', marginRight: 'auto' }}>
                {state.persona.paragraph}
              </p>

              {state.persona.bullets?.length > 0 && (
                <div style={{ marginBottom: 56 }}>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 18 }}>
                    You're drawn to
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 480, margin: '0 auto' }}>
                    {state.persona.bullets.map((b, i) => (
                      <motion.p
                        key={i}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.1 + i * 0.07, ease }}
                        style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 19, color: `${BONE}cc`, margin: 0, lineHeight: 1.4 }}
                      >
                        — {b}
                      </motion.p>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
                <motion.button
                  whileHover={{ y: -2, boxShadow: `0 0 64px ${ORANGE}55, 0 0 128px ${ORANGE}18`, transition: spring }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleConfirm}
                  style={ctaPrimary(true)}
                >
                  This feels like me
                </motion.button>
                <button onClick={handleAdjust} style={ctaSecondary}>
                  Adjust my answers
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function ctaPrimary(active) {
  return {
    minWidth: 280,
    padding: '19px 36px',
    background: active ? `linear-gradient(135deg, ${ORANGE} 0%, #EA580C 100%)` : 'rgba(212,182,134,0.06)',
    border: `1px solid ${active ? 'transparent' : HAIRLINE}`,
    borderRadius: 12,
    cursor: active ? 'pointer' : 'default',
    fontFamily: '"Inter Tight",sans-serif',
    fontSize: 11,
    letterSpacing: '0.22em',
    textTransform: 'uppercase',
    fontWeight: 500,
    color: '#fff',
    transition: 'all 0.25s',
    boxShadow: active ? `0 0 48px ${ORANGE}33, 0 0 96px ${ORANGE}11` : 'none',
  }
}

const ctaSecondary = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  padding: '12px 24px',
  fontFamily: '"Inter Tight",sans-serif',
  fontSize: 11,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  fontWeight: 400,
  color: MUTE,
  transition: 'color 0.2s',
}
