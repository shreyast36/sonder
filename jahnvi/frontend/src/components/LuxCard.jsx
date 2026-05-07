import { motion } from 'framer-motion'

const BORDER   = 'linear-gradient(145deg,rgba(232,212,168,0.28) 0%,rgba(232,212,168,0.05) 55%,rgba(232,212,168,0.14) 100%)'
const SHADOW   = '0 20px 60px rgba(0,0,0,0.48), 0 4px 16px rgba(0,0,0,0.28), inset 0 1px 0 rgba(232,212,168,0.09)'

export default function LuxCard({ children, style, onClick }) {
  return (
    <motion.div
      whileHover={onClick ? { y: -6, transition: { duration: 0.22, ease: 'easeOut' } } : undefined}
      onClick={onClick}
      style={{
        padding: 1,
        borderRadius: 20,
        background: BORDER,
        boxShadow: SHADOW,
        cursor: onClick ? 'pointer' : 'default',
        ...style,
      }}
    >
      <div style={{
        background: 'linear-gradient(160deg, rgba(22,18,12,0.97) 0%, rgba(14,11,8,0.99) 100%)',
        borderRadius: 19,
        height: '100%',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.025)',
      }}>
        {children}
      </div>
    </motion.div>
  )
}
