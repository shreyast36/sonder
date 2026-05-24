import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  MapPin, Users, Send, Loader2, Trash2, MessageCircle,
  Sparkles, Plus, Check, Radio, X,
} from 'lucide-react'
import { BG, BONE, GOLD, MUTE, DIM, HAIRLINE, ease } from '../lib/tokens'
import {
  listOpenTrips, requestToJoin, getTripPreview,
  listFeed, createPost, deletePost as apiDeletePost,
  listComments, addComment,
} from '../lib/api'

const VIOLET = '#8B5CF6'
const ROSE   = '#F43F5E'
const GREEN  = '#10B981'
const AMBER  = '#F59E0B'
const spring = { type: 'spring', stiffness: 280, damping: 22 }

// Hard cap for the live Pulse surfaces (trips + posts). Keeps the
// section scannable and prevents long sessions from accumulating
// hundreds of cards in memory as realtime events fire.
const PULSE_MAX = 10

// ── helpers ──────────────────────────────────────────────────────────────

function timeAgo(iso) {
  if (!iso) return ''
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 30_000)    return 'just now'
  if (ms < 3600_000)  return `${Math.floor(ms / 60_000)}m`
  if (ms < 86400_000) return `${Math.floor(ms / 3600_000)}h`
  return `${Math.floor(ms / 86400_000)}d`
}

function fmtRange(start, end) {
  if (!start && !end) return ''
  try {
    const fmt = d => d ? new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''
    if (start && end) return `${fmt(start)} – ${fmt(end)}`
    return fmt(start || end)
  } catch { return '' }
}

function initials(name) {
  return (name || '?').split(/\s+/).slice(0, 2).map(s => s[0]?.toUpperCase()).join('')
}

// ── Section header ───────────────────────────────────────────────────────

function SectionHeader({ eyebrow, title, accent, right }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 22, gap: 16 }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <motion.span
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
            style={{
              width: 6, height: 6, borderRadius: '50%', background: accent,
              boxShadow: `0 0 10px ${accent}`,
            }}
          />
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
            {eyebrow}
          </p>
        </div>
        <h3 style={{
          fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
          fontSize: 28, color: BONE, lineHeight: 1.05, margin: 0,
        }}>
          {title}
        </h3>
      </div>
      {right}
    </div>
  )
}

// ── Open trip card (compact, luxurious) ──────────────────────────────────

