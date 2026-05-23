import { Sparkles } from 'lucide-react'
import { BG } from '../lib/tokens'

/**
 * "Sonder Curated" disclosure pill.
 *
 * Renders nothing when the profile isn't a synthetic (is_seed === false).
 * When rendered, it's a small violet pill chip that sits unobtrusively
 * but visibly anywhere a user might mistake the synthetic for a real
 * traveller — match card, match detail, chat sidebar, notification banner.
 *
 * Variants:
 *   default  — pill with icon + "Sonder Curated" label
 *   compact  — just the icon + "Curated" (for tight spaces like chat banners)
 *   inline   — text-only, no chip background (for dense layouts)
 *
 * The component is always size-bounded by its content; callers position it
 * with absolute / flex.
 */
export default function SynthBadge({ isSeed = false, variant = 'default', style = {} }) {
  if (!isSeed) return null

  const VIOLET      = '#8B5CF6'
  const VIOLET_DIM  = '#8B5CF6cc'
  const VIOLET_BG   = 'rgba(139, 92, 246, 0.10)'
  const VIOLET_BD   = 'rgba(139, 92, 246, 0.35)'

  const baseLabelStyle = {
    fontFamily:     '"Inter Tight", sans-serif',
    fontSize:       9,
    fontWeight:     500,
    letterSpacing:  '0.16em',
    textTransform:  'uppercase',
    color:          VIOLET,
    lineHeight:     1,
  }

  if (variant === 'inline') {
    return (
      <span
        title="A Sonder-curated traveller — not a real user. Powered by AI."
        style={{
          ...baseLabelStyle,
          color: VIOLET_DIM,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          ...style,
        }}
      >
        <Sparkles size={9} style={{ color: VIOLET_DIM }} />
        Sonder Curated
      </span>
    )
  }

  if (variant === 'compact') {
    return (
      <span
        title="A Sonder-curated traveller — not a real user. Powered by AI."
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '3px 7px',
          borderRadius: 999,
          background: VIOLET_BG,
          border: `1px solid ${VIOLET_BD}`,
          ...style,
        }}
      >
        <Sparkles size={9} style={{ color: VIOLET }} />
        <span style={baseLabelStyle}>Curated</span>
      </span>
    )
  }

  return (
    <span
      title="A Sonder-curated traveller — not a real user. Powered by AI."
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '5px 10px',
        borderRadius: 999,
        background: VIOLET_BG,
        border: `1px solid ${VIOLET_BD}`,
        boxShadow: `0 0 0 0px ${BG}`,
        ...style,
      }}
    >
      <Sparkles size={10} style={{ color: VIOLET }} />
      <span style={baseLabelStyle}>Sonder Curated</span>
    </span>
  )
}
