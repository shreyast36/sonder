import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Globe, Check } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import WordLimitTextarea from '../components/WordLimitTextarea'

const ORANGE = '#F97316'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

const STYLES      = ['Adventure', 'Culture & history', 'Nature & landscape', 'City life', 'Food & wine', 'Wellness & rest', 'Nightlife', 'Arts & performance']
const PACES       = [{ key: 'relaxed', label: 'Slow', sub: 'Linger' }, { key: 'moderate', label: 'Moderate', sub: 'Balanced' }, { key: 'packed', label: 'Fast', sub: 'Pack it in' }]
const CURRENCIES  = ['USD', 'EUR', 'JPY', 'GBP', 'CNY', 'AUD', 'CAD', 'CHF', 'HKD', 'SGD', 'SEK', 'NOK', 'NZD', 'INR', 'MXN']
const WHO_OPTS    = [{ key: 'solo', label: 'Solo' }, { key: 'couple', label: 'Couple' }, { key: 'family', label: 'Family' }, { key: 'friends', label: 'Friends' }]
// Group size is only user-pickable for family / friends. Solo locks to 1,
// couple locks to 2. Cap at 8 — past that the trip-planning shape changes
// and the generator + ranker aren't tuned for it.
const PARTY_SIZES = [2, 3, 4, 5, 6, 7, 8]
const MAX_PARTY_SIZE = 8

const STRUCTURED_STEPS = 5
const STEP_LABELS = ['Destination', 'Dates', 'Travel style', 'Budget', 'Your group']

const PERSONA_SCREENS = [
  {
    type: 'radio',
    key: 'social_role',
    q: 'On a trip, people usually end up relying on you for:',
    options: [
      { key: 'place_finder',  label: 'Finding the place everyone talks about for years after' },
      { key: 'social_bridge', label: 'Talking to strangers nobody else would approach' },
      { key: 'day_anchor',    label: 'Keeping the day from completely falling apart' },
      { key: 'pace_reader',   label: 'Noticing when everyone needs to slow down' },
    ],
  },
  {
    type: 'radio',
    key: 'trip_feeling',
    q: 'The best trips usually leave you feeling:',
    options: [
      { key: 'brain_louder',    label: 'Like your brain got louder in a good way' },
      { key: 'disappeared',     label: 'Like you disappeared from your normal life for a bit' },
      { key: 'story_collector', label: "Like you collected stories you'll tell forever" },
      { key: 'exhaled',         label: 'Like you finally exhaled properly' },
    ],
  },
  {
    type: 'radio',
    key: 'friction_response',
    q: 'Something goes wrong halfway through the day. Your instinct is to:',
    options: [
      { key: 'regroup',  label: 'Find somewhere good to sit and regroup' },
      { key: 'pivot',    label: 'Turn the detour into the new plan' },
      { key: 'fix_fast', label: 'Fix it immediately before it gets worse' },
      { key: 'mask',     label: "Pretend it's fine until someone notices" },
    ],
  },
  {
    type: 'textarea',
    key: 'small_thing',
    q: "What's a tiny thing that made life feel unusually good recently?",
    hint: 'a warm plate, a perfectly timed train, hearing someone laugh from another room — anything',
  },
  {
    type: 'radio',
    key: 'ideal_atmosphere',
    q: 'You instantly feel at home in places that are:',
    options: [
      { key: 'loud_anonymous',  label: 'Loud enough that nobody notices your conversation' },
      { key: 'quiet_attentive', label: 'Quiet enough to hear glasses and footsteps' },
      { key: 'lively_chaos',    label: 'Slightly chaotic, but in a way that feels alive' },
      { key: 'slow_sunlit',     label: 'Slow, sunlit, and impossible to rush through' },
    ],
  },
]

const TOTAL_STEPS = STRUCTURED_STEPS + PERSONA_SCREENS.length