function OpenTripCard({ trip, onRequestJoin }) {
  const isYours = !!trip.is_yours
  const status  = trip.your_request_status
  const where = trip.destination_city
    ? trip.destination_country
      ? `${trip.destination_city}, ${trip.destination_country}`
      : trip.destination_city
    : 'Somewhere new'
  const dateRange = fmtRange(trip.start_date, trip.end_date)
  const accent = isYours ? GOLD : VIOLET

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 14, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.45, ease }}
      whileHover={{ y: -3 }}
      style={{
        padding: 1, borderRadius: 20,
        background: `linear-gradient(145deg, ${accent}55 0%, ${accent}11 22%, rgba(232,212,168,0.04) 50%, rgba(8,8,7,0) 75%, ${accent}33 100%)`,
        boxShadow: `0 16px 40px rgba(0,0,0,0.55), 0 0 0 1px rgba(0,0,0,0.4) inset`,
      }}
    >
      <div style={{
        position: 'relative', overflow: 'hidden',
        background: 'linear-gradient(160deg, rgba(24,19,13,0.99) 0%, rgba(10,9,7,1) 60%, rgba(14,11,8,1) 100%)',
        borderRadius: 19, padding: '22px 24px',
        display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        {/* ambient corner glow */}
        <div style={{
          position: 'absolute', top: -100, right: -100,
          width: 260, height: 260, borderRadius: '50%',
          background: `radial-gradient(circle, ${accent}22 0%, transparent 65%)`,
          pointerEvents: 'none',
        }}/>
        {/* subtle bottom shimmer */}
        <div style={{
          position: 'absolute', bottom: -60, left: -40,
          width: 180, height: 180, borderRadius: '50%',
          background: `radial-gradient(circle, ${accent}10 0%, transparent 70%)`,
          pointerEvents: 'none',
        }}/>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, position: 'relative' }}>
          {/* avatar with rotating halo */}
          <div style={{ position: 'relative', flexShrink: 0, width: 54, height: 54 }}>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
              style={{
                position: 'absolute', inset: -4, borderRadius: '50%',
                background: `conic-gradient(from 0deg, ${accent}88, transparent 30%, ${accent}55 60%, transparent 100%)`,
                filter: 'blur(5px)',
                opacity: 0.75,
              }}
            />
            <div style={{
              position: 'relative',
              width: 54, height: 54, borderRadius: '50%', overflow: 'hidden',
              background: 'linear-gradient(160deg, rgba(212,182,134,0.10) 0%, rgba(20,15,10,1) 100%)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: `1px solid ${accent}66`,
              boxShadow: `0 4px 12px ${accent}33`,
            }}>
              {trip.owner_avatar
                ? <img src={trip.owner_avatar} alt={trip.owner_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
                : <span style={{ fontFamily: '"Cormorant Garamond",serif', fontSize: 22, color: accent, fontStyle: 'italic' }}>
                    {initials(trip.owner_name)}
                  </span>}
            </div>
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{
              fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
              fontSize: 24, color: BONE, margin: 0, lineHeight: 1.05,
              letterSpacing: '-0.01em',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {where}
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 5, flexWrap: 'wrap' }}>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: accent, letterSpacing: '0.06em', fontWeight: 500 }}>
                {isYours ? 'Your trip' : trip.owner_name}
              </span>
              {dateRange && (
                <>
                  <span style={{ color: DIM, fontSize: 8 }}>●</span>
                  <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: MUTE }}>{dateRange}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {trip.note && (
          <p style={{
            fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic',
            fontSize: 13.5, color: 'rgba(244,237,224,0.78)', lineHeight: 1.5,
            margin: 0, padding: '0 2px',
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}>
            "{trip.note}"
          </p>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Users size={10} style={{ color: accent }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: MUTE, letterSpacing: '0.06em' }}>
              {trip.confirmed_companions} / {trip.join_capacity}
            </span>
          </div>
          {isYours && (
            <span style={{
              fontFamily: '"Inter Tight",sans-serif', fontSize: 8.5,
              letterSpacing: '0.24em', textTransform: 'uppercase',
              color: GOLD, padding: '5px 11px', borderRadius: 12,
              background: 'rgba(212,182,134,0.06)', border: `1px solid ${GOLD}44`,
              display: 'inline-flex', alignItems: 'center', gap: 5,
            }}>
              <Radio size={8}/> Yours · live
            </span>
          )}
          {!isYours && status === null && (
            <motion.button
              whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.96 }}
              onClick={() => onRequestJoin?.(trip)}
              style={{
                padding: '7px 14px', borderRadius: 16,
                background: `linear-gradient(135deg, ${VIOLET} 0%, #6D28D9 100%)`,
                border: 'none', cursor: 'pointer', color: '#fff',
                fontFamily: '"Inter Tight",sans-serif', fontSize: 8.5, fontWeight: 500,
                letterSpacing: '0.22em', textTransform: 'uppercase',
                boxShadow: `0 4px 14px ${VIOLET}55`,
              }}
            >
              Request
            </motion.button>
          )}
          {!isYours && status === 'proposed' && (
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8.5, letterSpacing: '0.24em', textTransform: 'uppercase', color: AMBER, padding: '5px 11px', borderRadius: 12, background: `${AMBER}10`, border: `1px solid ${AMBER}55` }}>
              Requested
            </span>
          )}
          {!isYours && status === 'approved' && (
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 8.5, letterSpacing: '0.24em', textTransform: 'uppercase', color: GREEN, padding: '5px 11px', borderRadius: 12, background: `${GREEN}10`, border: `1px solid ${GREEN}55`, display: 'inline-flex', alignItems: 'center', gap: 5 }}>
              <Check size={9}/> Joined
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// ── Trip detail + instant-verdict modal ─────────────────────────────────

function pctFromScore(s) {
  if (typeof s !== 'number') return null
  return Math.round(Math.max(0, Math.min(1, s)) * 100)
}

function fitLabel(score) {
  const p = pctFromScore(score)
  if (p == null) return null
  if (p >= 75) return { label: 'Strong fit',   tone: GREEN }
  if (p >= 55) return { label: 'Good fit',     tone: GOLD }
  if (p >= 40) return { label: 'Borderline',   tone: AMBER }
  return            { label: 'Long shot',    tone: ROSE }
}

