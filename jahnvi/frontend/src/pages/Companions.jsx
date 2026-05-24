import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Check } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import MatchCard from '../components/MatchCard'
import { getCompanionPrefs, saveCompanionPrefs, getCotravellers, getUserProfile, patchProfileGender } from '../lib/api'
import { useAuth } from '../hooks/useAuth'
/* eslint-disable react-refresh/only-export-components */

const SKY = '#38BDF8'
const spring = { type: 'spring', stiffness: 260, damping: 22 }

// Same dim → tag map as Dashboard (kept inline so this page is self-contained)
const DIM_TAG = {
  nature_outdoors: 'Nature', culture_history: 'Culture', food_drink: 'Food',
  nightlife_social: 'Nightlife', comfort_luxury: 'Luxury', exploration_local: 'Explore',
  escape_reset: 'Reset', adventure_novelty: 'Adventure', connection: 'Connection',
  reflection: 'Reflection', curiosity: 'Curious', prestige_reward: 'Milestone',
}
const _PACE_TAG = { relaxed: 'Relaxed', moderate: 'Moderate', packed: 'Packed' }
const _BUDGET_TAG = { budget: 'Budget', mid_range: 'Mid-range', luxury: 'Luxury' }

function matchToCard(m) {
  const p = m?.profile || {}
  const dimTags = (p.interests || []).slice(0, 2).map(d => DIM_TAG[d]).filter(Boolean)
  return {
    id:           p.profile_id || p.display_name,
    display_name: p.display_name || 'Anonymous',
    location:     p.location || '',
    match_score:  Math.round((Number(m?.match_score) || 0) * 100),
    tags:         [...dimTags, _PACE_TAG[p.pace], _BUDGET_TAG[p.budget_style]].filter(Boolean).slice(0, 3),
    avatar_url:   p.avatar_url || null,
    reasons:      Array.isArray(m?.match_reasons) ? m.match_reasons : [],
    is_seed:      Boolean(p.is_seed),
  }
}

// ── Intake questions ────────────────────────────────────────────────────────

const QUESTIONS = [
  {
    key: 'party_arrival',
    prompt: 'You walk into a party knowing one person —',
    options: [
      { value: 'close',    label: 'Stick close to them' },
      { value: 'explore',  label: 'Make a lap, see who’s around' },
      { value: 'anchored', label: 'Post up somewhere and let people come' },
    ],
  },
  {
    key: 'chat_lull',
    prompt: 'Group chat goes quiet for two days —',
    options: [
      { value: 'revive',    label: 'Drop a meme to revive it' },
      { value: 'hands_off', label: 'Don’t really notice' },
      { value: 'direct',    label: 'Hit someone up directly' },
    ],
  },
  {
    key: 'spontaneity',
    prompt: 'Someone you barely know invites you to something tomorrow —',
    options: [
      { value: 'yes',     label: 'Yes, why not' },
      { value: 'depends', label: 'Depends on who else is going' },
      { value: 'pass',    label: 'Pass — too last-minute' },
    ],
  },
]

// ── Page ────────────────────────────────────────────────────────────────────

