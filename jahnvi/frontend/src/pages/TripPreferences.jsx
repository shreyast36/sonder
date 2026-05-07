import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Globe } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'

const STYLES    = ['Adventure', 'Culture', 'Relaxed', 'Foodie', 'Nature', 'Wellness', 'Nightlife', 'History']
const PACES     = [{ key: 'slow', label: 'Slow', sub: 'Linger' }, { key: 'moderate', label: 'Moderate', sub: 'Balanced' }, { key: 'fast', label: 'Fast', sub: 'Pack it in' }]
const CURRENCIES = ['USD', 'EUR', 'GBP', 'INR', 'AUD', 'CAD', 'JPY', 'SGD']
const TOTAL_STEPS = 4

function ElegantInput({ value, onChange, placeholder, type = 'text', icon: Icon }) {
  const [focused, setFocused] = useState(false)
  return (
    <div style={{ position: 'relative' }}>
      {Icon && <Icon size={14} style={{ position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)', color: focused ? GOLD : MUTE, transition: 'color 0.2s', pointerEvents: 'none' }}/>}
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        style={{
          width: '100%', padding: `14px 0 14px ${Icon ? '26px' : '0'}`,
          background: 'none', border: 'none', borderBottom: `1px solid ${focused ? 'rgba(212,182,134,0.55)' : HAIRLINE}`,
          color: BONE, outline: 'none',
          fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 22,
          transition: 'border-color 0.25s', boxSizing: 'border-box',
        }}
      />
    </div>
  )
}

export default function TripPreferences() {
  const navigate = useNavigate()
  const [step, setStep]         = useState(0)
  const [destination, setDest]  = useState('')
  const [departure, setDepart]  = useState('')
  const [returnDate, setReturn] = useState('')
  const [styles, setStyles]     = useState([])
  const [pace, setPace]         = useState('moderate')
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

  const STEPS = [
    {
      number: '01',
      heading: 'Where are you dreaming of?',
      sub: "A city, a coast, a country you've always meant to visit.",
      content: (
        <div style={{ marginTop: 40 }}>
          <ElegantInput value={destination} onChange={setDest} placeholder="Bali, Kyoto, Patagonia…" icon={Globe}/>
        </div>
      ),
    },
    {
      number: '02',
      heading: 'When do you want to go?',
      sub: 'Give yourself something to look forward to.',
      content: (
        <div style={{ marginTop: 40 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>Departure</p>
          <ElegantInput value={departure} onChange={setDepart} placeholder="" type="date"/>
          <div style={{ marginTop: 32 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>Return</p>
            <ElegantInput value={returnDate} onChange={setReturn} placeholder="" type="date"/>
          </div>
        </div>
      ),
    },
    {
      number: '03',
      heading: 'How do you like to travel?',
      sub: 'Pick everything that sounds like you.',
      content: (
        <div style={{ marginTop: 40 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 36 }}>
            {STYLES.map(s => {
              const active = styles.includes(s)
              return (
                <button key={s} onClick={() => toggleStyle(s)} style={{
                  padding: '10px 18px', borderRadius: 24, cursor: 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.06em',
                  background: active ? 'rgba(212,182,134,0.10)' : 'transparent',
                  border: `1px solid ${active ? 'rgba(212,182,134,0.50)' : HAIRLINE}`,
                  color: active ? GOLD : MUTE,
                  transition: 'all 0.2s',
                }}>
                  {s}
                </button>
              )
            })}
          </div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Pace</p>
          <div style={{ display: 'flex', gap: 10 }}>
            {PACES.map(p => {
              const active = pace === p.key
              return (
                <button key={p.key} onClick={() => setPace(p.key)} style={{
                  flex: 1, padding: '16px 0', borderRadius: 12, cursor: 'pointer',
                  background: active ? 'rgba(212,182,134,0.08)' : 'transparent',
                  border: `1px solid ${active ? 'rgba(212,182,134,0.40)' : HAIRLINE}`,
                  transition: 'all 0.2s',
                }}>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12, fontWeight: 500, color: active ? GOLD : MUTE, marginBottom: 2 }}>{p.label}</p>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: active ? 'rgba(212,182,134,0.5)' : DIM }}>{p.sub}</p>
                </button>
              )
            })}
          </div>
        </div>
      ),
    },
    {
      number: '04',
      heading: "What's your budget?",
      sub: 'Total trip spend, not including flights.',
      content: (
        <div style={{ marginTop: 40 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 16 }}>Currency</p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 36 }}>
            {CURRENCIES.map(c => (
              <button key={c} onClick={() => setCurrency(c)} style={{
                padding: '8px 14px', borderRadius: 20, cursor: 'pointer',
                fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.10em',
                background: currency === c ? 'rgba(212,182,134,0.10)' : 'transparent',
                border: `1px solid ${currency === c ? 'rgba(212,182,134,0.45)' : HAIRLINE}`,
                color: currency === c ? GOLD : MUTE, transition: 'all 0.2s',
              }}>{c}</button>
            ))}
          </div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 12 }}>Amount</p>
          <ElegantInput value={budget} onChange={setBudget} placeholder="2500" type="number"/>
        </div>
      ),
    },
  ]

  const current = STEPS[step]

  return (
    <div style={{ maxWidth: 430, margin: '0 auto', minHeight: '100vh', background: BG, color: BONE, overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* header */}
      <div style={{ padding: '52px 28px 0', display: 'flex', alignItems: 'center', gap: 20, position: 'relative', zIndex: 10 }}>
        <button onClick={() => step > 0 ? setStep(s => s - 1) : navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0 }}>
          <ArrowLeft size={20}/>
        </button>
        {/* step dots */}
        <div style={{ display: 'flex', gap: 6 }}>
          {STEPS.map((_, i) => (
            <div key={i} style={{ width: i === step ? 20 : 5, height: 5, borderRadius: 3, background: i <= step ? GOLD : HAIRLINE, transition: 'all 0.4s ease' }}/>
          ))}
        </div>
      </div>

      {/* step content */}
      <div style={{ padding: '40px 28px 0', position: 'relative', zIndex: 10 }}>
        {/* ambient glow */}
        <div style={{ position: 'absolute', top: 20, left: -40, width: 280, height: 280, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(212,182,134,0.07) 0%, transparent 65%)', pointerEvents: 'none' }}/>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 32 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -32 }}
            transition={{ duration: 0.38, ease }}
          >
            {/* step number */}
            <span style={{
              fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
              fontSize: 72, lineHeight: 1, letterSpacing: '-0.04em',
              background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
              opacity: 0.25, display: 'block', marginBottom: 12,
            }}>
              {current.number}
            </span>

            <h2 style={{
              fontFamily: '"Cormorant Garamond",serif', fontWeight: 400,
              fontSize: 32, lineHeight: 1.2, color: BONE, marginBottom: 10,
            }}>
              {current.heading}
            </h2>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, lineHeight: 1.75, color: MUTE }}>
              {current.sub}
            </p>

            {current.content}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* footer CTA */}
      <div style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, padding: '20px 28px 40px', background: `linear-gradient(to top,${BG} 65%,transparent)`, zIndex: 50 }}>
        <button
          onClick={() => {
            if (!canProceed) return
            if (step < TOTAL_STEPS - 1) setStep(s => s + 1)
            else if (!submitting) handleSubmit()
          }}
          style={{
            width: '100%', padding: '17px 0',
            background: canProceed ? GOLD : 'rgba(212,182,134,0.08)',
            border: `1px solid ${canProceed ? 'transparent' : HAIRLINE}`,
            borderRadius: 12, cursor: canProceed ? 'pointer' : 'default',
            fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em',
            textTransform: 'uppercase', fontWeight: 500,
            color: canProceed ? BG : 'rgba(212,182,134,0.30)',
            transition: 'all 0.25s',
            boxShadow: canProceed ? '0 0 40px rgba(212,182,134,0.18)' : 'none',
          }}
        >
          {step < TOTAL_STEPS - 1 ? 'Continue' : submitting ? 'Planning your trip…' : 'Start planning'}
        </button>
      </div>
    </div>
  )
}
