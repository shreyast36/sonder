# Sonder — Frontend Design Specification

> Welcome page design system, component specs, and visual conventions for the Sonder luxury travel app.

---

## Brand Tokens

All tokens are defined at the top of `src/pages/Welcome.jsx` and should be referenced from there. Do not hardcode hex values inline.

| Token | Value | Usage |
|---|---|---|
| `BG` | `#080807` | Page background, canvas clear color |
| `GOLD` | `#D4B686` | Accent color — buttons, icons, dots, rings |
| `BONE` | `#F4EDE0` | Primary text — headings, card content |
| `HAIRLINE` | `rgba(232,212,168,0.11)` | Borders, dividers, card outlines |
| `MUTE` | `rgba(244,237,224,0.44)` | Secondary text — captions, nav links, descriptions |
| `DIM` | `rgba(244,237,224,0.16)` | Tertiary text — scroll hint, footer copyright |
| `GOLD_GRAD` | `linear-gradient(180deg,#F0DCB0 0%,#E8D4A8 28%,#D4B686 55%,#B89464 80%,#8A6F4A 100%)` | Italic headings, large display numbers, logo wordmark |
| `GRAPHITE` | `#15151A` | Avatar outline color in MatchCard |

---

## Typography

Three typefaces — each with a strict role. Never mix their roles.

| Family | Role | Weights used |
|---|---|---|
| **Cormorant Garamond** | Display / editorial headings, large italic accents | 300 (italic), 400, 400 italic |
| **Inter Tight** | All UI text — labels, captions, buttons, nav, body | 300, 400, 500, 600 |
| **JetBrains Mono** | Code, data values (not currently used in Welcome) | 300, 400 |

All loaded via Google Fonts in `index.html`.

### Typographic Scale

| Element | Font | Size | Weight | Letter-spacing | Notes |
|---|---|---|---|---|---|
| Hero H1 (roman) | Cormorant Garamond | `clamp(52px, 7.5vw, 108px)` | 400 | `-0.025em` | |
| Hero H1 (italic) | Cormorant Garamond | `clamp(52px, 7.5vw, 108px)` | 400 italic | `-0.025em` | Gold gradient fill |
| Section headline | Cormorant Garamond | `clamp(36px, 4.5vw, 60px)` | 400 italic | — | Used in ProductShowcase |
| CTA headline | Cormorant Garamond | `clamp(40px, 5.5vw, 76px)` | 400 italic | `-0.02em` | |
| Feature title | Cormorant Garamond | 28px | 400 | — | |
| Feature number | Cormorant Garamond | 64px italic | 400 | `-0.03em` | Gold gradient, opacity 0.28 |
| Body / description | Inter Tight | 14–15px | 300 | — | Line-height 1.8–1.88 |
| UI labels / eyebrows | Inter Tight | 9–10px | 300–500 | `0.22em–0.44em` | Uppercase |
| Button text | Inter Tight | 10–11px | 500 | `0.18em–0.22em` | Uppercase |
| Nav links | Inter Tight | 10px | 400 | `0.22em` | Uppercase |

---

## Animation

Custom ease used throughout: `[0.16, 1, 0.3, 1]` — a fast-out spring curve.

```js
const ease   = [0.16, 1, 0.3, 1]
const reveal = { hidden: { opacity: 0, y: 24 }, show: { opacity: 1, y: 0, transition: { duration: 1.2, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.18 } } }
```

| Element | Animation | Duration |
|---|---|---|
| Hero group | `stagger` → `reveal` on each child | 1.2s, stagger 0.18s |
| Scroll hint fade-in | `opacity: 0 → 1`, delay 2.8s | 1.2s |
| Scroll line pulse | `scaleY [1,1.7,1]` + opacity | 2.4s, infinite |
| ProductShowcase cards | `opacity 0, y 40 → 1, 0` on viewport | 1s, delay 0.1 / 0.22s |
| Floating cards | `y: [0, -12, 0]` | 7s, infinite easeInOut |
| MatchCard float offset | delay 2.8s (out of phase with ItineraryCard) | |
| LuxCard hover | `y: -6` | 0.3s easeOut |
| Feature rows | `opacity 0, y 16 → 1, 0` on viewport, stagger 0.08s | 0.9s |
| CTA section | `opacity 0, y 24 → 1, 0` on viewport | 1.2s |
| Nav button hover | `color: MUTE → BONE` | 0.25s |
| Nav CTA hover | background/color swap: gold outline → filled gold | 0.25s |
| Hero CTA hover | `translateY(-2px)` + stronger glow | 0.28s |

---

## Visual Effects

### Film Grain Overlay (`GrainOverlay`)
- SVG `feTurbulence` (`fractalNoise`, baseFrequency `0.85`, 4 octaves) encoded as a data URI
- `position: fixed`, `zIndex: 200`, `pointerEvents: none`
- Opacity: **0.034** — almost imperceptible, adds texture depth
- Tile: `200px × 200px`

