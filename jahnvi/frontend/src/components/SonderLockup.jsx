const GOLD = "linear-gradient(180deg, #F0DCB0 0%, #E8D4A8 35%, #D4B686 55%, #B89464 80%, #8A6F4A 100%)"

const GOLD_STOPS = [
  { offset: "0%",   stopColor: "#F0DCB0" },
  { offset: "35%",  stopColor: "#E8D4A8" },
  { offset: "55%",  stopColor: "#D4B686" },
  { offset: "80%",  stopColor: "#B89464" },
  { offset: "100%", stopColor: "#8A6F4A" },
]

export function SonderMark({ size = 80, gradientId = "sonderGold" }) {
  return (
    <svg
      viewBox="0 0 200 280"
      width={size * (200 / 280)}
      height={size}
      role="img"
      aria-label="Sonder"
      style={{ display: "block" }}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          {GOLD_STOPS.map(s => (
            <stop key={s.offset} offset={s.offset} stopColor={s.stopColor} />
          ))}
        </linearGradient>
      </defs>

      {/* Top blade: crescent opening down-right, sharp point top + bottom-left */}
      <path
        d="M 130 12 C 138 60, 132 96, 96 132 L 86 138 C 122 102, 128 64, 122 18 Z"
        fill={`url(#${gradientId})`}
      />

      {/* Mid stitch: small diagonal connector between blade tips */}
      <path
        d="M 86 138 L 100 144 L 114 138 L 100 150 Z"
        fill={`url(#${gradientId})`}
      />

      {/* Bottom blade: mirror of top, crescent opening up-left */}
      <path
        d="M 70 268 C 62 220, 68 184, 104 148 L 114 142 C 78 178, 72 216, 78 262 Z"
        fill={`url(#${gradientId})`}
      />
    </svg>
  )
}

export function SonderWordmark({ size = 32, theme = "dark" }) {
  return (
    <span
      style={{
        fontFamily: `"Cormorant Garamond", serif`,
        fontWeight: 400,
        fontSize: size,
        letterSpacing: "0.42em",
        textIndent: "0.42em",
        lineHeight: 1,
        background: theme === "dark" ? GOLD : "linear-gradient(180deg, #1A1A1A, #0A0A0B)",
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        color: "transparent",
        display: "inline-block",
      }}
    >
      SONDER
    </span>
  )
}

export function SonderTagline({ size = 9, theme = "dark", text = "TRAVEL, TOGETHER" }) {
  return (
    <span
      style={{
        fontFamily: `"Inter Tight", sans-serif`,
        fontWeight: 300,
        fontSize: size,
        letterSpacing: "0.42em",
        textIndent: "0.42em",
        textTransform: "uppercase",
        color: theme === "dark" ? "rgba(244, 237, 224, 0.55)" : "rgba(20, 20, 20, 0.55)",
        display: "inline-block",
      }}
    >
      {text}
    </span>
  )
}

export function SonderLockup({ variant = "stacked", theme = "dark", size = 240, tagline = true, uid = "a", className }) {
  const gid = `sg-${uid}`

  if (variant === "mark-only")
    return <SonderMark size={size} gradientId={gid} />

  if (variant === "wordmark-only")
    return <SonderWordmark size={size * 0.16} theme={theme} />

  if (variant === "horizontal") {
    return (
      <span className={className} style={{ display: "inline-flex", alignItems: "center", gap: size * 0.18 }}>
        <SonderMark size={size} gradientId={gid} />
        <SonderWordmark size={size * 0.36} theme={theme} />
      </span>
    )
  }

  // stacked (default)
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        gap: size * 0.18,
      }}
    >
      <SonderMark size={size} gradientId={gid} />
      <span style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: size * 0.06 }}>
        <SonderWordmark size={size * 0.13} theme={theme} />
        {tagline && <SonderTagline size={size * 0.038} theme={theme} />}
      </span>
    </span>
  )
}
