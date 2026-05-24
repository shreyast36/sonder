/**
 * Cloudflare Pages Function — proxy /api/* to the Render backend.
 *
 * Cloudflare Pages `_redirects` only supports SAME-domain rewrites;
 * proxying to an external origin requires a Function. This catch-all
 * forwards every /api/* request (any method, any headers, any body)
 * to https://sonder-16mj.onrender.com/api/* and streams the response
 * back to the caller.
 *
 * The `[[path]]` filename gives us catch-all routing — Pages matches
 * /api/anything/deeper to this single handler.
 *
 * Pages handles the SPA fallback automatically for client-side routes
 * (any unmatched path returns index.html), so we don't need a
 * separate _redirects rule for that either.
 */

const BACKEND = 'https://sonder-16mj.onrender.com'

export async function onRequest(context) {
  const url = new URL(context.request.url)
  // url.pathname already includes "/api/..."; just forward as-is + search.
  const target = BACKEND + url.pathname + url.search

  // Clone the incoming request with a new URL. Pass-through for method,
  // body, and headers — Authorization, Content-Type, custom WS upgrade
  // headers, etc. all reach the backend untouched.
  const init = {
    method:  context.request.method,
    headers: context.request.headers,
    body:    ['GET', 'HEAD'].includes(context.request.method) ? undefined : context.request.body,
    redirect: 'manual',
  }

  // Pages Functions run in the Workers runtime — fetch() streams
  // bodies natively, so large payloads (image uploads, SSE streams)
  // pass through without buffering.
  return fetch(target, init)
}
