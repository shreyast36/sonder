# Sonder — Task Board

Each section lists one person's title, their ownership boundaries, and every task they need to complete. Work in your own folder. Never define schemas outside `shared/` or `jahnvi/schemas/`.

---

## Shreyas — Lead AI Systems & Real-time Engineer

**Owns:** `shreyas/` · Co-traveller real-time layer · Pinecone index management

### Retrieval

- [ ] `shreyas/retrieval/client.py` — Initialise Pinecone client, create index if missing- [ ] `shreyas/retrieval/embeddings.py` — `embed_text()`, `embed_batch()`, `build_user_query()`- [ ] `shreyas/retrieval/search.py` — `search_destinations()`, `search_activities()`, `search_cotravellers()`, `upsert_*()` functions- [ ] Seed Pinecone index with destinations, activities, and synthetic co-traveller profiles

### Ranking & Filtering

- [ ] `shreyas/ranking/filters.py` — Hard constraint filters for destinations and activities- [ ] `shreyas/ranking/destination_ranker.py` — `score_destination()`, `rank_destinations()`- [ ] `shreyas/ranking/activity_ranker.py` — `score_activity()`, `rank_activities()`
### Co-Traveller Matching

- [ ] `shreyas/cotraveller/matching.py` — `score_compatibility()`, `get_top_matches()`- [ ] `shreyas/cotraveller/chat.py` — `ConnectionManager` WebSocket engine (connect, disconnect, send, broadcast)- [ ] `shreyas/cotraveller/presence.py` — `set_online()`, `set_offline()`, `is_online()`, `listen_presence()`- [ ] `shreyas/cotraveller/shared_itinerary.py` — `create_shared_itinerary()`, `add_note()`, `add_activity()`, `sync_changes()`- [ ] `shreyas/cotraveller/approval.py` — `approve_match()`, `deny_match()`, `get_approval_status()`
### Integration

- [ ] Confirm interface with Mushahid: `ConnectionManager` must be importable from `mushahid/routes/chat.py`
- [ ] Confirm interface with Ali: co-traveller topics use `match` + `user_profile` objects from `shared/schemas.py`

---

## Jahnvi — Lead Product, UX & Frontend Engineer

**Owns:** `jahnvi/` · `shared/schemas.py` · `shared/config.py` · Figma designs

### Schemas (do first — everyone is blocked on these)

- [x] `jahnvi/schemas/enums.py` — All enums: `PacePreference`, `BudgetStyle`, `TravelStyle`, `EmotionIntent`, `ValidationStatus`, `VisaRequirement`, `ModelTier`, `ApprovalStatus`- [x] `jahnvi/schemas/user.py` — `TripConstraints`, `PersonaQuestionAnswers`, `UserProfile`- [x] `jahnvi/schemas/trip.py` — `Destination`, `Activity`, `ItineraryActivity`, `ItineraryDay`, `Itinerary`- [x] `jahnvi/schemas/cotraveller.py` — `CoTravellerProfile`, `CoTravellerMatch`- [x] `jahnvi/schemas/chat.py` — `ChatMessage`, `ChatSession`, `SharedItinerary`, `ItineraryUpdateEvent`- [ ] Copy finalised models into `shared/schemas.py` and `shared/config.py` (single source of truth)

### User Pipeline

- [ ] `jahnvi/pipeline/module1_constraints.py` — `capture_constraints(raw_input) → TripConstraints`- [ ] `jahnvi/pipeline/module2_preferences.py` — `get_questions()`, `parse_answers() → PersonaQuestionAnswers`- [ ] `jahnvi/pipeline/module3_persona.py` — `infer_persona()`, `infer_emotion()`, `build_compatibility_signals()`, `build_travel_style_embedding()`
### Design (before any frontend code)

- [ ] Figma: design system tokens (colours, typography, spacing) matching dark purple UI
- [ ] Figma: all 9 screens at mobile size
- [ ] Figma: component library (ActivityCard, MatchCard, ChatBubble, BottomNav)
- [ ] Share Figma link with team before starting implementation

### Frontend — Foundation

- [ ] `src/lib/firebase.js` — Initialise Firebase app, Auth, Firestore
- [ ] `src/lib/api.js` — All typed API calls with Firebase Auth token headers
- [ ] `src/hooks/useAuth.js` — `user`, `loading`, `signIn()`, `signOut()`, `signInWithGoogle()`
- [ ] `src/hooks/useFirestore.js` — `useDocument()`, `useCollection()` with `onSnapshot`
- [ ] `src/hooks/useWebSocket.js` — Chat WebSocket hook with reconnect logic
- [ ] `src/hooks/useSSE.js` — SSE hook for itinerary generation stream
- [ ] `src/styles/globals.css` — Tailwind directives + CSS custom properties from Figma tokens
- [ ] `tailwind.config.js` — Brand palette and font tokens
- [ ] `src/App.jsx` — All 9 routes wired up with react-router-dom

### Frontend — Screens

- [ ] Screen 1: `Welcome.jsx` — Hero, feature list, Start Planning CTA
- [ ] Screen 2: `TripPreferences.jsx` — Form with SSE trigger on submit
- [ ] Screen 3: `Itinerary.jsx` — Day tabs, activity cards, streaming skeleton, "Why this?"
- [ ] Screen 4: `MatchDetail.jsx` — Profile card, match score, compatibility list, topics, Start Chat
- [ ] Screen 5: `Chat.jsx` — Real-time chat, typing indicators, seen receipts, AI icebreakers
- [ ] Screen 6: `ApproveDeny.jsx` — Match card, approve/deny buttons, live status
- [ ] Screen 7: `SharedItinerary.jsx` — Collaborative itinerary with "Added by" labels
- [ ] Screen 8: `Notes.jsx` — Shared notes feed
- [ ] Screen 9: `Dashboard.jsx` — Upcoming trip, active chats, other trips

