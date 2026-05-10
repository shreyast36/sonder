# Sonder — Task Board

Each section lists one person's title, their ownership boundaries, and every task they need to complete. Work in your own folder. Each person defines their own schemas in their subfolder (`jahnvi/schemas/`, `ali/schemas/`, `shreyas/schemas/`, `mushahid/schemas/`). `shared/schemas.py` re-exports everything — always import from there.

---

## Shreyas — Lead AI Systems & Real-time Engineer

**Owns:** `shreyas/` · Candidate selection (embeddings + search + ranking) · Co-traveller matching algorithms · Real-time layer (chat, presence, shared itinerary, approval)

> **One-liner:** Shreyas finds and ranks the right destinations, activities, and people. He does not explain them — that is Ali's RAG.

### Schemas

- [x] `shreyas/schemas/enums.py` — `ApprovalStatus` — verify values match approval flow
- [x] `shreyas/schemas/cotraveller.py` — `CoTravellerProfile`, `CoTravellerMatch` — verify fields match Screen 4 and your matching algorithm output
- [x] `shreyas/schemas/chat.py` — `ChatMessage`, `ChatSession`, `ChatStartResponse`, `SharedItinerary`, `ItineraryUpdateEvent` — verify match Screens 5–8 and WebSocket layer

### Candidate Selection — Embeddings

