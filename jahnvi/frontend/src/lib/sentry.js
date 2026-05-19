import * as Sentry from '@sentry/react'

// Initialize Sentry as early as possible (called from main.jsx before render).
// Reads config from Vite env: VITE_SENTRY_DSN, VITE_SENTRY_RELEASE, VITE_SENTRY_ENV.
// No-op when DSN is unset (local dev).
export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN
  if (!dsn) return

  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_SENTRY_ENV || (import.meta.env.PROD ? 'production' : 'development'),
    release: import.meta.env.VITE_SENTRY_RELEASE || undefined,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({ maskAllText: true, blockAllMedia: false }),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0,    // don't record session replays by default
    replaysOnErrorSampleRate: 1.0,  // but always capture replays on errors
    sendDefaultPii: false,
  })
}

export { Sentry }
