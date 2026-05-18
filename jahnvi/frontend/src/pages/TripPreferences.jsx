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

const STYLES      = ['Adventure', 'Culture & history', 'Nature & landscape', 'City life', 'Food & wine', 'Wellness & rest', 'Nightlife', 'Arts & performance']
const PACES       = [{ key: 'relaxed', label: 'Slow', sub: 'Linger' }, { key: 'moderate', label: 'Moderate', sub: 'Balanced' }, { key: 'packed', label: 'Fast', sub: 'Pack it in' }]
const CURRENCIES  = ['USD', 'EUR', 'JPY', 'GBP', 'CNY', 'AUD', 'CAD', 'CHF', 'HKD', 'SGD', 'SEK', 'NOK', 'NZD', 'INR', 'MXN']
const WHO_OPTS    = [{ key: 'solo', label: 'Solo' }, { key: 'couple', label: 'Couple' }, { key: 'family', label: 'Family' }, { key: 'friends', label: 'Friends' }]
const GROUP_SIZES = [1, 2, 3, 4, 5]

const STRUCTURED_STEPS = 5
const STEP_LABELS = ['Destination', 'Dates', 'Travel style', 'Budget', 'Your group']

const PERSONA_SCREENS = [
  {
    type: 'radio',
    key: 'friends_would_say',
    q: 'Your friends call you the one who:',
    options: [
      { key: 'knows_someone',      label: 'Knows someone everywhere' },
      { key: 'line_friends',       label: 'Makes new friends in every line they stand in' },
      { key: 'vanishes_for_story', label: 'Vanishes for an hour and comes back with a story' },
      { key: 'planner',            label: 'Has the spreadsheet, the playlist, and the backup plan' },
    ],
  },
  {
    type: 'radio',
    key: 'restaurant_order',
    q: "At a restaurant you've never been to, you:",
    options: [
      { key: 'cant_miss',        label: "Ask the server what you absolutely can't miss" },
      { key: 'order_for_table',  label: 'Order for the table before anyone else is ready' },
      { key: 'drink_and_sides',  label: "Get a drink and three sides, somehow that's dinner" },
      { key: 'find_familiar',    label: 'Find the one familiar thing and commit to it' },
    ],
  },
  {
    type: 'radio',
    key: 'what_you_notice',
    q: 'Walking into a new place, the first thing you clock:',
    options: [
      { key: 'light_feel',  label: 'The light and the way the room feels' },
      { key: 'sounds',      label: 'The sounds — music, voices, kitchen clatter' },
      { key: 'smell',       label: 'The smell — bread, candles, something on the fire' },
      { key: 'people_move', label: 'What people are wearing and how they move' },
    ],
  },
  {
    type: 'textarea',
    key: 'small_thing',
    q: "A small thing that's made you weirdly happy lately.",
    hint: 'the 4pm light, cold sheets, a perfectly timed green light — anything',
  },
  {
    type: 'radio',
    key: 'ideal_atmosphere',
    q: "Pick the vibe you'd be most at home in:",
    options: [
      { key: 'wood_bar',       label: 'Wood-panelled bar, low lighting, nobody rushing you out' },
      { key: 'loud_lunch',     label: 'Bright sun, loud lunch, two bottles already on the table' },
      { key: 'concrete_neon',  label: 'Concrete, neon, music you feel in your ribs' },
      { key: 'quiet_morning',  label: 'Quiet morning, open windows, nowhere to be for hours' },
    ],
  },
]

const TOTAL_STEPS = STRUCTURED_STEPS + PERSONA_SCREENS.length

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
  const [destination, setDest]        = useState('')
  const [departure, setDepart]        = useState('')
  const [returnDate, setReturn]       = useState('')
  const [styles, setStyles]           = useState([])
  const [pace, setPace]               = useState('moderate')
  const [budget, setBudget]           = useState('')
  const [currency, setCurrency]       = useState('USD')
  const [nationality, setNationality] = useState('')
  const [groupSize, setGroupSize]     = useState(1)
  const [travelsWith, setTravelsWith] = useState('')

  // ── Persona answers (survey + freeform mix) ──
  const [persona, setPersona] = useState({
    friends_would_say: '',
    restaurant_order:  '',
    what_you_notice:   '',
    small_thing:       '',
    ideal_atmosphere:  '',
  })

  const [step, setStep]         = useState(0)
  const [submitting, setSubmit] = useState(false)

  const toggleStyle = s => setStyles(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])

  const isPersonaStep = step >= STRUCTURED_STEPS
  const personaIdx    = step - STRUCTURED_STEPS
  const currentPersona = PERSONA_SCREENS[personaIdx]

  const canProceed = isPersonaStep
    ? true
    : [
        destination.trim().length > 0,
        departure && returnDate,
        styles.length > 0,
        budget.trim().length > 0,
        groupSize >= 1 && travelsWith.length > 0 && nationality.trim().length > 0,
      ][step]

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
        nationality,
        start_date:          departure || null,
        end_date:            returnDate || null,
        budget_usd:          parseFloat(budget) || 0,
        budget_currency:     currency,
        group_size:          groupSize,
        who_travelling_with: travelsWith || null,
        pace,
        must_haves:          styles,
        avoid_list:          [],
        friends_would_say:   persona.friends_would_say || null,
        restaurant_order:    persona.restaurant_order || null,
        what_you_notice:     persona.what_you_notice || null,
        ideal_atmosphere:    persona.ideal_atmosphere || null,
      },
      persona_answers: {
        small_thing: persona.small_thing,
      },
    }
    sessionStorage.setItem('sonder_trip_profile', JSON.stringify(profile))
    setTimeout(() => navigate('/itinerary'), 1800)
  }

  function advance() {
    if (!canProceed && !isPersonaStep) return
    if (step < TOTAL_STEPS - 1) setStep(s => s + 1)
    else if (!submitting) handleSubmit()
  }

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
            whileHover={{ y: -2, boxShadow: `0 0 48px ${ORANGE}44`, transition: spring }} whileTap={{ scale: 0.98 }}
            onClick={advance}
            style={{ width: '100%', padding: '18px 0', background: `linear-gradient(135deg, ${ORANGE} 0%, #EA580C 100%)`, border: 'none', borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: '#fff', transition: 'all 0.25s', boxShadow: `0 0 40px ${ORANGE}28` }}
          >
            {step < TOTAL_STEPS - 1 ? 'Continue' : submitting ? 'Planning your trip…' : 'Start planning'}
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
