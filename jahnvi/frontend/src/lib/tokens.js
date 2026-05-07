export const BG        = '#080807'
export const GOLD      = '#D4B686'
export const HAIRLINE  = 'rgba(232,212,168,0.11)'
export const BONE      = '#F4EDE0'
export const MUTE      = 'rgba(244,237,224,0.44)'
export const DIM       = 'rgba(244,237,224,0.16)'
export const GRAPHITE  = '#15151A'
export const GOLD_GRAD = 'linear-gradient(180deg,#F0DCB0 0%,#E8D4A8 28%,#D4B686 55%,#B89464 80%,#8A6F4A 100%)'
export const ease      = [0.16, 1, 0.3, 1]

const _svg = `<svg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="4" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>`
export const GRAIN = `url("data:image/svg+xml,${encodeURIComponent(_svg)}")`