function ElegantInput({ value, onChange, placeholder, type = 'text', icon: Icon, min, max }) {
  const [focused, setFocused] = useState(false)
  return (
    <div style={{ position: 'relative' }}>
      {Icon && <Icon size={14} style={{ position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)', color: focused ? ORANGE : MUTE, transition: 'color 0.2s', pointerEvents: 'none' }}/>}
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        min={min}
        max={max}
        style={{
          width: '100%', padding: `16px 0 16px ${Icon ? '28px' : '0'}`,
          background: 'none', border: 'none',
          borderBottom: `1px solid ${focused ? `${ORANGE}88` : HAIRLINE}`,
          color: BONE, outline: 'none',
          fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 28,
          transition: 'border-color 0.25s', boxSizing: 'border-box',
          boxShadow: focused ? `0 2px 0 ${ORANGE}22` : 'none',
        }}
      />
      {focused && (
        <motion.div
          initial={{ scaleX: 0 }} animate={{ scaleX: 1 }}
          style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 1, background: `linear-gradient(to right, transparent, ${ORANGE}, transparent)`, transformOrigin: 'left' }}
        />
      )}
    </div>
  )
}

// Today's date in ISO yyyy-mm-dd, used as the min attr on the
// departure date picker so the browser blocks past dates at the
// widget level (in addition to the canProceed JS guard).
function todayISO() {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function Toggle({ value, onChange, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 0', borderBottom: `1px solid ${HAIRLINE}` }}>
      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, color: BONE, fontWeight: 300 }}>{label}</span>
      <motion.button
        onClick={() => onChange(!value)}
        style={{ width: 48, height: 26, borderRadius: 13, background: value ? `${ORANGE}` : 'rgba(232,212,168,0.10)', border: `1px solid ${value ? ORANGE : HAIRLINE}`, cursor: 'pointer', position: 'relative', transition: 'all 0.25s' }}
      >
        <motion.div
          animate={{ x: value ? 22 : 2 }}
          transition={{ type: 'spring', stiffness: 400, damping: 28 }}
          style={{ width: 20, height: 20, borderRadius: '50%', background: value ? '#fff' : MUTE, position: 'absolute', top: 2 }}
        />
      </motion.button>
    </div>
  )
}

function VibeChip({ active, onClick, children, disabled = false }) {
  return (
    <motion.button
      whileHover={!disabled && !active ? { scale: 1.04 } : {}}
      whileTap={!disabled ? { scale: 0.96 } : {}}
      onClick={disabled ? undefined : onClick}
      style={{
        padding: '13px 22px', borderRadius: 26, cursor: disabled ? 'default' : 'pointer',
        fontFamily: '"Inter Tight",sans-serif', fontSize: 12.5, letterSpacing: '0.02em',
        background: active ? `${ORANGE}18` : 'transparent',
        border: `1px solid ${active ? `${ORANGE}66` : HAIRLINE}`,
        color: active ? ORANGE : (disabled ? DIM : MUTE),
        transition: 'all 0.2s',
        boxShadow: active ? `0 0 20px ${ORANGE}22` : 'none',
        opacity: disabled ? 0.5 : 1,
        textAlign: 'left',
      }}
    >
      {children}
    </motion.button>
  )
}