### Frontend — Components

- [ ] `ActivityCard.jsx`
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

- [x] `ali/clients/base.py` — Abstract base class: `complete()`, `stream()`, model name, tier, cost- [ ] `ali/clients/openai_client.py`- [ ] `ali/clients/anthropic_client.py`- [ ] `ali/clients/google_client.py`- [ ] `ali/clients/groq_client.py`- [ ] `ali/clients/mistral_client.py`- [ ] `ali/clients/bedrock_client.py`
### Routing Engine

- [ ] `ali/routing/classifier.py` — `classify(task_type, context) → ModelTier`, `estimate_tokens(prompt) → int`- [ ] `ali/routing/engine.py` — `route_request(task_type, context) → LLMResponse`  - Route SMALL → fastest available small model
  - Route LARGE → best large model for context length
  - Route VALIDATOR → GPT-4o critic or Claude 3.5 Sonnet
  - Fall back to next model in tier if one fails

### Itinerary Generation

- [ ] `ali/generation/prompts.py` — `ITINERARY_SYSTEM_PROMPT`, `build_itinerary_prompt()`, `REFINEMENT_SYSTEM_PROMPT`, `build_refinement_prompt()`- [ ] `ali/generation/output_parser.py` — `parse_itinerary()`, `validate_structure()`, retry on malformed JSON- [ ] `ali/generation/itinerary_generator.py` — `generate_itinerary()` streaming to Mushahid's SSE layer
### RAG

- [ ] `ali/rag/retriever.py` — `retrieve_activity_context()`, `retrieve_destination_context()` via Shreyas's search- [ ] `ali/rag/explainer.py` — `explain_activity()`, `explain_itinerary()` — populates `why_this` field on each activity
### Chat Topics

- [ ] `ali/generation/topics.py` — `generate_topics()` (5 topics, SMALL model), `generate_icebreaker()` (SMALL model)
### Integration

- [ ] Confirm streaming interface with Mushahid: `generate_itinerary()` must yield token chunks for SSE
- [ ] Confirm RAG interface with Shreyas: `retrieve_activity_context()` calls `shreyas/retrieval/search.py`

---

## Mushahid — Lead Backend, Validation & Infrastructure Engineer

**Owns:** `mushahid/` · FastAPI app · Pipeline orchestration · Validator + refinement loop · Pipeline real-time layer · Monitoring · Render deployment

### FastAPI App (do first)

- [x] `mushahid/main.py` — FastAPI app, CORS, lifespan hooks, register all routers- [ ] Firebase Auth middleware — verify ID token on all protected routes

### Routes

- [x] `mushahid/routes/health.py` — `/health` checks Firestore + Pinecone reachability- [ ] `mushahid/routes/visa.py` — `/visa-check` with static lookup or third-party API- [ ] `mushahid/routes/plan_trip.py` — `POST /plan-trip` → SSE stream via orchestrator- [ ] `mushahid/routes/update_trip.py` — `POST /update-trip` → refinement loop → Firestore push- [ ] `mushahid/routes/cotraveller.py` — `POST /cotraveller` → Shreyas's search + matching- [ ] `mushahid/routes/chat.py` — `POST /chat/start`, `/approve`, `/deny` + `WS /ws/chat/{id}`
### Real-time Layer

- [ ] `mushahid/realtime/firestore.py` — Firebase Admin init, `write_itinerary_status()`, `write_itinerary()`, `get_itinerary()`- [x] `mushahid/realtime/sse.py` — `format_event()`, `stream_pipeline_events()`- [ ] `mushahid/realtime/notifications.py` — `push_notification()`, `notify_match_found()`, `notify_itinerary_ready()`, `notify_co_traveller_approved()`
### Pipeline Orchestrator

- [ ] `mushahid/pipeline/orchestrator.py` — `run_plan_trip_pipeline()` async generator, all 7 steps with SSE events
### Validation

- [ ] `mushahid/validation/rules.py` — 5 deterministic checks: `check_budget()`, `check_duration()`, `check_pace()`, `check_must_haves()`, `check_avoid_list()`, `run_all_checks()`- [ ] `mushahid/validation/critic.py` — `validate_with_llm()` via Ali's VALIDATOR tier
### Refinement Loop

- [ ] `mushahid/refinement/loop.py` — `run_refinement_loop()` max `MAX_REFINEMENT_ATTEMPTS` iterations
### Monitoring & Deployment

- [ ] Integrate Sentry SDK in `main.py` (error tracking)
- [ ] Integrate PostHog in `main.py` (event analytics: trip planned, match found, chat started)
- [ ] `render.yaml` or Render dashboard setup — build + start commands, env vars
- [ ] Confirm health check URL with Render
- [ ] Share backend URL with Jahnvi for `vercel.json` rewrite

---

## Dependency Order (build in this sequence)

```
Phase 1 (parallel):
  Jahnvi  → schemas first (everyone is blocked until these exist)
  Ali     → LLM clients

Phase 2 (parallel):
  Shreyas → retrieval + ranking (needs schemas)
  Ali     → routing engine (needs clients)
  Mushahid → FastAPI app + real-time layer (needs schemas)

Phase 3 (parallel):
  Shreyas → co-traveller matching + chat (needs retrieval)
  Ali     → generation + RAG (needs routing engine + Shreyas's search)
  Mushahid → routes + validator (needs Ali's clients)

Phase 4:
  Mushahid → orchestrator (needs all of Phase 3)
  Jahnvi   → frontend (needs API + Figma designs)

Phase 5:
  All     → integration testing, deployment, monitoring
```
