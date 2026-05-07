import { useRef, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { ChevronRight, MapPin, Users, Landmark, Utensils, Sun } from 'lucide-react'
import { SonderNav3D } from '../components/SonderMark3D'

// ── Tokens ────────────────────────────────────────────────────────────────────

const BG        = '#080807'
const GOLD      = '#D4B686'
const HAIRLINE  = 'rgba(232,212,168,0.11)'
const BONE      = '#F4EDE0'
const MUTE      = 'rgba(244,237,224,0.44)'
const DIM       = 'rgba(244,237,224,0.16)'
const GOLD_GRAD = 'linear-gradient(180deg,#F0DCB0 0%,#E8D4A8 28%,#D4B686 55%,#B89464 80%,#8A6F4A 100%)'

const ease    = [0.16, 1, 0.3, 1]
const reveal  = { hidden: { opacity: 0, y: 24 }, show: { opacity: 1, y: 0, transition: { duration: 1.2, ease } } }
const stagger = { show: { transition: { staggerChildren: 0.18 } } }

// ── Film grain ────────────────────────────────────────────────────────────────

const _svg  = `<svg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="4" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>`
const GRAIN = `url("data:image/svg+xml,${encodeURIComponent(_svg)}")`

function GrainOverlay() {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200, pointerEvents: 'none',
      opacity: 0.034, backgroundImage: GRAIN, backgroundSize: '200px 200px',
    }}/>
  )
}

// ── Particles ─────────────────────────────────────────────────────────────────

function DriftParticles({ count, color, size, opacity, spread }) {
  const ref    = useRef()
  const posRef = useRef()

  const geo = useMemo(() => {
    const arr = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      arr[i*3]   = (Math.random() - 0.5) * spread[0]
      arr[i*3+1] = (Math.random() - 0.5) * spread[1]
      arr[i*3+2] = (Math.random() - 0.5) * spread[2]
    }
    posRef.current = arr
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(arr, 3))
    return g
  }, [count])

  useFrame(({ clock }) => {
    const t    = clock.elapsedTime
    const pos  = posRef.current
    const half = spread[1] / 2
    for (let i = 0; i < count; i++) {
      pos[i*3+1] += 0.0005 + (i % 4) * 0.00012
      if (pos[i*3+1] > half) pos[i*3+1] = -half
      pos[i*3]   += Math.sin(t * 0.18 + i * 0.7) * 0.00018
    }
    ref.current.geometry.attributes.position.needsUpdate = true
  })

  return (
    <points ref={ref} geometry={geo}>
      <pointsMaterial color={color} size={size} transparent opacity={opacity} sizeAttenuation depthWrite={false}/>
    </points>
  )
}

function ParticleCanvas() {
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }}>
      <Canvas style={{ width: '100%', height: '100%' }} camera={{ position: [0,0,8], fov: 55 }}
        gl={{ antialias: false, alpha: true }} frameloop="always">
        <DriftParticles count={360} color="#C9A45D" size={0.02}  opacity={0.28} spread={[26,16,10]}/>
        <DriftParticles count={80}  color="#F0DCB0" size={0.06}  opacity={0.06} spread={[32,20,14]}/>
        <DriftParticles count={40}  color="#FAF0CC" size={0.012} opacity={0.55} spread={[18,12,6]}/>
      </Canvas>
    </div>
  )
}

// ── Hero emblem ───────────────────────────────────────────────────────────────

