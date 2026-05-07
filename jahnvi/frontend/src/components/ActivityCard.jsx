import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, MoreVertical, RefreshCw, Trash2, Clock } from 'lucide-react'
import { GOLD, BONE, MUTE, HAIRLINE, ease } from '../lib/tokens'
import LuxCard from './LuxCard'

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

  return (
    <>
      <LuxCard style={{ width: '100%', marginBottom: 10 }}>
        <div style={{ padding: '16px 16px 12px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <span style={{
              fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE,
              width: 52, flexShrink: 0, paddingTop: 2, lineHeight: 1.4,
            }}>
              {time}
            </span>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <p style={{
                  fontFamily: '"Inter Tight",sans-serif', fontWeight: 500,
                  fontSize: 13, color: BONE, flex: 1, lineHeight: 1.3,
                }}>
                  {name}
                </p>
                {onFeedback && (
                  <button
                    onClick={() => setSheet(true)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 2, lineHeight: 0, flexShrink: 0 }}
                  >
                    <MoreVertical size={14}/>
                  </button>
                )}
              </div>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE, marginTop: 2 }}>
                {category}
              </p>
              {addedBy && (
                <span style={{
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.10em',
                  color: GOLD, textTransform: 'uppercase', marginTop: 5, display: 'block', opacity: 0.7,
                }}>
                  Added by {addedBy}
                </span>
              )}
            </div>
          </div>

          {whyThis && (
            <button
              onClick={() => setExpanded(v => !v)}
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                marginTop: 10, paddingLeft: 62,
                background: 'none', border: 'none', cursor: 'pointer',
              }}
            >
              <span style={{
                fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                letterSpacing: '0.16em', color: GOLD, textTransform: 'uppercase',
              }}>
                Why this?
              </span>
              <motion.div animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.22 }}>
                <ChevronDown size={11} style={{ color: GOLD }}/>
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
                transition={{ duration: 0.28, ease }}
                style={{ overflow: 'hidden' }}
              >
                <p style={{
                  fontFamily: '"Inter Tight",sans-serif', fontWeight: 300,
                  fontSize: 12, lineHeight: 1.75, color: MUTE,
                  marginTop: 8, paddingLeft: 62, paddingRight: 4,
                }}>
                  {whyThis}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </LuxCard>

      <AnimatePresence>
        {sheet && (
          <>
            <motion.div
              key="sheet-bg"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setSheet(false)}
              style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 200 }}
            />
            <motion.div
              key="sheet"
              initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 30, stiffness: 260 }}
              style={{
                position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)',
                width: '100%', maxWidth: 430, zIndex: 201,
                background: 'rgba(18,17,16,0.99)',
                borderRadius: '20px 20px 0 0',
                border: `1px solid rgba(232,212,168,0.10)`,
                borderBottom: 'none',
                padding: '12px 0 40px',
              }}
            >
              <div style={{ width: 36, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.14)', margin: '0 auto 20px' }}/>
              <p style={{
                fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
                fontSize: 18, color: BONE, textAlign: 'center',
                marginBottom: 20, paddingLeft: 24, paddingRight: 24,
              }}>
                {name}
              </p>
              {ACTIONS.map(({ key, Icon, label }) => (
                <button
                  key={key}
                  onClick={() => { onFeedback?.({ activity_id: activity?.id, action: key }); setSheet(false) }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    width: '100%', padding: '15px 28px',
                    background: 'none', border: 'none', cursor: 'pointer',
                    borderBottom: `1px solid rgba(232,212,168,0.07)`,
                  }}
                >
                  <Icon size={15} style={{ color: GOLD }}/>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 13, color: BONE }}>{label}</span>
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
