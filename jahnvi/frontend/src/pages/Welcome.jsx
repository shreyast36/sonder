import { motion } from 'framer-motion'
import {
  MapPin, Users, ChevronRight, Lock, CreditCard, Sparkles,
  MessageCircle, Heart, Landmark, Utensils, Sun,
} from 'lucide-react'
import { SonderMark } from '../components/SonderLogo'

// ── Design tokens ─────────────────────────────────────────────────────────────

const GOLD    = '#D8B77A'
const GOLDHI  = '#EDD59A'
const VIOLET  = '#8B5CF6'
const IVORY   = '#F5F1E8'
const MUTED   = '#9C968E'
const SURFACE = 'rgba(15,15,18,0.92)'
const BG      = '#040404'

// ── Motion variants ───────────────────────────────────────────────────────────

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.65, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { show: { transition: { staggerChildren: 0.11 } } }

// ── Gradient-border card wrapper ──────────────────────────────────────────────

function LuxCard({ children, style }) {
  return (
    <motion.div
      whileHover={{ y: -4, transition: { duration: 0.22, ease: 'easeOut' } }}
      style={{
        padding: 1,
        borderRadius: 18,
        background: 'linear-gradient(135deg, rgba(216,183,122,0.38) 0%, rgba(15,15,18,0) 48%, rgba(139,92,246,0.28) 100%)',
        ...style,
      }}
    >
      <div style={{ background: SURFACE, borderRadius: 17, height: '100%' }}>
        {children}
      </div>
    </motion.div>
  )
}

// ── Match ring ────────────────────────────────────────────────────────────────

function MatchRing({ pct = 92 }) {
  const r = 28
  const c = 2 * Math.PI * r
  const offset = c - (pct / 100) * c
  return (
    <div style={{ position: 'relative', width: 72, height: 72, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', transform: 'rotate(-90deg)' }}
        viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="3"/>
        <circle cx="36" cy="36" r={r} fill="none" stroke={GOLD} strokeWidth="3"
          strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"/>
      </svg>
      <div style={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <p style={{ color: IVORY, fontWeight: 700, fontSize: 13, lineHeight: 1 }}>{pct}%</p>
        <p style={{ fontSize: 9, letterSpacing: '0.12em', color: MUTED, marginTop: 3 }}>MATCH</p>
      </div>
    </div>
  )
}

// ── Itinerary card ────────────────────────────────────────────────────────────

function ItineraryCard() {
  const rows = [
    { time: '9:00 AM',  name: 'Uluwatu Temple',   cat: 'Culture', Icon: Landmark },
    { time: '1:00 PM',  name: 'Jimbaran Seafood', cat: 'Dining',  Icon: Utensils },
    { time: '6:00 PM',  name: 'Seminyak Sunset',  cat: 'Nature',  Icon: Sun      },
  ]
  return (
    <LuxCard style={{ width: 358 }}>
      <div style={{ padding: '22px 22px 18px' }}>

        <div style={{ fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTED, marginBottom: 18 }}>
          Your Upcoming Trip
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <MapPin size={13} style={{ color: GOLD }}/>
            <span style={{ color: IVORY, fontWeight: 500, fontSize: 14 }}>Bali, Indonesia</span>
          </div>
          <span style={{ fontSize: 11, color: MUTED }}>Day 1 of 7</span>
        </div>

        <div>
          {rows.map((row, i) => (
            <div key={row.name} style={{ display: 'flex', gap: 10 }}>
              <span style={{ fontSize: 10, width: 54, flexShrink: 0, paddingTop: 6, color: MUTED }}>
                {row.time}
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: GOLD, marginTop: 8, flexShrink: 0 }}/>
                {i < rows.length - 1 && (
                  <div style={{ width: 1, flex: 1, marginTop: 4, background: 'rgba(255,255,255,0.07)', minHeight: 28 }}/>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, paddingBottom: 16 }}>
                <div style={{
                  width: 34, height: 34, borderRadius: 10, flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
                }}>
                  <row.Icon size={14} style={{ color: MUTED }}/>
                </div>
                <div>
                  <p style={{ color: IVORY, fontSize: 13, fontWeight: 500, lineHeight: 1.25 }}>{row.name}</p>
                  <p style={{ fontSize: 11, marginTop: 3, color: MUTED }}>{row.cat}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.06)',
        }}>
          <span style={{ fontSize: 11, color: MUTED }}>Est. daily spend</span>
          <span style={{ color: IVORY, fontSize: 13, fontWeight: 500 }}>$85 – $120</span>
        </div>
      </div>
    </LuxCard>
  )
}

// ── Match card ────────────────────────────────────────────────────────────────

function MatchCard() {
  return (
    <LuxCard style={{ width: 290 }}>
      <div style={{ padding: '22px 20px 18px' }}>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
          <Users size={12} style={{ color: GOLD }}/>
          <span style={{ fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase', color: MUTED }}>
            2 Collaborating
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
          <div style={{ display: 'flex' }}>
            <img src="https://i.pravatar.cc/80?img=47" alt=""
              style={{ width: 60, height: 60, borderRadius: '50%', objectFit: 'cover', outline: '2px solid rgba(15,15,18,0.9)' }}/>
            <img src="https://i.pravatar.cc/80?img=12" alt=""
              style={{ width: 60, height: 60, borderRadius: '50%', objectFit: 'cover', marginLeft: -18, outline: '2px solid rgba(15,15,18,0.9)' }}/>
          </div>
          <div style={{ marginLeft: 'auto' }}>
            <MatchRing pct={92}/>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 16 }}>
          {[['RELAXED','Pace'],['MID-RANGE','Budget'],['COUPLE','Style']].map(([val, label]) => (
            <div key={label} style={{
              borderRadius: 10, padding: '9px 6px', textAlign: 'center',
              background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
            }}>
              <p style={{ color: IVORY, fontWeight: 600, fontSize: 9, letterSpacing: '0.06em', lineHeight: 1 }}>{val}</p>
              <p style={{ fontSize: 9, marginTop: 3, color: MUTED }}>{label}</p>
            </div>
          ))}
        </div>

        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.06)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="live-dot"/>
            <span style={{ fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: MUTED }}>
              Syncing Live
            </span>
          </div>
          <svg width="36" height="14" viewBox="0 0 36 14">
            {[3,6,10,4,9,5,8,3,7,11,4,6,9,3,5].map((h, i) => (
              <rect key={i} x={i * 2.3} y={(14 - h) / 2} width="1.4" height={h}
                rx="0.7" fill={VIOLET} opacity="0.45"/>
            ))}
          </svg>
        </div>
      </div>
    </LuxCard>
  )
}

