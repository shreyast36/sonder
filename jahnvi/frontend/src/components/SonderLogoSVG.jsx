// Sonder logo — CSS/SVG layered luxury presentation.
// Two crescent blades forming an S, with specular bevel, brushed grain,
// drop shadow, and the interlocking crossing effect via clipPath.

// Blade paths in a 160×220 viewBox (center 80,110).
// Top blade:    upper-right → lower-left  (top half of S, convex faces left)
// Bottom blade: lower-left  → upper-right (bottom half, convex faces right)
const TOP = 'M 91,18 C 52,32 18,82 50,112 C 72,98 78,38 91,18 Z'
const BOT = 'M 69,202 C 108,188 142,138 110,108 C 88,122 82,182 69,202 Z'

function Defs({ uid }) {
  return (
    <defs>

      {/* ── Champagne gradients ─────────────────────────────────── */}

      {/* Top blade: bright at outer/left edge (convex, lit), dark at inner/right */}
      <linearGradient id={`${uid}-tg`} x1="18" y1="18" x2="96" y2="118" gradientUnits="userSpaceOnUse">
        <stop offset="0%"   stopColor="#FAF0CC"/>
        <stop offset="18%"  stopColor="#F4DCA3"/>
        <stop offset="48%"  stopColor="#C9A45D"/>
        <stop offset="78%"  stopColor="#6F5225"/>
        <stop offset="100%" stopColor="#2B1D0E"/>
      </linearGradient>

      {/* Bottom blade: bright at outer/right edge, dark at inner/left */}
      <linearGradient id={`${uid}-bg`} x1="148" y1="202" x2="58" y2="102" gradientUnits="userSpaceOnUse">
        <stop offset="0%"   stopColor="#FAF0CC"/>
        <stop offset="18%"  stopColor="#F4DCA3"/>
        <stop offset="48%"  stopColor="#C9A45D"/>
        <stop offset="78%"  stopColor="#6F5225"/>
        <stop offset="100%" stopColor="#2B1D0E"/>
      </linearGradient>

      {/* Highlight streak: near-white along the lit outer edge */}
      <linearGradient id={`${uid}-hl`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"   stopColor="#FFFDF0" stopOpacity="0.9"/>
        <stop offset="50%"  stopColor="#F4DCA3" stopOpacity="0.4"/>
        <stop offset="100%" stopColor="#C9A45D" stopOpacity="0"/>
      </linearGradient>

      {/* ── Drop shadow ─────────────────────────────────────────── */}
      <filter id={`${uid}-sh`} x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="6"/>
        <feOffset dx="0" dy="5" result="shadow"/>
        <feFlood floodColor="#010101" floodOpacity="1" result="color"/>
        <feComposite in="color" in2="shadow" operator="in" result="darkShadow"/>
        <feMerge>
          <feMergeNode in="darkShadow"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>

      {/* ── Metallic surface: brushed grain + specular bevel ────── */}
      <filter id={`${uid}-metal`} x="-8%" y="-8%" width="116%" height="116%">

        {/* Brushed horizontal grain */}
        <feTurbulence type="fractalNoise" baseFrequency="0.02 0.9"
          numOctaves="2" seed="7" result="noise"/>
        <feColorMatrix type="saturate" values="0" in="noise" result="gray"/>
        <feBlend in="SourceGraphic" in2="gray" mode="soft-light" result="grained"/>
        <feComposite in="grained" in2="SourceAlpha" operator="in" result="textured"/>

        {/* Specular bevel — reads blade edges as a raised surface */}
        <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blurAlpha"/>
        <feSpecularLighting in="blurAlpha" result="spec"
          surfaceScale="8" specularConstant="1.6" specularExponent="42"
          lightingColor="#FFF8E0">
          <fePointLight x="30" y="-140" z="180"/>
        </feSpecularLighting>
        <feComposite in="spec" in2="SourceAlpha" operator="in" result="specClipped"/>

        {/* Blend specular over grained base */}
        <feBlend in="textured" in2="specClipped" mode="screen"/>
      </filter>

      {/* ── Arc glow ────────────────────────────────────────────── */}
      <filter id={`${uid}-glow`} x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="4" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>

      {/* ── Clip: only lower half for crossing layer ─────────────── */}
      <clipPath id={`${uid}-lower`}>
        <rect x="0" y="110" width="160" height="110"/>
      </clipPath>

    </defs>
  )
}

function Blade({ d, grad, uid, shadow }) {
  return (
    <g>
      {/* shadow pass */}
      {shadow && <path d={d} fill="#0A0805" filter={`url(#${uid}-sh)`} opacity="0.75"/>}
      {/* metallic surface */}
      <path d={d} fill={`url(#${grad})`} filter={`url(#${uid}-metal)`}/>
    </g>
  )
}

// ── S-mark ────────────────────────────────────────────────────────────────────

export function SonderMarkSVG({ size = 100, uid = 'sm' }) {
  const w = Math.round(size * (160 / 220))
  return (
    <svg
      viewBox="0 0 160 220"
      width={w}
      height={size}
      style={{ display: 'block', overflow: 'visible' }}
      role="img"
      aria-label="Sonder"
    >
      <Defs uid={uid}/>

      {/* Layer 1 — bottom blade behind */}
      <Blade d={BOT} grad={`${uid}-bg`} uid={uid} shadow/>

      {/* Layer 2 — top blade in front (in front at the top crossing) */}
      <Blade d={TOP} grad={`${uid}-tg`} uid={uid} shadow/>

      {/* Layer 3 — bottom blade's lower half redrawn in front (crossing effect) */}
      <g clipPath={`url(#${uid}-lower)`}>
        <Blade d={BOT} grad={`${uid}-bg`} uid={uid} shadow={false}/>
      </g>
    </svg>
  )
}

// ── Full stacked lockup (mark + wordmark + tagline) ───────────────────────────

const GOLD_TEXT = 'linear-gradient(180deg, #F0DCB0 0%, #E8D4A8 28%, #D4B686 55%, #B89464 80%, #8A6F4A 100%)'

export function SonderLockupSVG({ markSize = 120, showTagline = true, uid = 'lk' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: markSize * 0.14 }}>
      <SonderMarkSVG size={markSize} uid={uid}/>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: markSize * 0.04 }}>
        <span style={{
          fontFamily: '"Cormorant Garamond", serif',
          fontWeight: 400,
          fontSize: markSize * 0.14,
          letterSpacing: '0.44em',
          textIndent: '0.44em',
          lineHeight: 1,
          background: GOLD_TEXT,
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          color: 'transparent',
          display: 'inline-block',
          textShadow: 'none',
        }}>
          SONDER
        </span>
        {showTagline && (
          <span style={{
            fontFamily: '"Inter Tight", sans-serif',
            fontWeight: 300,
            fontSize: markSize * 0.042,
            letterSpacing: '0.44em',
            textIndent: '0.44em',
            textTransform: 'uppercase',
            color: 'rgba(244,237,224,0.42)',
            display: 'inline-block',
          }}>
            TRAVEL, TOGETHER
          </span>
        )}
      </div>
    </div>
  )
}

// ── Horizontal nav lockup (mark left, text right) ────────────────────────────

export function SonderNavLogo({ markHeight = 56, uid = 'nav' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: markHeight * 0.22 }}>
      <SonderMarkSVG size={markHeight} uid={uid}/>
      <div style={{ display: 'flex', flexDirection: 'column', gap: markHeight * 0.06 }}>
        <span style={{
          fontFamily: '"Cormorant Garamond", serif',
          fontWeight: 400,
          fontSize: markHeight * 0.38,
          letterSpacing: '0.42em',
          textIndent: '0.42em',
          lineHeight: 1,
          background: GOLD_TEXT,
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          color: 'transparent',
          display: 'inline-block',
        }}>
          SONDER
        </span>
        <span style={{
          fontFamily: '"Inter Tight", sans-serif',
          fontWeight: 300,
          fontSize: markHeight * 0.13,
          letterSpacing: '0.42em',
          textIndent: '0.42em',
          textTransform: 'uppercase',
          color: 'rgba(244,237,224,0.4)',
          display: 'inline-block',
        }}>
          TRAVEL, TOGETHER
        </span>
      </div>
    </div>
  )
}