export default function TripPreferences() {
  const navigate = useNavigate()

  // ── Structured steps (logistics) ──
  // Seed-from-dashboard: when the user clicks an inspiration destination
  // on the empty-state dashboard, we stash it in sessionStorage and read
  // it once here so the form lands with that city pre-filled.
  const [destination, setDest]        = useState(() => {
    try {
      const seed = sessionStorage.getItem('sonder_seed_destination')
      if (seed) {
        sessionStorage.removeItem('sonder_seed_destination')
        return seed
      }
    } catch { /* noop */ }
    return ''
  })
  const [departure, setDepart]        = useState('')
  const [returnDate, setReturn]       = useState('')
  const [styles, setStyles]           = useState([])
  // No default pace — make the user choose. A pre-selected pace
  // colours every downstream recommendation, and almost everyone
  // accepts the default without thinking; better to ask.
  const [pace, setPace]               = useState('')
  const [budget, setBudget]           = useState('')
  const [currency, setCurrency]       = useState('USD')
  const [groupSize, setGroupSize]     = useState(1)
  const [travelsWith, setTravelsWith] = useState('')
  // Solo-only — drives the same-gender hard filter for cotraveller
  // matching. We only ask solo travellers; couples are male+female by
  // design, family/friends matching is disabled.
  const [gender, setGender]           = useState('')

  // Group size follows from travel style:
  //   solo    → locked at 1
  //   couple  → locked at 2
  //   family  → user picks (2-8); skips matching downstream
  //   friends → user picks (2-8); matching kept on
  // Whenever travelsWith flips, snap group_size to the correct default
  // (and let the user adjust afterwards for family / friends).
  function chooseTravelsWith(key) {
    setTravelsWith(key)
    if (key === 'solo')   setGroupSize(1)
    else if (key === 'couple') setGroupSize(2)
    else if (key === 'family' || key === 'friends') {
      // Default the user into a sensible mid-size, let them adjust.
      setGroupSize(prev => (prev >= 2 && prev <= MAX_PARTY_SIZE) ? prev : 3)
    }
  }
  const needsPartySize = travelsWith === 'family' || travelsWith === 'friends'

  // ── Persona answers (survey + freeform mix) ──
  const [persona, setPersona] = useState({
    social_role:        '',
    trip_feeling:       '',
    friction_response:  '',
    small_thing:        '',
    ideal_atmosphere:   '',
  })

  const [step, setStep]         = useState(0)
  const [submitting, setSubmit] = useState(false)

  const toggleStyle = s => setStyles(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])

  const isPersonaStep = step >= STRUCTURED_STEPS
  const personaIdx    = step - STRUCTURED_STEPS
  const currentPersona = PERSONA_SCREENS[personaIdx]

  // Per-screen persona validation. Each screen type has its own
  // notion of "answered" — radio/multi need a selection, textarea
  // needs non-empty text, dual_text needs both inputs.
  function isPersonaScreenAnswered(screen) {
    if (!screen) return false
    if (screen.type === 'radio')    return !!persona[screen.key]
    if (screen.type === 'multi')    return Array.isArray(persona[screen.key]) && persona[screen.key].length >= 1
    if (screen.type === 'textarea') return (persona[screen.key] || '').trim().length > 0
    if (screen.type === 'dual_text') {
      const [k1, k2] = screen.keys
      return (persona[k1] || '').trim().length > 0 && (persona[k2] || '').trim().length > 0
    }
    return false
  }

  // Date validation: departure must be today or later; return must
  // be on or after departure. Used both by canProceed (JS gate) and
  // the date pickers' `min` attrs (browser-level gate).
  const today = todayISO()
  const datesValid = (
    !!departure && !!returnDate &&
    departure >= today &&
    returnDate >= departure
  )

  const canProceed = isPersonaStep
    ? isPersonaScreenAnswered(currentPersona)
    : [
        destination.trim().length > 0,
        datesValid,
        styles.length > 0 && pace.length > 0,
        budget.trim().length > 0 && parseFloat(budget) > 0,
        travelsWith.length > 0 &&
          (
            travelsWith === 'solo'   ? (groupSize === 1 && (gender === 'male' || gender === 'female')) :
            travelsWith === 'couple' ? groupSize === 2 :
            groupSize >= 2 && groupSize <= MAX_PARTY_SIZE
          ),
      ][step]

  // Final-submit gate: every persona screen must be answered before
  // the "Determine your persona" button fires. Without this the user
  // can land on the last screen, hit Continue, and skip past
  // unanswered earlier persona screens because each screen-level
  // check was independent.
  const allPersonaAnswered = PERSONA_SCREENS.every(isPersonaScreenAnswered)
  const isFinalStep = step === TOTAL_STEPS - 1
  const canSubmit = isFinalStep ? allPersonaAnswered : canProceed

  function toggleMulti(key, value, max = null) {
    setPersona(prev => {
      const list = prev[key] || []
      if (list.includes(value)) return { ...prev, [key]: list.filter(v => v !== value) }
      if (max && list.length >= max) return prev
      return { ...prev, [key]: [...list, value] }
    })
  }

  function setSingle(key, value) {
    setPersona(prev => ({ ...prev, [key]: value }))
  }

  function handleSubmit() {
    setSubmit(true)
    const profile = {
      constraints: {
        destination_query:   destination,
        start_date:          departure || null,
        end_date:            returnDate || null,
        budget_usd:          parseFloat(budget) || 0,
        budget_currency:     currency,
        group_size:          groupSize,
        who_travelling_with: travelsWith || null,
        gender:              travelsWith === 'solo' ? (gender || null) : null,
        pace,
        must_haves:          styles,
        avoid_list:          [],
        social_role:         persona.social_role || null,
        trip_feeling:        persona.trip_feeling || null,
        friction_response:   persona.friction_response || null,
        ideal_atmosphere:    persona.ideal_atmosphere || null,
      },
      persona_answers: {
        small_thing: persona.small_thing,
      },
    }
    sessionStorage.setItem('sonder_trip_profile', JSON.stringify(profile))
    setTimeout(() => navigate('/persona-reveal'), 1800)
  }

  function advance() {
    if (!canProceed) return
    if (step < TOTAL_STEPS - 1) {
      setStep(s => s + 1)
      return
    }
    // Final step — only fire submit when every persona screen is
    // answered, never just the current one. Prevents skipping past
    // earlier unanswered screens by tabbing through to the end.
    if (!allPersonaAnswered) return
    if (submitting) return
    handleSubmit()
  }

  // Enter advances when the current step is valid. Skipped inside
  // textareas (Enter there should newline) and during submit. Listens
  // at the window level so it works regardless of which field is
  // focused — including persona radio screens where no field has
  // focus by default.
  useEffect(() => {
    function onKey(e) {
      if (e.key !== 'Enter') return
      const tag = (e.target?.tagName || '').toUpperCase()
      if (tag === 'TEXTAREA') return
      if (!canProceed) return
      if (isFinalStep && !allPersonaAnswered) return
      if (submitting) return
      e.preventDefault()
      advance()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canProceed, isFinalStep, allPersonaAnswered, submitting, step])

  const STRUCTURED_CONTENT = [
    {
      number: '01', heading: 'Where are you dreaming of?',
      sub: "A city, a coast, a country you've always meant to visit.",
      content: (
        <div style={{ marginTop: 52 }}>
          <ElegantInput value={destination} onChange={setDest} placeholder="Bali, Kyoto, Patagonia…" icon={Globe}/>
        </div>
      ),
    },
    {
      number: '02', heading: 'When do you want to go?',
      sub: 'Give yourself something to look forward to.',
      content: (
        <div style={{ marginTop: 52 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Departure</p>
          <ElegantInput value={departure} onChange={setDepart} placeholder="" type="date" min={today}/>
          <div style={{ marginTop: 44 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Return</p>
            <ElegantInput value={returnDate} onChange={setReturn} placeholder="" type="date" min={departure || today}/>
          </div>
        </div>
      ),
    },
    {
      number: '03', heading: 'How do you like to travel?',
      sub: 'Pick everything that sounds like you.',
      content: (
        <div style={{ marginTop: 52 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 44 }}>
            {STYLES.map(s => {
              const active = styles.includes(s)
              return (
                <motion.button key={s} whileHover={{ scale: 1.06 }} whileTap={{ scale: 0.94 }} onClick={() => toggleStyle(s)}
                  style={{ padding: '11px 20px', borderRadius: 24, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 12, letterSpacing: '0.06em', background: active ? `${ORANGE}18` : 'transparent', border: `1px solid ${active ? `${ORANGE}66` : HAIRLINE}`, color: active ? ORANGE : MUTE, transition: 'all 0.2s', boxShadow: active ? `0 0 20px ${ORANGE}22` : 'none' }}>
                  {s}
                </motion.button>
              )
            })}
          </div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 18 }}>Pace</p>
          <div style={{ display: 'flex', gap: 12 }}>
            {PACES.map(p => {
              const active = pace === p.key
              return (
                <motion.button key={p.key} whileTap={{ scale: 0.97 }} onClick={() => setPace(p.key)}
                  style={{ flex: 1, padding: '20px 0', borderRadius: 14, cursor: 'pointer', background: active ? `${ORANGE}12` : 'rgba(232,212,168,0.02)', border: `1px solid ${active ? `${ORANGE}55` : HAIRLINE}`, transition: 'all 0.2s', boxShadow: active ? `0 0 24px ${ORANGE}22` : 'none' }}>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: active ? ORANGE : MUTE, marginBottom: 4 }}>{p.label}</p>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: active ? `${ORANGE}88` : DIM }}>{p.sub}</p>
                </motion.button>
              )
            })}
          </div>
        </div>
      ),
    },
    {
      number: '04', heading: "What's your budget?",
      sub: 'Total trip spend, including flights.',
      content: (
        <div style={{ marginTop: 52 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 18 }}>Currency</p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 44 }}>
            {CURRENCIES.map(c => (
              <motion.button key={c} whileHover={{ scale: 1.07 }} whileTap={{ scale: 0.93 }} onClick={() => setCurrency(c)}
                style={{ padding: '9px 16px', borderRadius: 20, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.10em', background: currency === c ? `${ORANGE}18` : 'transparent', border: `1px solid ${currency === c ? `${ORANGE}55` : HAIRLINE}`, color: currency === c ? ORANGE : MUTE, transition: 'all 0.2s' }}>
                {c}
              </motion.button>
            ))}
          </div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Amount</p>
          <ElegantInput value={budget} onChange={setBudget} placeholder="2500" type="number"/>
        </div>
      ),
    },
    {
      number: '05', heading: 'Who are you travelling with?',
      sub: 'Help us shape the trip around your group.',
      content: (
        <div style={{ marginTop: 52 }}>
          <div style={{ display: 'flex', gap: 10, marginBottom: needsPartySize ? 28 : 44 }}>
            {WHO_OPTS.map(w => {
              const active = travelsWith === w.key
              return (
                <motion.button key={w.key} whileTap={{ scale: 0.95 }} onClick={() => chooseTravelsWith(w.key)}
                  style={{ flex: 1, padding: '16px 0', borderRadius: 14, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 12, background: active ? `${ORANGE}12` : 'transparent', border: `1px solid ${active ? `${ORANGE}55` : HAIRLINE}`, color: active ? ORANGE : MUTE, transition: 'all 0.2s', boxShadow: active ? `0 0 20px ${ORANGE}22` : 'none' }}>
                  {w.label}
                </motion.button>
              )
            })}
          </div>
          <AnimatePresence>
            {needsPartySize && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.25 }}
                style={{ overflow: 'hidden' }}
              >
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 18 }}>
                  How many in your {travelsWith === 'family' ? 'family' : 'group'}?
                </p>
                <div style={{ display: 'flex', gap: 10, marginBottom: 44, flexWrap: 'wrap' }}>
                  {PARTY_SIZES.map(n => {
                    const active = groupSize === n
                    return (
                      <motion.button key={n} whileTap={{ scale: 0.92 }} onClick={() => setGroupSize(n)}
                        style={{ width: 52, height: 52, borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 16, fontWeight: 500, background: active ? `${ORANGE}18` : 'transparent', border: `1px solid ${active ? `${ORANGE}66` : HAIRLINE}`, color: active ? ORANGE : MUTE, transition: 'all 0.2s' }}>
                        {n}
                      </motion.button>
                    )
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          {/* Solo-only — drives the same-gender hard filter for
              cotraveller matching. Couples / family / friends skip
              this because their matching pool doesn't need gender
              (couples are male+female by seed design; family/friends
              matching is disabled). */}
          <AnimatePresence>
            {travelsWith === 'solo' && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.25 }}
                style={{ overflow: 'hidden' }}
              >
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 10 }}>
                  Your gender
                </p>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 11, color: DIM, marginBottom: 18, lineHeight: 1.5 }}>
                  We only match solo travellers with the same gender for safety. Skipped for couples / groups.
                </p>
                <div style={{ display: 'flex', gap: 10, marginBottom: 44 }}>
                  {[{ key: 'female', label: 'Female' }, { key: 'male', label: 'Male' }].map(g => {
                    const active = gender === g.key
                    return (
                      <motion.button
                        key={g.key} whileTap={{ scale: 0.95 }} onClick={() => setGender(g.key)}
                        style={{
                          flex: 1, padding: '16px 0', borderRadius: 14,
                          cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 12,
                          background: active ? `${ORANGE}12` : 'transparent',
                          border: `1px solid ${active ? `${ORANGE}55` : HAIRLINE}`,
                          color: active ? ORANGE : MUTE,
                          transition: 'all 0.2s',
                          boxShadow: active ? `0 0 20px ${ORANGE}22` : 'none',
                        }}
                      >
                        {g.label}
                      </motion.button>
                    )
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ),
    },
  ]

  const current = STRUCTURED_CONTENT[Math.min(step, STRUCTURED_STEPS - 1)]

  function renderPersonaScreen(screen) {
    if (screen.type === 'radio') {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
          {screen.options.map(o => {
            const active = persona[screen.key] === o.key
            return (
              <VibeChip key={o.key} active={active} onClick={() => setSingle(screen.key, o.key)}>
                {o.label}
              </VibeChip>
            )
          })}
        </div>
      )
    }
    if (screen.type === 'multi') {
      const selected = persona[screen.key] || []
      const atMax = screen.max && selected.length >= screen.max
      return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 12, justifyContent: 'center' }}>
          {screen.options.map(o => {
            const active = selected.includes(o)
            return (
              <VibeChip
                key={o} active={active}
                disabled={!active && atMax}
                onClick={() => toggleMulti(screen.key, o, screen.max)}
              >
                {o}
              </VibeChip>
            )
          })}
        </div>
      )
    }
    if (screen.type === 'textarea') {
      return (
        <WordLimitTextarea
          value={persona[screen.key]}
          onChange={val => setSingle(screen.key, val)}
          placeholder={screen.hint}
          rows={4}
        />
      )
    }
    if (screen.type === 'dual_text') {
      const [k1, k2] = screen.keys
      const [l1, l2] = screen.labels
      const [h1, h2] = screen.hints
      return (
        <div style={{ marginTop: 12, textAlign: 'left' }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>{l1}</p>
          <ElegantInput value={persona[k1]} onChange={v => setSingle(k1, v)} placeholder={h1}/>
          <div style={{ marginTop: 36 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>{l2}</p>
            <ElegantInput value={persona[k2]} onChange={v => setSingle(k2, v)} placeholder={h2}/>
          </div>
        </div>
      )
    }
    return null
  }

  if (isPersonaStep) {
    return (
      <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
        <AppBackground accent="#F97316"/>

        <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
          <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={() => setStep(s => s - 1)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, display: 'flex', alignItems: 'center', gap: 8 }}
            onMouseEnter={e => { e.currentTarget.style.color = BONE }} onMouseLeave={e => { e.currentTarget.style.color = MUTE }}>
            <ArrowLeft size={18}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
          </motion.button>
          <SonderNav3D markSize={32}/>
          <div style={{ width: 80 }}/>
        </nav>

        <div style={{ display: 'flex', justifyContent: 'center', gap: 6, paddingTop: 32, position: 'relative', zIndex: 1 }}>
          {PERSONA_SCREENS.map((_, i) => (
            <div key={i} style={{ width: i === personaIdx ? 20 : 6, height: 6, borderRadius: 3, background: i === personaIdx ? ORANGE : i < personaIdx ? `${ORANGE}44` : HAIRLINE, transition: 'all 0.35s ease' }}/>
          ))}
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 48px', maxWidth: 720, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>
          <AnimatePresence mode="wait">
            <motion.div key={step} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -24 }} transition={{ duration: 0.42, ease }} style={{ width: '100%', textAlign: 'center' }}>
              {personaIdx === 0 && (
                <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 18, color: `${ORANGE}cc`, marginBottom: 14 }}>
                  Okay. Let's make this feel like you.
                </p>
              )}
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 24 }}>
                {personaIdx + 1} of {PERSONA_SCREENS.length}
              </p>
              <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 44, lineHeight: 1.2, color: BONE, marginBottom: currentPersona.sub ? 14 : 36 }}>
                {currentPersona.q}
              </h2>
              {currentPersona.sub && (
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, color: MUTE, marginBottom: 36 }}>
                  {currentPersona.sub}
                </p>
              )}
              {renderPersonaScreen(currentPersona)}
            </motion.div>
          </AnimatePresence>
        </div>

        <div style={{ padding: '32px 48px 52px', maxWidth: 720, margin: '0 auto', width: '100%', boxSizing: 'border-box', position: 'relative', zIndex: 1 }}>
          <motion.button
            whileHover={canSubmit && !submitting ? { y: -2, boxShadow: `0 0 48px ${ORANGE}44`, transition: spring } : {}}
            whileTap={canSubmit && !submitting ? { scale: 0.98 } : {}}
            onClick={advance}
            disabled={!canSubmit || submitting}
            title={!canSubmit && isFinalStep ? 'Answer every question to reveal your persona' : (!canSubmit ? 'Complete this question first' : '')}
            style={{
              width: '100%', padding: '18px 0',
              background: (!canSubmit || submitting)
                ? 'rgba(232,212,168,0.06)'
                : `linear-gradient(135deg, ${ORANGE} 0%, #EA580C 100%)`,
              border: (!canSubmit || submitting) ? `1px solid ${HAIRLINE}` : 'none',
              borderRadius: 12,
              cursor: (!canSubmit || submitting) ? 'not-allowed' : 'pointer',
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
              letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500,
              color: (!canSubmit || submitting) ? MUTE : '#fff',
              transition: 'all 0.25s',
              boxShadow: (!canSubmit || submitting) ? 'none' : `0 0 40px ${ORANGE}28`,
              opacity: (!canSubmit || submitting) ? 0.7 : 1,
            }}
          >
            {step < TOTAL_STEPS - 1
              ? 'Continue'
              : submitting
                ? 'Reading your persona…'
                : allPersonaAnswered
                  ? 'Determine your persona'
                  : 'Answer every question to continue'}
          </motion.button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent="#F97316"/>

      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => step > 0 ? setStep(s => s - 1) : navigate('/dashboard')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, display: 'flex', alignItems: 'center', gap: 8, transition: 'color 0.2s' }}
          onMouseEnter={e => { e.currentTarget.style.color = BONE }} onMouseLeave={e => { e.currentTarget.style.color = MUTE }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>{step > 0 ? 'Back' : 'Dashboard'}</span>
        </motion.button>
        <SonderNav3D markSize={32}/>
        <div style={{ width: 80 }}/>
      </nav>

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>

        <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '68px 60px', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: `radial-gradient(ellipse 70% 50% at 20% 30%, ${ORANGE}0C 0%, transparent 65%)`, pointerEvents: 'none' }}/>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 24 }}>
            Step {step + 1} of {STRUCTURED_STEPS}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', marginBottom: 'auto' }}>
            {STEP_LABELS.map((label, i) => (
              <motion.div key={i} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, delay: i * 0.07, ease }}
                style={{ display: 'flex', alignItems: 'center', gap: 18, padding: '16px 0', borderBottom: `1px solid ${HAIRLINE}` }}>
                <motion.div
                  animate={i === step ? { boxShadow: [`0 0 0 0 ${ORANGE}00`, `0 0 16px ${ORANGE}44`, `0 0 0 0 ${ORANGE}00`] } : {}}
                  transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                  style={{ width: 30, height: 30, borderRadius: '50%', flexShrink: 0, border: `1px solid ${i === step ? `${ORANGE}66` : i < step ? `${ORANGE}33` : HAIRLINE}`, background: i === step ? `${ORANGE}14` : i < step ? `${ORANGE}08` : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.3s' }}>
                  {i < step
                    ? <Check size={12} style={{ color: ORANGE }}/>
                    : <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, fontWeight: 500, color: i <= step ? ORANGE : MUTE }}>{String(i + 1).padStart(2, '0')}</span>
                  }
                </motion.div>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, color: i === step ? BONE : i < step ? MUTE : DIM, fontWeight: i === step ? 500 : 300, transition: 'color 0.3s' }}>
                  {label}
                </span>
                {i < step && <span style={{ marginLeft: 'auto', fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: ORANGE, opacity: 0.70 }}>Done</span>}
              </motion.div>
            ))}
          </div>

        </div>

        <div style={{ padding: '68px 60px', display: 'flex', flexDirection: 'column' }}>
          <AnimatePresence mode="wait">
            <motion.div key={step} initial={{ opacity: 0, x: 32 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -32 }} transition={{ duration: 0.38, ease }} style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 42, lineHeight: 1.15, color: BONE, marginBottom: 14 }}>
                {current.heading}
              </h2>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, lineHeight: 1.75, color: MUTE }}>
                {current.sub}
              </p>
              {current.content}
            </motion.div>
          </AnimatePresence>

          <div style={{ marginTop: 60 }}>
            <motion.button
              whileHover={canProceed ? { y: -3, boxShadow: `0 0 64px ${ORANGE}55, 0 0 128px ${ORANGE}18`, transition: spring } : {}}
              whileTap={canProceed ? { scale: 0.98 } : {}}
              onClick={advance}
              disabled={!canProceed}
              title={!canProceed ? 'Fill out this step to continue' : ''}
              style={{ width: '100%', padding: '19px 0', background: canProceed ? `linear-gradient(135deg, ${ORANGE} 0%, #EA580C 100%)` : 'rgba(212,182,134,0.06)', border: `1px solid ${canProceed ? 'transparent' : HAIRLINE}`, borderRadius: 12, cursor: canProceed ? 'pointer' : 'not-allowed', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: canProceed ? '#fff' : 'rgba(212,182,134,0.28)', transition: 'all 0.25s', boxShadow: canProceed ? `0 0 48px ${ORANGE}33, 0 0 96px ${ORANGE}11` : 'none' }}
            >
              Continue
            </motion.button>
          </div>
        </div>
      </div>
    </div>
  )
}