// ── Feature cards data ────────────────────────────────────────────────────────

const features = [
  {
    Icon: Sparkles,
    title: 'AI Itinerary',
    desc:  'Personalized day-by-day plans crafted to your pace, preferences, and budget.',
  },
  {
    Icon: Users,
    title: 'Co-Traveller Match',
    desc:  'Connected with like-minded travelers by personality, interests, and travel style.',
  },
  {
    Icon: MessageCircle,
    title: 'Live Collaboration',
    desc:  'Chat, plan, and vote together. Every change syncs instantly for the whole group.',
  },
  {
    Icon: Heart,
    title: 'Shared Memories',
    desc:  'Capture moments, add notes, and build a trip story that lives in one private place.',
  },
]

const BRANDS    = ['AMAN', 'FOUR SEASONS', 'ROSEWOOD', 'EQUINOX', 'TUMI']
const NAV_LINKS = ['How It Works', 'Destinations', 'For Groups', 'Pricing']

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Welcome() {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: BG, color: IVORY, overflowX: 'hidden' }}>

      {/* ── Background ─────────────────────────────────────────────────── */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', overflow: 'hidden', zIndex: 0 }}>

        {/* contour texture — fine diagonal lines at 3% opacity */}
        <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.03 }}
          xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="contour" x="0" y="0" width="56" height="56"
              patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
              <line x1="0" y1="0" x2="0" y2="56" stroke="white" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#contour)"/>
        </svg>

        {/* faint architectural plane — upper diagonal */}
        <div style={{
          position: 'absolute', left: '-15%', top: '-5%',
          width: '85%', height: '65%',
          background: 'linear-gradient(148deg, transparent 0%, rgba(255,255,255,0.011) 42%, transparent 78%)',
          transform: 'rotate(-7deg)',
        }}/>

        {/* violet ambient glow — upper left */}
        <div style={{
          position: 'absolute', left: -120, top: -120,
          width: 640, height: 640,
          background: 'radial-gradient(circle, rgba(139,92,246,0.07) 0%, transparent 68%)',
          filter: 'blur(40px)',
        }}/>

        {/* gold edge reflection — bottom right */}
        <div style={{
          position: 'absolute', right: -80, bottom: -60,
          width: 560, height: 420,
          background: 'radial-gradient(ellipse at 80% 80%, rgba(216,183,122,0.1) 0%, transparent 62%)',
          filter: 'blur(50px)',
        }}/>
      </div>

      {/* ── Navbar ─────────────────────────────────────────────────────── */}
      <nav style={{
        position: 'relative', zIndex: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '20px 56px',
        borderBottom: '1px solid rgba(255,255,255,0.055)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <SonderMark size={26} uid="nav"/>
          <span style={{ fontFamily: 'Inter', fontWeight: 300, fontSize: '1rem', letterSpacing: '0.2em', color: IVORY }}>
            sonder
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 38 }}>
          {NAV_LINKS.map(l => (
            <button key={l}
              style={{ fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase', color: MUTED, background: 'none', border: 'none', cursor: 'pointer' }}
              onMouseEnter={e => e.currentTarget.style.color = IVORY}
              onMouseLeave={e => e.currentTarget.style.color = MUTED}>
              {l}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <button style={{ fontSize: 11, letterSpacing: '0.14em', textTransform: 'uppercase', color: MUTED, background: 'none', border: 'none', cursor: 'pointer' }}>
            Log In
          </button>
          <button
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '9px 20px', borderRadius: 8, fontSize: 11,
              letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 500,
              border: `1px solid ${GOLD}`, color: GOLD, background: 'none', cursor: 'pointer',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = GOLD; e.currentTarget.style.color = '#0a0a0a' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = GOLD }}>
            Join Sonder
            <ChevronRight size={12}/>
          </button>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <section style={{ position: 'relative', zIndex: 10, padding: '84px 56px 68px' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', display: 'flex', alignItems: 'flex-start', gap: 72 }}>

          {/* left copy */}
          <motion.div style={{ flex: 1, maxWidth: 500 }} variants={stagger} initial="hidden" animate="show">

            <motion.p variants={fadeUp} style={{
              fontSize: 10, letterSpacing: '0.3em', textTransform: 'uppercase',
              color: GOLD, marginBottom: 28,
            }}>
              Private Travel Operating System
            </motion.p>

            <motion.h1 variants={fadeUp} style={{
              fontFamily: '"Playfair Display", Georgia, serif',
              fontWeight: 800,
              fontSize: 'clamp(50px, 5.5vw, 74px)',
              lineHeight: 1.04,
              letterSpacing: '-0.02em',
              color: IVORY,
              marginBottom: 10,
            }}>
              Plan together.<br/>
              <span style={{
                background: `linear-gradient(135deg, ${GOLDHI} 0%, ${GOLD} 55%, #A07828 100%)`,
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}>
                Travel better.
              </span>
            </motion.h1>

            {/* gold rule */}
            <motion.div variants={fadeUp} style={{
              width: 34, height: 1.5, borderRadius: 2, marginBottom: 28, marginTop: 14,
              background: `linear-gradient(to right, ${GOLD}, transparent)`,
            }}/>

            <motion.p variants={fadeUp} style={{
              fontSize: 15, lineHeight: 1.72, color: MUTED, maxWidth: 420, marginBottom: 42,
            }}>
              Sonder is your private travel operating system. We handle the details, match the right people, and keep everything in sync — in real time.
            </motion.p>

            {/* CTAs */}
            <motion.div variants={fadeUp} style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 38 }}>
              <button style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '14px 28px', borderRadius: 8,
                background: GOLD, color: '#060606', border: 'none',
                fontSize: 12, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 600,
                cursor: 'pointer',
                boxShadow: `0 0 28px rgba(216,183,122,0.18), 0 0 56px rgba(216,183,122,0.07)`,
              }}>
                Start Planning
                <ChevronRight size={14}/>
              </button>
              <button style={{
                display: 'flex', alignItems: 'center', gap: 12,
                fontSize: 13, color: MUTED, background: 'none', border: 'none', cursor: 'pointer',
              }}>
                <span style={{
                  width: 32, height: 32, borderRadius: '50%',
                  border: '1px solid rgba(255,255,255,0.11)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <span style={{ fontSize: 9, marginLeft: 2 }}>▶</span>
                </span>
                See How It Works
              </button>
            </motion.div>

            {/* trust badges */}
            <motion.div variants={fadeUp} style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
              {[
                [Lock,       'Private & Secure'],
                [CreditCard, 'No Credit Card'],
                [Sparkles,   'Invite Only'],
              ].map(([Icon, label]) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Icon size={11} style={{ color: 'rgba(255,255,255,0.18)' }}/>
                  <span style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.22)' }}>
                    {label}
                  </span>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* right — floating cards */}
          <div style={{ flex: 1, display: 'flex', alignItems: 'flex-start', minHeight: 520 }}>
            {/* itinerary card — floats gently */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              style={{ flexShrink: 0 }}>
              <motion.div
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 5.5, repeat: Infinity, ease: 'easeInOut' }}>
                <ItineraryCard/>
              </motion.div>
            </motion.div>

            {/* match card — offset below, different float phase */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.5 }}
              style={{ flexShrink: 0, marginTop: 96, marginLeft: -28 }}>
              <motion.div
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 5.5, repeat: Infinity, ease: 'easeInOut', delay: 2.4 }}>
                <MatchCard/>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── Trusted By ─────────────────────────────────────────────────── */}
      <section style={{
        position: 'relative', zIndex: 10, padding: '46px 56px',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
      }}>
        <div style={{ maxWidth: 1280, margin: '0 auto' }}>
          <p style={{
            textAlign: 'center', fontSize: 10, letterSpacing: '0.3em',
            textTransform: 'uppercase', color: GOLD, marginBottom: 26,
          }}>
            Trusted By Members Worldwide
          </p>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 56, flexWrap: 'wrap' }}>
            {BRANDS.map(b => (
              <span key={b} style={{
                fontSize: 11, letterSpacing: '0.28em', textTransform: 'uppercase',
                fontWeight: 300, color: 'rgba(255,255,255,0.16)',
              }}>
                {b}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Feature cards ──────────────────────────────────────────────── */}
      <section style={{ position: 'relative', zIndex: 10, padding: '80px 56px' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              whileHover={{ y: -4, transition: { duration: 0.22, ease: 'easeOut' } }}
              viewport={{ once: true }}
              transition={{ duration: 0.55, delay: i * 0.09 }}
              style={{
                padding: 1, borderRadius: 18, cursor: 'pointer',
                background: 'linear-gradient(135deg, rgba(216,183,122,0.18) 0%, rgba(15,15,18,0) 50%, rgba(139,92,246,0.14) 100%)',
              }}>
              <div style={{
                background: SURFACE, borderRadius: 17,
                padding: '24px 22px 20px', height: '100%',
                display: 'flex', flexDirection: 'column',
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 11,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginBottom: 20,
                  background: 'rgba(139,92,246,0.09)', border: '1px solid rgba(139,92,246,0.18)',
                }}>
                  <f.Icon size={17} style={{ color: VIOLET }}/>
                </div>

                <h3 style={{
                  fontSize: 11, fontWeight: 600, letterSpacing: '0.17em',
                  textTransform: 'uppercase', marginBottom: 12, color: IVORY, lineHeight: 1.4,
                }}>
                  {f.title}
                </h3>

                <p style={{ fontSize: 13, lineHeight: 1.72, flex: 1, color: MUTED }}>
                  {f.desc}
                </p>

                <div style={{ marginTop: 20, fontSize: 15, color: 'rgba(255,255,255,0.18)' }}>→</div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer style={{
        position: 'relative', zIndex: 10, padding: '24px 56px',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        fontSize: 11, color: 'rgba(255,255,255,0.18)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <SonderMark size={18} uid="footer"/>
          <span style={{ fontWeight: 300, letterSpacing: '0.18em', color: 'rgba(255,255,255,0.28)' }}>sonder</span>
        </div>
        <span style={{ letterSpacing: '0.1em' }}>Built with care. Designed for wanderers.</span>
      </footer>
    </div>
  )
}
