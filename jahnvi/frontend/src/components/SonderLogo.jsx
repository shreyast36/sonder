// Two precision-cut crescent ribbons that interlock to form the Sonder S mark.
// Each crescent: outer arc sweeps wide → inner arc follows closely → sharp pointed tips.
// Inner arc also swings toward the arc peak so the ribbon stays thin (≈10–14 u wide).
const TOP = 'M 20,64 C 4,44 8,8 38,6 C 56,4 76,14 74,32 C 65,18 52,10 42,14 C 32,18 22,46 20,64 Z'
const BOT = 'M 80,36 C 96,56 92,92 62,94 C 44,96 24,86 26,68 C 35,82 48,90 58,86 C 68,82 78,54 80,36 Z'

export function SonderMark({ size = 28, uid = 'a' }) {
  const p = `sm-${uid}`
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        {/* Top crescent — outer face is upper-left → bright; inner face lower-right → dark */}
        <linearGradient id={`${p}-tg`} x1="5" y1="2" x2="90" y2="95" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#F0E4A8"/>
          <stop offset="18%"  stopColor="#D4AA54"/>
          <stop offset="48%"  stopColor="#8C6318"/>
          <stop offset="76%"  stopColor="#4A2C08"/>
          <stop offset="100%" stopColor="#180A00"/>
        </linearGradient>
        {/* Top specular bloom at outer-arc peak */}
        <radialGradient id={`${p}-ts`} cx="38" cy="6" r="42" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#FFFEF8" stopOpacity="0.88"/>
          <stop offset="28%"  stopColor="#F0E080" stopOpacity="0.38"/>
          <stop offset="100%" stopColor="#D4AA54" stopOpacity="0"/>
        </radialGradient>

        {/* Bottom crescent — outer face is lower-right → bright; inner face upper-left → dark */}
        <linearGradient id={`${p}-bg`} x1="95" y1="98" x2="10" y2="5" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#F0E4A8"/>
          <stop offset="18%"  stopColor="#D4AA54"/>
          <stop offset="48%"  stopColor="#8C6318"/>
          <stop offset="76%"  stopColor="#4A2C08"/>
          <stop offset="100%" stopColor="#180A00"/>
        </linearGradient>
        {/* Bottom specular bloom at outer-arc peak */}
        <radialGradient id={`${p}-bs`} cx="62" cy="94" r="42" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#FFFEF8" stopOpacity="0.88"/>
          <stop offset="28%"  stopColor="#F0E080" stopOpacity="0.38"/>
          <stop offset="100%" stopColor="#D4AA54" stopOpacity="0"/>
        </radialGradient>

        {/* Weave clip: redraw bottom crescent's lower half in front of top crescent */}
        <clipPath id={`${p}-wc`}>
          <rect x="0" y="50" width="100" height="50"/>
        </clipPath>
      </defs>

      {/* Layer 1 — bottom crescent, behind */}
      <path d={BOT} fill={`url(#${p}-bg)`}/>
      <path d={BOT} fill={`url(#${p}-bs)`}/>

      {/* Layer 2 — top crescent, in front at top */}
      <path d={TOP} fill={`url(#${p}-tg)`}/>
      <path d={TOP} fill={`url(#${p}-ts)`}/>

      {/* Layer 3 — bottom crescent lower half, weaves in front at bottom */}
      <g clipPath={`url(#${p}-wc)`}>
        <path d={BOT} fill={`url(#${p}-bg)`}/>
        <path d={BOT} fill={`url(#${p}-bs)`}/>
      </g>
    </svg>
  )
}

export function SonderWordmark({ size = 28 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: size * 0.38 }}>
      <SonderMark size={size} uid="wm"/>
      <span style={{
        fontFamily: '"Playfair Display", Georgia, serif',
        fontWeight: 400,
        fontSize: size * 0.72,
        letterSpacing: '0.24em',
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
        letterSpacing: '0.32em',
        color: '#C9A840',
        lineHeight: 1,
      }}>
        sonder
      </span>
      <span style={{
        fontFamily: 'Inter, system-ui, sans-serif',
        fontWeight: 300,
        fontSize: markSize * 0.095,
        letterSpacing: '0.48em',
        color: '#A07830',
        textTransform: 'uppercase',
        lineHeight: 1,
        marginTop: markSize * 0.04,
      }}>
        Travel, Together
      </span>
    </div>
  )
}
