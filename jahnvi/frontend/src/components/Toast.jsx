import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const GOLD = '#D4B686'
const BONE = '#F4EDE0'
const MUTE = 'rgba(244,237,224,0.44)'

const ToastCtx = createContext(null)
let uid = 0

function ToastItem({ title, sub, duration, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, duration)
    return () => clearTimeout(t)
  }, [])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 6, scale: 0.97, transition: { duration: 0.22 } }}
      transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
      onClick={onDismiss}
      style={{
        pointerEvents: 'auto',
        position: 'relative',
        overflow: 'hidden',
        minWidth: 260,
        maxWidth: 360,
        background: 'rgba(10,8,6,0.95)',
        backdropFilter: 'blur(28px)',
        WebkitBackdropFilter: 'blur(28px)',
        border: '1px solid rgba(232,212,168,0.13)',
        borderLeft: `2px solid ${GOLD}`,
        borderRadius: 14,
        padding: '16px 20px 20px',
        boxShadow: '0 8px 48px rgba(0,0,0,0.65), 0 0 0 0.5px rgba(232,212,168,0.05)',
        cursor: 'pointer',
      }}
    >
      <p style={{
        fontFamily: '"Cormorant Garamond",serif',
        fontStyle: 'italic',
        fontWeight: 400,
        fontSize: 18,
        color: BONE,
        lineHeight: 1.2,
        marginBottom: sub ? 5 : 0,
      }}>
        {title}
      </p>
      {sub && (
        <p style={{
          fontFamily: '"Inter Tight",sans-serif',
          fontWeight: 300,
          fontSize: 11,
          color: MUTE,
          lineHeight: 1.55,
        }}>
          {sub}
        </p>
      )}
      <motion.div
        initial={{ scaleX: 1 }}
        animate={{ scaleX: 0 }}
        transition={{ duration: duration / 1000, ease: 'linear' }}
        style={{
          position: 'absolute',
          bottom: 0, left: 0, right: 0,
          height: 1.5,
          background: `linear-gradient(to right, ${GOLD}, rgba(212,182,134,0.18))`,
          transformOrigin: 'left',
        }}
      />
    </motion.div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismiss = useCallback(id => setToasts(p => p.filter(t => t.id !== id)), [])

  const toast = useCallback(({ title, sub, duration = 3500 }) => {
    const id = ++uid
    setToasts(p => [...p, { id, title, sub, duration }])
  }, [])

  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div style={{
        position: 'fixed', bottom: 36, left: 0, right: 0,
        zIndex: 9998,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', gap: 10,
        pointerEvents: 'none',
      }}>
        <AnimatePresence>
          {toasts.map(t => (
            <ToastItem key={t.id} {...t} onDismiss={() => dismiss(t.id)}/>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  )
}

export const useToast = () => useContext(ToastCtx)