### Particle Field (`DriftParticles` + `ParticleCanvas`)
- Three.js `points` rendered via `@react-three/fiber`
- Canvas: `alpha: false`, `gl.setClearColor('#080807', 1)` — eliminates gray flash on mount
- Deferred mount via `useState` + `useEffect` to prevent SSR/hydration issues
- Three particle layers:

| Layer | Count | Color | Size | Opacity | Spread (x,y,z) |
|---|---|---|---|---|---|
| Mid gold | 360 | `#C9A45D` | 0.02 | 0.28 | 26, 16, 10 |
| Soft cream | 80 | `#F0DCB0` | 0.06 | 0.06 | 32, 20, 14 |
| Fine bright | 40 | `#FAF0CC` | 0.012 | 0.55 | 18, 12, 6 |

- Particles drift upward and reset; horizontal sine-wave sway per particle
- Camera: `position [0,0,8]`, `fov: 55`

### Ambient Glows
- Hero: `radial-gradient(ellipse 70% 65% at 50% 48%, rgba(10,9,8,0.94) 0%, transparent)` overlay + gold ellipse glow
- ProductShowcase: `900×500` ellipse, `rgba(212,182,134,0.04)`
- CTA: `800×500` ellipse, `rgba(212,182,134,0.07)`

---

## Page Layout

```
┌────────────────────────────────────────────────────┐
│  Nav (sticky, blur backdrop)                       │
├────────────────────────────────────────────────────┤
│  Hero (100vh – nav, centered, full-screen)         │
├────────────────────────────────────────────────────┤
│  Marquee (destination ticker, hairline borders)    │
├────────────────────────────────────────────────────┤
│  ProductShowcase (floating ItineraryCard+MatchCard)│
├────────────────────────────────────────────────────┤
│  Features (4-row editorial grid)                   │
├────────────────────────────────────────────────────┤
│  CTA (email capture, invitation-only copy)         │
├────────────────────────────────────────────────────┤
│  Footer                                            │
└────────────────────────────────────────────────────┘
```

All sections: `position: relative; zIndex: 10` (above particle canvas at z=0, below grain at z=200).
Horizontal padding: `64px` on both sides. Max content width: `1100px` (centered).

---

## Component Specs

### Nav
- `position: relative; zIndex: 10`
- Padding: `20px 64px`
- Background: `rgba(8,8,7,0.50)`, `backdropFilter: blur(16px)`
- Bottom border: `1px solid HAIRLINE`
- Left: `SonderNav3D` (3D mark, markSize=48)
- Center: 3 ghost nav links (`HOW IT WORKS`, `DESTINATIONS`, `FOR GROUPS`) — uppercase, 10px, spacing 0.22em
- Right: "Join Sonder" ghost button — gold border (`rgba(212,182,134,0.45)`), gold text, fills on hover

### Hero
- Min-height: `calc(100vh - 81px)` (full viewport minus nav)
- Centered column layout
- Content max-width: 860px
- Eyebrow: `"For the Chronically Curious"` — Inter Tight, 10px, spacing 0.40em, gold, opacity 0.75, 32px below
- H1 line 1: `"Plan together."` — roman, BONE
- H1 line 2: `"Travel better."` — italic, gold gradient fill
- Subtext: 15px, 340px max-width, MUTE, lh 1.88
- CTA button: gold fill, `BG` text, `17px 44px` padding, glow shadow
- Scroll hint: fades in after 2.8s delay, animated vertical line + "SCROLL" label

### Marquee
- 12 destination names × 2 (seamless loop): `KYOTO`, `AMALFI COAST`, `PATAGONIA`, `MARRAKECH`, `SANTORINI`, `MALDIVES`, `CAPPADOCIA`, `QUEENSTOWN`, `LOFOTEN`, `RAJASTHAN`, `LAKE COMO`, `ICELAND`
- Animation: `marqueeScroll` CSS keyframe, 48s linear infinite (defined in `globals.css`)
- 9px Inter Tight, spacing 0.40em, opacity 0.18, gold dot separators

### ProductShowcase
- Headline: `"Everything, in sync."` — Cormorant Garamond italic, 60px, BONE
- Two floating cards side-by-side, centered, gap 28px
- MatchCard offset: `marginTop: 80px`, float phase offset 2.8s
- Background radial glow ellipse (900×500)

#### ItineraryCard (340px wide)
- Dark glass card via `LuxCard` (gradient border, `rgba(14,14,13,0.98)` fill)
- Timeline rows: Uluwatu Temple (Culture) / Jimbaran Seafood (Dining) / Seminyak Sunset (Nature)
- Timeline connector: 5px gold dot + 1px HAIRLINE vertical line
- Icons: Lucide (`Landmark`, `Utensils`, `Sun`) in 32px rounded squares
- Footer: estimated daily spend `$85 – $120`

