import { useEffect } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'

const GOLD = '#D4B686'

export default function LuxCursor() {
  const mx = useMotionValue(-100)
  const my = useMotionValue(-100)

  const rx = useSpring(mx, { stiffness: 160, damping: 18, mass: 0.6 })
  const ry = useSpring(my, { stiffness: 160, damping: 18, mass: 0.6 })

  useEffect(() => {
    const move = e => { mx.set(e.clientX); my.set(e.clientY) }
    window.addEventListener('mousemove', move)
    return () => window.removeEventListener('mousemove', move)
  }, [mx, my])

  return (
    <>
      {/* ring — spring lag */}
      <motion.div
        style={{
          position: 'fixed', top: 0, left: 0,
          x: rx, y: ry,
          translateX: '-50%', translateY: '-50%',
          width: 36, height: 36, borderRadius: '50%',
          border: '0.5px solid rgba(212,182,134,0.30)',
          pointerEvents: 'none', zIndex: 9999,
        }}
      />
      {/* dot — direct follow */}
      <motion.div
        style={{
          position: 'fixed', top: 0, left: 0,
          x: mx, y: my,
          translateX: '-50%', translateY: '-50%',
          width: 4, height: 4, borderRadius: '50%',
          background: GOLD,
          pointerEvents: 'none', zIndex: 9999,
        }}
      />
    </>
  )
}
