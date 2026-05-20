/* Sonder service worker — Web Push only.
 *
 * The backend POSTs a JSON payload of shape
 *   {title, body, url, tag}
 * to the user's push subscription. We render an OS notification and route
 * the click back into the SPA at the given url.
 *
 * No caching / offline behaviour intentionally — that's a separate concern.
 */

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('push', (event) => {
  let data = {}
  try { data = event.data ? event.data.json() : {} } catch { /* opaque */ }
  const title = data.title || 'Sonder'
  const body  = data.body  || ''
  const url   = data.url   || '/'
  const tag   = data.tag   || 'sonder'

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      tag,                  // collapses duplicate notifs for the same chat
      renotify: true,
      icon:  '/sonder-logo.png',
      badge: '/sonder-logo.png',
      data:  { url },
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const targetUrl = (event.notification.data && event.notification.data.url) || '/'

  event.waitUntil((async () => {
    // Prefer focusing an already-open tab to launching a new one.
    const clientList = await self.clients.matchAll({
      type: 'window', includeUncontrolled: true,
    })
    for (const client of clientList) {
      try {
        const u = new URL(client.url)
        if (u.origin === self.location.origin) {
          await client.focus()
          if ('navigate' in client) await client.navigate(targetUrl)
          return
        }
      } catch { /* ignore */ }
    }
    await self.clients.openWindow(targetUrl)
  })())
})
