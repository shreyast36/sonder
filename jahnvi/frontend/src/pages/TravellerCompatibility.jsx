import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { BG, BONE, MUTE, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'

const ORANGE = '#F97316'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

const QUESTIONS = [
  {
    key:  'rhythm',
    q:    'Morning person or night owl?',
    hint: '"I am usually up with the sun"',
  },
  {
    key:  'food_priority',
    q:    'Do you eat to live or live to eat?',
    hint: '"I eat buffets for breakfast, lunch, and dinner - so I guess I live to eat??"',
  },
  {
    key:  'recharge',
    q:    'You have a completely free afternoon. What do you actually do?',
    hint: '"Order a good latte, go sit on the beach, and get lost in my inner thoughts"',
  },
  {
    key:  'social_energy',
    q:    'Do you talk to strangers when you travel?',
    hint: '"If they seem interesting. Almost never. It\'s how I got my best recommendations."',
  },
  {
    key:  'mood_handling',
    q:    'What do you do when someone you\'re with is in a bad mood?',
    hint: '"Give them space. Check in quietly. Try to fix it."',
  },
  {
    key:  'budget_style',
    q:    'Would you rather travel comfortably or cheaply?',
    hint: '"Comfortably — I\'m on holiday. Cheaply — more trips per year."',
  },
  {
    key:  'novelty',
    q:    'Would you revisit somewhere you loved, or always go somewhere new?',
    hint: '"Always somewhere new. Revisit — there\'s always more to find."',
  },
  {
    key:  'documentation',
    q:    'Do you document your trips or just live them?',
    hint: '"A few photos. Aggressively. I forget everything if I don\'t write it down."',
  },
  {
    key:  'conflict_style',
    q:    'When you and someone disagree on what to do, what usually happens?',
    hint: '"We find a third option. I usually give in. We split up and compare notes."',
  },
  {
    key:  'trip_value',
    q:    'What makes a trip feel worth it to you?',
    hint: '"One moment I couldn\'t have planned. Feeling genuinely rested."',
  },
]

export default function TravellerCompatibility() {
  const navigate = useNavigate()
  const [step, setStep]       = useState(0)
  const [answers, setAnswers] = useState(
    Object.fromEntries(QUESTIONS.map(q => [q.key, ''])),
  )
  const [saving, setSaving] = useState(false)

  const current = QUESTIONS[step]
  const isLast  = step === QUESTIONS.length - 1

  function advance() {
    if (!isLast) setStep(s => s + 1)
    else save()
  }

  function skip() {
    setAnswers(prev => ({ ...prev, [current.key]: '' }))
    advance()
  }

  function save() {
    setSaving(true)
    const existing = JSON.parse(sessionStorage.getItem('sonder_trip_profile') || '{}')
    sessionStorage.setItem('sonder_trip_profile', JSON.stringify({
      ...existing,
      compatibility_answers: answers,
    }))
    setTimeout(() => navigate('/discover'), 900)
  }

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent="#F97316"/>

      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', padding: '0 48px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => step > 0 ? setStep(s => s - 1) : navigate('/discover')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, display: 'flex', alignItems: 'center', gap: 8, transition: 'color 0.2s' }}
          onMouseEnter={e => { e.currentTarget.style.color = BONE }}
          onMouseLeave={e => { e.currentTarget.style.color = MUTE }}>
          <ArrowLeft size={18}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>{step > 0 ? 'Back' : 'Discover'}</span>
        </motion.button>
        <SonderNav3D markSize={32}/>
        <div style={{ width: 80 }}/>
      </nav>

      {/* Progress bar */}
      <div style={{ height: 2, background: HAIRLINE, position: 'relative', zIndex: 1 }}>
        <motion.div
          animate={{ width: `${((step + 1) / QUESTIONS.length) * 100}%` }}
          transition={{ duration: 0.4, ease }}
          style={{ height: '100%', background: `linear-gradient(to right, ${ORANGE}, #EA580C)`, borderRadius: 1 }}
        />
      </div>

      {/* Question */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 48px', maxWidth: 720, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -28 }}
            transition={{ duration: 0.42, ease }}
            style={{ width: '100%', textAlign: 'center' }}
          >
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, marginBottom: 28 }}>
              {step + 1} of {QUESTIONS.length}
            </p>

            <h2 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 46, lineHeight: 1.2, color: BONE, marginBottom: 52 }}>
              {current.q}
            </h2>

            <textarea
              key={current.key}
              value={answers[current.key]}
              onChange={e => setAnswers(prev => ({ ...prev, [current.key]: e.target.value }))}
              placeholder={current.hint}
              rows={4}
              style={{
                width: '100%', background: 'rgba(232,212,168,0.03)',
                border: `1px solid ${HAIRLINE}`, borderRadius: 16,
                padding: '20px 24px', color: BONE, outline: 'none', resize: 'none',
                fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 22,
                lineHeight: 1.65, boxSizing: 'border-box', transition: 'border-color 0.2s',
              }}
              onFocus={e => { e.target.style.borderColor = `${ORANGE}66` }}
              onBlur={e => { e.target.style.borderColor = HAIRLINE }}
            />
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Actions */}
      <div style={{ padding: '32px 48px 52px', maxWidth: 720, margin: '0 auto', width: '100%', boxSizing: 'border-box', position: 'relative', zIndex: 1 }}>

        {/* Progress dots */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 5, marginBottom: 28 }}>
          {QUESTIONS.map((_, i) => (
            <div key={i} style={{ width: i === step ? 18 : 5, height: 5, borderRadius: 2.5, background: i === step ? ORANGE : i < step ? `${ORANGE}44` : HAIRLINE, transition: 'all 0.3s ease' }}/>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 12 }}>
          <motion.button
            whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={skip}
            style={{ flex: 1, padding: '18px 0', background: 'transparent', border: `1px solid ${HAIRLINE}`, borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, transition: 'all 0.2s' }}
          >
            Skip
          </motion.button>
          <motion.button
            whileHover={{ y: -2, boxShadow: `0 0 48px ${ORANGE}44`, transition: spring }} whileTap={{ scale: 0.98 }}
            onClick={advance}
            style={{ flex: 3, padding: '18px 0', background: `linear-gradient(135deg, ${ORANGE} 0%, #EA580C 100%)`, border: 'none', borderRadius: 12, cursor: 'pointer', fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, color: '#fff', transition: 'all 0.25s', boxShadow: `0 0 40px ${ORANGE}28` }}
          >
            {isLast ? (saving ? 'Saving…' : 'Find my matches') : 'Continue'}
          </motion.button>
        </div>
      </div>
    </div>
  )
}
