import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Check, X, Loader2, MapPin } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import {
  getChatSession, getCotravellerProfile, getUserProfile,
  approveMatch, denyMatch,
} from '../lib/api'
import { useAuth } from '../hooks/useAuth'
import SynthBadge from '../components/SynthBadge'

const VIOLET = '#8B5CF6'
const GREEN  = '#10B981'
const RED    = '#EF4444'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

function useCountUp(target, duration = 1000, delay = 500) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    if (!target) return
    const timer = setTimeout(() => {
      const start = performance.now()
      const tick = now => {
        const p = Math.min((now - start) / duration, 1)
        const e = 1 - Math.pow(1 - p, 3)
        setCount(Math.round(e * target))
        if (p < 1) requestAnimationFrame(tick)
      }
      requestAnimationFrame(tick)
    }, delay)
    return () => clearTimeout(timer)
  }, [target, duration, delay])
  return count
}

/**
 * One person's decision pill. Three states map to three visuals:
 *   - pending + not their turn yet → muted "Deciding..."
 *   - pending + waiting on them    → spinner "Reviewing..."
 *   - approved                     → green check + label
 *   - denied                       → red X + label
 */
function DecisionPill({ label, decision, waitingOnThem }) {
  const isApproved = decision === 'approved'
  const isDenied   = decision === 'denied'
  const isPending  = !decision || decision === 'pending'

  const color =
    isApproved ? GREEN :
    isDenied   ? RED   :
    waitingOnThem ? VIOLET : MUTE

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
      <span style={{
        fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500,
        letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE,
      }}>{label}</span>

      <motion.div
        animate={isPending && waitingOnThem
          ? { boxShadow: [`0 0 0 0 ${color}55`, `0 0 0 14px ${color}00`, `0 0 0 0 ${color}00`] }
          : { boxShadow: 'none' }}
        transition={isPending && waitingOnThem
          ? { duration: 1.6, repeat: Infinity, ease: 'easeInOut' }
          : { duration: 0.25 }}
        style={{
          width: 52, height: 52, borderRadius: '50%',
          border: `1.5px solid ${color}${isPending && !waitingOnThem ? '33' : '88'}`,
          background: isApproved ? `${GREEN}14` : isDenied ? `${RED}14` : `${color}08`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
      >
        {isApproved && <Check size={22} style={{ color: GREEN }}/>}
        {isDenied  && <X size={22} style={{ color: RED }}/>}
        {isPending && (
          waitingOnThem
            ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.2, ease: 'linear', repeat: Infinity }} style={{ display: 'inline-flex' }}>
                <Loader2 size={20} style={{ color: VIOLET }}/>
              </motion.span>
            : <span style={{ width: 8, height: 8, borderRadius: '50%', background: MUTE, opacity: 0.4 }}/>
        )}
      </motion.div>

      <span style={{
        fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
        color, opacity: isPending && !waitingOnThem ? 0.6 : 1,
      }}>
        {isApproved ? 'Wants to travel' :
         isDenied   ? 'Passed' :
         waitingOnThem ? 'Reviewing…' : 'Yet to decide'}
      </span>
    </div>
  )
}

