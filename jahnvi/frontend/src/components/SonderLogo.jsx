// Two filled crescents interlocking to form a luxury S mark
// Each path: outer arc sweeps wide → inner arc cuts back, forming a closed crescent
const TOP = 'M 14,68 C 2,48 8,10 36,3 C 53,-1 73,9 80,28 C 70,36 58,46 47,52 C 36,58 24,64 14,68 Z'
const BOT = 'M 86,32 C 98,52 92,90 64,97 C 47,101 27,91 20,72 C 30,64 42,54 53,48 C 64,42 76,36 86,32 Z'

export function SonderMark({ size = 28, uid = 'a' }) {
  const p = `sm-${uid}`
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        {/* Top crescent: outer edge is upper-left → bright; inner edge lower-right → dark */}
        <linearGradient id={`${p}-tg`} x1="5" y1="5" x2="95" y2="95" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#F5EBC0"/>
          <stop offset="14%"  stopColor="#E2C160"/>
          <stop offset="36%"  stopColor="#B08828"/>
          <stop offset="60%"  stopColor="#6B4A0E"/>
          <stop offset="84%"  stopColor="#3A2206"/>
          <stop offset="100%" stopColor="#180A00"/>
        </linearGradient>
        {/* Top specular: white-gold bloom at the outermost tip of the upper arc */}
        <radialGradient id={`${p}-ts`} cx="36" cy="3" r="48" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#FFFDF4" stopOpacity="0.92"/>
          <stop offset="22%"  stopColor="#F5E8A0" stopOpacity="0.55"/>
          <stop offset="60%"  stopColor="#D4AA54" stopOpacity="0.14"/>
          <stop offset="100%" stopColor="#D4AA54" stopOpacity="0"/>
        </radialGradient>
        {/* Top edge rim: thin bright stroke trace along outer convex edge */}
        <radialGradient id={`${p}-tr`} cx="52" cy="2" r="62" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#FFF8DC" stopOpacity="0.45"/>
          <stop offset="55%"  stopColor="#C9A840" stopOpacity="0.1"/>
          <stop offset="100%" stopColor="#C9A840" stopOpacity="0"/>
        </radialGradient>

        {/* Bottom crescent: outer edge is lower-right → bright; inner edge upper-left → dark */}
        <linearGradient id={`${p}-bg`} x1="95" y1="95" x2="5" y2="5" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#F5EBC0"/>
          <stop offset="14%"  stopColor="#E2C160"/>
          <stop offset="36%"  stopColor="#B08828"/>
          <stop offset="60%"  stopColor="#6B4A0E"/>
          <stop offset="84%"  stopColor="#3A2206"/>
          <stop offset="100%" stopColor="#180A00"/>
        </linearGradient>
        {/* Bottom specular: white-gold bloom at the outermost tip of the lower arc */}
        <radialGradient id={`${p}-bs`} cx="64" cy="97" r="48" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#FFFDF4" stopOpacity="0.92"/>
          <stop offset="22%"  stopColor="#F5E8A0" stopOpacity="0.55"/>
          <stop offset="60%"  stopColor="#D4AA54" stopOpacity="0.14"/>
          <stop offset="100%" stopColor="#D4AA54" stopOpacity="0"/>
        </radialGradient>
        {/* Bottom edge rim */}
        <radialGradient id={`${p}-br`} cx="48" cy="98" r="62" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#FFF8DC" stopOpacity="0.45"/>
          <stop offset="55%"  stopColor="#C9A840" stopOpacity="0.1"/>
          <stop offset="100%" stopColor="#C9A840" stopOpacity="0"/>
        </radialGradient>

        {/* Interlocking weave: redraw bottom crescent's lower half in front of top */}
        <clipPath id={`${p}-wc`}>
          <rect x="0" y="50" width="100" height="50"/>
        </clipPath>
      </defs>

      {/* ── Layer 1: Bottom crescent (behind top at center) ── */}
      <path d={BOT} fill={`url(#${p}-bg)`}/>
      <path d={BOT} fill={`url(#${p}-bs)`}/>
      <path d={BOT} fill={`url(#${p}-br)`}/>

      {/* ── Layer 2: Top crescent (in front at top) ── */}
      <path d={TOP} fill={`url(#${p}-tg)`}/>
      <path d={TOP} fill={`url(#${p}-ts)`}/>
      <path d={TOP} fill={`url(#${p}-tr)`}/>

      {/* ── Layer 3: Bottom crescent lower half redrawn — weaves in front at bottom ── */}
      <g clipPath={`url(#${p}-wc)`}>
        <path d={BOT} fill={`url(#${p}-bg)`}/>
        <path d={BOT} fill={`url(#${p}-bs)`}/>
        <path d={BOT} fill={`url(#${p}-br)`}/>
      </g>
    </svg>
  )
}

export function SonderWordmark({ size = 28 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: size * 0.36 }}>
      <SonderMark size={size} uid="wm"/>
      <span style={{
        fontFamily: '"Playfair Display", Georgia, serif',
        fontWeight: 400,
        fontSize: size * 0.72,
        letterSpacing: '0.22em',
        color: '#C9A840',
        lineHeight: 1,
      }}>
        sonder
      </span>
    </div>
  )
}

export function SonderFullLogo({ markSize = 96 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: markSize * 0.14 }}>
      <SonderMark size={markSize} uid="full"/>
      <span style={{
        fontFamily: '"Playfair Display", Georgia, serif',
        fontWeight: 400,
        fontSize: markSize * 0.38,
        letterSpacing: '0.3em',
        color: '#C9A840',
        lineHeight: 1,
      }}>
        sonder
      </span>
      <span style={{
        fontFamily: 'Inter, system-ui, sans-serif',
        fontWeight: 300,
        fontSize: markSize * 0.1,
        letterSpacing: '0.46em',
        color: '#7C5A14',
        textTransform: 'uppercase',
        lineHeight: 1,
        marginTop: markSize * 0.05,
      }}>
        Travel, Together
      </span>
    </div>
  )
}
