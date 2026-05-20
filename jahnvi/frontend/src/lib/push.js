/**
 * Web Push registration helper.
 *
 * Flow:
 *   1. Make sure the browser supports SW + Push + Notifications.
 *   2. Register /sw.js (idempotent — the browser de-dupes by URL).
 *   3. Fetch the VAPID public key from the backend.
 *   4. Subscribe to push using that key (or reuse the existing subscription).
 *   5. POST the subscription to /api/push/subscribe.
 *
 * Permission is requested lazily by the caller (NotificationProvider asks
 * the first time a chat notification arrives) so we don't ambush the user
 * on app boot.
 */

import {
  getVapidPublicKey, registerPushSubscription, unregisterPushSubscription,
} from './api'

const SW_URL = '/sw.js'

export function pushSupported() {
  return (
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw     = atob(base64)
  const out     = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i)
  return out
}

async function registerServiceWorker() {
  const existing = await navigator.serviceWorker.getRegistration(SW_URL)
  if (existing) return existing
  return navigator.serviceWorker.register(SW_URL, { scope: '/' })
}

/**
 * Idempotent. Safe to call on every auth state change. Returns the
 * PushSubscription on success, or null when push isn't available
 * (unsupported browser, permission denied, backend not configured).
 */
export async function ensurePushSubscribed() {
  if (!pushSupported()) return null
  if (Notification.permission !== 'granted') return null

  let publicKey
  try {
    publicKey = (await getVapidPublicKey()).key
  } catch (e) {
    // 503 — server-side web push not configured. Caller should fall back
    // to the in-page Notification API.
    if (e?.status !== 503) console.warn('vapid-public-key fetch failed:', e?.message || e)
    return null
  }
  if (!publicKey) return null

  const reg = await registerServiceWorker()
  // Wait until the SW is actually controlling the page — subscribing on a
  // not-yet-active registration is a no-op on some browsers.
  await navigator.serviceWorker.ready

  let sub = await reg.pushManager.getSubscription()
  if (sub) {
    // Same browser/permission cycle — server already has it; nothing to do.
    return sub
  }

  try {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    })
  } catch (e) {
    console.warn('pushManager.subscribe failed:', e?.message || e)
    return null
  }

  try {
    await registerPushSubscription(sub.toJSON())
  } catch (e) {
    console.warn('registerPushSubscription failed:', e?.message || e)
    // Roll back — no point keeping a subscription the server doesn't know.
    try { await sub.unsubscribe() } catch { /* ignore */ }
    return null
  }
  return sub
}

/**
 * Called on sign-out so future pushes don't land on a stale browser.
 */
export async function dropPushSubscription() {
  if (!pushSupported()) return
  try {
    const reg = await navigator.serviceWorker.getRegistration(SW_URL)
    if (!reg) return
    const sub = await reg.pushManager.getSubscription()
    if (!sub) return
    try { await unregisterPushSubscription(sub.endpoint) } catch { /* server may be down */ }
    try { await sub.unsubscribe() } catch { /* ignore */ }
  } catch (e) {
    console.warn('dropPushSubscription failed:', e?.message || e)
  }
}
