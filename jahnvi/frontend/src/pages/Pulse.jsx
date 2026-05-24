/* Sonder Pulse — full-page social surface, lifted out of the Dashboard
 * so the "your trip" view stays focused on the trip itself and the
 * social media content gets its own room to breathe.
 *
 * Renders the existing DashboardPulse component verbatim — same data
 * flow, same realtime listeners, same layout — just under a dedicated
 * URL with its own nav. */
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { BG, BONE, GOLD, GOLD_GRAD, MUTE, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import AppBackground from '../components/AppBackground'
import NavTabs from '../components/NavTabs'
import DashboardPulse from '../components/DashboardPulse'
import { useAuth } from '../hooks/useAuth'

const AMBER  = '#F59E0B'

export default function Pulse() {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <AppBackground accent="#8B5CF6"/>

      {/* Top nav — matches Dashboard's nav so the two tabs feel like
          one app, just with the active pill on Pulse. */}
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

      {/* Standalone Pulse — no greeting / no grid, just the social surface */}
      <div style={{ flex: 1, maxWidth: 1240, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>
        <DashboardPulse selfUid={user?.uid}/>
      </div>
    </div>
  )
}
