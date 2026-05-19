import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Check, Globe, Lock, Trash2 } from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import { SonderNav3D } from '../components/SonderMark3D'
import { useAuth } from '../hooks/useAuth'
import {
  listTripJournal, upsertJournalEntry, deleteJournalEntry, getCurrentItinerary,
} from '../lib/api'

const spring = { type: 'spring', stiffness: 260, damping: 22 }

function _fmt(v) {
  if (!v) return ''
  try {
    const d = new Date(v)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch { return '' }
}

function _fmtRel(iso) {
  if (!iso) return ''
  try {
    const t = new Date(iso).getTime()
    if (isNaN(t)) return ''
    const diff = Date.now() - t
    const m = Math.floor(diff / 60000)
    if (m < 1) return 'just now'
    if (m < 60) return `${m} min${m === 1 ? '' : 's'} ago`
    const h = Math.floor(m / 60)
    if (h < 24) return `${h} hr${h === 1 ? '' : 's'} ago`
    const d = Math.floor(h / 24)
    if (d < 7) return `${d} day${d === 1 ? '' : 's'} ago`
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch { return '' }
}

export default function Journal() {
  const navigate = useNavigate()
  const { itineraryId } = useParams()
  const { user, loading: authLoading } = useAuth()

  const [itinerary, setItinerary] = useState(null)
  const [entries, setEntries]     = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)

  const [text, setText]           = useState('')
  const [dayNumber, setDayNumber] = useState(null)
  const [isPublic, setIsPublic]   = useState(false)
  const [saving, setSaving]       = useState(false)

  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/signin'); return }
    if (!itineraryId) { navigate('/dashboard'); return }

    let cancelled = false
    ;(async () => {
      try {
        // We don't have a 'get itinerary by id' route yet, so we pull
        // current (the most common case) and verify the id matches.
        // If not — show a slim header from the entries list.
        const [it, j] = await Promise.all([
          getCurrentItinerary().catch(() => null),
          listTripJournal(itineraryId),
        ])
        if (cancelled) return
        if (it?.itinerary?.itinerary_id === itineraryId) {
          setItinerary(it.itinerary)
        }
        setEntries(Array.isArray(j?.entries) ? j.entries : [])
      } catch (err) {
        if (cancelled) return
        setError(err?.message || 'Could not load journal')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [authLoading, user?.uid, itineraryId, navigate])

  const days = itinerary?.days || []
  const liveEntries = useMemo(() => (entries || []).filter(e => !e.deleted_at), [entries])

  async function handlePost() {
    if (saving) return
    const trimmed = text.trim()
    if (!trimmed) return
    setSaving(true)
    try {
      const res = await upsertJournalEntry(itineraryId, {
        text: trimmed,
        day_number: dayNumber,
        is_public: isPublic,
        photos: [],
      })
      const fresh = res?.entry
      if (fresh) setEntries(prev => [...prev.filter(e => e.entry_id !== fresh.entry_id), fresh])
      setText('')
      setDayNumber(null)
      // Keep isPublic sticky — users often share several at once.
    } catch (err) {
      setError(err?.message || 'Could not save entry')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(entryId) {
    if (!entryId) return
    try {
      await deleteJournalEntry(entryId)
      setEntries(prev => prev.map(e => e.entry_id === entryId ? { ...e, deleted_at: new Date().toISOString() } : e))
    } catch (err) {
      console.warn('delete failed:', err)
    }
  }

  const headerCity = itinerary?.destination?.city || (liveEntries[0]?.city) || 'Your trip'
  const headerCountry = itinerary?.destination?.country || (liveEntries[0]?.country) || ''

  return (
    <div style={{ minHeight: '100vh', background: BG, color: BONE, display: 'flex', flexDirection: 'column' }}>
      <nav style={{ position: 'sticky', top: 0, zIndex: 50, borderBottom: `1px solid ${HAIRLINE}`, background: 'rgba(10,8,5,0.88)', backdropFilter: 'blur(24px)', padding: '0 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/dashboard')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTE, padding: 0, lineHeight: 0, display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <ArrowLeft size={16}/>
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>Dashboard</span>
        </motion.button>
        <SonderNav3D markSize={28}/>
        <div style={{ width: 100 }}/>
      </nav>

      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, background: 'radial-gradient(ellipse 85% 75% at 50% 45%, rgba(212,182,134,0.07) 0%, transparent 70%)' }}/>

      <main style={{ flex: 1, position: 'relative', zIndex: 1, padding: '44px 24px 96px', maxWidth: 760, width: '100%', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.30em', textTransform: 'uppercase', color: MUTE, marginBottom: 10 }}>
            Travel journal
          </p>
          <h1 style={{ fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic', fontSize: 'clamp(36px, 4.8vw, 52px)', color: BONE, margin: 0, lineHeight: 1.05, letterSpacing: '-0.01em' }}>
            {headerCity}{headerCountry ? `, ${headerCountry}` : ''}
          </h1>
        </div>

        {/* Composer */}
        <div style={{ background: 'rgba(232,212,168,0.03)', border: `1px solid ${HAIRLINE}`, borderRadius: 14, padding: '18px 18px 14px', marginBottom: 36 }}>
          <textarea
            value={text}
            onChange={e => setText(e.target.value.slice(0, 1200))}
            placeholder="What stayed with you?"
            rows={3}
            style={{
              width: '100%', boxSizing: 'border-box',
              background: 'transparent', border: 'none', outline: 'none',
              color: BONE, resize: 'none',
              fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
              fontSize: 17, lineHeight: 1.55, letterSpacing: '0.005em',
            }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10, flexWrap: 'wrap' }}>
            {/* Day picker */}
            {days.length > 0 && (
              <select
                value={dayNumber ?? ''}
                onChange={e => setDayNumber(e.target.value ? Number(e.target.value) : null)}
                style={{
                  background: 'rgba(232,212,168,0.05)', border: `1px solid ${HAIRLINE}`,
                  borderRadius: 18, padding: '6px 12px',
                  color: MUTE, fontFamily: '"Inter Tight",sans-serif',
                  fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', outline: 'none',
                }}
              >
                <option value="">Whole trip</option>
                {days.map(d => (
                  <option key={d.day_number} value={d.day_number}>
                    Day {d.day_number}{d.theme ? ` — ${d.theme}` : ''}
                  </option>
                ))}
              </select>
            )}

            {/* Visibility toggle */}
            <motion.button
              whileTap={{ scale: 0.96 }}
              onClick={() => setIsPublic(p => !p)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: isPublic ? 'rgba(212,182,134,0.10)' : 'rgba(232,212,168,0.03)',
                border: `1px solid ${isPublic ? 'rgba(212,182,134,0.40)' : HAIRLINE}`,
                borderRadius: 18, padding: '6px 12px', cursor: 'pointer',
              }}
            >
              {isPublic ? <Globe size={10} style={{ color: GOLD }}/> : <Lock size={10} style={{ color: MUTE }}/>}
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: isPublic ? GOLD : MUTE }}>
                {isPublic ? 'Public to ' + headerCity : 'Private'}
              </span>
            </motion.button>

            <div style={{ flex: 1, textAlign: 'right' }}>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM, marginRight: 12 }}>
                {text.length} / 1200
              </span>
              <motion.button
                whileHover={text.trim() && !saving ? { scale: 1.03 } : {}}
                whileTap={text.trim() && !saving ? { scale: 0.97 } : {}}
                onClick={handlePost}
                disabled={!text.trim() || saving}
                style={{
                  background: text.trim() ? `linear-gradient(135deg, ${GOLD} 0%, #B89464 100%)` : 'rgba(212,182,134,0.10)',
                  border: 'none', borderRadius: 10,
                  padding: '8px 18px',
                  cursor: text.trim() && !saving ? 'pointer' : 'not-allowed',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                  letterSpacing: '0.22em', textTransform: 'uppercase', fontWeight: 500,
                  color: text.trim() ? '#0a0807' : MUTE,
                }}
              >
                {saving ? 'Saving…' : 'Note it down'}
              </motion.button>
            </div>
          </div>
        </div>

        {/* Entries */}
        {loading && (
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE, textAlign: 'center' }}>
            Loading…
          </p>
        )}
        {error && (
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: '#E89B7C', textAlign: 'center' }}>{error}</p>
        )}
        {!loading && liveEntries.length === 0 && (
          <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 17, color: MUTE, textAlign: 'center', marginTop: 24 }}>
            Nothing here yet. Write the first thing you remember.
          </p>
        )}

        <AnimatePresence initial={false}>
          {liveEntries.map(e => (
            <motion.div
              key={e.entry_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.4, ease }}
              style={{
                padding: '20px 18px',
                background: 'rgba(232,212,168,0.025)',
                border: `1px solid ${HAIRLINE}`,
                borderRadius: 12, marginBottom: 14, position: 'relative',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {e.day_number && (
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.22em', textTransform: 'uppercase', color: GOLD }}>
                      Day {e.day_number}
                    </span>
                  )}
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: MUTE }}>
                    {_fmtRel(e.updated_at || e.created_at)}
                  </span>
                  {e.is_public && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      <Globe size={9} style={{ color: GOLD }}/>
                      <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: GOLD }}>
                        Public
                      </span>
                    </span>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(e.entry_id)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
                  title="Delete"
                >
                  <Trash2 size={11} style={{ color: DIM }}/>
                </button>
              </div>
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 16, color: BONE, lineHeight: 1.5, margin: 0, whiteSpace: 'pre-wrap' }}>
                {e.text}
              </p>
            </motion.div>
          ))}
        </AnimatePresence>
      </main>
    </div>
  )
}
