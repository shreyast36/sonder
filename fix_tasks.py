# -*- coding: utf-8 -*-
import sys, os

base = os.path.dirname(os.path.abspath(__file__))

# ── P4 TASKS.md ──────────────────────────────────────────────────────────────
p4_path = os.path.join(base, 'p4_validation_pipeline_mushahid/TASKS.md')
p4 = open(p4_path, encoding='utf-8').read()

p4 = p4.replace(
    "## backend_api/routes/plan_trip.py\n\n- [ ] Implement `POST /plan-trip` → call `run_plan_trip_pipeline()`; handle exceptions → 500 with error detail",
    "## backend_api/routes/plan_trip.py\n\n"
    "- [ ] Implement `POST /plan-trip` as a **streaming SSE endpoint**\n"
    "  - Return `StreamingResponse(stream_plan_trip_pipeline(request), media_type=\"text/event-stream\")`\n"
    "  - Add headers: `Cache-Control: no-cache` and `X-Accel-Buffering: no`\n"
    "    (X-Accel-Buffering prevents Nginx from buffering the stream in production)\n"
    "  - On exception inside the generator: yield an error event then return gracefully"
)

p4 = p4.replace(
    "## backend_api/routes/update_trip.py\n\n- [ ] Implement `POST /update-trip` → call `run_update_trip_pipeline()`",
    "## backend_api/routes/update_trip.py\n\n"
    "- [ ] Implement `POST /update-trip` as a **streaming SSE endpoint** -- same pattern as plan_trip.py\n"
    "  - Return `StreamingResponse(stream_update_trip_pipeline(request), media_type=\"text/event-stream\")`\n"
    "  - Same `Cache-Control` and `X-Accel-Buffering` headers"
)

p4 = p4.replace(
    "## backend_api/pipeline.py\n\n"
    "- [ ] Implement `run_plan_trip_pipeline(request: PlanTripRequest) -> PlanTripResponse`\n"
    "  - Call modules 1–9 in sequence (see README for order)\n"
    "  - Validation-regeneration loop with a sensible max retry count\n"
    "  - Return full `PlanTripResponse` with itinerary, validation result, and co-traveller matches\n"
    "- [ ] Implement `run_update_trip_pipeline(request: UpdateTripRequest) -> UpdateTripResponse`\n"
    "  - Delegate to `refinement_loop/loop.py`",
    "## backend_api/pipeline.py\n\n"
    "- [ ] Implement `stream_plan_trip_pipeline(request: PlanTripRequest) -> AsyncGenerator[str, None]`\n"
    "  - This is an **async generator** -- use `yield`, not `return`\n"
    "  - Each yield produces one SSE string: `\"data: \" + json.dumps(event) + \"\\n\\n\"`\n"
    "  - Emit a named stage event before and after each slow module (see architecture.md)\n"
    "  - Validation loop: on REVISE, yield a `revision` event then re-generate (max 2 retries)\n"
    "  - Final yield: `{\"stage\": \"done\", \"data\": response.model_dump()}` -- full PlanTripResponse\n"
    "  - Wrap entire generator in try/except; yield an `error` event on unhandled exception\n"
    "  - In LOCAL_MODE: `await asyncio.sleep(0.1-0.3)` between stages so the UI animation fires\n"
    "- [ ] Implement `stream_update_trip_pipeline(request: UpdateTripRequest) -> AsyncGenerator[str, None]`\n"
    "  - Same SSE pattern; emit: `re_ranking`, `regenerating_itinerary`, `re_validating`, `done`"
)

p4 = p4.replace(
    "## backend_api/routes/cotraveller.py\n\n"
    "- [ ] Implement `POST /cotraveller` → call `match_cotravellers(request.user_profile)` → return `CoTravellerResponse`",
    "## backend_api/routes/cotraveller.py\n\n"
    "- [ ] Implement `POST /cotraveller` -- call `match_cotravellers(request.user_profile)`, return `CoTravellerResponse`\n"
    "  - After returning, call `register_active_user(request.user_id, request.user_profile)` (Shreyas scorer)\n"
    "    so the live match push loop tracks this user while they are on Screen 5\n"
    "- [ ] Implement `POST /cotraveller/close` -- call `deregister_active_user(request.user_id)`\n"
    "  when the user navigates away from Screen 5 or approves/denies a match"
)

