import { useState } from 'react'
import { BONE, HAIRLINE, MUTE } from '../lib/tokens'

const ORANGE = '#F97316'
const LIMIT  = 20

function countWords(text) {
  return text.trim() === '' ? 0 : text.trim().split(/\s+/).length
}

function enforceLimit(text, limit = LIMIT) {
  const words = text.split(/\s+/)
  // Allow typing within the last word even if over limit — trim on word completion
  if (countWords(text) > limit) {
    return words.slice(0, limit).join(' ')
  }
  return text
}

export default function WordLimitTextarea({ value, onChange, placeholder, rows = 4, limit = LIMIT }) {
  const [focused, setFocused] = useState(false)
  const words     = countWords(value)
  const remaining = limit - words
  const nearLimit = remaining <= 5
  const atLimit   = remaining <= 0

  function handleChange(e) {
    const clamped = enforceLimit(e.target.value, limit)
    onChange(clamped)
  }

  const counterColor = atLimit ? ORANGE : nearLimit ? `${ORANGE}99` : MUTE

  return (
    <div style={{ position: 'relative' }}>
      <textarea
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        rows={rows}
        style={{
          width: '100%',
          background: 'rgba(232,212,168,0.03)',
          border: `1px solid ${focused ? `${ORANGE}66` : HAIRLINE}`,
          borderRadius: 16,
          padding: '20px 24px 44px',
          color: BONE,
          outline: 'none',
          resize: 'none',
          fontFamily: '"Cormorant Garamond",serif',
          fontStyle: 'italic',
          fontWeight: 400,
          fontSize: 22,
          lineHeight: 1.65,
          boxSizing: 'border-box',
          transition: 'border-color 0.2s',
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      />
      <div style={{
        position: 'absolute',
        bottom: 14,
        right: 20,
        fontFamily: '"Inter Tight",sans-serif',
        fontSize: 10,
        letterSpacing: '0.12em',
        color: counterColor,
        transition: 'color 0.2s',
        userSelect: 'none',
        pointerEvents: 'none',
      }}>
        {words} / {limit}
      </div>
    </div>
  )
}
