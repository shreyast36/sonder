import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, Mail, Lock, User } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

// ── Tokens ────────────────────────────────────────────────────────────────────
const BG        = '#080807'
const GOLD      = '#D4B686'
const BONE      = '#F4EDE0'
const MUTE      = 'rgba(244,237,224,0.44)'
const HAIRLINE  = 'rgba(232,212,168,0.11)'
const HAIRLINE_HOVER = 'rgba(232,212,168,0.28)'
const GOLD_GRAD = 'linear-gradient(180deg,#F0DCB0 0%,#E8D4A8 28%,#D4B686 55%,#B89464 80%,#8A6F4A 100%)'
const ease      = [0.16, 1, 0.3, 1]

// ── Firebase error → human copy ───────────────────────────────────────────────
function humanizeAuthError(code) {
  switch (code) {
    case 'auth/invalid-email':           return 'That email address doesn\'t look right.'
    case 'auth/user-disabled':           return 'This account has been disabled.'
    case 'auth/user-not-found':          return 'No account found with that email.'
    case 'auth/wrong-password':          return 'Incorrect password. Try again.'
    case 'auth/invalid-credential':      return 'Incorrect email or password.'
    case 'auth/email-already-in-use':    return 'An account with that email already exists.'
    case 'auth/weak-password':           return 'Password should be at least 6 characters.'
    case 'auth/too-many-requests':       return 'Too many attempts. Try again in a moment.'
    case 'auth/network-request-failed':  return 'Network error. Check your connection.'
    default:                             return 'Something went wrong. Please try again.'
  }
}

