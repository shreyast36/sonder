import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Globe } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import { useAuth } from '../hooks/useAuth'
import { getDestinationFeed } from '../lib/api'
import { useDestinationPhoto } from '../lib/destinationPhoto'

function _fmtRel(iso) {
  if (!iso) return ''
  try {
    const t = new Date(iso).getTime()
    if (isNaN(t)) return ''
    const diff = Date.now() - t
    const days = Math.floor(diff / 86400000)
    if (days < 1) return 'today'
    if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`
    if (days < 30) return `${Math.floor(days / 7)}w ago`
    if (days < 365) return `${Math.floor(days / 30)}mo ago`
    return `${Math.floor(days / 365)}y ago`
  } catch { return '' }
}

export default function Destination() {
  const navigate = useNavigate()
  const { city }    = useParams()
  const [search]    = useSearchParams()
  const country     = search.get('country') || ''
  const { user, loading: authLoading } = useAuth()

  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  const photo = useDestinationPhoto(city, country)

  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/signin'); return }
    if (!city) { navigate('/dashboard'); return }
    let cancelled = false
    ;(async () => {
      try {
        const res = await getDestinationFeed(city, country || null)
        if (cancelled) return
        setEntries(Array.isArray(res?.entries) ? res.entries : [])
      } catch (err) {
        if (cancelled) return
        setError(err?.message || 'Could not load destination notes')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [authLoading, user?.uid, city, country, navigate])

  const decoded = useMemo(() => city ? decodeURIComponent(city) : '', [city])

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', padding: '0 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => navigate(-1)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <ArrowLeft size={16}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Back</span>
        </motion.button>
        <SonderNav3D markSize={28}/>
        <div style={{ width: 80 }}/>
      </nav>

      {/* Hero */}
      <div style={{ position: 'relative', height: 320, overflow: 'hidden', borderBottom: `1px solid ${HAIRLINE}` }}>
        {photo && (
          <img src={photo} alt={decoded} referrerPolicy="no-referrer"
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', filter: 'saturate(0.85) brightness(0.55)' }}/>
        )}
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(8,8,7,0.20) 0%, rgba(8,8,7,0.55) 60%, rgba(8,8,7,0.95) 100%)' }}/>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', padding: '0 32px 36px', maxWidth: 980, margin: '0 auto' }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.36em', textTransform: 'uppercase', color: GOLD, margin: 0 }}>
            Trip notes from Sonder
          </p>
          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontWeight: 400, fontSize: 'clamp(48px, 6vw, 72px)', color: BONE, margin: '8px 0 0', lineHeight: 1, letterSpacing: '-0.02em' }}>
            {decoded}{country ? `, ${country}` : ''}
          </h1>
        </div>
      </div>

      <main style={{ flex: 1, padding: '40px 24px 96px', maxWidth: 920, width: '100%', margin: '0 auto' }}>
        {loading && (
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, textAlign: 'center' }}>
            Loading…
          </p>
        )}
        {error && (
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: '#E89B7C', textAlign: 'center' }}>{error}</p>
        )}
        {!loading && entries.length === 0 && (
          <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 18, color: MUTE, textAlign: 'center', marginTop: 36 }}>
            No public notes from this destination yet. Be the first.
          </p>
        )}

        <AnimatePresence initial={false}>
          {entries.map((e, i) => (
            <motion.article
              key={e.entry_id || i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.04 + i * 0.05, ease }}
              style={{
                padding: '22px 22px',
                background: 'rgba(232,212,168,0.025)',
                border: `1px solid ${HAIRLINE}`,
                borderRadius: 14, marginBottom: 16,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <img
                  src={e.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(e.display_name || 'A')}`}
                  alt={e.display_name || 'Anonymous'}
                  referrerPolicy="no-referrer"
                  style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover', border: `1px solid ${HAIRLINE}` }}
                />
                <div style={{ flex: 1 }}>
                  <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 15, color: BONE, margin: 0 }}>
                    {e.display_name || 'A Sonder traveller'}
                  </p>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: DIM, margin: '2px 0 0' }}>
                    {_fmtRel(e.updated_at || e.created_at)}{e.day_number ? ` · Day ${e.day_number}` : ''}
                  </p>
                </div>
                <Globe size={11} style={{ color: GOLD, opacity: 0.7 }}/>
              </div>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 17, color: `${BONE}e8`, lineHeight: 1.55, margin: 0, whiteSpace: 'pre-wrap' }}>
                {e.text}
              </p>
            </motion.article>
          ))}
        </AnimatePresence>
      </main>
    </div>
  )
}