#### MatchCard (272px wide)
- Same `LuxCard` wrapping
- Avatar stack: two 54px overlapping circles (margin-left -15px), GRAPHITE outline
- `MatchRing`: SVG circle progress ring at 92%, 72px container
- Stat pills: RELAXED / MID-RANGE / COUPLE (Pace / Budget / Style) in 3-column grid
- Live sync indicator: gold pulse dot + 12-bar waveform
- Waveform: 2px wide bars, heights `[3,6,10,4,9,5,8,3,7,11,4,6]`, opacity 0.28

### Features
- 4 rows, full-width hairline dividers (top of row 1, bottom of all rows)
- 3-column grid: `80px | 1fr | 1fr` with 56px column gap, 36px vertical padding
- Number: 64px Cormorant italic, gold gradient, opacity 0.28
- Title: 28px Cormorant, BONE
- Description: 14px Inter Tight 300, MUTE, lh 1.80

| # | Title | Description |
|---|---|---|
| 01 | Your itinerary, perfected. | Day-by-day plans shaped to your pace, your budget, and your version of a good day. |
| 02 | Matched to the right people. | Companions selected by how you move, what you value, and the kind of trip you want to have. |
| 03 | Plans that evolve together. | Every decision lands in real time — across everyone, always. |
| 04 | A record of everything. | The places, the moments, the notes. Kept privately, beautifully, long after you're home. |

### CTA
- Top hairline border
- Headline: `"Where will you go next?"` — Cormorant italic, 76px, BONE
- Subtext: `"A curated few are granted access each season."` — 14px, 340px wide, MUTE
- Email input + "Request Access" button inline (split pill shape, border-radius 5px)
  - Input: `rgba(232,212,168,0.04)` bg, `rgba(232,212,168,0.18)` border
  - Button: gold fill, BG text, 10px Inter Tight 500, spacing 0.20em
- Footer line: `"By invitation only · No spam, ever"` — 10px, spacing 0.22em, DIM
- Background: centered 800×500 gold ellipse glow

### Footer
- `24px 64px` padding, hairline top border
- `rgba(8,8,7,0.7)` background, `blur(16px)` backdrop
- Left: `SonderNav3D` (markSize=32)
- Right: `© 2025 Sonder` — 10px Inter Tight 300, DIM

---

## Logo Components

All logo components live in `src/components/SonderMark3D.jsx` and `src/components/SonderLogoSVG.jsx`.

### `SonderNav3D` (used in Nav + Footer)
- Horizontal lockup: 3D blade mark (left) + wordmark "SONDER" + tagline "TRAVEL, TOGETHER" (right)
- Mark: Three.js `ExtrudeGeometry` crescents, `MeshPhysicalMaterial` gold (`#C8A86A`, metalness 1.0, roughness 0.14)
- Canvas: `frameloop="demand"`, `alpha: true`, Environment preset="studio"
- Wordmark: Cormorant Garamond, spacing 0.42em, gold gradient
- Tagline: Inter Tight 300, spacing 0.42em, `rgba(244,237,224,0.4)`

### `SonderMark3D` (standalone 3D mark)
- Props: `size` (height in px), width auto-calculated at `size × (200/280)` ratio
- Camera: `position [0,0,3.4]`, `fov: 36`

### `SonderMarkSVG` / `SonderLockupSVG` / `SonderNavLogo` (SVG fallbacks)
- Pure SVG crescents with gradient fills, bevel filters, brushed grain texture
- Used as fallbacks or in contexts where WebGL overhead is undesirable

---

## Background / Dark Mode Anti-Flash

The following layered approach prevents the white/gray flash on page load:

1. `<html style="background:#080807;color-scheme:dark">` in `index.html`
2. Inline `<style>html,body,#root{background:#080807;color-scheme:dark;transition:none}</style>` in `<head>`
3. `globals.css`: `html { background-color: #080807; color-scheme: dark; }` + `body { background-color: #080807; }`
4. `ParticleCanvas`: `gl={{ alpha: false }}` + `onCreated={({ gl }) => gl.setClearColor('#080807', 1)}`
5. `ParticleCanvas`: deferred mount (`useState(false)` + `useEffect(() => setMounted(true), [])`) to prevent WebGL canvas appearing before background color

---

## Key Files

| File | Role |
|---|---|
| `src/pages/Welcome.jsx` | Entire landing page — all design tokens, layout, and components |
| `src/components/SonderMark3D.jsx` | 3D logo mark (Three.js) — `SonderMark3D`, `SonderNav3D` |
| `src/components/SonderLogoSVG.jsx` | SVG logo variants — `SonderMarkSVG`, `SonderLockupSVG`, `SonderNavLogo` |
| `src/styles/globals.css` | Tailwind directives, utility classes (`glass`, `text-gradient`, `live-dot`), `@keyframes marqueeScroll` |
| `index.html` | Font imports (Cormorant Garamond, Inter, Inter Tight, JetBrains Mono, Playfair Display), dark mode anti-flash inline styles |
