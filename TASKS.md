# Sonder — Task Board

Each section lists one person's title, their ownership boundaries, and every task they need to complete. Work in your own folder. Never define schemas outside `shared/` or `jahnvi/schemas/`.

---

## Shreyas — Lead AI Systems & Real-time Engineer

**Owns:** `shreyas/` · Co-traveller real-time layer · Pinecone index management

### Retrieval

- [ ] `shreyas/retrieval/client.py` — Initialise Pinecone client, create index if missing
- [ ] `shreyas/retrieval/embeddings.py` — `embed_text()`, `embed_batch()`, `build_user_query()`, `build_refined_query()`
- [ ] `shreyas/retrieval/search.py` — `search_destinations()`, `search_activities()`, `search_cotravellers()`, `upsert_cotraveller_profile()`
- [ ] Seed Pinecone index: `python -m scripts.seed_pinecone --namespace all`

### Ranking & Filtering

- [ ] `shreyas/ranking/filters.py` — Hard constraint filters (budget, dates, avoid_list, must_haves)
- [ ] `shreyas/ranking/destination_ranker.py` — `score_destination()`, `rank_destinations()`
- [ ] `shreyas/ranking/activity_ranker.py` — `score_activity()`, `rank_activities()`

### Co-Traveller Matching

- [ ] `shreyas/cotraveller/matching.py` — `score_compatibility()`, `get_top_matches()`
- [ ] `shreyas/cotraveller/chat.py` — `ConnectionManager` WebSocket engine (connect, disconnect, send, broadcast, ping/heartbeat)
- [ ] `shreyas/cotraveller/presence.py` — `set_online()`, `set_offline()`, `is_online()`, `cleanup_stale_presence()`
- [ ] `shreyas/cotraveller/shared_itinerary.py` — `create_shared_itinerary()`, `add_note()`, `add_activity()`, `sync_changes()` with optimistic locking (version field)
- [ ] `shreyas/cotraveller/approval.py` — `approve_match()`, `deny_match()`, `get_approval_status()`

### Integration

- [ ] Confirm with Mushahid: `ConnectionManager` is importable from `mushahid/routes/chat.py`
- [ ] Confirm with Ali: `generate_topics()` + `generate_icebreaker()` are called by Mushahid's `start_chat` route (not Shreyas directly)
- [ ] Announce `EMBED_MODEL` + `EMBED_DIMENSIONS` choice so Jahnvi can update `shared/config.py`

---

## Jahnvi — Lead Product, UX & Frontend Engineer

**Owns:** `jahnvi/` · `shared/schemas.py` · `shared/config.py` · `shared/currency.py` · Figma designs

### Schemas (do first — everyone is blocked on these)

- [ ] `jahnvi/schemas/enums.py` — Verify `PacePreference`, `BudgetStyle`, `TravelStyle`, `EmotionIntent`, `ValidationStatus`, `VisaRequirement`, `ModelTier`, `ApprovalStatus` match Figma; delete `scaffold_review()`
- [ ] `jahnvi/schemas/user.py` — Verify `TripConstraints` (note `budget_currency` field + `budget_usd` is always USD), `PersonaQuestionAnswers`, `UserProfile`; add `fcm_token` if using FCM; delete `scaffold_review()`
- [ ] `jahnvi/schemas/trip.py` — Verify `Destination`, `Activity`, `ItineraryActivity` (has `why_this`), `ItineraryDay` (note: field is `trip_date` not `date`), `Itinerary`; decide image source + add `image_url`; delete `scaffold_review()`
- [ ] `jahnvi/schemas/cotraveller.py` — Verify `CoTravellerProfile`, `CoTravellerMatch` match Screen 4 and Shreyas's matching needs; delete `scaffold_review()`
- [ ] `jahnvi/schemas/chat.py` — Verify `ChatMessage`, `ChatSession`, `ChatStartResponse` (session + icebreaker + topics), `SharedItinerary`, `ItineraryUpdateEvent` match Screens 5–8 and WebSocket layer; delete `scaffold_review()`
- [ ] `jahnvi/schemas/api.py` — Verify `PlanTripRequest`, `PlanTripResponse`, `UpdateTripRequest` (has `activity_feedback: list[ActivityFeedback]`), `UpdateTripResponse`, `ActivityFeedback`, `EmailItineraryRequest`
- [ ] Copy finalised models into `shared/schemas.py` re-exports (already wired — just ensure all new models are exported)

