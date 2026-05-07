import { useNavigate, useLocation } from 'react-router-dom'
import { Home, Compass, Users, User, List, Map, FileText, DollarSign } from 'lucide-react'
import { GOLD, MUTE, HAIRLINE, BG } from '../lib/tokens'

const DASHBOARD_TABS = [
  { label: 'Home',    Icon: Home,        path: '/dashboard' },
  { label: 'Trips',   Icon: Compass,     path: '/preferences' },
  { label: 'Matches', Icon: Users,       path: '/match/1' },
  { label: 'Profile', Icon: User,        path: '/profile' },
]

const ITINERARY_TABS = [
  { label: 'Itinerary', Icon: List,        tab: 'itinerary' },
  { label: 'Map',       Icon: Map,         tab: 'map'       },
  { label: 'Notes',     Icon: FileText,    tab: 'notes'     },
  { label: 'Budget',    Icon: DollarSign,  tab: 'budget'    },
]

export default function BottomNav({ variant = 'dashboard', activeTab, onTabChange }) {
  const navigate   = useNavigate()
  const location   = useLocation()
  const tabs = variant === 'dashboard' ? DASHBOARD_TABS : ITINERARY_TABS

  return (
    <div style={{
      position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)',
      width: '100%', maxWidth: 430, zIndex: 100,
      background: 'rgba(8,8,7,0.94)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      borderTop: `1px solid ${HAIRLINE}`,
      display: 'flex',
      paddingBottom: 'env(safe-area-inset-bottom,0px)',
    }}>
      {tabs.map(({ label, Icon, path, tab }) => {
        const isActive = path ? location.pathname === path : activeTab === tab
        return (
          <button
            key={label}
            onClick={() => path ? navigate(path) : onTabChange?.(tab)}
            style={{
              flex: 1, display: 'flex', flexDirection: 'column',
              alignItems: 'center', gap: 4,
              padding: '12px 0 14px',
              background: 'none', border: 'none', cursor: 'pointer',
              color: isActive ? GOLD : MUTE,
              transition: 'color 0.2s',
            }}
          >
            <Icon size={20} strokeWidth={isActive ? 1.75 : 1.25}/>
            <span style={{
              fontFamily: '"Inter Tight",sans-serif',
              fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase',
            }}>
              {label}
            </span>
          </button>
        )
      })}
    </div>
  )
}