function TripDetailModal({ trip, onClose, onSubmit, busy, error, preview, previewLoading, verdict }) {
  const [msg, setMsg] = useState('')
  const owner = preview?.owner || {}
  const fit = fitLabel(preview?.match_score)
  const dest = preview?.destination || {}
  const where = dest.city
    ? dest.country ? `${dest.city}, ${dest.country}` : dest.city
    : trip?.destination_city || 'Somewhere'

  // Three-state UI: loading preview → confirmation → verdict
  const stage = verdict ? 'verdict' : (previewLoading ? 'loading' : 'confirm')
  const verdictApproved = verdict?.status === 'approved'

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      style={{
        position: 'fixed', inset: 0, zIndex: 200,
        background: 'rgba(10,8,5,0.82)', backdropFilter: 'blur(10px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32,
      }}
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, y: 12 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 12 }}
        transition={spring}
        onClick={e => e.stopPropagation()}
        style={{
          padding: 1, borderRadius: 22,
          background: `linear-gradient(135deg, ${VIOLET}66 0%, rgba(232,212,168,0.12) 50%, ${GOLD}33 100%)`,
          boxShadow: `0 36px 100px rgba(0,0,0,0.7), 0 0 80px ${VIOLET}22`,
          maxWidth: 520, width: '100%',
        }}
      >
        <div style={{
          padding: '32px 34px', borderRadius: 21,
          background: 'linear-gradient(160deg, rgba(24,19,13,0.99) 0%, rgba(10,9,7,1) 100%)',
          display: 'flex', flexDirection: 'column', gap: 18,
          position: 'relative', overflow: 'hidden',
        }}>
          <div style={{
            position: 'absolute', top: -100, right: -80, width: 280, height: 280, borderRadius: '50%',
            background: `radial-gradient(circle, ${VIOLET}18 0%, transparent 65%)`, pointerEvents: 'none',
          }}/>

          {stage === 'loading' && (
            <div style={{ padding: '40px 0', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
              <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.2, ease: 'linear', repeat: Infinity }}>
                <Loader2 size={18} style={{ color: VIOLET }}/>
              </motion.span>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase', color: MUTE }}>
                Reading the trip…
              </span>
            </div>
          )}

          {stage === 'confirm' && (
            <>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, position: 'relative' }}>
                {/* avatar with halo */}
                <div style={{ position: 'relative', width: 64, height: 64, flexShrink: 0 }}>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
                    style={{
                      position: 'absolute', inset: -4, borderRadius: '50%',
                      background: `conic-gradient(from 0deg, ${VIOLET}88, transparent 30%, ${GOLD}66 60%, transparent 100%)`,
                      filter: 'blur(5px)', opacity: 0.75,
                    }}
                  />
                  <div style={{
                    position: 'relative',
                    width: 64, height: 64, borderRadius: '50%', overflow: 'hidden',
                    background: 'linear-gradient(160deg, rgba(212,182,134,0.10) 0%, rgba(20,15,10,1) 100%)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    border: `1px solid ${VIOLET}66`,
                  }}>
                    {owner.avatar_url
                      ? <img src={owner.avatar_url} alt={owner.display_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
                      : <span style={{ fontFamily: '"Cormorant Garamond",serif', fontSize: 24, color: VIOLET, fontStyle: 'italic' }}>
                          {initials(owner.display_name || trip?.owner_name)}
                        </span>}
                  </div>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.24em', textTransform: 'uppercase', color: VIOLET, margin: 0, fontWeight: 500 }}>
                    {owner.is_synthetic ? 'Curated companion' : 'Trip owner'}
                  </p>
                  <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 26, color: BONE, margin: '4px 0 2px', lineHeight: 1.05 }}>
                    {owner.display_name || trip?.owner_name || 'Traveller'}
                  </p>
                  {owner.archetype && (
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: MUTE, margin: 0, letterSpacing: '0.04em' }}>
                      {owner.archetype}{owner.location ? ` · ${owner.location}` : ''}
                    </p>
                  )}
                </div>
              </div>

              {/* destination strip */}
              <div style={{
                padding: '14px 16px', borderRadius: 12,
                background: 'rgba(232,212,168,0.04)', border: `1px solid ${HAIRLINE}`,
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
              }}>
                <div>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.24em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
                    Destination
                  </p>
                  <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: BONE, margin: '2px 0 0', lineHeight: 1 }}>
                    {where}
                  </p>
                </div>
                {preview?.day_count != null && (
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.24em', textTransform: 'uppercase', color: MUTE, margin: 0 }}>
                      Length
                    </p>
                    <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 22, color: BONE, margin: '2px 0 0', lineHeight: 1 }}>
                      {preview.day_count}d
                    </p>
                  </div>
                )}
              </div>

              {/* interests row */}
              {owner.interests && owner.interests.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {owner.interests.slice(0, 6).map(i => (
                    <span key={i} style={{
                      fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: 'rgba(244,237,224,0.78)',
                      padding: '5px 11px', borderRadius: 999,
                      background: 'rgba(212,182,134,0.06)', border: `1px solid ${HAIRLINE}`,
                    }}>{i}</span>
                  ))}
                </div>
              )}

              {/* compatibility readout */}
              {preview?.match_score != null && fit && (
                <div style={{
                  padding: '14px 16px', borderRadius: 12,
                  background: `linear-gradient(135deg, ${fit.tone}12 0%, ${fit.tone}04 100%)`,
                  border: `1px solid ${fit.tone}44`,
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14,
                }}>
                  <div>
                    <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.24em', textTransform: 'uppercase', color: fit.tone, margin: 0, fontWeight: 500 }}>
                      Match preview
                    </p>
                    <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 20, color: BONE, margin: '2px 0 0', lineHeight: 1 }}>
                      {fit.label}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 36, color: fit.tone, lineHeight: 1 }}>
                      {pctFromScore(preview.match_score)}
                    </span>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: fit.tone, marginLeft: 2 }}>%</span>
                  </div>
                </div>
              )}

              <textarea
                value={msg}
                onChange={e => setMsg(e.target.value)}
                placeholder="A line about why this pulls you. Optional."
                rows={3} maxLength={400}
                style={{
                  padding: '12px 14px', borderRadius: 12,
                  background: 'rgba(232,212,168,0.03)', border: `1px solid ${HAIRLINE}`,
                  color: BONE, outline: 'none', resize: 'none',
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300, lineHeight: 1.5,
                }}
              />

              {error && <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: '#F87171', margin: 0 }}>{error}</p>}

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  disabled={busy}
                  onClick={() => onSubmit?.(msg.trim())}
                  style={{
                    flex: 1, padding: '13px 22px', borderRadius: 18,
                    background: `linear-gradient(135deg, ${VIOLET} 0%, #6D28D9 100%)`,
                    border: 'none', cursor: busy ? 'wait' : 'pointer', color: '#fff',
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 10, fontWeight: 500,
                    letterSpacing: '0.22em', textTransform: 'uppercase',
                    opacity: busy ? 0.7 : 1,
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                    boxShadow: `0 8px 22px ${VIOLET}55`,
                  }}
                >
                  {busy
                    ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, ease: 'linear', repeat: Infinity }}><Loader2 size={12}/></motion.span>
                    : <Send size={12}/>}
                  Send request
                </button>
                <button
                  onClick={onClose}
                  style={{
                    padding: '13px 22px', borderRadius: 18,
                    background: 'transparent', border: `1px solid ${HAIRLINE}`,
                    cursor: 'pointer', color: MUTE,
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 10,
                    letterSpacing: '0.22em', textTransform: 'uppercase',
                  }}
                >
                  Not now
                </button>
              </div>
            </>
          )}

          {stage === 'verdict' && (
            <div style={{ padding: '14px 0', display: 'flex', flexDirection: 'column', gap: 18, alignItems: 'center', textAlign: 'center' }}>
              <motion.div
                initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 240, damping: 18 }}
                style={{
                  width: 72, height: 72, borderRadius: '50%',
                  background: verdictApproved
                    ? `radial-gradient(circle, ${GREEN}44 0%, transparent 70%)`
                    : `radial-gradient(circle, ${MUTE} 0%, transparent 70%)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  boxShadow: verdictApproved ? `0 0 40px ${GREEN}55` : 'none',
                }}
              >
                {verdictApproved
                  ? <Check size={32} style={{ color: GREEN }}/>
                  : <X size={28} style={{ color: MUTE }}/>}
              </motion.div>
              <div>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: verdictApproved ? GREEN : MUTE, margin: 0, fontWeight: 500 }}>
                  {verdictApproved ? 'You\'re in' : 'Not this time'}
                </p>
                <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 26, color: BONE, margin: '6px 0 0', lineHeight: 1.15 }}>
                  {verdictApproved
                    ? `${owner.display_name || 'They'} said yes.`
                    : `${owner.display_name || 'They'} passed.`}
                </p>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, color: MUTE, margin: '10px 0 0', maxWidth: 360, lineHeight: 1.55 }}>
                  {verdictApproved
                    ? `Match score ${pctFromScore(verdict?.match_score)}%. You're now on the trip — open the shared itinerary to start planning together.`
                    : `Match score ${pctFromScore(verdict?.match_score)}% — not quite there this time. Other travellers are opening trips at all hours; the next one might be the one.`}
                </p>
              </div>
              <button
                onClick={onClose}
                style={{
                  padding: '12px 26px', borderRadius: 18,
                  background: verdictApproved
                    ? `linear-gradient(135deg, ${GREEN} 0%, #059669 100%)`
                    : 'transparent',
                  border: verdictApproved ? 'none' : `1px solid ${HAIRLINE}`,
                  cursor: 'pointer',
                  color: verdictApproved ? '#fff' : MUTE,
                  fontFamily: '"Inter Tight",sans-serif', fontSize: 10, fontWeight: 500,
                  letterSpacing: '0.22em', textTransform: 'uppercase',
                  boxShadow: verdictApproved ? `0 8px 22px ${GREEN}55` : 'none',
                }}
              >
                {verdictApproved ? 'Open trip' : 'Close'}
              </button>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Comment thread ───────────────────────────────────────────────────────

function CommentThread({ postId, selfUid, initialCount }) {
  const [open, setOpen]         = useState(false)
  const [loading, setLoading]   = useState(false)
  const [comments, setComments] = useState([])
  const [draft, setDraft]       = useState('')
  const [posting, setPosting]   = useState(false)

  async function loadOnce() {
    setLoading(true)
    try {
      const res = await listComments(postId)
      setComments(res?.comments || [])
    } catch { /* noop */ }
    finally { setLoading(false) }
  }
  function toggle() {
    const next = !open
    setOpen(next)
    if (next && comments.length === 0 && !loading) loadOnce()
  }
  async function submit() {
    const text = draft.trim()
    if (!text || posting) return
    setPosting(true)
    try {
      const res = await addComment(postId, text)
      setComments(prev => [...prev, res.comment])
      setDraft('')
    } catch { /* noop */ }
    finally { setPosting(false) }
  }

  useEffect(() => {
    function onNewComment(e) {
      const d = e.detail
      if (!d || d.post_id !== postId || !d.comment) return
      setComments(prev => prev.some(c => c.comment_id === d.comment.comment_id)
        ? prev : [...prev, d.comment])
      setOpen(true)
    }
    window.addEventListener('sonder:comment:new', onNewComment)
    return () => window.removeEventListener('sonder:comment:new', onNewComment)
  }, [postId])

  return (
    <div style={{ marginTop: 6 }}>
      <button
        onClick={toggle}
        style={{
          background: 'none', border: 'none', padding: 0, cursor: 'pointer',
          color: MUTE, fontFamily: '"Inter Tight",sans-serif', fontSize: 10.5,
          display: 'inline-flex', alignItems: 'center', gap: 6, letterSpacing: '0.02em',
        }}
      >
        <MessageCircle size={10}/>
        {open ? 'Hide' : initialCount > 0 ? `${initialCount} ${initialCount === 1 ? 'reply' : 'replies'}` : 'Reply'}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 10, borderLeft: `1px solid ${GOLD}33`, paddingLeft: 12 }}>
              {loading && <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: DIM, margin: 0 }}>Loading…</p>}
              {comments.map(c => (
                <div key={c.comment_id} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10.5, fontWeight: 500, color: c.author_id === selfUid ? GOLD : BONE }}>
                      {c.author_name}
                    </span>
                    <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: DIM }}>{timeAgo(c.created_at)}</span>
                  </div>
                  <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 12, color: BONE, margin: 0, lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {c.text}
                  </p>
                </div>
              ))}
              <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
                <input
                  value={draft}
                  onChange={e => setDraft(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') submit() }}
                  placeholder="Reply…"
                  maxLength={400}
                  style={{
                    flex: 1, padding: '7px 11px', borderRadius: 14,
                    background: 'rgba(232,212,168,0.03)', border: `1px solid ${HAIRLINE}`,
                    color: BONE, outline: 'none',
                    fontFamily: '"Inter Tight",sans-serif', fontSize: 11.5,
                  }}
                />
                <button
                  onClick={submit}
                  disabled={!draft.trim() || posting}
                  style={{
                    padding: '6px 11px', borderRadius: 14,
                    background: draft.trim() ? VIOLET : 'transparent',
                    border: `1px solid ${draft.trim() ? VIOLET : HAIRLINE}`,
                    cursor: draft.trim() && !posting ? 'pointer' : 'not-allowed',
                    color: draft.trim() ? '#fff' : MUTE,
                    opacity: posting ? 0.6 : 1,
                  }}
                >
                  {posting
                    ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, ease: 'linear', repeat: Infinity }}><Loader2 size={10}/></motion.span>
                    : <Send size={10}/>}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Post card ────────────────────────────────────────────────────────────