### Persona Templates

- [ ] `jahnvi/data/persona_templates.py` — Review `PERSONA_TEMPLATES` (5 archetypes: Cultural Explorer, Adventure Seeker, Relaxed Wanderer, Party Traveller, Foodie). Confirm archetype names, interests, embed_keywords, and labels match the product spec and Figma. Delete `scaffold_review()`

### User Pipeline

- [ ] `jahnvi/pipeline/module1_constraints.py` — `capture_constraints(raw_input) → TripConstraints` (async; accepts `budget_amount` + `budget_currency`, calls `convert_to_usd()` from `shared/currency.py`)
- [ ] `jahnvi/pipeline/module2_preferences.py` — `get_questions()`, `parse_answers() → PersonaQuestionAnswers`
- [ ] `jahnvi/pipeline/module3_persona.py` — `infer_persona()` (uses `PERSONA_TEMPLATES`), `infer_emotion()`, `build_compatibility_signals()`, `build_travel_style_embedding()`; `update_profile_from_feedback()` for refinement loop

### Multi-currency

- [ ] `shared/currency.py` — Implement `convert_to_usd(amount, currency_code)` and `format_budget_display(budget_usd, currency_code)`. Set `EXCHANGE_RATE_API_KEY` in `.env` for live rates; static `FALLBACK_RATES` used in LOCAL_MODE

### Design (before any frontend code)

- [ ] Figma: design system tokens (colours, typography, spacing) matching dark purple UI
- [ ] Figma: all 9 screens at mobile size
- [ ] Figma: component library (ActivityCard, MatchCard, ChatBubble, BottomNav)
- [ ] Share Figma link with team before starting implementation

### Frontend — Foundation

- [ ] `src/lib/firebase.js` — Initialise Firebase app, Auth, Firestore
- [ ] `src/lib/api.js` — All typed API calls with Firebase Auth token headers (see inline docs for full endpoint list)
- [ ] `src/hooks/useAuth.js` — `user`, `loading`, `signIn()`, `signOut()`, `signInWithGoogle()`
- [ ] `src/hooks/useFirestore.js` — `useDocument()`, `useCollection()` with `onSnapshot`
- [ ] `src/hooks/useWebSocket.js` — Chat WebSocket hook with reconnect + 30s ping heartbeat
- [ ] `src/hooks/useSSE.js` — SSE hook for itinerary generation stream
- [ ] `src/styles/globals.css` — Tailwind directives + CSS custom properties from Figma tokens
- [ ] `tailwind.config.js` — Brand palette and font tokens
- [ ] `src/App.jsx` — All 9 routes wired up with react-router-dom

### Frontend — Screens

- [ ] Screen 1: `Welcome.jsx` — Hero, feature list, Start Planning CTA
- [ ] Screen 2: `TripPreferences.jsx` — Form with currency selector (send `budget_amount` + `budget_currency`, not `budget_usd`); SSE trigger on submit
- [ ] Screen 3: `Itinerary.jsx` — Day tabs, activity cards, streaming skeleton, "Why this?" expand, per-activity swap/remove (long-press → bottom sheet → batch confirm)
- [ ] Screen 4: `MatchDetail.jsx` — Profile card, match score, compatibility breakdown, AI topics list, Start Chat
- [ ] Screen 5: `Chat.jsx` — Real-time chat, typing indicators, seen receipts, icebreaker pre-fill, AI topic chips from `ChatStartResponse`
- [ ] Screen 6: `ApproveDeny.jsx` — Match card, approve/deny buttons, live status via Firestore
- [ ] Screen 7: `SharedItinerary.jsx` — Collaborative itinerary with "Added by" labels; email/PDF export button in header
- [ ] Screen 8: `Notes.jsx` — Shared notes feed with real-time Firestore updates
- [ ] Screen 9: `Dashboard.jsx` — Upcoming trip, active chats, other trips

