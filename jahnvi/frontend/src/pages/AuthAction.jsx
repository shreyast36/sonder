/**
 * Custom Firebase Auth action handler — lives at /auth/action.
 *
 * Firebase emails (password reset, email verification, recover email)
 * link here with a `?mode=...&oobCode=...` query string. This page reads
 * the params, calls the matching Firebase client SDK call, and handles
 * the UX entirely within our domain.
 *
 * Currently implements: resetPassword. (verifyEmail / recoverEmail are
 * stubbed — easy to fill in later.)
 *
 * To wire this up: Firebase Console → Authentication → Templates →
 * (any template, they all share one setting) → "Customize action URL"
 * → set to https://discoversonder.com/auth/action
 */

import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Lock, ArrowLeft, Check } from 'lucide-react'
import {
  verifyPasswordResetCode,
  confirmPasswordReset,
  applyActionCode,
} from 'firebase/auth'
import { auth } from '../lib/firebase'

// Shared tokens with SignUp.jsx
const BG        = '#080807'
const GOLD      = '#D4B686'
const BONE      = '#F4EDE0'
const MUTE      = 'rgba(244,237,224,0.44)'
const HAIRLINE  = 'rgba(232,212,168,0.11)'
const HAIRLINE_HOVER = 'rgba(232,212,168,0.28)'
const GOLD_GRAD = 'linear-gradient(180deg,#F0DCB0 0%,#E8D4A8 28%,#D4B686 55%,#B89464 80%,#8A6F4A 100%)'
const ease      = [0.16, 1, 0.3, 1]

function Field({ icon: Icon, type, value, onChange, placeholder, autoComplete }) {
  const [focused, setFocused] = useState(false)
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '14px 18px',
      background: 'rgba(232,212,168,0.025)',
      border: `1px solid ${focused ? HAIRLINE_HOVER : HAIRLINE}`,
      borderRadius: 8,
      transition: 'border-color 0.25s, background 0.25s',
    }}>
      <Icon size={15} style={{ color: focused ? GOLD : MUTE, transition: 'color 0.25s', flexShrink: 0 }}/>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        style={{
          flex: 1, background: 'none', border: 'none', outline: 'none',
          fontFamily: '"Inter Tight",sans-serif', fontSize: 14, color: BONE, letterSpacing: '0.01em',
        }}
      />
    </div>
  )
}