function PostCard({ post, selfUid, onDelete }) {
  const isMine = post.author_id === selfUid
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
      transition={{ duration: 0.4, ease }}
      style={{
        padding: 1, borderRadius: 16,
        background: `linear-gradient(150deg, ${GOLD}22 0%, rgba(232,212,168,0.04) 40%, rgba(8,8,7,0) 75%, ${GOLD}14 100%)`,
      }}
    >
      <div style={{
        padding: '18px 22px', borderRadius: 15,
        background: 'linear-gradient(160deg, rgba(22,18,12,0.98) 0%, rgba(10,9,7,1) 100%)',
        display: 'flex', flexDirection: 'column', gap: 11,
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <div style={{
            width: 34, height: 34, borderRadius: '50%', overflow: 'hidden',
            background: 'rgba(212,182,134,0.06)', flexShrink: 0,
            border: `1px solid ${GOLD}44`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {post.author_avatar
              ? <img src={post.author_avatar} alt={post.author_name} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
              : <span style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 14, color: GOLD }}>
                  {initials(post.author_name)}
                </span>}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 12.5, fontWeight: 500, color: isMine ? GOLD : BONE }}>
                {post.author_name}
              </span>
              <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 10, color: DIM }}>{timeAgo(post.created_at)}</span>
            </div>
          </div>
          {isMine && (
            <button
              onClick={() => onDelete?.(post)}
              title="Delete"
              style={{ background: 'none', border: 'none', padding: 2, cursor: 'pointer', color: DIM, display: 'flex' }}
            >
              <Trash2 size={11}/>
            </button>
          )}
        </div>
        <p style={{
          fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 13.5,
          color: BONE, margin: 0, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        }}>
          {post.text}
        </p>
        <CommentThread postId={post.post_id} selfUid={selfUid} initialCount={post.comment_count || 0}/>
      </div>
    </motion.div>
  )
}

