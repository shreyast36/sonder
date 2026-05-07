// Orbital S mark: two sweeping arcs that interlock to form an S
// Upper arc — sweeps from left-center, over the top, to right-center (in front)
const UPPER = "M 25,58 C 16,50 10,34 14,20 C 18,8 32,2 48,4 C 62,6 74,16 78,30 C 82,44 76,58 68,60"
// Lower arc — sweeps from right-center, under the bottom, to left-center (behind)
const LOWER = "M 75,42 C 84,50 90,64 86,78 C 82,90 68,98 52,96 C 38,94 26,84 22,70 C 18,56 24,44 32,40"

export function SonderMark({ size = 28, uid = 'a' }) {
  const p = `sm-${uid}`
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        {/* Upper arc: brightest at crown (top of symbol) */}
        <radialGradient id={`${p}-ug`} cx="50" cy="4" r="68" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#EDD59A"/>
          <stop offset="22%"  stopColor="#D4AA54"/>
          <stop offset="52%"  stopColor="#9A7218"/>
          <stop offset="80%"  stopColor="#5C3D06"/>
          <stop offset="100%" stopColor="#251800"/>
        </radialGradient>

        {/* Lower arc: brightest at crown (bottom of symbol) */}
        <radialGradient id={`${p}-lg`} cx="52" cy="96" r="68" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#EDD59A"/>
          <stop offset="22%"  stopColor="#D4AA54"/>
          <stop offset="52%"  stopColor="#9A7218"/>
          <stop offset="80%"  stopColor="#5C3D06"/>
          <stop offset="100%" stopColor="#251800"/>
        </radialGradient>

        {/* Specular highlight for upper arc — tight bright strip at crown */}
        <radialGradient id={`${p}-uhl`} cx="50" cy="2" r="50" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#FFFCF0" stopOpacity="1"/>
          <stop offset="35%"  stopColor="#F5E07A" stopOpacity="0.75"/>
          <stop offset="75%"  stopColor="#C9A840" stopOpacity="0.2"/>
          <stop offset="100%" stopColor="#C9A840" stopOpacity="0"/>
        </radialGradient>

        {/* Specular highlight for lower arc */}
        <radialGradient id={`${p}-lhl`} cx="52" cy="98" r="50" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#FFFCF0" stopOpacity="1"/>
          <stop offset="35%"  stopColor="#F5E07A" stopOpacity="0.75"/>
          <stop offset="75%"  stopColor="#C9A840" stopOpacity="0.2"/>
          <stop offset="100%" stopColor="#C9A840" stopOpacity="0"/>
        </radialGradient>

        {/* Ambient halo filter */}
        <filter id={`${p}-halo`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      {/* ── Ambient warm glow behind both arcs ── */}
      <path d={LOWER} fill="none" stroke="#C9A840" strokeWidth="20" strokeLinecap="round"
        opacity="0.055" filter={`url(#${p}-halo)`}/>
      <path d={UPPER} fill="none" stroke="#C9A840" strokeWidth="20" strokeLinecap="round"
        opacity="0.055" filter={`url(#${p}-halo)`}/>

      {/* ── Lower arc (behind) ── */}
      {/* dark base shadow — creates depth and edge definition */}
      <path d={LOWER} fill="none" stroke="#0E0700" strokeWidth="16" strokeLinecap="round" opacity="0.75"/>
      {/* brushed metal body */}
      <path d={LOWER} fill="none" stroke={`url(#${p}-lg)`} strokeWidth="12" strokeLinecap="round"/>
      {/* inner mid-tone to blend layers */}
      <path d={LOWER} fill="none" stroke="#8B6618" strokeWidth="7" strokeLinecap="round" opacity="0.22"/>
      {/* specular edge highlight */}
      <path d={LOWER} fill="none" stroke={`url(#${p}-lhl)`} strokeWidth="4.5" strokeLinecap="round"/>

      {/* ── Upper arc (in front) ── */}
      <path d={UPPER} fill="none" stroke="#0E0700" strokeWidth="16" strokeLinecap="round" opacity="0.75"/>
      <path d={UPPER} fill="none" stroke={`url(#${p}-ug)`} strokeWidth="12" strokeLinecap="round"/>
      <path d={UPPER} fill="none" stroke="#8B6618" strokeWidth="7" strokeLinecap="round" opacity="0.22"/>
      <path d={UPPER} fill="none" stroke={`url(#${p}-uhl)`} strokeWidth="4.5" strokeLinecap="round"/>
    </svg>
  )
}

export function SonderWordmark({ size = 28 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: size * 0.32 }}>
      <SonderMark size={size} uid="wm"/>
      <span style={{
        fontFamily: '"Playfair Display", Georgia, serif',
        fontWeight: 400,
        fontSize: size * 0.7,
        letterSpacing: '0.2em',
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
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: markSize * 0.18 }}>
      <SonderMark size={markSize} uid="full"/>
      <span style={{
        fontFamily: '"Playfair Display", Georgia, serif',
        fontWeight: 400,
        fontSize: markSize * 0.36,
        letterSpacing: '0.26em',
        color: '#C9A840',
        lineHeight: 1,
      }}>
        sonder
      </span>
      <span style={{
        fontFamily: 'Inter, system-ui, sans-serif',
        fontWeight: 300,
        fontSize: markSize * 0.095,
        letterSpacing: '0.4em',
        color: '#7A5C14',
        textTransform: 'uppercase',
        lineHeight: 1,
        marginTop: markSize * 0.04,
      }}>
        Travel, Together
      </span>
    </div>
  )
}