// ── Reusable input field ──────────────────────────────────────────────────────
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
          flex: 1,
          background: 'none',
          border: 'none',
          outline: 'none',
          fontFamily: '"Inter Tight",sans-serif',
          fontSize: 14,
          color: BONE,
          letterSpacing: '0.01em',
        }}
      />
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function SignUp() {
  const navigate = useNavigate()
  const location = useLocation()
  const { signIn, signUp, resetPassword } = useAuth()

  const initialMode = location.pathname === '/signin' ? 'signin' : 'signup'
  const [mode, setMode]               = useState(initialMode)   // 'signup' | 'signin' | 'reset'
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail]             = useState('')
  const [password, setPassword]       = useState('')
  const [confirmPassword, setConfirm] = useState('')
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)
  const [resetSent, setResetSent]     = useState(false)

  function flip(newMode) {
    setError(null)
    setResetSent(false)
    setConfirm('')
    setMode(newMode)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)

    if (mode === 'signup' && password !== confirmPassword) {
      setError('Passwords don\'t match.')
      return
    }

    setLoading(true)
    try {
      if (mode === 'signup') {
        await signUp(email.trim(), password, displayName.trim() || null)
        navigate('/dashboard')
      } else if (mode === 'signin') {
        await signIn(email.trim(), password)
        navigate('/dashboard')
      } else if (mode === 'reset') {
        await resetPassword(email.trim())
        setResetSent(true)
      }
    } catch (err) {
      setError(humanizeAuthError(err.code))
    } finally {
      setLoading(false)
    }
  }

  const title = mode === 'signup' ? 'Welcome to Sonder!'
              : mode === 'signin' ? ''
              : 'Reset your password'

  const subtitle = mode === 'signup' ? 'Create your account.'
                 : mode === 'signin' ? 'Sign in to continue.'
                 : 'We\'ll send you a secure link to reset it.'

  return (
    <div style={{
      minHeight: '100vh',
      background: BG,
      color: BONE,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '32px 24px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background glow */}
      <div style={{ position: 'absolute', top: '20%', left: '50%', transform: 'translateX(-50%)', width: 900, height: 700, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(212,182,134,0.10) 0%, transparent 65%)', pointerEvents: 'none' }}/>

      {/* Back to landing */}
      <motion.button
        whileHover={{ x: -3, color: BONE }}
        onClick={() => navigate('/')}
        style={{
          position: 'absolute', top: 28, left: 28,
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'none', border: 'none', cursor: 'pointer',
          color: MUTE, padding: 0,
        }}
      >
        <ArrowLeft size={16}/>
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase' }}>Home</span>
      </motion.button>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease }}
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: 440,
          padding: '52px 44px',
          background: 'linear-gradient(160deg, rgba(20,17,12,0.92) 0%, rgba(12,10,7,0.96) 100%)',
          border: `1px solid ${HAIRLINE}`,
          borderRadius: 16,
          boxShadow: '0 32px 80px rgba(0,0,0,0.55), 0 0 60px rgba(212,182,134,0.05)',
        }}
      >
        {/* Eyebrow */}
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.38em', textTransform: 'uppercase', color: GOLD, opacity: 0.75, marginBottom: 18, textAlign: 'center' }}>
          Sonder
        </p>

        {/* Title */}
        <AnimatePresence mode="wait">
          <motion.h1
            key={title}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease }}
            style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 38, lineHeight: 1.1, color: BONE, marginBottom: 10, textAlign: 'center', letterSpacing: '-0.01em' }}
          >
            {title}
          </motion.h1>
        </AnimatePresence>

        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, color: MUTE, marginBottom: 36, textAlign: 'center', lineHeight: 1.5 }}>
          {subtitle}
        </p>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {mode === 'signup' && (
            <Field
              icon={User} type="text" value={displayName} onChange={setDisplayName}
              placeholder="Your name" autoComplete="name"
            />
          )}
          <Field
            icon={Mail} type="email" value={email} onChange={setEmail}
            placeholder="Email address" autoComplete="email"
          />
          {mode !== 'reset' && (
            <Field
              icon={Lock} type="password" value={password} onChange={setPassword}
              placeholder="Password" autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
            />
          )}
          {mode === 'signup' && (
            <Field
              icon={Lock} type="password" value={confirmPassword} onChange={setConfirm}
              placeholder="Confirm password" autoComplete="new-password"
            />
          )}

          {/* Error / success */}
          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: '#E89B7C', marginTop: 4, marginBottom: 0, paddingLeft: 4 }}
              >
                {error}
              </motion.p>
            )}
            {resetSent && (
              <motion.p
                initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: GOLD, marginTop: 4, paddingLeft: 4 }}
              >
                Check your email for the reset link.
              </motion.p>
            )}
          </AnimatePresence>

          {/* CTA */}
          <motion.button
            type="submit"
            disabled={loading}
            whileHover={!loading ? { y: -2, boxShadow: '0 0 50px rgba(212,182,134,0.38),0 0 100px rgba(212,182,134,0.12)' } : {}}
            whileTap={!loading ? { scale: 0.98 } : {}}
            style={{
              marginTop: 16,
              padding: '16px 28px',
              background: GOLD_GRAD,
              color: BG,
              border: 'none',
              borderRadius: 8,
              cursor: loading ? 'wait' : 'pointer',
              fontFamily: '"Inter Tight",sans-serif',
              fontSize: 11,
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              fontWeight: 600,
              boxShadow: '0 0 36px rgba(212,182,134,0.24),0 0 80px rgba(212,182,134,0.08)',
              opacity: loading ? 0.65 : 1,
              transition: 'opacity 0.25s, transform 0.25s, box-shadow 0.25s',
            }}
          >
            {loading
              ? 'One moment…'
              : mode === 'signup'  ? 'Create account'
              : mode === 'signin'  ? 'Sign in'
              :                      'Send reset link'}
          </motion.button>
        </form>

        {/* Mode toggles */}
        <div style={{ marginTop: 28, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          {mode === 'signup' && (
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>
              Already have an account?{' '}
              <button onClick={() => flip('signin')} style={{ background: 'none', border: 'none', color: GOLD, cursor: 'pointer', fontFamily: 'inherit', fontSize: 'inherit', padding: 0, letterSpacing: '0.02em' }}>
                Sign in
              </button>
            </p>
          )}
          {mode === 'signin' && (
            <>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>
                New to Sonder?{' '}
                <button onClick={() => flip('signup')} style={{ background: 'none', border: 'none', color: GOLD, cursor: 'pointer', fontFamily: 'inherit', fontSize: 'inherit', padding: 0, letterSpacing: '0.02em' }}>
                  Create an account
                </button>
              </p>
              <button onClick={() => flip('reset')} style={{ background: 'none', border: 'none', color: MUTE, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.04em', padding: 0 }}>
                Forgot password?
              </button>
            </>
          )}
          {mode === 'reset' && (
            <button onClick={() => flip('signin')} style={{ background: 'none', border: 'none', color: GOLD, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 12, padding: 0 }}>
              Back to sign in
            </button>
          )}
        </div>
      </motion.div>
    </div>
  )
}