// ── Inline post composer ─────────────────────────────────────────────────

function Composer({ onCreated }) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err,  setErr]  = useState(null)
  const [focused, setFocused] = useState(false)

  async function submit() {
    const t = text.trim()
    if (!t || busy) return
    setBusy(true); setErr(null)
    try {
      const res = await createPost({ text: t })
      onCreated?.(res.post)
      setText('')
      setFocused(false)
    } catch (e) {
      setErr(e?.message || 'Could not post')
    } finally {
      setBusy(false)
    }
  }

  return (
    <motion.div
      animate={{ borderColor: focused ? `${GOLD}55` : HAIRLINE }}
      style={{
        padding: '14px 18px', borderRadius: 14,
        background: 'rgba(232,212,168,0.025)',
        border: `1px solid ${HAIRLINE}`,
        display: 'flex', flexDirection: 'column', gap: 10,
      }}
    >
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => { if (!text.trim()) setFocused(false) }}
        placeholder="Drop a thought, a recommendation, a half-formed plan…"
        rows={focused || text ? 3 : 1}
        maxLength={600}
        style={{
          padding: '8px 10px', borderRadius: 10,
          background: 'transparent', border: 'none',
          color: BONE, outline: 'none', resize: 'none',
          fontFamily: '"Inter Tight",sans-serif', fontSize: 13, fontWeight: 300,
          lineHeight: 1.55,
          transition: 'all 0.2s',
        }}
      />
      {err && <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: '#F87171', margin: 0 }}>{err}</p>}
      {(focused || text) && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
        >
          <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9.5, color: DIM, letterSpacing: '0.06em' }}>
            {text.length} / 600
          </span>
          <button
            onClick={submit}
            disabled={!text.trim() || busy}
            style={{
              padding: '7px 16px', borderRadius: 16,
              background: text.trim() ? `linear-gradient(135deg, ${GOLD} 0%, #B89464 100%)` : 'transparent',
              border: `1px solid ${text.trim() ? GOLD : HAIRLINE}`,
              cursor: text.trim() && !busy ? 'pointer' : 'not-allowed',
              color: text.trim() ? BG : MUTE,
              fontFamily: '"Inter Tight",sans-serif', fontSize: 9, fontWeight: 500,
              letterSpacing: '0.22em', textTransform: 'uppercase',
              opacity: busy ? 0.7 : 1,
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {busy
              ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, ease: 'linear', repeat: Infinity }}><Loader2 size={10}/></motion.span>
              : <Send size={10}/>}
            Share
          </button>
        </motion.div>
      )}
    </motion.div>
  )
}

