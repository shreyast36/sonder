import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ChevronRight, Globe } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GRAIN, ease } from '../lib/tokens'

const STYLES = ['Adventure', 'Culture', 'Relaxed', 'Foodie', 'Nature', 'Wellness', 'Nightlife', 'History']
const PACES  = ['Slow', 'Moderate', 'Fast']
const CURRENCIES = ['USD', 'EUR', 'GBP', 'INR', 'AUD', 'CAD', 'JPY', 'SGD']

const TOTAL_STEPS = 4
const STEP_LABELS = ['Destination', 'Dates', 'Your style', 'Budget']

function SectionLabel({ children }) {
  return (
    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 16 }}>
      {children}
    </p>
  )
}

function TextInput({ value, onChange, placeholder, type = 'text' }) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        width: '100%', padding: '14px 16px',
        background: 'rgba(232,212,168,0.03)', border: `1px solid ${HAIRLINE}`,
        borderRadius: 10, color: BONE, outline: 'none',
        fontFamily: '"Inter Tight",sans-serif', fontSize: 14, fontWeight: 300,
        boxSizing: 'border-box',
      }}
    />
  )
}

export default function TripPreferences() {
  const navigate = useNavigate()
  const [step, setStep]         = useState(0)
  const [destination, setDest]  = useState('')
  const [departure, setDepart]  = useState('')
  const [returnDate, setReturn] = useState('')
  const [styles, setStyles]     = useState([])
  const [pace, setPace]         = useState('Moderate')
  const [budget, setBudget]     = useState('')
  const [currency, setCurrency] = useState('USD')
  const [submitting, setSubmit] = useState(false)

  const toggleStyle = s => setStyles(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])

  const canProceed = [
    destination.trim().length > 0,
    departure && returnDate,
    styles.length > 0,
    budget.trim().length > 0,
  ][step]

  function handleSubmit() {
    setSubmit(true)
    setTimeout(() => navigate('/itinerary'), 1800)
  }

  const stepComponents = [
    /* Step 0 — Destination */
    <div key="dest">
      <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 32, color: BONE, lineHeight: 1.15, marginBottom: 8 }}>
        Where are you<br/><em>dreaming of?</em>
      </h2>
      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, lineHeight: 1.7, marginBottom: 32 }}>
        A city, a country, or somewhere you can barely pronounce.
      </p>
      <SectionLabel>Destination</SectionLabel>
      <div style={{ position: 'relative' }}>
        <Globe size={14} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: MUTE, pointerEvents: 'none' }}/>
        <input
          value={destination}
          onChange={e => setDest(e.target.value)}
          placeholder="Bali, Kyoto, Patagonia…"
          style={{
            width: '100%', padding: '14px 16px 14px 38px',
            background: 'rgba(232,212,168,0.03)', border: `1px solid ${HAIRLINE}`,
            borderRadius: 10, color: BONE, outline: 'none',
            fontFamily: '"Inter Tight",sans-serif', fontSize: 14, fontWeight: 300,
            boxSizing: 'border-box',
          }}
        />
      </div>
    </div>,

    /* Step 1 — Dates */
    <div key="dates">
      <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 32, color: BONE, lineHeight: 1.15, marginBottom: 8 }}>
        When do you<br/><em>want to go?</em>
      </h2>
      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, lineHeight: 1.7, marginBottom: 32 }}>
        Give yourself something to look forward to.
      </p>
      <SectionLabel>Departure</SectionLabel>
      <div style={{ marginBottom: 16 }}>
        <TextInput value={departure} onChange={setDepart} placeholder="Departure date" type="date"/>
      </div>
      <SectionLabel>Return</SectionLabel>
      <TextInput value={returnDate} onChange={setReturn} placeholder="Return date" type="date"/>
    </div>,

    /* Step 2 — Style + Pace */
    <div key="style">
      <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 32, color: BONE, lineHeight: 1.15, marginBottom: 8 }}>
        How do you<br/><em>like to travel?</em>
      </h2>
      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, lineHeight: 1.7, marginBottom: 32 }}>
        Pick everything that sounds like you.
      </p>
      <SectionLabel>Travel style (pick all that apply)</SectionLabel>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 32 }}>
        {STYLES.map(s => {
          const active = styles.includes(s)
          return (
            <button
              key={s}
              onClick={() => toggleStyle(s)}
              style={{
                padding: '9px 16px', borderRadius: 20, cursor: 'pointer',
                fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.08em',
                background: active ? 'rgba(212,182,134,0.12)' : 'rgba(232,212,168,0.03)',
                border: `1px solid ${active ? 'rgba(212,182,134,0.45)' : HAIRLINE}`,
                color: active ? GOLD : MUTE,
                transition: 'all 0.2s',
              }}
            >
              {s}
            </button>
          )
        })}
      </div>
      <SectionLabel>Pace</SectionLabel>
      <div style={{ display: 'flex', gap: 10 }}>
        {PACES.map(p => {
          const active = pace === p
          return (
            <button
              key={p}
              onClick={() => setPace(p)}
              style={{
                flex: 1, padding: '12px 0', borderRadius: 10, cursor: 'pointer',
                fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.10em',
                background: active ? 'rgba(212,182,134,0.10)' : 'rgba(232,212,168,0.03)',
                border: `1px solid ${active ? 'rgba(212,182,134,0.40)' : HAIRLINE}`,
                color: active ? GOLD : MUTE,
                transition: 'all 0.2s',
              }}
            >
              {p}
            </button>
          )
        })}
      </div>
    </div>,

    /* Step 3 — Budget */
    <div key="budget">
      <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 32, color: BONE, lineHeight: 1.15, marginBottom: 8 }}>
        What's your<br/><em>budget?</em>
      </h2>
      <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, color: MUTE, lineHeight: 1.7, marginBottom: 32 }}>
        Total trip spend, excluding flights.
      </p>
      <SectionLabel>Currency</SectionLabel>
      <div style={{ position: 'relative', marginBottom: 16 }}>
        <select
          value={currency}
          onChange={e => setCurrency(e.target.value)}
          style={{
            width: '100%', padding: '14px 16px', appearance: 'none',
            background: 'rgba(232,212,168,0.03)', border: `1px solid ${HAIRLINE}`,
            borderRadius: 10, color: BONE, outline: 'none', cursor: 'pointer',
            fontFamily: '"Inter Tight",sans-serif', fontSize: 13,
            boxSizing: 'border-box',
          }}
        >
          {CURRENCIES.map(c => <option key={c} value={c} style={{ background: '#12120F' }}>{c}</option>)}
        </select>
      </div>
      <SectionLabel>Amount</SectionLabel>
      <input
        type="number"
        value={budget}
        onChange={e => setBudget(e.target.value)}
        placeholder="2500"
        style={{
          width: '100%', padding: '14px 16px',
          background: 'rgba(232,212,168,0.03)', border: `1px solid ${HAIRLINE}`,
          borderRadius: 10, color: BONE, outline: 'none',
          fontFamily: '"Inter Tight",sans-serif', fontSize: 14, fontWeight: 300,
          boxSizing: 'border-box',
        }}
      />
    </div>,
  ]

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* header */}
      <div style={{ padding: '52px 24px 24px', position: 'relative', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 32 }}>
          <button onClick={() => step > 0 ? setStep(s => s - 1) : navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0 }}>
            <ArrowLeft size={20}/>
          </button>
          <div style={{ flex: 1, height: 2, borderRadius: 1, background: HAIRLINE, overflow: 'hidden' }}>
            <motion.div
              animate={{ width: `${((step + 1) / TOTAL_STEPS) * 100}%` }}
              transition={{ duration: 0.5, ease }}
              style={{ height: '100%', background: GOLD, borderRadius: 1 }}
            />
          </div>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', color: MUTE }}>
            {step + 1}/{TOTAL_STEPS}
          </span>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.35, ease }}
          >
            {stepComponents[step]}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* footer CTA */}
      <div style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, padding: '20px 24px 36px', background: `linear-gradient(to top,${BG} 70%,transparent)`, zIndex: 10 }}>
        {step < TOTAL_STEPS - 1 ? (
          <button
            onClick={() => canProceed && setStep(s => s + 1)}
            style={{
              width: '100%', padding: '16px 0',
              background: canProceed ? GOLD : 'rgba(212,182,134,0.12)',
              border: 'none', borderRadius: 12, cursor: canProceed ? 'pointer' : 'default',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
              textTransform: 'uppercase', fontWeight: 500,
              color: canProceed ? BG : 'rgba(212,182,134,0.35)',
              transition: 'all 0.25s',
            }}
          >
            Continue <ChevronRight size={12}/>
          </button>
        ) : (
          <button
            onClick={() => canProceed && !submitting && handleSubmit()}
            style={{
              width: '100%', padding: '16px 0',
              background: canProceed ? GOLD : 'rgba(212,182,134,0.12)',
              border: 'none', borderRadius: 12, cursor: canProceed ? 'pointer' : 'default',
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
              textTransform: 'uppercase', fontWeight: 500,
              color: canProceed ? BG : 'rgba(212,182,134,0.35)',
              transition: 'all 0.25s',
            }}
          >
            {submitting ? 'Planning your trip…' : 'Start Planning →'}
          </button>
        )}
      </div>
    </div>
  )
}