p4 = p4.replace(
    "- [ ] Implement `WS /ws/chat/{session_id}`\n"
    "  - Validate session exists before accepting (close with 4004 if not found)\n"
    "  - On connect: join room; replay message history to the newly connected client\n"
    "  - On message: parse `ChatMessage`, set server-side timestamp, `save_message()`, `broadcast_except()`\n"
    "  - On `WebSocketDisconnect`: `disconnect()` from room; close session if both sides disconnected",
    "- [ ] Implement `WS /ws/chat/{session_id}`\n"
    "  - Validate session exists -- close with code 4004 if session_id not found in SQLite\n"
    "  - On connect: `await connect(session_id, websocket)`; replay history via `get_messages()`\n"
    "  - On message: parse ChatMessage JSON, set server-side ISO timestamp, `save_message()`,\n"
    "    then `await broadcast_except(session_id, websocket, msg.model_dump_json())`\n"
    "  - On WebSocketDisconnect: `await disconnect(session_id, websocket)`;\n"
    "    if no connections remain in the room, call `close_session(session_id)`\n"
    "  - Wrap the receive loop in try/except WebSocketDisconnect -- a disconnect must never crash the server"
)

p4 = p4.replace(
    "- [ ] Implement `WS /ws/itinerary/{itinerary_id}`\n"
    "  - Validate itinerary_id is a known shared itinerary before accepting (close with 4004 if not found)\n"
    "  - On connect: join itinerary room\n"
    "  - On event: parse `ItineraryUpdateEvent`; persist change; `broadcast_itinerary()`\n"
    "  - On `WebSocketDisconnect`: leave room",
    "- [ ] Implement `WS /ws/itinerary/{itinerary_id}`\n"
    "  - Validate itinerary_id is a known shared itinerary -- close with 4004 if not found\n"
    "  - On connect: `await connect_itinerary(itinerary_id, websocket)`\n"
    "  - On event: parse ItineraryUpdateEvent JSON; persist to SQLite;\n"
    "    `await broadcast_itinerary(itinerary_id, event.model_dump_json())`\n"
    "  - On WebSocketDisconnect: `await disconnect_itinerary(itinerary_id, websocket)`\n"
    "  - All five event types must be handled: co_traveller_added, note_added,\n"
    "    change_proposed, change_accepted, change_rejected"
)

with open(p4_path, 'w', encoding='utf-8') as f:
    f.write(p4)
print('P4 done')

# ── P3 TASKS.md ──────────────────────────────────────────────────────────────
p3_path = os.path.join(base, 'p3_product_user_jahnvi/TASKS.md')
p3 = open(p3_path, encoding='utf-8').read()

old_js = (
    "## frontend/app.js\n\n"
    "- [ ] `submitPlan()` — POST /plan-trip → store response → render Screen 3\n"
    "- [ ] `submitRefinement()` — POST /update-trip → render diff between old/new itinerary\n"
    "- [ ] `loadCoTravellers()` — POST /cotraveller → render top-3 profile cards on Screen 5\n"
    "- [ ] `startChat(profileId)` — POST /chat/start → returns `session_id` + topic chips → open chat panel\n"
    "- [ ] `openChatSocket(sessionId)` — open `WS /ws/chat/{session_id}`; bind send/receive handlers\n"
    "- [ ] `sendMessage(sessionId, content)` — send message over chat WebSocket\n"
    "- [ ] `onChatMessage(event)` — append received message to chat thread\n"
    "- [ ] `approveMatch(sessionId, itineraryId)` — POST /chat/approve → on success open itinerary socket\n"
    "- [ ] `denyMatch(sessionId)` — POST /chat/deny → renders fresh match cards from `RematchResponse`\n"
    "- [ ] `openItinerarySocket(itineraryId)` — open `WS /ws/itinerary/{itinerary_id}`; bind update handler\n"
    "- [ ] `onItineraryUpdate(event)` — apply `ItineraryUpdateEvent` to Screen 6 view in real time\n"
    "- [ ] `pollHealth()` — GET /health → update status bar indicator\n"
    "- [ ] `renderItinerary(itinerary)` — day tabs + activity cards from JSON\n"
    "- [ ] `renderCoTravellerCards(matches)` — profile cards with select/chat entry point\n"
    "- [ ] `renderTopicChips(topics)` — chip row; clicking a chip pre-fills the message input\n"
    "- [ ] `renderBudgetBreakdown(breakdown)` — bar or pie chart\n"
    "- [ ] Show loading state during API calls; error state for every failure mode (timeout, 422, 500, empty results, WebSocket disconnect) with a clear message and recovery action\n"
    "- [ ] Set `BASE_URL = 'http://localhost:8000'` for local dev; switch to `BASE_URL = '/api'` for Vercel\n"
    "- [ ] Set `WS_BASE_URL = 'ws://localhost:8000'` for local dev; switch to the deployed WSS URL for Vercel"
)

