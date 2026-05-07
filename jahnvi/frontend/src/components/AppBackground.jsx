import { motion } from 'framer-motion'
import { GRAIN } from '../lib/tokens'

export default function AppBackground() {
  return (
    <>
      {/* grain — same as homepage opacity */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none',
        opacity: 0.034, backgroundImage: GRAIN, backgroundSize: '200px 200px',
      }}/>

      {/* blob 1 — top-left, warm amber, organic shape that drifts */}
      <motion.div
        animate={{ scale: [1, 1.18, 1], opacity: [0.60, 1, 0.60], x: [0, 36, 0], y: [0, -24, 0] }}
        transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'fixed', top: '-20%', left: '-10%',
          width: '58vw', height: '58vw',
          borderRadius: '42% 58% 52% 48% / 46% 54% 58% 42%',
          background: 'radial-gradient(ellipse at 40% 40%, rgba(224,178,96,0.13) 0%, rgba(212,182,134,0.05) 45%, transparent 70%)',
          pointerEvents: 'none', zIndex: 0,
        }}
      />

      {/* blob 2 — bottom-right, slightly cooler, slower */}
      <motion.div
        animate={{ scale: [1, 1.22, 1], opacity: [0.45, 0.80, 0.45], x: [0, -28, 0], y: [0, 20, 0] }}
        transition={{ duration: 17, repeat: Infinity, ease: 'easeInOut', delay: 6 }}
        style={{
          position: 'fixed', bottom: '-14%', right: '-14%',
          width: '50vw', height: '50vw',
          borderRadius: '58% 42% 46% 54% / 54% 46% 42% 58%',
          background: 'radial-gradient(ellipse at 60% 60%, rgba(180,138,68,0.10) 0%, rgba(212,182,134,0.04) 50%, transparent 72%)',
          pointerEvents: 'none', zIndex: 0,
        }}
      />

      {/* blob 3 — centre-top, very faint, midscreen presence */}
      <motion.div
        animate={{ opacity: [0.3, 0.55, 0.3], scale: [1, 1.08, 1] }}
        transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut', delay: 3 }}
        style={{
          position: 'fixed', top: '25%', left: '35%',
          width: '30vw', height: '30vw',
          borderRadius: '50%',
          background: 'radial-gradient(ellipse, rgba(212,182,134,0.045) 0%, transparent 65%)',
          pointerEvents: 'none', zIndex: 0,
        }}
      />
    </>
  )
}