// ── The full section ─────────────────────────────────────────────────────

export default function DashboardPulse({ selfUid }) {
  const navigate = useNavigate()
  const [trips, setTrips] = useState([])
  const [posts, setPosts] = useState([])
  const [loadingTrips, setLoadingTrips] = useState(true)
  const [loadingFeed,  setLoadingFeed]  = useState(true)
  const [joinTarget, setJoinTarget] = useState(null)
  const [joinBusy, setJoinBusy] = useState(false)
  const [joinErr, setJoinErr] = useState(null)
  const [tripPreview, setTripPreview] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [verdict, setVerdict] = useState(null)

  // initial + slow background poll (real-time WS fills the gap)
  const tripsPollRef = useRef(null)
  const feedPollRef  = useRef(null)

  // Hard cap the live surfaces so the section stays scannable and
  // realtime pushes don't grow the arrays unbounded over a long
  // session. Applied at every entry point (poll, WS push, optimistic
  // local insert) so the invariant holds.
  const fetchTrips = useCallback(async () => {
    try {
      const res = await listOpenTrips(24)
      setTrips((res?.trips || []).slice(0, PULSE_MAX))
    } catch { /* surface via empty state */ }
    finally { setLoadingTrips(false) }
  }, [])
  const fetchFeed = useCallback(async () => {
    try {
      const res = await listFeed({ limit: 20 })
      setPosts(prev => {
        const next = (res?.posts || []).slice(0, PULSE_MAX)
        if (next.length && prev.length && next[0]?.post_id === prev[0]?.post_id) return prev
        return next
      })
    } catch { /* noop */ }
    finally { setLoadingFeed(false) }
  }, [])

  useEffect(() => {
    fetchTrips(); fetchFeed()
    tripsPollRef.current = setInterval(fetchTrips, 20_000)
    feedPollRef.current  = setInterval(fetchFeed, 15_000)
    return () => { clearInterval(tripsPollRef.current); clearInterval(feedPollRef.current) }
  }, [fetchTrips, fetchFeed])

  // Real-time WS push handlers (NotificationProvider re-dispatches these)
  useEffect(() => {
    function onTripOpen(e) {
      const trip = e.detail
      if (!trip?.itinerary_id) return
      const card = { ...trip, is_yours: trip.owner_uid === selfUid }
      setTrips(prev => {
        if (prev.some(t => t.itinerary_id === card.itinerary_id)) return prev
        return [card, ...prev].slice(0, PULSE_MAX)
      })
    }
    function onTripClose(e) {
      const id = e.detail?.itinerary_id
      if (!id) return
      setTrips(prev => prev.filter(t => t.itinerary_id !== id))
    }
    function onPostNew(e) {
      const post = e.detail
      if (!post?.post_id) return
      setPosts(prev => {
        if (prev.some(p => p.post_id === post.post_id)) return prev
        return [post, ...prev].slice(0, PULSE_MAX)
      })
    }
    function onResolved(e) {
      const req = e.detail
      if (!req?.itinerary_id) return
      setTrips(prev => prev.map(t =>
        t.itinerary_id === req.itinerary_id
          ? { ...t, your_request_status: req.status }
          : t,
      ))
    }
    window.addEventListener('sonder:discover:trip_open',  onTripOpen)
    window.addEventListener('sonder:discover:trip_close', onTripClose)
    window.addEventListener('sonder:discover:post_new',   onPostNew)
    window.addEventListener('sonder:join_request:resolved', onResolved)
    return () => {
      window.removeEventListener('sonder:discover:trip_open',  onTripOpen)
      window.removeEventListener('sonder:discover:trip_close', onTripClose)
      window.removeEventListener('sonder:discover:post_new',   onPostNew)
      window.removeEventListener('sonder:join_request:resolved', onResolved)
    }
  }, [selfUid])

  async function openJoinModal(trip) {
    setJoinTarget(trip); setJoinErr(null); setVerdict(null); setTripPreview(null)
    setPreviewLoading(true)
    try {
      const preview = await getTripPreview(trip.itinerary_id)
      setTripPreview(preview)
    } catch (e) {
      // Preview is non-fatal — modal still works without the persona detail.
      console.warn('getTripPreview failed:', e?.message || e)
    } finally {
      setPreviewLoading(false)
    }
  }

  function closeJoinModal() {
    // If the verdict was approved, take the user to the shared itinerary.
    if (verdict?.status === 'approved' && joinTarget?.itinerary_id) {
      navigate(`/shared/${encodeURIComponent(joinTarget.itinerary_id)}`)
    }
    setJoinTarget(null); setVerdict(null); setTripPreview(null); setJoinErr(null)
  }

  async function submitJoin(message) {
    if (!joinTarget) return
    setJoinBusy(true); setJoinErr(null)
    try {
      const res = await requestToJoin(joinTarget.itinerary_id, message)
      const req = res?.request || {}
      const newStatus = req.status || 'proposed'
      setTrips(prev => prev.map(t =>
        t.itinerary_id === joinTarget.itinerary_id
          ? { ...t, your_request_status: newStatus }
          : t,
      ))
      // Auto-resolved (synthetic trip): show verdict inline.
      if (res?.auto_resolved && (newStatus === 'approved' || newStatus === 'denied')) {
        setVerdict({ status: newStatus, match_score: req.match_score })
      } else {
        // Non-synthetic: close modal, the request sits as proposed.
        setJoinTarget(null)
      }
    } catch (e) {
      setJoinErr(e?.message || 'Could not send request')
    } finally {
      setJoinBusy(false)
    }
  }

  async function deleteOne(post) {
    if (!confirm('Delete this post?')) return
    try {
      await apiDeletePost(post.post_id)
      setPosts(prev => prev.filter(p => p.post_id !== post.post_id))
    } catch (e) {
      alert(e?.message || 'Could not delete')
    }
  }

  // Arrays are already capped at PULSE_MAX at every entry point; render
  // all of them. The slice would be a no-op now but keep an explicit
  // cap here as a safety net in case the invariant ever drifts.
  const tripsToShow = useMemo(() => trips.slice(0, PULSE_MAX), [trips])
  const postsToShow = useMemo(() => posts.slice(0, PULSE_MAX), [posts])

  return (
    <section style={{
      gridColumn: '1 / -1',   // span both Dashboard columns
      padding: '64px 44px 52px',
      borderTop: `1px solid ${HAIRLINE}`,
      background: `linear-gradient(180deg, transparent 0%, rgba(212,182,134,0.025) 50%, transparent 100%)`,
      position: 'relative',
      scrollMarginTop: 80,
    }} data-pulse-anchor>
      {/* ambient drift */}
      <motion.div
        animate={{ opacity: [0.06, 0.14, 0.06] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute', top: 40, left: '20%',
          width: 460, height: 460, borderRadius: '50%',
          background: `radial-gradient(circle, ${VIOLET}22 0%, transparent 65%)`,
          pointerEvents: 'none', filter: 'blur(40px)',
        }}
      />
      <motion.div
        animate={{ opacity: [0.05, 0.10, 0.05] }}
        transition={{ duration: 11, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
        style={{
          position: 'absolute', bottom: 80, right: '15%',
          width: 380, height: 380, borderRadius: '50%',
          background: `radial-gradient(circle, ${GOLD}22 0%, transparent 65%)`,
          pointerEvents: 'none', filter: 'blur(40px)',
        }}
      />

      {/* hero header */}
      <div style={{ marginBottom: 52, position: 'relative', textAlign: 'center' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 10, marginBottom: 16,
          padding: '6px 14px', borderRadius: 999,
          background: `linear-gradient(135deg, ${VIOLET}14 0%, ${GOLD}10 100%)`,
          border: `1px solid ${VIOLET}33`,
          boxShadow: `0 4px 16px ${VIOLET}22`,
        }}>
          <motion.span
            animate={{ scale: [1, 1.4, 1], opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
            style={{ width: 7, height: 7, borderRadius: '50%', background: '#10B981', boxShadow: '0 0 10px #10B981' }}
          />
          <p style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, letterSpacing: '0.34em', textTransform: 'uppercase', color: BONE, margin: 0, fontWeight: 500 }}>
            Sonder Pulse · live now
          </p>
          <motion.span
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          >
            <Sparkles size={11} style={{ color: GOLD }}/>
          </motion.span>
        </div>
        <motion.h2
          animate={{ filter: [`drop-shadow(0 0 20px ${VIOLET}22)`, `drop-shadow(0 0 44px ${VIOLET}55)`, `drop-shadow(0 0 20px ${VIOLET}22)`] }}
          transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            fontFamily: '"Cormorant Garamond",serif', fontWeight: 400, fontStyle: 'italic',
            fontSize: 52, color: BONE, lineHeight: 1.02, margin: 0,
            letterSpacing: '-0.02em',
          }}
        >
          Who's moving where, right now.
        </motion.h2>
        <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 16, color: 'rgba(244,237,224,0.62)', margin: '16px 0 0', maxWidth: 580, marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.55 }}>
          Trips opening for company. Half-formed plans. Recommendations from
          travellers whose rhythm might match yours.
        </p>
        {/* live counts strip */}
        <div style={{
          marginTop: 22,
          display: 'inline-flex', alignItems: 'center', gap: 24,
          padding: '10px 22px', borderRadius: 999,
          background: 'rgba(8,8,7,0.55)', backdropFilter: 'blur(20px)',
          border: `1px solid ${HAIRLINE}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <MapPin size={11} style={{ color: VIOLET }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: BONE, fontWeight: 500 }}>
              {trips.length}
            </span>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: MUTE, letterSpacing: '0.22em', textTransform: 'uppercase' }}>
              {trips.length === 1 ? 'open trip' : 'open trips'}
            </span>
          </div>
          <span style={{ width: 1, height: 14, background: HAIRLINE }}/>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <MessageCircle size={11} style={{ color: GOLD }}/>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, color: BONE, fontWeight: 500 }}>
              {posts.length}
            </span>
            <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 9, color: MUTE, letterSpacing: '0.22em', textTransform: 'uppercase' }}>
              voices in the room
            </span>
          </div>
        </div>
      </div>

      <div style={{ position: 'relative', display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: 36, alignItems: 'start' }}>

        {/* LEFT — open trips */}
        <div>
          <SectionHeader
            eyebrow="Trips you could join"
            title="Open invitations"
            accent={VIOLET}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {loadingTrips && (
              <div style={{ padding: '20px 0', display: 'flex', alignItems: 'center', gap: 10, color: MUTE }}>
                <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.3, ease: 'linear', repeat: Infinity }}>
                  <Loader2 size={14} style={{ color: VIOLET }}/>
                </motion.span>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase' }}>
                  Listening for trips…
                </span>
              </div>
            )}
            {!loadingTrips && tripsToShow.length === 0 && (
              <div style={{ padding: '32px 24px', borderRadius: 14, border: `1px dashed ${HAIRLINE}`, textAlign: 'center' }}>
                <MapPin size={18} style={{ color: VIOLET, opacity: 0.6, marginBottom: 8 }}/>
                <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 18, color: BONE, margin: 0 }}>
                  Quiet for now.
                </p>
                <p style={{ fontFamily: '"Inter Tight",sans-serif', fontWeight: 300, fontSize: 11.5, color: MUTE, margin: '6px 0 0', lineHeight: 1.55 }}>
                  Open your own trip to companions — your card will appear here first.
                </p>
              </div>
            )}
            <AnimatePresence initial={false}>
              {tripsToShow.map(t => (
                <OpenTripCard
                  key={t.itinerary_id}
                  trip={t}
                  onRequestJoin={openJoinModal}
                />
              ))}
            </AnimatePresence>
          </div>
        </div>

        {/* RIGHT — feed */}
        <div>
          <SectionHeader
            eyebrow="What travellers are saying"
            title="The room"
            accent={GOLD}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Composer onCreated={(p) => setPosts(prev => [p, ...prev].slice(0, PULSE_MAX))}/>
            {loadingFeed && (
              <div style={{ padding: '20px 0', display: 'flex', alignItems: 'center', gap: 10, color: MUTE }}>
                <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.3, ease: 'linear', repeat: Infinity }}>
                  <Loader2 size={14} style={{ color: GOLD }}/>
                </motion.span>
                <span style={{ fontFamily: '"Inter Tight",sans-serif', fontSize: 11, letterSpacing: '0.22em', textTransform: 'uppercase' }}>
                  Catching the room…
                </span>
              </div>
            )}
            {!loadingFeed && postsToShow.length === 0 && (
              <p style={{ fontFamily: '"Cormorant Garamond",serif', fontStyle: 'italic', fontSize: 17, color: MUTE, margin: '8px 4px' }}>
                Be the first voice in the room.
              </p>
            )}
            <AnimatePresence initial={false}>
              {postsToShow.map(p => (
                <PostCard key={p.post_id} post={p} selfUid={selfUid} onDelete={deleteOne}/>
              ))}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {joinTarget && (
          <TripDetailModal
            trip={joinTarget}
            onClose={closeJoinModal}
            onSubmit={submitJoin}
            busy={joinBusy}
            error={joinErr}
            preview={tripPreview}
            previewLoading={previewLoading}
            verdict={verdict}
          />
        )}
      </AnimatePresence>
    </section>
  )
}
