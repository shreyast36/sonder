import { BONE, MUTE, GOLD, HAIRLINE } from '../lib/tokens'

export default function ChatBubble({ message, isOwn }) {
  const { content, timestamp, seen, sender_name } = message
  const time = timestamp
    ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: isOwn ? 'flex-end' : 'flex-start',
      marginBottom: 14,
    }}>
      {!isOwn && sender_name && (
        <span style={{
          fontFamily: '"Inter Tight",sans-serif', fontSize: 9,
          letterSpacing: '0.12em', color: MUTE, marginBottom: 4, paddingLeft: 2,
        }}>
          {sender_name}
        </span>
      )}
      <div style={{
        maxWidth: '72%',
        padding: '11px 15px',
        borderRadius: isOwn ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        background: isOwn
          ? 'linear-gradient(135deg,rgba(212,182,134,0.20) 0%,rgba(212,182,134,0.08) 100%)'
          : 'rgba(255,255,255,0.04)',
        border: `1px solid ${isOwn ? 'rgba(212,182,134,0.22)' : HAIRLINE}`,
      }}>
        <p style={{
          fontFamily: '"Inter Tight",sans-serif', fontWeight: 300,
          fontSize: 13, lineHeight: 1.65, color: BONE, margin: 0,
        }}>
          {content}
        </p>
      </div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 4, marginTop: 3,
        paddingRight: isOwn ? 2 : 0, paddingLeft: isOwn ? 0 : 2,
      }}>
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: MUTE }}>{time}</span>
        {isOwn && seen && (
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: GOLD }}>Seen</span>
        )}
      </div>
    </div>
  )
}
