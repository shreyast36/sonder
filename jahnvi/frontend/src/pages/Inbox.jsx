/* Inbox — every chat session in one page. Lifted out of the Dashboard
 * right column into its own top-level tab so chat messages have room
 * to breathe and don't share real estate with matches + trip vault. */
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { BG, BONE, HAIRLINE } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import NavTabs from '../components/NavTabs'
import InboxStrip from '../components/InboxStrip'
import { useAuth } from '../hooks/useAuth'

const AMBER = '#F59E0B'
const ROSE  = '#F43F5E'

export default function Inbox() {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent={ROSE}/>

      <nav style={{
        position: 'sticky', top: 0, zIndex: 50,
        borderBottom: `1px solid ${HAIRLINE}`,
        background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        padding: '0 48px', height: 68,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <SonderNav3D markSize={32}/>
        <NavTabs/>
        <motion.button
          whileHover={{ y: -2, boxShadow: `0 8px 24px rgba(245,158,11,0.30)` }}
          whileTap={{ scale: 0.97 }}
          onClick={() => navigate('/preferences')}
          style={{
            padding: '9px 18px', borderRadius: 999,
            background: `linear-gradient(135deg, ${AMBER} 0%, #D97706 100%)`,
            border: 'none', cursor: 'pointer', color: '#0a0807',
            fontFamily: '"Inter Tight",sans-serif', fontSize: 10, fontWeight: 600,
            letterSpacing: '0.20em', textTransform: 'uppercase',
            display: 'inline-flex', alignItems: 'center', gap: 7,
            boxShadow: `0 6px 18px rgba(245,158,11,0.30)`,
          }}
        >
          <Plus size={12}/> Plan a trip
        </motion.button>
      </nav>

      {/* Centered column to match Pulse's reading width */}
      <div style={{
        flex: 1, padding: '40px 24px 80px',
        maxWidth: 640, margin: '0 auto', width: '100%',
        position: 'relative', zIndex: 1,
        display: 'flex', flexDirection: 'column', gap: 24,
      }}>
        <div>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '5px 12px', borderRadius: 999,
            background: `linear-gradient(135deg, ${ROSE}14 0%, rgba(244,237,224,0.04) 100%)`,
            border: `1px solid ${ROSE}33`,
          }}>
            <motion.span
              animate={{ scale: [1, 1.4, 1], opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
              style={{ width: 6, height: 6, borderRadius: '50%', background: ROSE, boxShadow: `0 0 8px ${ROSE}` }}
            />
            <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: BONE, margin: 0, fontWeight: 500 }}>
              Inbox · live
            </p>
          </div>
          <h2 style={{
            fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
            fontSize: 34, color: BONE, lineHeight: 1.1, margin: '12px 0 0',
            letterSpacing: '-0.015em',
          }}>
            Every conversation, one place.
          </h2>
        </div>

        {/* Higher limit on the dedicated page — dashboard strip caps
            at 8, this surface shows everything. */}
        <InboxStrip selfUid={user?.uid} limit={50}/>
      </div>
    </div>
  )
}
