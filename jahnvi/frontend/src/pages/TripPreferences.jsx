import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Globe, Check, Users } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import WordLimitTextarea from '../components/WordLimitTextarea'

const ORANGE = '#F97316'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

const STYLES     = ['Adventure', 'Culture', 'Relaxed', 'Foodie', 'Nature', 'Wellness', 'Nightlife', 'History']
const PACES      = [{ key: 'slow', label: 'Slow', sub: 'Linger' }, { key: 'moderate', label: 'Moderate', sub: 'Balanced' }, { key: 'fast', label: 'Fast', sub: 'Pack it in' }]
const CURRENCIES = ['USD', 'EUR', 'JPY', 'GBP', 'CNY', 'AUD', 'CAD', 'CHF', 'HKD', 'SGD', 'SEK', 'NOK', 'NZD', 'INR', 'MXN']
const WHO_OPTS   = [{ key: 'solo', label: 'Solo' }, { key: 'couple', label: 'Couple' }, { key: 'family', label: 'Family' }, { key: 'friends', label: 'Friends' }]
const GROUP_SIZES = [1, 2, 3, 4, 5]

const STRUCTURED_STEPS = 6
const STEP_LABELS = ['Destination', 'Dates', 'Travel style', 'Budget', 'Your group', 'Stay & transport']

const PERSONA_QUESTIONS = [
  { key: 'travel_goal',          q: 'What do you want to feel on this trip?',                          hint: '"Alive, unplug, at peace, inspired…"' },
  { key: 'travel_personality',   q: 'How do your friends describe you as a traveller?',                hint: '"The one who finds the hidden spots no one else knows about…"' },
  { key: 'pace_preference',      q: 'How do you like your days to feel?',                              hint: '"Mornings packed and afternoons free to wander…"' },
  { key: 'must_not_miss',        q: "What's the one thing that would make this trip unforgettable?",   hint: '"Eating at a place with no English menu…"' },
  { key: 'leave_behind',         q: 'What do you want to leave behind?',                               hint: '"My inbox and the urge to document everything…"' },
  { key: 'ideal_companion',      q: 'Describe your ideal travel companion.',                            hint: '"Someone who can sit in comfortable silence but goes deep when we talk…"' },
  { key: 'dream_trip',           q: 'In a few words, what does your ideal trip feel like?',            hint: '"Slow, unexpected, nourishing…"' },
  { key: 'memorable_moment',     q: "What's a travel moment you keep coming back to?",                 hint: '"Getting lost in a medina and stumbling into a family\'s courtyard…"' },
  { key: 'natural_drift',        q: 'Where do you naturally drift when you have no plan?',             hint: '"Markets, side streets, anywhere with locals and no tourists…"' },
  { key: 'impulsive_decision',   q: 'Tell us about a time you made an impulsive travel decision.',     hint: '"Missed my flight and ended up staying three extra days…"' },
  { key: 'experiences_avoided',  q: 'What kinds of experiences do you usually avoid?',                 hint: '"Anything with a queue, a tour group, or a gift shop at the exit…"' },
  { key: 'perfect_afternoon',    q: 'Describe your perfect unplanned afternoon.',                       hint: '"A good book, a slow walk, stumbling into something unexpected…"' },
  { key: 'lose_track_of_time',   q: 'What makes you completely lose track of time?',                   hint: '"Conversations that go nowhere and everywhere at once…"' },
  { key: 'small_special',        q: 'What small thing always makes a trip feel special?',              hint: '"A coffee drunk standing up at a bar, watching the street wake up…"' },
]

const TOTAL_STEPS = STRUCTURED_STEPS + PERSONA_QUESTIONS.length

