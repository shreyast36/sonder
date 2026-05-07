import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Globe } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, GOLD_GRAD, GRAIN, ease } from '../lib/tokens'
import { SonderNavLogo } from '../components/SonderLogoSVG'

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
          fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 26,
          transition: 'border-color 0.25s', boxSizing: 'border-box',
        }}
      />
    </div>
  )
}

const STEP_LABELS = ['Destination', 'Dates', 'Travel style', 'Budget']

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
        <div style={{ marginTop: 48 }}>
          <ElegantInput value={destination} onChange={setDest} placeholder="Bali, Kyoto, Patagonia…" icon={Globe}/>
        </div>
      ),
    },
    {
      number: '02',
      heading: 'When do you want to go?',
      sub: 'Give yourself something to look forward to.',
      content: (
        <div style={{ marginTop: 48 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Departure</p>
          <ElegantInput value={departure} onChange={setDepart} placeholder="" type="date"/>
          <div style={{ marginTop: 40 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Return</p>
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
        <div style={{ marginTop: 48 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 40 }}>
            {STYLES.map(s => {
              const active = styles.includes(s)
              return (
                <button key={s} onClick={() => toggleStyle(s)} style={{
                  padding: '11px 20px', borderRadius: 24, cursor: 'pointer',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 12, letterSpacing: '0.06em',
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
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 16 }}>Pace</p>
          <div style={{ display: 'flex', gap: 12 }}>
            {PACES.map(p => {
              const active = pace === p.key
              return (
                <button key={p.key} onClick={() => setPace(p.key)} style={{
                  flex: 1, padding: '18px 0', borderRadius: 14, cursor: 'pointer',
                  background: active ? 'rgba(212,182,134,0.08)' : 'transparent',
                  border: `1px solid ${active ? 'rgba(212,182,134,0.40)' : HAIRLINE}`,
                  transition: 'all 0.2s',
                }}>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 500, color: active ? GOLD : MUTE, marginBottom: 3 }}>{p.label}</p>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: active ? 'rgba(212,182,134,0.5)' : DIM }}>{p.sub}</p>
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
        <div style={{ marginTop: 48 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 18 }}>Currency</p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 40 }}>
            {CURRENCIES.map(c => (
              <button key={c} onClick={() => setCurrency(c)} style={{
                padding: '9px 16px', borderRadius: 20, cursor: 'pointer',
                fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.10em',
                background: currency === c ? 'rgba(212,182,134,0.10)' : 'transparent',
                border: `1px solid ${currency === c ? 'rgba(212,182,134,0.45)' : HAIRLINE}`,
                color: currency === c ? GOLD : MUTE, transition: 'all 0.2s',
              }}>{c}</button>
            ))}
          </div>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.26em', textTransform: 'uppercase', color: MUTE, marginBottom: 14 }}>Amount</p>
          <ElegantInput value={budget} onChange={setBudget} placeholder="2500" type="number"/>
        </div>
      ),
    },
  ]

  const current = STEPS[step]

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none', opacity: 0.025, backgroundImage: GRAIN, backgroundSize: '200px 200px' }}/>

      {/* top nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(8,8,7,0.92)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <button onClick={() => step > 0 ? setStep(s => s - 1) : navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>{step > 0 ? 'Back' : 'Dashboard'}</span>
        </button>
        <SonderNavLogo markHeight={32}/>
        <div style={{ width: 80 }}/>
      </nav>

      {/* 2-column layout */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', maxWidth: 1100, margin: '0 auto', width: '100%' }}>

        {/* left — progress + decorative */}
        <div style={{ borderRight: `1px solid ${HAIRLINE}`, padding: '64px 56px', position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'radial-gradient(ellipse 70% 50% at 20% 30%, rgba(212,182,134,0.07) 0%, transparent 65%)', pointerEvents: 'none' }}/>

          {/* step progress */}
          <div style={{ marginBottom: 56 }}>
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 20 }}>
              Step {step + 1} of {TOTAL_STEPS}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
              {STEP_LABELS.map((label, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 0', borderBottom: i < STEP_LABELS.length - 1 ? `1px solid ${HAIRLINE}` : 'none' }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                    border: `1px solid ${i === step ? 'rgba(212,182,134,0.5)' : i < step ? 'rgba(212,182,134,0.25)' : HAIRLINE}`,
                    background: i === step ? 'rgba(212,182,134,0.10)' : i < step ? 'rgba(212,182,134,0.05)' : 'transparent',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, fontWeight: 500, color: i <= step ? GOLD : MUTE }}>
                      {String(i + 1).padStart(2, '0')}
                    </span>
                  </div>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, color: i === step ? BONE : i < step ? MUTE : DIM, fontWeight: i === step ? 500 : 300, transition: 'color 0.3s' }}>
                    {label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* decorative large number */}
          <div style={{ marginTop: 'auto', position: 'relative' }}>
            <AnimatePresence mode="wait">
              <motion.span key={step}
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5, ease }}
                style={{
                  display: 'block',
                  fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
                  fontSize: 200, lineHeight: 0.85, letterSpacing: '-0.05em',
                  background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
                  opacity: 0.10, userSelect: 'none',
                }}
              >
                {current.number}
              </motion.span>
            </AnimatePresence>
          </div>
        </div>

        {/* right — form content */}
        <div style={{ padding: '64px 56px', display: 'flex', flexDirection: 'column' }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 32 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -32 }}
              transition={{ duration: 0.38, ease }}
              style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
            >
              <h2 style={{
                fontFamily: '"Cormorant Garamond",serif', fontWeight: 400,
                fontSize: 40, lineHeight: 1.15, color: BONE, marginBottom: 12,
              }}>
                {current.heading}
              </h2>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13, lineHeight: 1.75, color: MUTE }}>
                {current.sub}
              </p>

              {current.content}
            </motion.div>
          </AnimatePresence>

          {/* CTA */}
          <div style={{ marginTop: 56 }}>
            <button
              onClick={() => {
                if (!canProceed) return
                if (step < TOTAL_STEPS - 1) setStep(s => s + 1)
                else if (!submitting) handleSubmit()
              }}
              style={{
                width: '100%', padding: '18px 0',
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
      </div>
    </div>
  )
}
