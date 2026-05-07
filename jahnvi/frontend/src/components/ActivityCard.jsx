import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, MoreVertical, RefreshCw, Trash2, Clock } from 'lucide-react'
import { GOLD, BONE, MUTE, HAIRLINE, DIM, ease } from '../lib/tokens'

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
      <div style={{
        display: 'flex', gap: 16, paddingBottom: 24,
        borderBottom: `1px solid ${HAIRLINE}`,
        marginBottom: 24,
      }}>
        {/* time column */}
        <div style={{ width: 52, flexShrink: 0, paddingTop: 4 }}>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontStyle: 'italic', fontSize: 11, color: MUTE, lineHeight: 1.3 }}>
            {time}
          </span>
        </div>

        {/* dot + line connector */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 7, flexShrink: 0 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: GOLD, flexShrink: 0 }}/>
        </div>

        {/* content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <h3 style={{
                fontFamily: '"Cormorant Garamond",serif', fontWeight: 400,
                fontSize: 18, lineHeight: 1.25, color: BONE, margin: '0 0 4px',
              }}>
                {name}
              </h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                  letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE,
                }}>
                  {category}
                </span>
                {addedBy && (
                  <>
                    <span style={{ color: HAIRLINE }}>·</span>
                    <span style={{
                      fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
                      letterSpacing: '0.14em', textTransform: 'uppercase', color: GOLD, opacity: 0.7,
                    }}>
                      {addedBy}
                    </span>
                  </>
                )}
              </div>
            </div>
            {onFeedback && (
              <button onClick={() => setSheet(true)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 2, lineHeight: 0, flexShrink: 0, marginTop: 2 }}>
                <MoreVertical size={13}/>
              </button>
            )}
          </div>

          {whyThis && (
            <button
              onClick={() => setExpanded(v => !v)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 10, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            >
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.16em', color: 'rgba(212,182,134,0.55)', textTransform: 'uppercase' }}>
                Why this?
              </span>
              <motion.div animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.22 }}>
                <ChevronDown size={10} style={{ color: 'rgba(212,182,134,0.55)' }}/>
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
                  marginTop: 8, fontStyle: 'italic',
                  padding: '10px 14px',
                  borderLeft: `1px solid rgba(212,182,134,0.20)`,
                  background: 'rgba(212,182,134,0.03)',
                  borderRadius: '0 8px 8px 0',
                }}>
                  {whyThis}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <AnimatePresence>
        {sheet && (
          <>
            <motion.div key="sb" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSheet(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 200 }}/>
            <motion.div key="ss" initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', damping: 30, stiffness: 260 }}
              style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '100%', maxWidth: 430, zIndex: 201, background: 'rgba(18,17,16,0.99)', borderRadius: '20px 20px 0 0', border: `1px solid rgba(232,212,168,0.10)`, borderBottom: 'none', padding: '12px 0 40px' }}>
              <div style={{ width: 36, height: 3, borderRadius: 2, background: 'rgba(232,212,168,0.14)', margin: '0 auto 20px' }}/>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 20, color: BONE, textAlign: 'center', marginBottom: 20, paddingLeft: 24, paddingRight: 24 }}>{name}</p>
              {ACTIONS.map(({ key, Icon, label }) => (
                <button key={key} onClick={() => { onFeedback?.({ activity_id: activity?.id, action: key }); setSheet(false) }}
                  style={{ display: 'flex', alignItems: 'center', gap: 14, width: '100%', padding: '16px 28px', background: 'none', border: 'none', cursor: 'pointer', borderBottom: `1px solid rgba(232,212,168,0.07)` }}>
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