function HeroEmblem({ size = 320 }) {
  const cx = size / 2, cy = size / 2
  const r0 = size * 0.50
  const r1 = size * 0.445
  const r2 = size * 0.365
  const r3 = size * 0.285

  const mkTicks = (r, angles, len, op, w) => angles.map(deg => {
    const rad = (deg - 90) * Math.PI / 180
    return <line key={deg}
      x1={cx + r * Math.cos(rad)}         y1={cy + r * Math.sin(rad)}
      x2={cx + (r + len) * Math.cos(rad)} y2={cy + (r + len) * Math.sin(rad)}
      stroke={`rgba(212,182,134,${op})`}  strokeWidth={w}/>
  })

  return (
    <div style={{ position: 'relative', width: size, height: size, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible' }}
        viewBox={`0 0 ${size} ${size}`}>
        <circle cx={cx} cy={cy} r={r0} fill="none" stroke="rgba(232,212,168,0.06)" strokeWidth="0.5"/>
        <circle cx={cx} cy={cy} r={r2} fill="none" stroke="rgba(232,212,168,0.10)" strokeWidth="0.5"/>
        <circle cx={cx} cy={cy} r={r3} fill="none" stroke="rgba(232,212,168,0.06)" strokeWidth="0.5"/>
      </svg>
      <motion.svg
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible' }}
        viewBox={`0 0 ${size} ${size}`}
        animate={{ rotate: 360 }}
        transition={{ duration: 90, repeat: Infinity, ease: 'linear' }}>
        <circle cx={cx} cy={cy} r={r1} fill="none" stroke="rgba(232,212,168,0.20)" strokeWidth="0.75"/>
        {mkTicks(r1, [0, 90, 180, 270],              15, 0.50, 1.0)}
        {mkTicks(r1, [45, 135, 225, 315],             9, 0.25, 0.75)}
        {mkTicks(r1, [30,60,120,150,210,240,300,330], 5, 0.12, 0.5)}
      </motion.svg>
      <motion.div
        style={{
          position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
          width: size * 0.55, height: size * 0.55, borderRadius: '50%',
          background: 'radial-gradient(ellipse, rgba(212,182,134,0.22) 0%, transparent 70%)',
          pointerEvents: 'none', zIndex: 0,
        }}
        animate={{ opacity: [0.55, 1, 0.55], scale: [0.95, 1.05, 0.95] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}/>
      <span style={{
        fontFamily: '"Cormorant Garamond",serif',
        fontStyle: 'italic', fontWeight: 300,
        fontSize: size * 0.72, lineHeight: 1,
        background: GOLD_GRAD,
        WebkitBackgroundClip: 'text', backgroundClip: 'text',
        color: 'transparent',
        display: 'block', position: 'relative', zIndex: 1,
        userSelect: 'none', letterSpacing: '-0.04em',
        filter: 'drop-shadow(0 0 32px rgba(212,182,134,0.28))',
      }}>
        S
      </span>
    </div>
  )
}

// ── Product cards ─────────────────────────────────────────────────────────────

const GRAPHITE = '#15151A'

function LuxCard({ children, style }) {
  return (
    <motion.div whileHover={{ y: -6, transition: { duration: 0.3, ease: 'easeOut' } }}
      style={{ padding: 1, borderRadius: 22, background: 'linear-gradient(145deg,rgba(232,212,168,0.18) 0%,rgba(8,8,7,0) 55%,rgba(232,212,168,0.06) 100%)', ...style }}>
      <div style={{ background: 'rgba(14,14,13,0.98)', borderRadius: 21, height: '100%' }}>
        {children}
      </div>
    </motion.div>
  )
}

function MatchRing({ pct = 92 }) {
  const r = 28, c = 2 * Math.PI * r
  return (
    <div style={{ position: 'relative', width: 72, height: 72, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', transform: 'rotate(-90deg)' }} viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={r} fill="none" stroke={HAIRLINE} strokeWidth="2"/>
        <circle cx="36" cy="36" r={r} fill="none" stroke={GOLD} strokeWidth="2" strokeDasharray={c} strokeDashoffset={c - (pct/100)*c} strokeLinecap="round"/>
      </svg>
      <div style={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <p style={{ color: BONE, fontWeight: 700, fontSize: 13, lineHeight: 1 }}>{pct}%</p>
        <p style={{ fontSize: 9, letterSpacing: '0.14em', color: MUTE, marginTop: 2, fontFamily: '"Inter Tight",sans-serif' }}>MATCH</p>
      </div>
    </div>
  )
}

function ItineraryCard() {
  const rows = [
    { time: '9:00 AM', name: 'Uluwatu Temple',   cat: 'Culture', Icon: Landmark },
    { time: '1:00 PM', name: 'Jimbaran Seafood', cat: 'Dining',  Icon: Utensils },
    { time: '6:00 PM', name: 'Seminyak Sunset',  cat: 'Nature',  Icon: Sun      },
  ]
  return (
    <LuxCard style={{ width: 340 }}>
      <div style={{ padding: '28px 26px 22px' }}>
        <div style={{ fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 20, fontFamily: '"Inter Tight",sans-serif' }}>Your Upcoming Trip</div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <MapPin size={11} style={{ color: GOLD }}/>
            <span style={{ color: BONE, fontWeight: 500, fontSize: 14, fontFamily: '"Inter Tight",sans-serif' }}>Bali, Indonesia</span>
          </div>
          <span style={{ fontSize: 10, color: MUTE, fontFamily: '"Inter Tight",sans-serif' }}>Day 1 of 7</span>
        </div>
        {rows.map((row, i) => (
          <div key={row.name} style={{ display: 'flex', gap: 12 }}>
            <span style={{ fontSize: 10, width: 54, flexShrink: 0, paddingTop: 7, color: MUTE, fontFamily: '"Inter Tight",sans-serif' }}>{row.time}</span>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{ width: 5, height: 5, borderRadius: '50%', background: GOLD, marginTop: 10, flexShrink: 0 }}/>
              {i < rows.length - 1 && <div style={{ width: 1, flex: 1, marginTop: 5, background: HAIRLINE, minHeight: 28 }}/>}
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, paddingBottom: 18 }}>
              <div style={{ width: 32, height: 32, borderRadius: 9, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(212,182,134,0.05)', border: `1px solid ${HAIRLINE}` }}>
                <row.Icon size={13} style={{ color: GOLD }}/>
              </div>
              <div>
                <p style={{ color: BONE, fontSize: 13, fontWeight: 500, lineHeight: 1.2, fontFamily: '"Inter Tight",sans-serif' }}>{row.name}</p>
                <p style={{ fontSize: 10, marginTop: 3, color: MUTE, fontFamily: '"Inter Tight",sans-serif' }}>{row.cat}</p>
              </div>
            </div>
          </div>
        ))}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 16, borderTop: `1px solid ${HAIRLINE}` }}>
          <span style={{ fontSize: 10, color: MUTE, fontFamily: '"Inter Tight",sans-serif' }}>Est. daily spend</span>
          <span style={{ color: BONE, fontSize: 13, fontWeight: 500, fontFamily: '"Inter Tight",sans-serif' }}>$85 – $120</span>
        </div>
      </div>
    </LuxCard>
  )
}

function MatchCard() {
  return (
    <LuxCard style={{ width: 272 }}>
      <div style={{ padding: '26px 22px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
          <Users size={11} style={{ color: GOLD }}/>
          <span style={{ fontSize: 9, letterSpacing: '0.24em', textTransform: 'uppercase', color: MUTE, fontFamily: '"Inter Tight",sans-serif' }}>2 Collaborating</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <div style={{ display: 'flex' }}>
            <img src="https://i.pravatar.cc/80?img=47" alt="" style={{ width: 54, height: 54, borderRadius: '50%', objectFit: 'cover', outline: `2px solid ${GRAPHITE}` }}/>
            <img src="https://i.pravatar.cc/80?img=12" alt="" style={{ width: 54, height: 54, borderRadius: '50%', objectFit: 'cover', marginLeft: -15, outline: `2px solid ${GRAPHITE}` }}/>
          </div>
          <div style={{ marginLeft: 'auto' }}><MatchRing pct={92}/></div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 6, marginBottom: 18 }}>
          {[['RELAXED','Pace'],['MID-RANGE','Budget'],['COUPLE','Style']].map(([v,l]) => (
            <div key={l} style={{ borderRadius: 8, padding: '9px 6px', textAlign: 'center', background: 'rgba(212,182,134,0.04)', border: `1px solid ${HAIRLINE}` }}>
              <p style={{ color: BONE, fontWeight: 600, fontSize: 8, letterSpacing: '0.06em', fontFamily: '"Inter Tight",sans-serif' }}>{v}</p>
              <p style={{ fontSize: 9, marginTop: 3, color: MUTE, fontFamily: '"Inter Tight",sans-serif' }}>{l}</p>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 14, borderTop: `1px solid ${HAIRLINE}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <div className="live-dot" style={{ background: GOLD, boxShadow: `0 0 6px rgba(212,182,134,0.55)` }}/>
            <span style={{ fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTE, fontFamily: '"Inter Tight",sans-serif' }}>Syncing Live</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
            {[3,6,10,4,9,5,8,3,7,11,4,6].map((h,i) => (
              <div key={i} style={{ width: 2, height: h, borderRadius: 1, background: GOLD, opacity: 0.28 }}/>
            ))}
          </div>
        </div>
      </div>
    </LuxCard>
  )
}

function ProductShowcase() {
  return (
    <section style={{ position: 'relative', zIndex: 10, padding: '80px 64px' }}>
      <div style={{
        position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
        width: 900, height: 500, borderRadius: '50%',
        background: 'radial-gradient(ellipse, rgba(212,182,134,0.04) 0%, transparent 70%)',
        pointerEvents: 'none',
      }}/>
      <div style={{ maxWidth: 1100, margin: '0 auto', position: 'relative' }}>
        <motion.p initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 1.1, ease }}
          style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 'clamp(36px, 4.5vw, 60px)', lineHeight: 1.1, color: BONE, textAlign: 'center', marginBottom: 72 }}>
          Everything, in sync.
        </motion.p>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', gap: 28 }}>
          <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 1, delay: 0.1, ease }}>
            <motion.div animate={{ y: [0,-12,0] }} transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}>
              <ItineraryCard/>
            </motion.div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 1, delay: 0.22, ease }}
            style={{ marginTop: 80 }}>
            <motion.div animate={{ y: [0,-12,0] }} transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut', delay: 2.8 }}>
              <MatchCard/>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

// ── Marquee ───────────────────────────────────────────────────────────────────

const DESTINATIONS = ['KYOTO', 'AMALFI COAST', 'PATAGONIA', 'MARRAKECH', 'SANTORINI', 'MALDIVES', 'CAPPADOCIA', 'QUEENSTOWN', 'LOFOTEN', 'RAJASTHAN', 'LAKE COMO', 'ICELAND']

function Marquee() {
  const items = [...DESTINATIONS, ...DESTINATIONS]
  return (
    <div style={{ position: 'relative', zIndex: 10, overflow: 'hidden', padding: '20px 0', borderTop: `1px solid ${HAIRLINE}`, borderBottom: `1px solid ${HAIRLINE}` }}>
      <div style={{ display: 'flex', width: 'max-content', animation: 'marqueeScroll 48s linear infinite' }}>
        {items.map((d, i) => (
          <span key={i} style={{ display: 'inline-flex', alignItems: 'center' }}>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.40em', textTransform: 'uppercase', fontWeight: 300, color: 'rgba(244,237,224,0.18)', padding: '0 44px' }}>
              {d}
            </span>
            <span style={{ color: GOLD, opacity: 0.18, fontSize: 10 }}>·</span>
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Features ──────────────────────────────────────────────────────────────────

const features = [
  { n: '01', title: 'Your itinerary, perfected.',   desc: 'Day-by-day plans shaped to your pace, your budget, and your version of a good day.' },
  { n: '02', title: 'Matched to the right people.', desc: 'Companions selected by how you move, what you value, and the kind of trip you want to have.' },
  { n: '03', title: 'Plans that evolve together.',  desc: 'Every decision lands in real time — across everyone, always.' },
  { n: '04', title: 'A record of everything.',      desc: 'The places, the moments, the notes. Kept privately, beautifully, long after you\'re home.' },
]

function Features() {
  return (
    <section style={{ position: 'relative', zIndex: 10, padding: '0 64px 80px' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        {features.map((f, i) => (
          <motion.div key={f.n}
            initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.9, delay: i * 0.08, ease }}>
            <div style={{
              display: 'grid', gridTemplateColumns: '80px 1fr 1fr',
              gap: '0 56px', alignItems: 'center',
              padding: '36px 0',
              borderBottom: `1px solid ${HAIRLINE}`,
              borderTop: i === 0 ? `1px solid ${HAIRLINE}` : 'none',
            }}>
              <span style={{
                fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400,
                fontSize: 64, lineHeight: 1,
                background: GOLD_GRAD, WebkitBackgroundClip: 'text',
                backgroundClip: 'text', color: 'transparent',
                opacity: 0.28, letterSpacing: '-0.03em', display: 'block',
              }}>
                {f.n}
              </span>
              <h3 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 28, lineHeight: 1.2, color: BONE, margin: 0 }}>
                {f.title}
              </h3>
              <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, lineHeight: 1.80, color: MUTE, margin: 0 }}>
                {f.desc}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  )
}

// ── CTA ───────────────────────────────────────────────────────────────────────

function CTA() {
  return (
    <section style={{ position: 'relative', zIndex: 10, padding: '80px 64px 100px', textAlign: 'center', borderTop: `1px solid ${HAIRLINE}` }}>
      <div style={{
        position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
        width: 800, height: 500, borderRadius: '50%',
        background: 'radial-gradient(ellipse, rgba(212,182,134,0.07) 0%, transparent 65%)',
        pointerEvents: 'none',
      }}/>
      <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }} transition={{ duration: 1.2, ease }}
        style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>

        <h2 style={{
          fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
          fontSize: 'clamp(40px, 5.5vw, 76px)', lineHeight: 1.06,
          letterSpacing: '-0.02em', color: BONE, marginBottom: 16,
        }}>
          Where will you go next?
        </h2>

        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 14, lineHeight: 1.8, color: MUTE, maxWidth: 340, marginBottom: 36 }}>
          A curated few are granted access each season.
        </p>

        <div style={{ display: 'flex', maxWidth: 480, width: '100%' }}>
          <input type="email" placeholder="your@email.com" style={{
            flex: 1, padding: '15px 20px',
            background: 'rgba(232,212,168,0.04)',
            border: `1px solid rgba(232,212,168,0.18)`, borderRight: 'none',
            borderRadius: '5px 0 0 5px', color: BONE,
            fontFamily: '"Inter Tight",sans-serif', fontSize: 13, outline: 'none',
          }}/>
          <button style={{
            padding: '15px 26px', background: GOLD, color: BG, border: 'none',
            borderRadius: '0 5px 5px 0',
            fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
            letterSpacing: '0.20em', textTransform: 'uppercase', fontWeight: 500,
            cursor: 'pointer', whiteSpace: 'nowrap',
          }}>
            Request Access
          </button>
        </div>

        <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: DIM, marginTop: 16 }}>
          By invitation only &nbsp;·&nbsp; No spam, ever
        </p>
      </motion.div>
    </section>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

const NAV_LINKS = ['How It Works', 'Destinations', 'For Groups']

export default function Welcome() {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: BG, color: BONE, overflowX: 'hidden' }}>

      <GrainOverlay/>
      <ParticleCanvas/>

      {/* Nav */}
      <nav style={{
        position: 'relative', zIndex: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '20px 64px', borderBottom: `1px solid ${HAIRLINE}`,
        backdropFilter: 'blur(16px)', background: 'rgba(8,8,7,0.50)',
      }}>
        <SonderNav3D markSize={48}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 44 }}>
          {NAV_LINKS.map(l => (
            <button key={l}
              style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, background: 'none', border: 'none', cursor: 'pointer', transition: 'color 0.25s' }}
              onMouseEnter={e => e.currentTarget.style.color = BONE}
              onMouseLeave={e => e.currentTarget.style.color = MUTE}>
              {l}
            </button>
          ))}
        </div>
        <button
          style={{ fontFamily: '"Inter Tight",sans-serif', display: 'flex', alignItems: 'center', gap: 8, padding: '11px 26px', borderRadius: 5, fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', fontWeight: 500, border: `1px solid rgba(212,182,134,0.45)`, color: GOLD, background: 'none', cursor: 'pointer', transition: 'all 0.25s' }}
          onMouseEnter={e => { e.currentTarget.style.background = GOLD; e.currentTarget.style.color = BG }}
          onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = GOLD }}>
          Join Sonder <ChevronRight size={11}/>
        </button>
      </nav>

      {/* Hero */}
      <section style={{
        position: 'relative', zIndex: 10,
        minHeight: 'calc(100vh - 81px)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '40px 64px 60px', textAlign: 'center',
      }}>
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background: 'radial-gradient(ellipse 70% 65% at 50% 48%, rgba(10,9,8,0.94) 0%, transparent 100%)' }}/>
        <div style={{ position: 'absolute', top: '26%', left: '50%', transform: 'translateX(-50%)', width: 800, height: 560, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(212,182,134,0.12) 0%, transparent 65%)', pointerEvents: 'none' }}/>

        <motion.div variants={stagger} initial="hidden" animate="show"
          style={{ position: 'relative', zIndex: 1, maxWidth: 860 }}>

          <motion.p variants={reveal} style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.40em', textTransform: 'uppercase', color: GOLD, opacity: 0.75, marginBottom: 32 }}>
            Private Travel Intelligence
          </motion.p>

          <motion.h1 variants={reveal} style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontSize: 'clamp(52px, 7.5vw, 108px)', lineHeight: 1.02, letterSpacing: '-0.025em', color: BONE, margin: '0 0 4px' }}>
            Plan together.
          </motion.h1>
          <motion.h1 variants={reveal} style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 'clamp(52px, 7.5vw, 108px)', lineHeight: 1.02, letterSpacing: '-0.025em', background: GOLD_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', display: 'block', marginBottom: 32 }}>
            Travel better.
          </motion.h1>

          <motion.p variants={reveal} style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 15, lineHeight: 1.88, color: MUTE, maxWidth: 340, margin: '0 auto 40px' }}>
            The private intelligence layer for people who know exactly where they want to go.
          </motion.p>

          <motion.div variants={reveal}>
            <button
              style={{ fontFamily: '"Inter Tight",sans-serif', display: 'inline-flex', alignItems: 'center', gap: 12, padding: '17px 44px', borderRadius: 6, background: GOLD, color: BG, border: 'none', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500, cursor: 'pointer', boxShadow: '0 0 60px rgba(212,182,134,0.26), 0 0 120px rgba(212,182,134,0.09)', transition: 'transform 0.28s, box-shadow 0.28s' }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 0 80px rgba(212,182,134,0.38),0 0 140px rgba(212,182,134,0.13)' }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 0 60px rgba(212,182,134,0.26),0 0 120px rgba(212,182,134,0.09)' }}>
              Begin Your Journey <ChevronRight size={14}/>
            </button>
          </motion.div>
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 2.8, duration: 1.2 }}
          style={{ position: 'absolute', bottom: 36, left: '50%', transform: 'translateX(-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.30em', textTransform: 'uppercase', color: DIM }}>Scroll</span>
          <motion.div animate={{ scaleY: [1, 1.7, 1], opacity: [0.3, 0.8, 0.3] }} transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
            style={{ width: 1, height: 28, background: `linear-gradient(to bottom,${GOLD},transparent)`, transformOrigin: 'top' }}/>
        </motion.div>
      </section>

      {/* Marquee */}
      <Marquee/>

      {/* Product showcase */}
      <ProductShowcase/>

      {/* Features */}
      <Features/>

      {/* CTA */}
      <CTA/>

      {/* Footer */}
      <footer style={{ position: 'relative', zIndex: 10, padding: '24px 64px', borderTop: `1px solid ${HAIRLINE}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(8,8,7,0.7)', backdropFilter: 'blur(16px)' }}>
        <SonderNav3D markSize={32}/>
        <span style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 10, letterSpacing: '0.18em', color: DIM }}>
          © 2025 Sonder
        </span>
      </footer>

    </div>
  )
}
