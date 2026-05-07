import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, MoreVertical, RefreshCw, Trash2, Clock } from 'lucide-react'
import { GOLD, BONE, MUTE, HAIRLINE, DIM, ease } from '../lib/tokens'

const CAT_COLORS = {
  'Accommodation': '#9B7FD4',
  'Nature':        '#4CAF7D',
  'Culture':       '#D4A840',
  'Fine Dining':   '#E07060',
  'Dining':        '#E07060',
  'Wellness':      '#4DBFCC',
}

function getCatColor(cat) { return CAT_COLORS[cat] ?? GOLD }

const ACTIONS = [
  { key: 'swap',        Icon: RefreshCw, label: 'Swap this'   },
  { key: 'remove',      Icon: Trash2,    label: 'Remove'      },
  { key: 'adjust_time', Icon: Clock,     label: 'Adjust time' },
]

export default function ActivityCard({ activity, time, whyThis, addedBy = null, onFeedback }) {
  const [expanded, setExpanded] = useState(false)
  const [sheet, setSheet]       = useState(false)

  const name     = activity?.name     ?? 'Activity'
  const category = activity?.category ?? ''
  const catColor = getCatColor(category)

  return (
    <>
      <motion.div
        whileHover={{ x: 4, transition: { duration: 0.18 } }}
        style={{ display: 'flex', gap: 16, paddingBottom: 28, borderBottom: `1px solid ${HAIRLINE}`, marginBottom: 28 }}
      >
        {/* time */}
        <div style={{ width: 56, flexShrink: 0, paddingTop: 5 }}>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontStyle: 'italic', fontSize: 11, color: MUTE, lineHeight: 1.3 }}>
            {time}
          </span>
        </div>

        {/* dot + line */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 8, flexShrink: 0 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: catColor, boxShadow: `0 0 10px ${catColor}88`, flexShrink: 0 }}/>
        </div>

        {/* content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <h3 style={{
                fontFamily: '"Cormorant Garamond",serif', fontWeight: 400,
                fontSize: 20, lineHeight: 1.2, color: BONE, margin: '0 0 6px',
                filter: 'drop-shadow(0 0 20px rgba(244,237,224,0.08))',
              }}>
                {name}
              </h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 5,
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                  letterSpacing: '0.16em', textTransform: 'uppercase',
                  color: catColor, padding: '3px 8px', borderRadius: 20,
                  background: `${catColor}14`, border: `1px solid ${catColor}28`,
                }}>
                  <span style={{ width: 4, height: 4, borderRadius: '50%', background: catColor, display: 'inline-block' }}/>
                  {category}
                </span>
                {addedBy && (
                  <span style={{
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                    letterSpacing: '0.14em', textTransform: 'uppercase', color: MUTE, opacity: 0.7,
                  }}>
                    · {addedBy}
                  </span>
                )}
              </div>
            </div>
            {onFeedback && (
              <button
                onClick={() => setSheet(true)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: DIM, padding: 4, lineHeight: 0, flexShrink: 0, marginTop: 2, borderRadius: 6, transition: 'color 0.18s' }}
                onMouseEnter={e => { e.currentTarget.style.color = MUTE }}
                onMouseLeave={e => { e.currentTarget.style.color = DIM }}
              >
                <MoreVertical size={13}/>
              </button>
            )}
          </div>

          {whyThis && (
            <button
              onClick={() => setExpanded(v => !v)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 12, background: 'none', border: 'none', cursor: 'pointer', padding: 0, transition: 'opacity 0.18s' }}
              onMouseEnter={e => { e.currentTarget.style.opacity = '0.7' }}
              onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
            >
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.16em', color: `${catColor}99`, textTransform: 'uppercase' }}>
                Why this?
              </span>
              <motion.div animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.22 }}>
                <ChevronDown size={10} style={{ color: `${catColor}99` }}/>
              </motion.div>
            </button>
          )}

          <AnimatePresence initial={false}>
            {expanded && (
              <motion.div
                key="why"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.26, ease }}
                style={{ overflow: 'hidden' }}
              >
                <p style={{
                  fontFamily: '"Inter Tight",sans-serif', fontWeight: 300,
                  fontSize: 12, lineHeight: 1.8, color: MUTE,
                  marginTop: 10, fontStyle: 'italic',
                  padding: '12px 16px',
                  borderLeft: `2px solid ${catColor}55`,
                  background: `${catColor}08`,
                  borderRadius: '0 10px 10px 0',
                }}>
                  {whyThis}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      <AnimatePresence>
        {sheet && (
          <>
            <motion.div key="sb" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSheet(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', zIndex: 400, backdropFilter: 'blur(4px)' }}/>
            <motion.div key="ss" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', damping: 32, stiffness: 280 }}
              style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 560, zIndex: 401, background: 'rgba(18,14,9,0.98)', borderRadius: '24px 24px 0 0', border: `1px solid rgba(232,212,168,0.12)`, borderBottom: 'none', padding: '12px 0 48px', backdropFilter: 'blur(24px)' }}>
              <div style={{ width: 40, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.16)', margin: '0 auto 24px' }}/>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 28px 20px' }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: catColor, boxShadow: `0 0 10px ${catColor}88` }}/>
                <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: BONE }}>{name}</p>
              </div>
              {ACTIONS.map(({ key, Icon, label }) => (
                <button key={key} onClick={() => { onFeedback?.({ activity_id: activity?.id, action: key }); setSheet(false) }}
                  style={{ display: 'flex', alignItems: 'center', gap: 16, width: '100%', padding: '16px 28px', background: 'none', border: 'none', cursor: 'pointer', borderTop: `1px solid rgba(232,212,168,0.06)`, transition: 'background 0.18s' }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(232,212,168,0.04)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'none' }}
                >
                  <Icon size={15} style={{ color: GOLD }}/>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 14, color: BONE }}>{label}</span>
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