export default function AuthAction() {
  const navigate = useNavigate()
  const search   = new URLSearchParams(useLocation().search)
  const mode     = search.get('mode')
  const oobCode  = search.get('oobCode')

  // shared state
  const [phase, setPhase]       = useState('verifying')   // 'verifying' | 'ready' | 'success' | 'error'
  const [error, setError]       = useState(null)
  const [email, setEmail]       = useState(null)

  // password-reset-specific state
  const [password, setPassword] = useState('')
  const [confirm, setConfirm]   = useState('')
  const [submitting, setSubmit] = useState(false)

  // On mount: verify the oobCode is valid before showing the form
  useEffect(() => {
    if (!oobCode || !mode) {
      setPhase('error')
      setError('Invalid or missing reset link.')
      return
    }
    if (mode === 'resetPassword') {
      verifyPasswordResetCode(auth, oobCode)
        .then(em => { setEmail(em); setPhase('ready') })
        .catch(() => { setPhase('error'); setError('This reset link has expired or already been used.') })
    } else if (mode === 'verifyEmail') {
      applyActionCode(auth, oobCode)
        .then(() => setPhase('success'))
        .catch(() => { setPhase('error'); setError('This verification link has expired or already been used.') })
    } else {
      setPhase('error')
      setError(`Unsupported action: ${mode}`)
    }
  }, [mode, oobCode])

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    if (password.length < 6) {
      setError('Password should be at least 6 characters.')
      return
    }
    if (password !== confirm) {
      setError('Passwords don\'t match.')
      return
    }
    setSubmit(true)
    try {
      await confirmPasswordReset(auth, oobCode, password)
      setPhase('success')
    } catch (err) {
      setError('Something went wrong. The link may have expired.')
    } finally {
      setSubmit(false)
    }
  }

  // ── Subviews ──────────────────────────────────────────────────────────────
  const title    = phase === 'verifying' ? 'One moment'
                 : phase === 'ready'     ? 'Choose a new password'
                 : phase === 'success'   ? (mode === 'verifyEmail' ? 'Email verified' : 'Password updated')
                 :                         'Link unavailable'

  const subtitle = phase === 'verifying' ? 'Verifying your link…'
                 : phase === 'ready'     ? `Setting a new password for ${email}.`
                 : phase === 'success'   ? (mode === 'verifyEmail' ? 'Your email has been confirmed.' : 'You can now sign in with your new password.')
                 :                         error

  return (
    <div style={{
      minHeight: '100vh', background: BG, color: BONE,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '32px 24px', position: 'relative', overflow: 'hidden',
    }}>
      <div style={{ position: 'absolute', top: '20%', left: '50%', transform: 'translateX(-50%)', width: 900, height: 700, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(212,182,134,0.10) 0%, transparent 65%)', pointerEvents: 'none' }}/>

      <motion.button
        whileHover={{ x: -3, color: BONE }}
        onClick={() => navigate('/')}
        style={{
          position: 'absolute', top: 28, left: 28,
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0,
        }}
      >
        <ArrowLeft size={16}/>
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase' }}>Home</span>
      </motion.button>

      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease }}
        style={{
          position: 'relative', width: '100%', maxWidth: 440, padding: '52px 44px',
          background: 'linear-gradient(160deg, rgba(20,17,12,0.92) 0%, rgba(12,10,7,0.96) 100%)',
          border: `1px solid ${HAIRLINE}`, borderRadius: 16,
          boxShadow: '0 32px 80px rgba(0,0,0,0.55), 0 0 60px rgba(212,182,134,0.05)',
        }}
      >
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.38em', textTransform: 'uppercase', color: GOLD, opacity: 0.75, marginBottom: 18, textAlign: 'center' }}>
          Sonder
        </p>

        <AnimatePresence mode="wait">
          <motion.div
            key={phase}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease }}
          >
            <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 38, lineHeight: 1.1, color: BONE, marginBottom: 10, textAlign: 'center', letterSpacing: '-0.01em' }}>
              {title}
            </h1>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, color: MUTE, marginBottom: 36, textAlign: 'center', lineHeight: 1.5 }}>
              {subtitle}
            </p>
          </motion.div>
        </AnimatePresence>

        {/* Verifying — just a soft spinner */}
        {phase === 'verifying' && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '24px 0' }}>
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.1, repeat: Infinity, ease: 'linear' }}
              style={{ width: 28, height: 28, border: '2px solid transparent', borderTopColor: GOLD, borderRadius: '50%' }}/>
          </div>
        )}

        {/* Password reset form */}
        {phase === 'ready' && mode === 'resetPassword' && (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Field icon={Lock} type="password" value={password} onChange={setPassword}
                   placeholder="New password" autoComplete="new-password"/>
            <Field icon={Lock} type="password" value={confirm} onChange={setConfirm}
                   placeholder="Confirm new password" autoComplete="new-password"/>

            <AnimatePresence>
              {error && (
                <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: '#E89B7C', marginTop: 4, paddingLeft: 4 }}>
                  {error}
                </motion.p>
              )}
            </AnimatePresence>

            <motion.button
              type="submit" disabled={submitting}
              whileHover={!submitting ? { y: -2, boxShadow: '0 0 50px rgba(212,182,134,0.38),0 0 100px rgba(212,182,134,0.12)' } : {}}
              whileTap={!submitting ? { scale: 0.98 } : {}}
              style={{
                marginTop: 16, padding: '16px 28px', background: GOLD_GRAD, color: BG,
                border: 'none', borderRadius: 8, cursor: submitting ? 'wait' : 'pointer',
                fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em',
                textTransform: 'uppercase', fontWeight: 600,
                boxShadow: '0 0 36px rgba(212,182,134,0.24),0 0 80px rgba(212,182,134,0.08)',
                opacity: submitting ? 0.65 : 1, transition: 'opacity 0.25s, transform 0.25s, box-shadow 0.25s',
              }}
            >
              {submitting ? 'Updating…' : 'Update password'}
            </motion.button>
          </form>
        )}

        {/* Success — checkmark + CTA back to signin */}
        {phase === 'success' && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24 }}>
            <motion.div
              initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5, ease }}
              style={{
                width: 64, height: 64, borderRadius: '50%',
                background: 'rgba(212,182,134,0.10)',
                border: `1px solid ${GOLD}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 0 40px rgba(212,182,134,0.30)',
              }}
            >
              <Check size={28} style={{ color: GOLD }}/>
            </motion.div>
            <motion.button
              whileHover={{ y: -2, boxShadow: '0 0 50px rgba(212,182,134,0.38)' }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/signin')}
              style={{
                padding: '16px 36px', background: GOLD_GRAD, color: BG,
                border: 'none', borderRadius: 8, cursor: 'pointer',
                fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em',
                textTransform: 'uppercase', fontWeight: 600,
                boxShadow: '0 0 36px rgba(212,182,134,0.24)',
              }}
            >
              Continue to sign in
            </motion.button>
          </div>
        )}

        {/* Error — CTA back to signin */}
        {phase === 'error' && (
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: 8 }}>
            <button
              onClick={() => navigate('/signin')}
              style={{
                background: 'none', border: `1px solid ${HAIRLINE_HOVER}`, color: GOLD,
                cursor: 'pointer', padding: '12px 28px', borderRadius: 8,
                fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase',
              }}
            >
              Request a new link
            </button>
          </div>
        )}
      </motion.div>
    </div>
  )
}