function ElegantInput({ value, onChange, placeholder, type = 'text', icon: Icon }) {
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

export default function TripPreferences() {
  const navigate = useNavigate()

  // Step 0 — Destination
  const [destination, setDest] = useState('')

  // Step 1 — Dates
  const [departure, setDepart]  = useState('')
  const [returnDate, setReturn] = useState('')

  // Step 2 — Travel style
  const [styles, setStyles] = useState([])
  const [pace, setPace]     = useState('moderate')

  // Step 3 — Budget
  const [budget, setBudget]     = useState('')
  const [currency, setCurrency] = useState('USD')

  // Step 4 — Your group
  const [nationality, setNationality] = useState('')
  const [groupSize, setGroupSize]     = useState(1)
  const [travelsWith, setTravelsWith] = useState('')

  // Step 5 — Stay & transport
  const [accommodationPref, setAccommodationPref] = useState('')
  const [hireCar, setHireCar]                     = useState(false)
  const [hasLicence, setHasLicence]               = useState(null)

  // Steps 6–12 — Persona questions
  const [persona, setPersona] = useState({
    travel_goal: '', travel_personality: '', pace_preference: '',
    must_not_miss: '', leave_behind: '', ideal_companion: '', dream_trip: '',
    memorable_moment: '', natural_drift: '', impulsive_decision: '',
    experiences_avoided: '', perfect_afternoon: '', lose_track_of_time: '', small_special: '',
  })

  const [step, setStep]         = useState(0)
  const [submitting, setSubmit] = useState(false)

  const toggleStyle = s => setStyles(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])

  const isPersonaStep = step >= STRUCTURED_STEPS
  const personaIdx    = step - STRUCTURED_STEPS
  const currentPersona = PERSONA_QUESTIONS[personaIdx]

  const canProceed = isPersonaStep
    ? true  // persona questions are always skippable
    : [
        destination.trim().length > 0,
        departure && returnDate,
        styles.length > 0,
        budget.trim().length > 0,
        groupSize >= 1,
        accommodationPref.trim().length > 0,
      ][step]

  function handleSubmit() {
    setSubmit(true)
    const profile = {
      constraints: {
        destination_query:        destination,
        nationality,
        start_date:               departure || null,
        end_date:                 returnDate || null,
        flexible_dates:           false,
        budget_usd:               parseFloat(budget) || 0,
        budget_currency:          currency,
        group_size:               groupSize,
        who_travelling_with:      travelsWith || null,
        accommodation_preference: accommodationPref,
        hire_car:                 hireCar,
        has_driving_licence:      hireCar ? hasLicence : null,
        must_haves:               styles,
        avoid_list:               [],
      },
      persona_answers: persona,
    }
    sessionStorage.setItem('sonder_trip_profile', JSON.stringify(profile))
    setTimeout(() => navigate('/itinerary'), 1800)
  }

  function advance() {
    if (!canProceed && !isPersonaStep) return
    if (step < TOTAL_STEPS - 1) setStep(s => s + 1)
    else if (!submitting) handleSubmit()
  }

  const structuredStepNumber = `0${step + 1}`.slice(-2)

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
          <ElegantInput value={departure} onChange={setDepart} placeholder="" type="date"/>
          <div style={{ marginTop: 44 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Return</p>
            <ElegantInput value={returnDate} onChange={setReturn} placeholder="" type="date"/>
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
          <div style={{ display: 'flex', gap: 10, marginBottom: 44 }}>
            {WHO_OPTS.map(w => {
              const active = travelsWith === w.key
              return (
                <motion.button key={w.key} whileTap={{ scale: 0.95 }} onClick={() => setTravelsWith(w.key)}
                  style={{ flex: 1, padding: '16px 0', borderRadius: 14, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 12, background: active ? `${ORANGE}12` : 'transparent', border: `1px solid ${active ? `${ORANGE}55` : HAIRLINE}`, color: active ? ORANGE : MUTE, transition: 'all 0.2s', boxShadow: active ? `0 0 20px ${ORANGE}22` : 'none' }}>
                  {w.label}
                </motion.button>
              )
            })}
          </div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 18 }}>Group size</p>
          <div style={{ display: 'flex', gap: 10, marginBottom: 44 }}>
            {GROUP_SIZES.map(n => {
              const active = groupSize === n
              return (
                <motion.button key={n} whileTap={{ scale: 0.92 }} onClick={() => setGroupSize(n)}
                  style={{ width: 52, height: 52, borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 16, fontWeight: 500, background: active ? `${ORANGE}18` : 'transparent', border: `1px solid ${active ? `${ORANGE}66` : HAIRLINE}`, color: active ? ORANGE : MUTE, transition: 'all 0.2s' }}>
                  {n === 5 ? '5+' : n}
                </motion.button>
              )
            })}
          </div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Your nationality</p>
          <ElegantInput value={nationality} onChange={setNationality} placeholder="British, Indian, Brazilian…" icon={Users}/>
        </div>
      ),
    },
    {
      number: '06', heading: 'How do you want to stay and get around?',
      sub: 'No wrong answers — this helps us find the right kind of place.',
      content: (
        <div style={{ marginTop: 52 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Where would you like to stay?</p>
          <ElegantInput value={accommodationPref} onChange={setAccommodationPref} placeholder="Boutique hotel, Airbnb, hostel…"/>
          <div style={{ marginTop: 44 }}>
            <Toggle value={hireCar} onChange={setHireCar} label="I'd like to hire a car at the destination"/>
          </div>
          <AnimatePresence>
            {hireCar && (
              <motion.div
                initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.28, ease }}
              >
                <Toggle
                  value={hasLicence === true}
                  onChange={v => setHasLicence(v ? true : false)}
                  label="I have a valid driving licence"
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ),
    },
  ]

  const current = STRUCTURED_CONTENT[Math.min(step, STRUCTURED_STEPS - 1)]

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

        {/* Progress dots */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 6, paddingTop: 32, position: 'relative', zIndex: 1 }}>
          {PERSONA_QUESTIONS.map((_, i) => (
            <div key={i} style={{ width: i === personaIdx ? 20 : 6, height: 6, borderRadius: 3, background: i === personaIdx ? ORANGE : i < personaIdx ? `${ORANGE}44` : HAIRLINE, transition: 'all 0.35s ease' }}/>
          ))}
        </div>

        {/* Question */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 48px', maxWidth: 720, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>
          <AnimatePresence mode="wait">
            <motion.div key={step} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -24 }} transition={{ duration: 0.42, ease }} style={{ width: '100%', textAlign: 'center' }}>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 24 }}>
                {personaIdx + 1} of {PERSONA_QUESTIONS.length}
              </p>
              <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 48, lineHeight: 1.2, color: BONE, marginBottom: 48 }}>
                {currentPersona.q}
              </h2>
              <WordLimitTextarea
                value={persona[currentPersona.key]}
                onChange={val => setPersona(prev => ({ ...prev, [currentPersona.key]: val }))}
                placeholder={currentPersona.hint}
                rows={4}
              />
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Actions */}
        <div style={{ padding: '32px 48px 52px', maxWidth: 720, margin: '0 auto', width: '100%', boxSizing: 'border-box', position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <motion.button
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={() => { setPersona(prev => ({ ...prev, [currentPersona.key]: '' })); advance() }}
              style={{ flex: 1, padding: '18px 0', background: 'transparent', border: `1px solid ${HAIRLINE}`, borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, transition: 'all 0.2s' }}
            >
              Skip
            </motion.button>
            <motion.button
              whileHover={{ y: -2, boxShadow: `0 0 48px ${ORANGE}44`, transition: spring }} whileTap={{ scale: 0.98 }}
              onClick={advance}
              style={{ flex: 3, padding: '18px 0', background: `linear-gradient(135deg, ${ORANGE} 0%, #EA580C 100%)`, border: 'none', borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: '#fff', transition: 'all 0.25s', boxShadow: `0 0 40px ${ORANGE}28` }}
            >
              {step < TOTAL_STEPS - 1 ? 'Continue' : submitting ? 'Planning your trip…' : 'Start planning'}
            </motion.button>
          </div>
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
          onClick={() => step > 0 ? setStep(s => s - 1) : navigate(-1)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, display: 'flex', alignItems: 'center', gap: 8, transition: 'color 0.2s' }}
          onMouseEnter={e => { e.currentTarget.style.color = BONE }} onMouseLeave={e => { e.currentTarget.style.color = MUTE }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>{step > 0 ? 'Back' : 'Dashboard'}</span>
        </motion.button>
        <SonderNav3D markSize={32}/>
        <div style={{ width: 80 }}/>
      </nav>

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>

        {/* left — progress track */}
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

          {/* giant ghost number */}
          <div style={{ position: 'relative', marginTop: 32 }}>
            <AnimatePresence mode="wait">
              <motion.span key={step} initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0, filter: [`drop-shadow(0 0 24px ${ORANGE}22)`, `drop-shadow(0 0 64px ${ORANGE}55)`, `drop-shadow(0 0 24px ${ORANGE}22)`] }} exit={{ opacity: 0, y: -30 }} transition={{ duration: 0.45, ease, filter: { duration: 5, repeat: Infinity, ease: 'easeInOut' } }}
                style={{ display: 'block', fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 220, lineHeight: 0.82, letterSpacing: '-0.05em', color: ORANGE, opacity: 0.10, userSelect: 'none' }}>
                {current.number}
              </motion.span>
            </AnimatePresence>
          </div>
        </div>

        {/* right — form */}
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
              style={{ width: '100%', padding: '19px 0', background: canProceed ? `linear-gradient(135deg, ${ORANGE} 0%, #EA580C 100%)` : 'rgba(212,182,134,0.06)', border: `1px solid ${canProceed ? 'transparent' : HAIRLINE}`, borderRadius: 12, cursor: canProceed ? 'pointer' : 'default', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: canProceed ? '#fff' : 'rgba(212,182,134,0.28)', transition: 'all 0.25s', boxShadow: canProceed ? `0 0 48px ${ORANGE}33, 0 0 96px ${ORANGE}11` : 'none' }}
            >
              Continue
            </motion.button>
          </div>
        </div>
      </div>
    </div>
  )
}