### Frontend — Components

- [ ] `ActivityCard.jsx` — Props: activity, time, whyThis, addedBy, onFeedback (for swap/remove bottom sheet)
- [ ] `MatchCard.jsx`
- [ ] `ChatBubble.jsx`
- [ ] `BottomNav.jsx` (itinerary variant + dashboard variant)

### Deployment

- [ ] Update `vercel.json` API rewrite URL once Mushahid has a Render URL
- [ ] Deploy to Vercel and confirm all 9 screens load

---

## Ali — Lead AI Intelligence & Multi-model Engineer

**Owns:** `ali/` · Routing engine · All LLM clients · Itinerary generation · RAG · Chat topics

### LLM Clients (do first — routing engine depends on these)

- [ ] `ali/clients/base.py` — Review abstract interface (`complete()`, `stream()`, `model_name`, `tier`, `cost_per_1k_input_tokens`); add any additional methods needed (e.g. `count_tokens`); delete `scaffold_review()`
- [ ] `ali/clients/openai_client.py`
- [ ] `ali/clients/anthropic_client.py`
- [ ] `ali/clients/google_client.py`
- [ ] `ali/clients/groq_client.py`
- [ ] `ali/clients/mistral_client.py`
- [ ] `ali/clients/bedrock_client.py`

### Routing Engine

- [ ] `ali/routing/classifier.py` — `classify(task_type, context) → ModelTier`, `estimate_tokens(prompt) → int`
- [ ] `ali/routing/engine.py` — `route_request(task_type, context) → LLMResponse`
  - SMALL → fastest available small model (chat_topics, icebreaker, persona_label, quick_edit)
  - LARGE → best large model for context length (itinerary_generation, rag_explanation, conflict_resolution)
  - VALIDATOR → critic check (validate_itinerary, critic_check)
  - Fallback to next model in tier if one fails

### Itinerary Generation

- [ ] `ali/generation/prompts.py` — `ITINERARY_SYSTEM_PROMPT`, `build_itinerary_prompt()`, `REFINEMENT_SYSTEM_PROMPT`, `build_refinement_prompt()` (accepts `activity_feedback: list[ActivityFeedback]` for targeted swaps)
- [ ] `ali/generation/output_parser.py` — `parse_itinerary()`, `validate_structure()`, retry on malformed JSON
- [ ] `ali/generation/itinerary_generator.py` — `generate_itinerary()` streaming to Mushahid's SSE layer

### RAG

- [ ] `ali/rag/retriever.py` — `retrieve_activity_context()`, `retrieve_destination_context()` via Shreyas's search
- [ ] `ali/rag/explainer.py` — `explain_activity()`, `explain_day()`, `explain_itinerary()` — populates `why_this` on each `ItineraryActivity`

### Chat Topics

- [ ] `ali/generation/topics.py` — `generate_topics()` (5 topics, SMALL model), `generate_icebreaker()` (SMALL model); both called by Mushahid's `POST /chat/start` route, result returned in `ChatStartResponse`

### Integration

- [ ] Confirm streaming interface with Mushahid: `generate_itinerary()` must yield token chunks for SSE
- [ ] Confirm RAG interface with Shreyas: `retrieve_activity_context()` calls `shreyas/retrieval/search.py`
- [ ] Announce model and embed dimension choices early — Shreyas is blocked on `EMBED_DIMENSIONS` for Pinecone

---

## Mushahid — Lead Backend, Validation & Infrastructure Engineer

**Owns:** `mushahid/` · FastAPI app · Pipeline orchestration · Validator + refinement loop · Real-time layer · Email/PDF export · Monitoring · Render deployment

### FastAPI App (do first)

- [ ] `mushahid/main.py` — Register all routers (plan_trip, update_trip, cotraveller, chat, health, visa, users, export); CORS; lifespan hooks (Firestore init, Sentry, PostHog, presence cleanup)
- [ ] `mushahid/auth.py` — Firebase ID token verification (`verify_token` + `verify_ws_token` for WebSocket query param auth)

### Routes