- [x] `shreyas/retrieval/embeddings.py` — `embed_text()`, `embed_batch()`, `build_user_query()`, `build_refined_query()` — converts user profile into a Pinecone query vector (uses Ali's `EMBED_MODEL` from `shared/config.py`)

### Candidate Selection — Search

- [ ] `shreyas/retrieval/search.py` — given a user profile, query Ali's Pinecone index and return the top-N candidate destinations, activities, or co-travellers
  - `search_destinations(user_profile) → list[dict]` — top destination candidates for the trip plan
  - `search_activities(user_profile, destination) → list[dict]` — top activity candidates
  - `search_cotravellers(user_profile) → list[dict]` — top co-traveller profile candidates
  - `upsert_cotraveller_profile(profile)` — writes a user's profile vector into Pinecone so others can find them

> **Note:** This is pure SELECTION — finding the best candidates. Ali's RAG (`ali/rag/retriever.py`) separately fetches context about already-chosen activities to feed into the LLM. They call the same Pinecone index but for completely different purposes.

### Candidate Selection — Ranking

- [ ] `shreyas/ranking/filters.py` — hard constraint filters applied before scoring (budget, dates, avoid_list, must_haves)
- [ ] `shreyas/ranking/destination_ranker.py` — `score_destination()`, `rank_destinations()` — multi-signal scoring (vector similarity 60%, budget fit 20%, persona tag match 20%)
- [ ] `shreyas/ranking/activity_ranker.py` — `score_activity()`, `rank_activities()`

### Co-Traveller Matching Algorithms

- [ ] `shreyas/cotraveller/matching.py` — `score_compatibility()`, `get_top_matches()` — scores pairs of user profiles on interests, pace, and budget; returns top 3 `CoTravellerMatch` objects

### Real-time Layer

- [ ] `shreyas/cotraveller/chat.py` — `ConnectionManager` WebSocket engine (connect, disconnect, send, broadcast, 30s ping/heartbeat)
- [ ] `shreyas/cotraveller/presence.py` — `set_online()`, `set_offline()`, `is_online()`, `cleanup_stale_presence()`
- [ ] `shreyas/cotraveller/shared_itinerary.py` — `create_shared_itinerary()`, `add_note()`, `add_activity()`, `sync_changes()` with optimistic locking (version field)
- [ ] `shreyas/cotraveller/approval.py` — `approve_match()`, `deny_match()`, `get_approval_status()`

### Integration

- [ ] Confirm with Ali: `get_pinecone_index()` from `ali/vector/client.py` is available and `EMBED_DIMENSIONS` is in `shared/config.py` before building `search.py` or `embeddings.py`
- [ ] Confirm with Mushahid: `ConnectionManager` lives in `shreyas/cotraveller/chat.py` — Mushahid imports it from there in `routes/chat.py`
- [ ] Confirm with Ali: `generate_topics()` + `generate_icebreaker()` are called by Mushahid's `start_chat` route — you do not call them

---

## Jahnvi — Lead Product, UX & Frontend Engineer

**Owns:** `jahnvi/` · `shared/config.py` · `shared/currency.py` · Figma designs

### Schemas (do first — Shreyas and Mushahid are blocked on UserProfile)

Jahnvi owns only the user-facing input schemas. Each other team member owns their own schema files.

- [x] `jahnvi/schemas/enums.py` — `PacePreference`, `BudgetStyle`, `TravelStyle`, `EmotionIntent`
- [x] `jahnvi/schemas/user.py` — `TripConstraints` (`budget_usd` is always USD, `budget_currency` for display), `PersonaQuestionAnswers`, `UserProfile`; add `fcm_token` if using FCM

### Persona Templates

- [x] `jahnvi/data/persona_templates.py` — Review `PERSONA_TEMPLATES` (5 archetypes: Cultural Explorer, Adventure Seeker, Relaxed Wanderer, Party Traveller, Foodie). Confirm archetype names, interests, embed_keywords, and labels match the product spec and Figma

### User Pipeline

- [ ] `jahnvi/pipeline/module1_constraints.py` — `capture_constraints(raw_input) → TripConstraints` (async; accepts `budget_amount` + `budget_currency`, calls `convert_to_usd()` from `shared/currency.py`)
- [ ] `jahnvi/pipeline/module2_preferences.py` — `get_questions()`, `parse_answers() → PersonaQuestionAnswers`
- [ ] `jahnvi/pipeline/module3_persona.py` — `infer_persona()` (uses `PERSONA_TEMPLATES`), `infer_emotion()`, `build_compatibility_signals()`, `build_travel_style_embedding()`; `update_profile_from_feedback()` for refinement loop

### Multi-currency

- [x] `shared/currency.py` — Implement `convert_to_usd(amount, currency_code)` and `format_budget_display(budget_usd, currency_code)`. Set `EXCHANGE_RATE_API_KEY` in `.env` for live rates; static `FALLBACK_RATES` used in LOCAL_MODE

### Design (before any frontend code)

- [x] Figma: design system tokens (colours, typography, spacing) — implemented as `src/lib/tokens.js` (BG, BONE, GOLD, HAIRLINE, MUTE, DIM, GOLD_GRAD, ease)
- [x] Figma: all screens designed and implemented at full desktop width
- [x] Figma: component library (ActivityCard, MatchCard, ChatBubble, BottomNav) — all built
- [x] Share Figma link with team before starting implementation

### Frontend — Foundation

- [ ] `src/lib/firebase.js` — Initialise Firebase app, Auth, Firestore
- [ ] `src/lib/api.js` — All typed API calls with Firebase Auth token headers (see inline docs for full endpoint list)
- [ ] `src/hooks/useAuth.js` — `user`, `loading`, `signIn()`, `signOut()`, `signInWithGoogle()`
- [ ] `src/hooks/useFirestore.js` — `useDocument()`, `useCollection()` with `onSnapshot`
- [ ] `src/hooks/useWebSocket.js` — Chat WebSocket hook with reconnect + 30s ping heartbeat
- [ ] `src/hooks/useSSE.js` — SSE hook for itinerary generation stream
- [x] `src/styles/globals.css` — Tailwind directives + CSS custom properties from Figma tokens
- [x] `tailwind.config.js` — Brand palette and font tokens
- [x] `src/App.jsx` — All routes wired up with react-router-dom (10 routes incl. /discover)

### Frontend — Screens

- [x] Screen 1: `Welcome.jsx` — Hero, feature list, Start Planning CTA; 3D metallic Sonder logo
- [x] Screen 2: `TripPreferences.jsx` — Multi-step form (destination, dates, travel style, budget + currency); orange accent; ElegantInput with animated focus line; step tracker with spring pulse
- [x] Screen 3: `Itinerary.jsx` — Day tabs, activity cards with stagger entrance, "Why this?" expand, batch confirm; sky blue accent
- [x] Screen 4: `MatchDetail.jsx` — Profile card, animated SVG score ring, compatibility breakdown, AI topics list, Start Chat; violet accent
- [x] Screen 5: `Chat.jsx` — Chat UI with slide-in bubbles, typing indicator, icebreaker pre-fill, Review match CTA; rose accent
- [x] Screen 6: `ApproveDeny.jsx` — Match card with score ring, stat rows, approve/deny with green ripple confirm; violet + green accents
- [x] Screen 7: `SharedItinerary.jsx` — Collaborative itinerary with "Added by" labels, Export/PDF bottom sheet, Add activity sheet; cyan accent
- [x] Screen 8: `Notes.jsx` — Shared notes feed with slide-in bubbles, real-time add; teal accent
- [x] Screen 9: `Dashboard.jsx` — Upcoming trip card, companion matches, Plan new trip CTA; amber accent
- [x] Screen 10: `Discover.jsx` — Match discovery with filter sidebar (style, pace, score), animated card grid, MiniRing SVG per card; pink accent

### Frontend — Components

- [x] `ActivityCard.jsx` — Props: activity, time, whyThis, addedBy, onFeedback (swap/remove bottom sheet)
- [x] `MatchCard.jsx`
- [x] `ChatBubble.jsx`
- [x] `BottomNav.jsx` (itinerary variant + dashboard variant)
- [x] `AppBackground.jsx` — Breathing organic blobs + grain overlay (used on all app screens)
- [x] `SonderMark3D.jsx` — Three.js PBR metallic logo; `SonderNav3D` lockup used on all screens

### Deployment

- [ ] Update `vercel.json` API rewrite URL once Mushahid has a Render URL
- [ ] Deploy to Vercel and confirm all 10 screens load

---

## Ali — Lead AI Intelligence & Multi-model Engineer

**Owns:** `ali/` · Pinecone vector database · All LLM clients + routing · Itinerary generation · RAG (context retrieval + "Why this?" explanations) · Chat topics

> **One-liner:** Ali owns the database and everything that runs through an LLM. His RAG fetches factual context about already-chosen activities and uses an LLM to write the "Why this?" text. He does not decide which activities to show — that is Shreyas's search and ranking.

### Schemas

- [x] `ali/schemas/enums.py` — `ModelTier` — verify values are correct
- [x] `ali/schemas/trip.py` — `Destination`, `Activity`, `ItineraryActivity`, `ItineraryDay`, `Itinerary` — verify fields match your generation output and Figma Screen 3

### Vector Database (do first — Shreyas is blocked on this)

- [x] `ali/vector/client.py` — initialise Pinecone client, create index if missing, expose `get_pinecone_index()` for Shreyas's `search.py` to import
- [ ] Decide data source (Amadeus / Foursquare / Tripadvisor / curated CSV) and seed the index: `python -m scripts.seed_pinecone --namespace all`
- [ ] Decide `EMBED_MODEL` + `EMBED_DIMENSIONS`, write both into `shared/config.py` — Shreyas reads these in `embeddings.py`

### LLM Clients (do first — routing engine depends on these)

Ali configures two slots — Small and Large — via env vars. Mushahid separately configures two validator slots.

- [x] `ali/clients/base.py` — abstract interface (`complete()`, `stream()`, `model_name`, `tier`, `cost_per_1k_input_tokens`) — done
- [ ] Create one provider client file per provider you use (e.g. `ali/clients/openai_client.py`) — subclass `BaseLLMClient`, implement `complete()` and `stream()`

### Routing Engine

- [x] `ali/routing/classifier.py` — `classify(task_type) → "small" | "large"`, `estimate_tokens(prompt) → int`
- [x] `ali/routing/engine.py` — `route_request(task_type, prompt, system) → LLMResponse`, `stream_request(task_type, prompt, system) → AsyncGenerator`
  - SMALL → chat_topics, icebreaker, persona_label, quick_edit, short_explanation
  - LARGE → itinerary_generation, rag_explanation, conflict_resolution, complex_refinement
  - Reads `SMALL_MODEL_PROVIDER` + `LARGE_MODEL_PROVIDER` from `shared/config.py` to pick client

### Itinerary Generation

- [x] `ali/generation/prompts.py` — `ITINERARY_SYSTEM_PROMPT`, `build_itinerary_prompt()`, `REFINEMENT_SYSTEM_PROMPT`, `build_refinement_prompt()` (accepts `activity_feedback: list[ActivityFeedback]` for targeted swaps)
- [x] `ali/generation/output_parser.py` — `parse_itinerary()`, `validate_structure()`, retry on malformed JSON
- [x] `ali/generation/itinerary_generator.py` — `generate_itinerary()` streaming to Mushahid's SSE layer

### RAG — Context Retrieval + Explanation

> **What this is NOT:** Shreyas's `search.py` selects candidates from Pinecone (e.g. "show me the top 20 destinations"). Ali's RAG is different — once a specific activity is already chosen, it fetches factual text about that activity from Pinecone, then passes those facts to the LLM to write the "Why this?" blurb shown on Screen 3.

- [x] `ali/rag/retriever.py` — given an already-chosen activity or destination, call `shreyas/retrieval/search.py` to fetch relevant text context chunks from Pinecone
  - `retrieve_activity_context(activity, user_profile) → list[str]`
  - `retrieve_destination_context(destination, user_profile) → list[str]`
- [x] `ali/rag/explainer.py` — take the context chunks from `retriever.py` and pass them to the LLM to generate the explanation
  - `explain_activity(activity, context, user_profile) → str` — one-paragraph "Why this?" shown under each activity on Screen 3
  - `explain_day(day, context, user_profile) → str`
  - `explain_itinerary(itinerary, user_profile)` — populates `why_this` on every `ItineraryActivity`

### Chat Topics

- [x] `ali/generation/topics.py` — `generate_topics()` (5 topics, SMALL model), `generate_icebreaker()` (SMALL model); both called by Mushahid's `POST /chat/start` via `asyncio.gather`, returned in `ChatStartResponse`

### Integration

- [ ] Share `get_pinecone_index()` + `EMBED_DIMENSIONS` with Shreyas before he starts `search.py` — he is blocked until both exist
- [ ] Confirm streaming interface with Mushahid: `generate_itinerary()` must yield token chunks for SSE
- [ ] Confirm RAG call chain with Shreyas: `ali/rag/retriever.py` calls `shreyas/retrieval/search.py` — agree on function signatures

---

## Mushahid — Lead Backend, Validation & Infrastructure Engineer

**Owns:** `mushahid/` · FastAPI app · Pipeline orchestration · Validator + refinement loop · Real-time layer · Email/PDF export · Monitoring · Render deployment

### Schemas

- [x] `mushahid/schemas/enums.py` — `ValidationStatus`, `VisaRequirement` — verify values
- [x] `mushahid/schemas/validation.py` — `ConstraintSatisfaction`, `ValidationResult` — verify fields match your rule checks and LLM critic output
- [x] `mushahid/schemas/api.py` — `PlanTripRequest`, `PlanTripResponse`, `UpdateTripRequest`, `UpdateTripResponse`, `ActivityFeedback`, `EmailItineraryRequest`, `VisaInfo` — verify all API contracts match your route handlers

### FastAPI App (do first)

- [x] `mushahid/main.py` — Register all routers (plan_trip, update_trip, cotraveller, chat, health, visa, users, export); CORS; lifespan hooks (Firestore init, Sentry, PostHog, presence cleanup)
- [x] `mushahid/auth.py` — Firebase ID token verification (`verify_token` + `verify_ws_token` for WebSocket query param auth)

### Routes

- [x] `mushahid/routes/health.py` — `/health` pings Firestore + Pinecone, returns `{"status": "healthy"|"degraded", "services": {...}}`
- [x] `mushahid/routes/visa.py` — `/visa-check` with static JSON dataset (top 20 nationality/destination combos) or Sherpa API
- [x] `mushahid/routes/plan_trip.py` — `POST /plan-trip` → SSE stream via orchestrator
- [x] `mushahid/routes/update_trip.py` — `POST /update-trip` → refinement loop (passes both `feedback` and `activity_feedback` to loop)
- [x] `mushahid/routes/cotraveller.py` — `POST /cotraveller` + `POST /cotraveller/regenerate`
- [x] `mushahid/routes/chat.py` — `POST /chat/start` (returns `ChatStartResponse` with session + icebreaker + topics), `/approve`, `/deny`, `WS /ws/chat/{id}`
- [x] `mushahid/routes/export.py` — `POST /export/email` (sends itinerary via `shared/email.py`), `GET /export/pdf/{id}` (streams weasyprint PDF); both verify requester is a participant

### Real-time Layer

- [x] `mushahid/realtime/firestore.py` — Firebase Admin init, `write_itinerary_status()`, `write_itinerary()`, `get_itinerary()`, `create_user_profile()`, `update_user_profile()`
- [x] `mushahid/realtime/sse.py` — `format_event()`, `stream_pipeline_events()`
- [x] `mushahid/realtime/notifications.py` — `push_notification()`, `notify_match_found()`, `notify_itinerary_ready()`, `notify_co_traveller_approved()`

### Pipeline Orchestrator

- [x] `mushahid/pipeline/orchestrator.py` — `run_plan_trip_pipeline()` async generator — all 7 steps with SSE events; calls `explain_day()` per day as it's yielded (pipelined, not batched)

### Validation

Mushahid owns two validator LLMs — one that checks Small model outputs, one that checks Large model outputs. Both are configured via env vars and called directly from `critic.py` (not through Ali's routing engine).

- [x] `mushahid/validation/rules.py` — `check_budget()`, `check_duration()`, `check_pace()`, `check_must_haves()`, `check_avoid_list()`, `run_all_checks()`
- [x] `mushahid/validation/critic.py` — `validate_small_output(output) → ValidationResult`, `validate_large_output(output) → ValidationResult`; each calls its own validator LLM configured via `SMALL_VALIDATOR_PROVIDER` + `LARGE_VALIDATOR_PROVIDER` in `.env`

### Refinement Loop

- [x] `mushahid/refinement/loop.py` — `run_refinement_loop()` up to `MAX_REFINEMENT_ATTEMPTS`; handles both free-text `feedback` and `activity_feedback` list; re-embeds with updated signals before each Pinecone query (not just re-prompting)

### Email & PDF Export

- [ ] `shared/email.py` — `render_itinerary_html()` (inline-styled HTML), `send_itinerary_email()` (Resend / SendGrid / SES — set `EMAIL_PROVIDER` in `.env`)
- [x] `mushahid/routes/export.py` — Wire `render_itinerary_html()` into the PDF route via weasyprint; add `weasyprint` to `requirements.txt`

### Monitoring & Deployment

- [ ] Integrate Sentry SDK in `main.py`
- [ ] Integrate PostHog in `main.py` (events: trip_planned, match_found, chat_started, itinerary_emailed)
- [ ] `render.yaml` or Render dashboard — build + start commands, env vars, health check path (`/health`)
- [ ] Share backend URL with Jahnvi for `vercel.json` rewrite

---

## Dependency Order (build in this sequence)

```
Phase 1 (parallel — start now):
  Jahnvi   → user.py + enums.py schemas (unblocks Shreyas + Mushahid); pipeline modules 1–2
  Ali      → LLM clients + Pinecone vector DB setup + embed dimension decision
  Shreyas  → verify own schemas; begin embeddings once Ali has EMBED_DIMENSIONS
  Mushahid → verify own schemas; FastAPI app + auth + real-time layer

Phase 2 (parallel):
  Shreyas  → search + ranking (needs Ali's Pinecone client + EMBED_DIMENSIONS)
  Ali      → routing engine (needs clients)
  Mushahid → routes (needs Ali's clients)
  Jahnvi   → module3_persona (needs embed_text from Shreyas)

Phase 3 (parallel):
  Shreyas  → co-traveller matching + chat
  Ali      → generation + RAG (needs routing engine + Shreyas's search)
  Mushahid → validator + refinement loop (needs Ali's clients)

Phase 4:
  Mushahid → orchestrator (needs all of Phase 3)
  Mushahid → export routes
  Jahnvi   → frontend API integration: firebase.js, api.js, auth + SSE + WebSocket hooks
             (UI is done — just needs backend running)

Phase 5:
  All      → integration testing, deployment, monitoring
```