export default function Companions() {
  const navigate = useNavigate()
  const { itineraryId } = useParams()
  const { user, loading: authLoading } = useAuth()

  const [phase, setPhase]       = useState('loading')   // loading | intake | matches | error
  const [error, setError]       = useState(null)
  const [matches, setMatches]   = useState([])
  const [matchesLoading, setMl] = useState(false)
  const [answers, setAnswers]   = useState({ party_arrival: null, chat_lull: null, spontaneity: null, companion_text: '' })
  const [saving, setSaving]     = useState(false)
  // Gender backfill — only kicks in when the user's profile lacks
  // gender AND they're solo. Older profiles predate the field, so
  // the cotraveller route would silently mix-match without this.
  const [needsGender, setNeedsGender] = useState(false)
  const [pickedGender, setPickedGender] = useState('')

  // Bootstrap: check whether prefs exist for this trip, jump straight to
  // matches if so. Otherwise show the intake first. Also check whether
  // the user's profile has a gender — if they're solo and don't, we
  // force the intake step so they can backfill it before matches load.
  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/signin'); return }
    if (!itineraryId) { navigate('/dashboard'); return }
    let cancelled = false
    ;(async () => {
      // Profile lookup decides whether gender backfill is needed.
      let missingGender = false
      try {
        const prof = await getUserProfile()
        const style = prof?.constraints?.who_travelling_with
        const g = (prof?.constraints?.gender || '').toLowerCase()
        missingGender = style === 'solo' && g !== 'male' && g !== 'female'
        if (!cancelled) setNeedsGender(missingGender)
      } catch (err) {
        if (cancelled) return
        // 404 (no profile yet) or 503: best-effort, treat as no-gender-
        // needed and let matching fall through.
        console.warn('getUserProfile failed:', err?.message || err)
      }

      try {
        const res = await getCompanionPrefs(itineraryId)
        if (cancelled) return
        const prefs = res?.prefs
        const hasPrefs = prefs && (prefs.party_arrival || prefs.chat_lull || prefs.spontaneity || prefs.companion_text)
        if (hasPrefs && !missingGender) {
          setAnswers({
            party_arrival: prefs.party_arrival ?? null,
            chat_lull:     prefs.chat_lull     ?? null,
            spontaneity:   prefs.spontaneity   ?? null,
            companion_text: prefs.companion_text ?? '',
          })
          setPhase('matches')
          loadMatches()
        } else {
          // Either no prefs yet, OR prefs exist but gender is missing
          // → route through the intake so the picker shows.
          if (hasPrefs) {
            setAnswers({
              party_arrival: prefs.party_arrival ?? null,
              chat_lull:     prefs.chat_lull     ?? null,
              spontaneity:   prefs.spontaneity   ?? null,
              companion_text: prefs.companion_text ?? '',
            })
          }
          setPhase('intake')
        }
      } catch (err) {
        if (cancelled) return
        // Couldn't reach backend — let the user fill the intake anyway.
        console.warn('getCompanionPrefs failed:', err?.message || err)
        setPhase('intake')
      }
    })()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user?.uid, itineraryId])

  async function loadMatches() {
    setMl(true)
    try {
      const res = await getCotravellers(itineraryId)
      // Already paired for this trip → backend returns active_pair and an
      // empty matches list. Skip the matching surface entirely and send
      // the user to the shared itinerary.
      const activePair = !Array.isArray(res) ? res?.active_pair : null
      if (activePair?.itinerary_id) {
        navigate(`/shared/${encodeURIComponent(activePair.itinerary_id)}`, { replace: true })
        return
      }
      const arr = Array.isArray(res) ? res : (res?.matches || [])
      setMatches(arr.map(matchToCard))
    } catch (err) {
      console.warn('getCotravellers failed:', err?.message || err)
      setMatches([])
    } finally {
      setMl(false)
    }
  }

  async function handleIntakeSubmit() {
    setSaving(true)
    try {
      // If the user needed to set their gender, persist it first so
      // the next cotraveller fetch sees it on the profile and the
      // hard filter starts working.
      if (needsGender && (pickedGender === 'male' || pickedGender === 'female')) {
        try {
          await patchProfileGender(pickedGender)
          setNeedsGender(false)
        } catch (gErr) {
          console.warn('patchProfileGender failed:', gErr?.message || gErr)
          // Don't block the flow on a failed gender write — the user
          // still gets matches (mixed), and they can re-try later.
        }
      }
      await saveCompanionPrefs(itineraryId, answers)
      setPhase('matches')
      loadMatches()
    } catch (err) {
      setError(err?.message || 'Could not save your answers')
      setPhase('error')
    } finally {
      setSaving(false)
    }
  }

  function setAnswer(key, value) {
    setAnswers(a => ({ ...a, [key]: value }))
  }

  const allAnswered = QUESTIONS.every(q => !!answers[q.key])
    && (!needsGender || pickedGender === 'male' || pickedGender === 'female')

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      {/* nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/dashboard')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <ArrowLeft size={16}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Dashboard</span>
        </motion.button>
        <SonderNav3D markSize={28}/>
        <div style={{ width: 100 }}/>
      </nav>

      {/* gentle ambient gold glow centred */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, background: 'radial-gradient(ellipse 85% 75% at 50% 50%, rgba(212,182,134,0.08) 0%, rgba(184,150,104,0.03) 40%, transparent 75%)' }}/>

      <main style={{ flex: 1, position: 'relative', zIndex: 1, padding: '48px 24px 64px', maxWidth: 1080, width: '100%', margin: '0 auto' }}>
        <AnimatePresence mode="wait">
          {phase === 'loading' && (
            <motion.p key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: `${GOLD}cc`, textAlign: 'center', marginTop: 80 }}>
              Reading the room…
            </motion.p>
          )}

          {phase === 'intake' && (
            <IntakeView
              key="intake"
              answers={answers}
              setAnswer={setAnswer}
              allAnswered={allAnswered}
              saving={saving}
              onSubmit={handleIntakeSubmit}
              needsGender={needsGender}
              pickedGender={pickedGender}
              setPickedGender={setPickedGender}
            />
          )}

          {phase === 'matches' && (
            <MatchesView
              key="matches"
              matches={matches}
              loading={matchesLoading}
              onRefine={() => setPhase('intake')}
              onDone={() => navigate('/dashboard')}
              onTap={(id) => navigate(`/match/${id}`)}
            />
          )}

          {phase === 'error' && (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ textAlign: 'center', marginTop: 80 }}>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 26, color: BONE, marginBottom: 14 }}>Something didn't load.</p>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, color: MUTE, marginBottom: 28 }}>{error}</p>
              <button onClick={() => { setError(null); setPhase('intake') }} style={primaryBtn()}>Try again</button>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}

