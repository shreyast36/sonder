import { MapPin } from 'lucide-react'
import { GOLD, BONE, MUTE, HAIRLINE } from '../lib/tokens'
import LuxCard from './LuxCard'

function MatchRing({ pct = 92 }) {
  const r = 22, c = 2 * Math.PI * r
  return (
    <div style={{
      position: 'relative', width: 56, height: 56,
      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
    }}>
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', transform: 'rotate(-90deg)' }} viewBox="0 0 56 56">
        <circle cx="28" cy="28" r={r} fill="none" stroke={HAIRLINE} strokeWidth="2.5"/>
        <circle cx="28" cy="28" r={r} fill="none" stroke={GOLD} strokeWidth="2.5"
          strokeDasharray={c} strokeDashoffset={c - (pct / 100) * c} strokeLinecap="round"/>
      </svg>
      <div style={{ textAlign: 'center', position: 'relative' }}>
        <p style={{ color: BONE, fontWeight: 700, fontSize: 11, lineHeight: 1 }}>{pct}%</p>
        <p style={{ fontSize: 7, letterSpacing: '0.14em', color: MUTE, marginTop: 1, fontFamily: '"Inter Tight",sans-serif' }}>MATCH</p>
      </div>
    </div>
  )
}

function Initials({ name, size = 50 }) {
  const initials = (name || '?')
    .split(/\s+/).filter(Boolean).slice(0, 2).map(s => s[0].toUpperCase()).join('') || '?'
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', flexShrink: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(212,182,134,0.10)',
      border: `1px solid ${HAIRLINE}`,
      color: GOLD, fontFamily: '"Cormorant Garamond",serif', fontSize: size * 0.4,
    }}>{initials}</div>
  )
}

export default function MatchCard({ match, onClick }) {
  const {
    display_name = '',
    avatar_url,
    location = '',
    match_score = 0,
    tags = [],
  } = match ?? {}

  return (
    <LuxCard style={{ width: '100%' }} onClick={onClick}>
      <div style={{ padding: '18px 16px', display: 'flex', alignItems: 'center', gap: 14 }}>
        {avatar_url ? (
          <img
            src={avatar_url}
            alt={display_name}
            style={{ width: 50, height: 50, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }}
          />
        ) : (
          <Initials name={display_name} size={50} />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{
            color: BONE, fontSize: 15,
            fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, marginBottom: 3,
          }}>
            {display_name}
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
            <MapPin size={9} style={{ color: GOLD, flexShrink: 0 }}/>
            <span style={{ fontSize: 10, color: MUTE, fontFamily: '"Inter Tight",sans-serif' }}>{location}</span>
          </div>
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
            {tags.map(tag => (
              <span key={tag} style={{
                fontSize: 8, letterSpacing: '0.10em', textTransform: 'uppercase',
                color: GOLD, fontFamily: '"Inter Tight",sans-serif',
                padding: '3px 8px', borderRadius: 20,
                border: `1px solid rgba(212,182,134,0.20)`,
                background: 'rgba(212,182,134,0.04)',
              }}>
                {tag}
              </span>
            ))}
          </div>
        </div>
        <MatchRing pct={match_score}/>
      </div>
    </LuxCard>
  )
}
