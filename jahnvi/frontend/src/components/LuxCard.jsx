import { motion } from 'framer-motion'

const BORDER = 'linear-gradient(145deg,rgba(232,212,168,0.15) 0%,rgba(8,8,7,0) 55%,rgba(232,212,168,0.06) 100%)'

export default function LuxCard({ children, style, hover = false, onClick }) {
  const inner = (
    <div style={{ background: 'rgba(14,14,13,0.98)', borderRadius: 19, height: '100%' }}>
      {children}
    </div>
  )
  const wrap = {
    padding: 1,
    borderRadius: 20,
    background: BORDER,
    cursor: onClick ? 'pointer' : 'default',
    ...style,
  }
  if (!hover) return <div style={wrap} onClick={onClick}>{inner}</div>
  return (
    <motion.div
      whileHover={{ y: -4, transition: { duration: 0.25, ease: 'easeOut' } }}
      style={wrap}
      onClick={onClick}
    >
      {inner}
    </motion.div>
  )
}