new_js = (
    "## frontend/app.js\n\n"
    "### SSE stream reading (Fetch Streams API)\n\n"
    "`POST /plan-trip` and `POST /update-trip` return `text/event-stream`. Do NOT use `EventSource`\n"
    "(GET-only). Use `fetch()` + `response.body.getReader()` to consume the SSE stream.\n\n"
    "- [ ] Implement `readSSEStream(url, payload, onEvent)`\n"
    "  - `fetch(url, {method: 'POST', body: JSON.stringify(payload)})`\n"
    "  - Get `response.body.getReader()`; decode chunks with `new TextDecoder()`\n"
    "  - Buffer partial lines across chunks; fire `onEvent(parsed)` for each `data: {...}` line\n"
    "  - On stream end or network error: update status bar to idle or error state\n\n"
    "### Pipeline submission\n\n"
    "- [ ] `submitPlan()`\n"
    "  - Collect form values; call `readSSEStream(BASE_URL + '/plan-trip', payload, handlePipelineEvent)`\n"
    "  - `handlePipelineEvent(event)`: update status bar on every stage; on `done` render Screen 3\n"
    "  - Stage labels: `persona_inferring` -> 'Understanding your travel style...';\n"
    "    `retrieving` -> 'Finding destinations...'; `generating_itinerary` -> 'Building your itinerary...';\n"
    "    `validating` -> 'Checking constraints...'; `revision` -> 'Refining based on validation...';\n"
    "    `matching_cotravellers` -> 'Finding travel companions...'\n"
    "- [ ] `submitRefinement()`\n"
    "  - Same SSE pattern via POST /update-trip\n"
    "  - On `done`: diff old vs new itinerary day cards and highlight changed activities\n\n"
    "### WebSocket -- co-traveller chat\n\n"
    "- [ ] `startChat(profileId)` -- POST /chat/start; store session_id and topic chips\n"
    "- [ ] `openChatSocket(sessionId)`\n"
    "  - `new WebSocket(WS_BASE_URL + '/ws/chat/' + sessionId)`\n"
    "  - `ws.onmessage`: parse ChatMessage JSON, append bubble to thread, scroll to bottom\n"
    "  - `ws.onclose`: show non-blocking reconnection banner with retry button\n"
    "  - `ws.onerror`: show error state without hiding the chat panel\n"
    "- [ ] `sendMessage(sessionId, content)` -- send ChatMessage JSON over the open WebSocket\n"
    "- [ ] `approveMatch(sessionId, itineraryId)` -- POST /chat/approve; on 200 call `openItinerarySocket`\n"
    "- [ ] `denyMatch(sessionId)` -- POST /chat/deny; re-render match cards from RematchResponse\n\n"
    "### WebSocket -- shared itinerary\n\n"
    "- [ ] `openItinerarySocket(itineraryId)`\n"
    "  - `new WebSocket(WS_BASE_URL + '/ws/itinerary/' + itineraryId)`\n"
    "  - `ws.onmessage`: parse ItineraryUpdateEvent JSON and call `applyItineraryUpdate(event)`\n"
    "- [ ] `applyItineraryUpdate(event)` -- handle each event_type:\n"
    "  - `co_traveller_added`: show co-traveller badge in Screen 6 header\n"
    "  - `note_added`: append note to the relevant day card\n"
    "  - `change_proposed`: show a diff overlay on the affected activity with accept/reject buttons\n"
    "  - `change_accepted` / `change_rejected`: resolve the diff overlay\n\n"
    "### Live match push (Screen 5)\n\n"
    "- [ ] Handle `pool_updated` event pushed by the server:\n"
    "  - Smoothly swap in the new match card at its rank position (CSS transition, not full re-render)\n"
    "  - Show a 'New match!' badge on the swapped card for 3 seconds\n\n"
    "### Rendering helpers\n\n"
    "- [ ] `renderItinerary(itinerary)` -- day tabs + activity cards with collapsible RAG explanations\n"
    "- [ ] `renderCoTravellerCards(matches)` -- profile cards with compatibility bar + match_reasons\n"
    "- [ ] `renderTopicChips(topics)` -- chip row; clicking a chip pre-fills the message input\n"
    "- [ ] `renderBudgetBreakdown(breakdown)` -- bar or pie chart\n"
    "- [ ] `pollHealth()` -- GET /health every 30s; update status bar dot (green / amber / red)\n\n"
    "### Error and loading states\n\n"
    "- [ ] Every fetch call: show loading skeleton while waiting; error banner with retry on failure\n"
    "- [ ] WebSocket disconnect: non-blocking reconnection banner; auto-retry with backoff\n"
    "- [ ] Empty co-traveller pool: 'No more matches available' state with option to proceed solo\n\n"
    "### Config\n\n"
    "- [ ] `BASE_URL = 'http://localhost:8000'` for local dev; `'/api'` for Vercel\n"
    "- [ ] `WS_BASE_URL = 'ws://localhost:8000'` for local dev; deployed WSS URL for Vercel"
)

if old_js in p3:
    p3 = p3.replace(old_js, new_js)
    print('P3 app.js section replaced')
else:
    print('P3: old_js not found in file')

with open(p3_path, 'w', encoding='utf-8') as f:
    f.write(p3)
print('P3 saved')
