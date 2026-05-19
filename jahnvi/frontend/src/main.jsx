import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { initSentry, Sentry } from './lib/sentry'
import './styles/globals.css'

initSentry()

function FallbackUI({ error, resetError }) {
  return (
    <div style={{ minHeight: '100vh', background: '#080807', color: '#F4EDE0', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, textAlign: 'center', fontFamily: '"Inter Tight", sans-serif' }}>
      <p style={{ fontFamily: '"Cormorant Garamond", serif', fontStyle: 'italic', fontSize: 32, marginBottom: 14 }}>Something broke.</p>
      <p style={{ fontSize: 12, color: 'rgba(244,237,224,0.44)', maxWidth: 480, marginBottom: 28, lineHeight: 1.6 }}>
        {error?.message || 'An unexpected error occurred.'}
      </p>
      <button onClick={resetError} style={{ padding: '14px 28px', background: 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)', border: 'none', borderRadius: 10, color: '#fff', cursor: 'pointer', fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase' }}>
        Try again
      </button>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Sentry.ErrorBoundary fallback={FallbackUI}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </Sentry.ErrorBoundary>
  </React.StrictMode>
)