// ── Intake view ─────────────────────────────────────────────────────────────

function IntakeView({ answers, setAnswer, allAnswered, saving, onSubmit, needsGender, pickedGender, setPickedGender }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.45, ease }}>
      <div style={{ textAlign: 'center', marginBottom: 56 }}>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.32em', textTransform: 'uppercase', color: GOLD, marginBottom: 14 }}>
          A few quick questions
        </p>
        <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 'clamp(36px, 4.8vw, 54px)', lineHeight: 1.1, color: BONE, margin: 0, letterSpacing: '-0.01em' }}>
          So we know who feels right.
        </h1>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, color: MUTE, marginTop: 16, lineHeight: 1.6, maxWidth: 480, marginLeft: 'auto', marginRight: 'auto' }}>
          Nothing about travel. Just how you move through the world.
        </p>
      </div>

      {/* Gender backfill — only shown for solo users whose profile
          predates the field. Same-gender hard filter only fires when
          this is set; without it, solo travellers get mixed matches. */}
      {needsGender && (
        <div style={{ maxWidth: 640, margin: '0 auto 44px' }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.26em', textTransform: 'uppercase', color: GOLD, marginBottom: 10 }}>
            One quick thing first
          </p>
          <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 28, color: BONE, margin: '0 0 10px', lineHeight: 1.2 }}>
            Your gender
          </h2>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, lineHeight: 1.6, marginBottom: 22 }}>
            We only match solo travellers with the same gender for safety. We didn't ask earlier — set it now and we'll filter your matches.
          </p>
          <div style={{ display: 'flex', gap: 10 }}>
            {[{ key: 'female', label: 'Female' }, { key: 'male', label: 'Male' }].map(g => {
              const active = pickedGender === g.key
              return (
                <motion.button
                  key={g.key} whileTap={{ scale: 0.95 }} onClick={() => setPickedGender(g.key)}
                  style={{
                    flex: 1, padding: '16px 0', borderRadius: 14,
                    cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 12,
                    background: active ? `${GOLD}1A` : 'transparent',
                    border: `1px solid ${active ? `${GOLD}66` : HAIRLINE}`,
                    color: active ? GOLD : MUTE,
                    transition: 'all 0.2s',
                    boxShadow: active ? `0 0 20px ${GOLD}22` : 'none',
                    letterSpacing: '0.08em',
                  }}
                >
                  {g.label}
                </motion.button>
              )
            })}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 44, maxWidth: 640, margin: '0 auto' }}>
        {QUESTIONS.map((q, qi) => (
          <motion.div
            key={q.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.05 + qi * 0.08, ease }}
          >
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>
              0{qi + 1}
            </p>
            <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 26, color: BONE, marginBottom: 22, lineHeight: 1.25 }}>
              {q.prompt}
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {q.options.map(opt => {
                const active = answers[q.key] === opt.value
                return (
                  <motion.button
                    key={opt.value}
                    whileHover={!active ? { x: 3, borderColor: 'rgba(212,182,134,0.45)' } : {}}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => setAnswer(q.key, opt.value)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      width: '100%', padding: '16px 22px',
                      background: active ? 'rgba(212,182,134,0.08)' : 'rgba(232,212,168,0.02)',
                      border: `1px solid ${active ? 'rgba(212,182,134,0.55)' : HAIRLINE}`,
                      borderRadius: 12, cursor: 'pointer',
                      transition: 'all 0.2s', textAlign: 'left',
                    }}
                  >
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 14, fontWeight: 400, color: active ? BONE : `${BONE}c0` }}>
                      {opt.label}
                    </span>
                    {active && <Check size={14} style={{ color: GOLD, flexShrink: 0 }}/>}
                  </motion.button>
                )
              })}
            </div>
          </motion.div>
        ))}

        {/* Free text */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.05 + QUESTIONS.length * 0.08, ease }}
        >
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>
            0{QUESTIONS.length + 1} · optional
          </p>
          <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 24, color: BONE, marginBottom: 18, lineHeight: 1.25 }}>
            Something a friend would call annoying-but-loveable about you:
          </h2>
          <textarea
            value={answers.companion_text}
            onChange={e => setAnswer('companion_text', e.target.value.slice(0, 200))}
            placeholder="One sentence is enough."
            rows={2}
            style={{
              width: '100%', padding: '14px 18px',
              background: 'rgba(232,212,168,0.02)',
              border: `1px solid ${HAIRLINE}`,
              borderRadius: 12, outline: 'none',
              fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 16, color: BONE,
              resize: 'none', lineHeight: 1.5,
              boxSizing: 'border-box',
            }}
          />
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, marginTop: 6, textAlign: 'right' }}>
            {(answers.companion_text || '').length} / 200
          </p>
        </motion.div>

        {/* Submit */}
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 12 }}>
          <motion.button
            whileHover={allAnswered && !saving ? { y: -2, boxShadow: `0 0 48px ${GOLD}33, 0 0 96px ${GOLD}11`, transition: spring } : {}}
            whileTap={allAnswered && !saving ? { scale: 0.98 } : {}}
            onClick={onSubmit}
            disabled={!allAnswered || saving}
            style={primaryBtn(allAnswered && !saving)}
          >
            {saving ? 'Saving…' : allAnswered ? 'Find my people' : 'Pick one from each'}
          </motion.button>
        </div>
      </div>
    </motion.div>
  )
}

