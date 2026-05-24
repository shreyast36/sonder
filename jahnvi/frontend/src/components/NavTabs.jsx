import { motion } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'
import { BONE, MUTE, HAIRLINE } from '../lib/tokens'

const VIOLET = '#8B5CF6'

// Top-nav tab switcher shared between Dashboard + Pulse pages.
// Pulses a small accent dot on the active tab so the rhythm matches
// the rest of the section headers.
const TABS = [
  { key: 'dashboard', label: 'Your trip', path: '/dashboard' },
  { key: 'pulse',     label: 'Sonder Pulse', path: '/pulse'    },
]

export default function NavTabs() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const activeKey =
    pathname.startsWith('/pulse')     ? 'pulse'     :
    pathname.startsWith('/dashboard') ? 'dashboard' :
                                         null
  return (
    <div style={{
      display: 'flex', gap: 4, alignItems: 'center',
      padding: '4px', borderRadius: 999,
      background: 'rgba(8,8,7,0.55)',
      border: `1px solid ${HAIRLINE}`,
      backdropFilter: 'blur(20px)',
    }}>
      {TABS.map(t => {
        const active = t.key === activeKey
        return (
          <motion.button
            key={t.key}
            whileHover={!active ? { color: BONE } : {}}
            whileTap={{ scale: 0.97 }}
            onClick={() => { if (!active) navigate(t.path) }}
            style={{
              position: 'relative',
              padding: '7px 16px', borderRadius: 999,
              background: 'transparent', border: 'none', cursor: active ? 'default' : 'pointer',
              color: active ? BONE : MUTE,
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
              letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500,
              transition: 'color 0.18s',
              display: 'inline-flex', alignItems: 'center', gap: 6,
            }}
          >
            {active && (
              <motion.span
                layoutId="navtabs-pill"
                style={{
                  position: 'absolute', inset: 0, borderRadius: 999,
                  background: `linear-gradient(135deg, ${VIOLET}28 0%, rgba(212,182,134,0.10) 100%)`,
                  border: `1px solid ${VIOLET}44`,
                  zIndex: 0,
                }}
                transition={{ type: 'spring', stiffness: 320, damping: 28 }}
              />
            )}
            <span style={{ position: 'relative', zIndex: 1 }}>{t.label}</span>
          </motion.button>
        )
      })}
    </div>
  )
}