export default function ApproveDeny() {
  const navigate         = useNavigate()
  const { sessionId }    = useParams()
  const { user }         = useAuth()
  const selfId           = user?.uid

  const [session, setSession]   = useState(null)
  const [match,   setMatch]     = useState(null)   // CoTravellerMatch
  const [me,      setMe]        = useState(null)   // user profile
  const [submitting, setSubmitting] = useState(false)
  const [error,   setError]     = useState(null)
  const pollRef = useRef(null)

  // Hydrate session + match + user profile once on mount.
  useEffect(() => {
    if (!sessionId) return
    let cancelled = false
    ;(async () => {
      try {
        const s = await getChatSession(sessionId)
        if (cancelled) return
        setSession(s)
        if (s?.profile_id) {
          try {
            const m = await getCotravellerProfile(s.profile_id, s.itinerary_id || '')
            if (!cancelled) setMatch(m)
          } catch (e) {
            console.warn('getCotravellerProfile failed:', e?.message || e)
          }
        }
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Could not load match')
      }
      try {
        const profile = await getUserProfile()
        if (!cancelled) setMe(profile)
      } catch (e) {
        console.warn('getUserProfile failed:', e?.message || e)
      }
    })()
    return () => { cancelled = true }
  }, [sessionId])

  // Poll while waiting on the persona's decision. Stops when the session
  // is fully decided. 1.5s cadence keeps the wait feeling responsive
  // without hammering the backend.
  useEffect(() => {
    if (!session) return
    const waitingOnPersona =
      session.user_decision === 'approved' && session.profile_decision === 'pending'
    if (!waitingOnPersona) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      return
    }
    pollRef.current = setInterval(async () => {
      try {
        const next = await getChatSession(sessionId)
        setSession(next)
        if (next.profile_decision !== 'pending') {
          clearInterval(pollRef.current); pollRef.current = null
        }
      } catch { /* keep polling */ }
    }, 1500)
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null } }
  }, [session, sessionId])

  const profile      = match?.profile
  const matchScore   = match?.match_score ? Math.round(match.match_score * 100) : 0
  const scoreDisp    = useCountUp(matchScore, 900, 400)
  const reasons      = match?.match_reasons || []

  // When the match ends in denial — either the user or the persona —
  // briefly show the outcome panel, then auto-replace the route with
  // the matches list so the user lands on a refreshed top-3 that
  // filters this profile out. replace:true so the dead approval URL
  // isn't in the back-stack. Approved is handled separately (the
  // "See your itinerary" CTA navigates explicitly).
  useEffect(() => {
    if (session?.approval_status !== 'denied') return
    const itinId = session?.itinerary_id
    const t = setTimeout(() => {
      navigate(itinId ? `/companions/${encodeURIComponent(itinId)}` : '/dashboard',
               { replace: true })
    }, 1800)
    return () => clearTimeout(t)
  }, [session?.approval_status, session?.itinerary_id, navigate])

  // Early return AFTER all hook calls so React's hook-order invariant holds
  // when error transitions in/out across renders.
  const fatalError = error && !session
  if (fatalError) {
    return (
      <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ color: MUTE, fontSize: 13 }}>{error}</p>
          <button onClick={() => navigate(-1)} style={{ marginTop: 16, color: GOLD, background: 'none', border: 'none', cursor: 'pointer' }}>Go back</button>
        </div>
      </div>
    )
  }

  const userDecision    = session?.user_decision    || 'pending'
  const profileDecision = session?.profile_decision || 'pending'
  const overall         = session?.approval_status  || 'pending'

  const canAct        = userDecision === 'pending'
  const waitingOnThem = userDecision === 'approved' && profileDecision === 'pending'
  const fullyDecided  = overall !== 'pending'

  async function onApprove() {
    if (!canAct || submitting) return
    setSubmitting(true); setError(null)
    try {
      const res = await approveMatch(sessionId)
      setSession(prev => ({ ...prev, ...res }))
    } catch (e) {
      setError(e?.message || 'Could not record approval')
    } finally {
      setSubmitting(false)
    }
  }

  async function onDeny() {
    if (!canAct || submitting) return
    setSubmitting(true); setError(null)
    try {
      const res = await denyMatch(sessionId)
      setSession(prev => ({ ...prev, ...res }))
    } catch (e) {
      setError(e?.message || 'Could not record decision')
    } finally {
      setSubmitting(false)
    }
  }

  const myName    = (me?.display_name || 'You').split(/\s+/)[0]
  const themName  = (profile?.display_name || 'them').split(/\s+/)[0]

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent={VIOLET}/>

      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={() => navigate(-1)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back to chat</span>
        </motion.button>
        <SonderNav3D markSize={32}/>
        <div style={{ width: 110 }}/>
      </nav>

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1, minHeight: 0 }}>

        {/* LEFT — the persona */}
        <motion.div
          initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.7, ease }}
          style={{ padding: '60px 52px', borderRight: `1px solid ${HAIRLINE}`, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}
        >
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 450, background: `radial-gradient(ellipse 90% 60% at 35% 18%, ${VIOLET}18 0%, transparent 65%)`, pointerEvents: 'none' }}/>

          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 40 }}>Match decision</p>

          <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 28, marginBottom: 32 }}>
            <motion.div
              animate={{ boxShadow: [`0 0 0 2px ${VIOLET}33, 0 0 32px ${VIOLET}18`, `0 0 0 2px ${VIOLET}77, 0 0 64px ${VIOLET}38`, `0 0 0 2px ${VIOLET}33, 0 0 32px ${VIOLET}18`] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
              style={{ width: 116, height: 116, borderRadius: '50%', overflow: 'hidden', flexShrink: 0, background: 'rgba(212,182,134,0.08)' }}
            >
              {profile?.avatar_url
                ? <img src={profile.avatar_url} alt={profile.display_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
                : <div style={{ width: '100%', height: '100%' }}/>}
            </motion.div>
            {matchScore > 0 && (
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', width: 130, height: 130 }}>
                <motion.span
                  animate={{ filter: [`drop-shadow(0 0 10px ${VIOLET}88)`, `drop-shadow(0 0 28px ${VIOLET}cc)`, `drop-shadow(0 0 10px ${VIOLET}88)`] }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 56, lineHeight: 1, color: BONE, letterSpacing: '-0.03em' }}
                >
                  {scoreDisp}
                </motion.span>
                <span style={{ position: 'absolute', bottom: 24, fontFamily: '"Inter Tight",sans-serif', fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: `${VIOLET}99` }}>% match</span>
              </div>
            )}
          </div>

          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 44, color: BONE, lineHeight: 1, marginBottom: 8 }}>
            {profile?.display_name || '…'}
          </h1>
          {profile?.is_seed && <div style={{ marginBottom: 12 }}><SynthBadge isSeed variant="default"/></div>}
          {profile?.location && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 24 }}>
              <MapPin size={11} style={{ color: GOLD }}/>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE }}>{profile.location}</span>
            </div>
          )}

          {reasons.length > 0 && (
            <div style={{ marginTop: 18 }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Why this match</p>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {reasons.slice(0, 4).map((r, i) => (
                  <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                    <span style={{ width: 4, height: 4, borderRadius: '50%', background: GOLD, marginTop: 8, flexShrink: 0 }}/>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, lineHeight: 1.55, color: BONE }}>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>

        {/* RIGHT — decision + dual progress */}
        <motion.div
          initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.7, ease }}
          style={{ padding: '60px 52px', display: 'flex', flexDirection: 'column' }}
        >
          <motion.h2
            animate={{ filter: ['drop-shadow(0 0 12px rgba(244,237,224,0.06))', 'drop-shadow(0 0 28px rgba(244,237,224,0.14))', 'drop-shadow(0 0 12px rgba(244,237,224,0.06))'] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
            style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 50, color: BONE, lineHeight: 1.05, marginBottom: 12 }}
          >
            Travel together?
          </motion.h2>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, fontWeight: 300, color: MUTE, lineHeight: 1.6, marginBottom: 36 }}>
            Both of you have to want this. Your decision unlocks the shared itinerary —
            theirs makes it real.
          </p>

          <div style={{ height: 1, background: `linear-gradient(to right, transparent, ${VIOLET}44, transparent)`, marginBottom: 36 }}/>

          {/* Dual progress: you on the left, them on the right */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 'auto', padding: '8px 0' }}>
            <DecisionPill
              label={myName}
              decision={userDecision}
              waitingOnThem={false}
            />
            <DecisionPill
              label={themName}
              decision={profileDecision}
              waitingOnThem={waitingOnThem}
            />
          </div>

          {/* Action area: buttons if user hasn't decided yet, otherwise contextual status */}
          {canAct && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.3, ease }}
              style={{ marginTop: 40, display: 'flex', flexDirection: 'column', gap: 12 }}
            >
              <motion.button
                whileHover={!submitting ? { y: -2, boxShadow: `0 0 64px ${GREEN}55, 0 0 128px ${GREEN}22`, transition: spring } : {}}
                whileTap={!submitting ? { scale: 0.98 } : {}}
                onClick={onApprove}
                disabled={submitting}
                style={{
                  width: '100%', padding: '18px 0',
                  background: `linear-gradient(135deg, ${GREEN} 0%, #059669 100%)`,
                  border: 'none', borderRadius: 12, cursor: submitting ? 'wait' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
                  textTransform: 'uppercase', fontWeight: 500, color: '#fff',
                  boxShadow: `0 0 48px ${GREEN}33`, opacity: submitting ? 0.7 : 1,
                }}
              >
                <Check size={14}/> Approve & travel together
              </motion.button>
              <motion.button
                whileHover={!submitting ? { borderColor: 'rgba(232,212,168,0.24)', color: BONE, background: 'rgba(212,182,134,0.06)' } : {}}
                whileTap={!submitting ? { scale: 0.98 } : {}}
                onClick={onDeny}
                disabled={submitting}
                style={{
                  width: '100%', padding: '15px 0',
                  background: 'rgba(212,182,134,0.03)', border: `1px solid ${HAIRLINE}`,
                  borderRadius: 12, cursor: submitting ? 'wait' : 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
                  textTransform: 'uppercase', color: MUTE, opacity: submitting ? 0.7 : 1,
                }}
              >
                Not a match
              </motion.button>
            </motion.div>
          )}

          {!canAct && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease }}
              style={{ marginTop: 40, padding: '20px 22px', borderRadius: 14,
                background: fullyDecided
                  ? (overall === 'approved' ? `${GREEN}10` : 'rgba(100,116,139,0.10)')
                  : `${VIOLET}10`,
                border: `1px solid ${fullyDecided ? (overall === 'approved' ? `${GREEN}44` : 'rgba(100,116,139,0.35)') : `${VIOLET}44`}`,
                textAlign: 'center',
              }}
            >
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 500, fontSize: 11, letterSpacing: '0.2em', textTransform: 'uppercase', margin: 0,
                color: fullyDecided ? (overall === 'approved' ? GREEN : MUTE) : VIOLET }}>
                {overall === 'approved' && "It's a match"}
                {overall === 'denied'   && (userDecision === 'denied' ? 'You passed on this match' : `${themName} passed`)}
                {!fullyDecided && (userDecision === 'approved' ? `Waiting for ${themName}…` : 'Reviewing…')}
              </p>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE, marginTop: 8, marginBottom: 0, lineHeight: 1.6 }}>
                {overall === 'approved' && 'Your shared itinerary is ready when you are.'}
                {overall === 'denied' && userDecision === 'denied' && 'No worries — we\'ll surface fresher matches next round.'}
                {overall === 'denied' && userDecision !== 'denied' && 'It happens. The chemistry wasn\'t there on their side.'}
                {!fullyDecided && userDecision === 'approved' && 'They\'re reading back through your chat. This usually takes a few seconds.'}
              </p>
              {overall === 'approved' && (
                <motion.button
                  whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    const itinId = session?.itinerary_id
                    navigate(itinId ? `/shared/${encodeURIComponent(itinId)}` : '/dashboard')
                  }}
                  style={{
                    marginTop: 18, padding: '10px 22px', borderRadius: 18,
                    background: `linear-gradient(135deg, ${GREEN} 0%, #059669 100%)`,
                    border: 'none', cursor: 'pointer', color: '#fff',
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 10, fontWeight: 500,
                    letterSpacing: '0.2em', textTransform: 'uppercase',
                  }}
                >
                  See your itinerary
                </motion.button>
              )}
            </motion.div>
          )}

          {error && (
            <p style={{ marginTop: 14, fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: '#F87171', textAlign: 'center' }}>
              {error}
            </p>
          )}
        </motion.div>
      </div>
    </div>
  )
}