- [ ] `mushahid/routes/health.py` — `/health` pings Firestore + Pinecone, returns `{"status": "healthy"|"degraded", "services": {...}}`
- [ ] `mushahid/routes/visa.py` — `/visa-check` with static JSON dataset (top 20 nationality/destination combos) or Sherpa API
- [ ] `mushahid/routes/plan_trip.py` — `POST /plan-trip` → SSE stream via orchestrator
- [ ] `mushahid/routes/update_trip.py` — `POST /update-trip` → refinement loop (passes both `feedback` and `activity_feedback` to loop)
- [ ] `mushahid/routes/cotraveller.py` — `POST /cotraveller` + `POST /cotraveller/regenerate`
- [ ] `mushahid/routes/chat.py` — `POST /chat/start` (returns `ChatStartResponse` with session + icebreaker + topics), `/approve`, `/deny`, `WS /ws/chat/{id}`
- [ ] `mushahid/routes/export.py` — `POST /export/email` (sends itinerary via `shared/email.py`), `GET /export/pdf/{id}` (streams weasyprint PDF); both verify requester is a participant

### Real-time Layer

- [ ] `mushahid/realtime/firestore.py` — Firebase Admin init, `write_itinerary_status()`, `write_itinerary()`, `get_itinerary()`, `get_shared_itinerary()`
- [x] `mushahid/realtime/sse.py` — `format_event()`, `stream_pipeline_events()`
- [ ] `mushahid/realtime/notifications.py` — `push_notification()`, `notify_match_found()`, `notify_itinerary_ready()`, `notify_co_traveller_approved()`

### Pipeline Orchestrator

- [ ] `mushahid/pipeline/orchestrator.py` — `run_plan_trip_pipeline()` async generator — all 7 steps with SSE events; calls `explain_day()` per day as it's yielded (pipelined, not batched)

### Validation

- [ ] `mushahid/validation/rules.py` — `check_budget()`, `check_duration()`, `check_pace()`, `check_must_haves()`, `check_avoid_list()`, `run_all_checks()`
- [ ] `mushahid/validation/critic.py` — `validate_with_llm()` via Ali's VALIDATOR tier

### Refinement Loop

- [ ] `mushahid/refinement/loop.py` — `run_refinement_loop()` up to `MAX_REFINEMENT_ATTEMPTS`; handles both free-text `feedback` and `activity_feedback` list; re-embeds with updated signals before each Pinecone query (not just re-prompting)

### Email & PDF Export

- [ ] `shared/email.py` — `render_itinerary_html()` (inline-styled HTML), `send_itinerary_email()` (Resend / SendGrid / SES — set `EMAIL_PROVIDER` in `.env`)
- [ ] `mushahid/routes/export.py` — Wire `render_itinerary_html()` into the PDF route via weasyprint; add `weasyprint` to `requirements.txt`

### Monitoring & Deployment

- [ ] Integrate Sentry SDK in `main.py`
- [ ] Integrate PostHog in `main.py` (events: trip_planned, match_found, chat_started, itinerary_emailed)
- [ ] `render.yaml` or Render dashboard — build + start commands, env vars, health check path (`/health`)
- [ ] Share backend URL with Jahnvi for `vercel.json` rewrite

---

## Dependency Order (build in this sequence)

```
Phase 1 (parallel):
  Jahnvi   → schemas first — everyone is blocked until these are finalised
  Ali      → LLM clients

Phase 2 (parallel):
  Shreyas  → retrieval + ranking (needs schemas)
  Ali      → routing engine (needs clients)
  Mushahid → FastAPI app + auth + real-time layer (needs schemas)
  Jahnvi   → pipeline modules 1–2 (no external deps)

Phase 3 (parallel):
  Shreyas  → co-traveller matching + chat (needs retrieval)
  Ali      → generation + RAG (needs routing engine + Shreyas's search)
  Mushahid → routes + validator (needs Ali's clients)
  Jahnvi   → module3_persona (needs embed_text from Shreyas)

Phase 4:
  Mushahid → orchestrator (needs all of Phase 3)
  Mushahid → refinement loop + export routes
  Jahnvi   → frontend (needs API + Figma designs)

Phase 5:
  All      → integration testing, deployment, monitoring
```