// ── Matches view ────────────────────────────────────────────────────────────

function MatchesView({ matches, loading, onRefine, onDone, onTap }) {
  const shown = useMemo(() => matches.slice(0, 4), [matches])
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.55, ease }}>
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.32em', textTransform: 'uppercase', color: GOLD, marginBottom: 14 }}>
          Curated for this trip
        </p>
        <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 'clamp(36px, 4.8vw, 54px)', lineHeight: 1.1, color: BONE, margin: 0 }}>
          Travellers whose rhythm fits yours.
        </h1>
      </div>

      {loading && (
        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, textAlign: 'center', marginTop: 40 }}>
          Finding companions…
        </p>
      )}

      {!loading && shown.length === 0 && (
        <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 16, color: MUTE, textAlign: 'center', marginTop: 40 }}>
          No matches surfaced this round. Try refining your answers below.
        </p>
      )}

      {!loading && shown.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 18, maxWidth: 880, margin: '0 auto' }}>
          {shown.map((m, i) => (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.05 + i * 0.08, ease }}
            >
              <MatchCard match={m} onClick={() => onTap(m.id)}/>
            </motion.div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'center', gap: 14, marginTop: 56, flexWrap: 'wrap' }}>
        <button onClick={onRefine} style={secondaryBtn()}>
          Refine my answers
        </button>
        <motion.button
          whileHover={{ y: -2, boxShadow: `0 0 48px ${GOLD}33`, transition: spring }}
          whileTap={{ scale: 0.98 }}
          onClick={onDone}
          style={primaryBtn(true)}
        >
          Back to dashboard
        </motion.button>
      </div>
    </motion.div>
  )
}

// ── Buttons ─────────────────────────────────────────────────────────────────

function primaryBtn(active) {
  return {
    minWidth: 240, padding: '17px 36px',
    background: active === false ? 'rgba(212,182,134,0.10)' : `linear-gradient(135deg, ${GOLD} 0%, #B89464 100%)`,
    border: 'none', borderRadius: 10,
    cursor: active === false ? 'not-allowed' : 'pointer',
    fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
    letterSpacing: '0.24em', textTransform: 'uppercase', fontWeight: 500,
    color: active === false ? MUTE : '#0a0807',
    transition: 'all 0.25s',
    boxShadow: active === false ? 'none' : `0 0 36px ${GOLD}22, 0 0 72px ${GOLD}08`,
  }
}

function secondaryBtn() {
  return {
    minWidth: 200, padding: '17px 36px',
    background: 'none', border: `1px solid ${HAIRLINE}`, borderRadius: 10, cursor: 'pointer',
    fontFamily: '"Inter Tight",sans-serif', fontSize: 11,
    letterSpacing: '0.24em', textTransform: 'uppercase', fontWeight: 500, color: GOLD,
    transition: 'all 0.25s',
  }
}
