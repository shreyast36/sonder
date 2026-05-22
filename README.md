# Sonder — AI Co-Traveller Trip Planner

> Plan smarter. Find your perfect co-traveller.

AI-powered trip planning, smart co-traveller matching, and real-time collaboration — all in one product.

---

## What It Does

Sonder takes a user from zero to a fully personalised, day-by-day itinerary and then matches them with a compatible co-traveller to plan, chat, and travel together in real time.

**User journey:**
1. Enter trip basics (destination, dates, budget in any currency, must-haves)
2. Answer five oblique persona questions (social role, trip feeling, friction response, ideal atmosphere, plus a free-text "small thing that made you happy lately")
3. Get a persona reveal — descriptor, paragraph, bullets, and an emotional-tone subtitle — backed by inferred push/pull dimensions + an emotional signature
4. Receive a live-generated itinerary with "Why this?" explanations per activity, auto-saved to your trip history
5. Browse Past Trips on the dashboard, write Journal entries, and explore the Destination Discovery feed (public entries from other travellers in your city)
6. Get matched with compatible synthetic co-travellers (LLM-designed personas with stylised AI portraits + assigned voices)
7. Chat in real time with presence indicators, typing dots, read receipts, in-app banner notifications when away from the chat, and OS push notifications when the browser is closed
8. Approve, build a shared itinerary together, then email or download it as PDF

---

## Team Ownership

| Person | Role | Owns |
|---|---|---|
| **Jahnvi** | Lead Product, UX & Frontend | User input schemas (`UserProfile`, `TripConstraints`, `PersonaQuestionAnswers`) · User input pipeline · GoEmotions classifier · React frontend |
| **Shreyas** | Lead AI Systems & Real-time | Co-traveller + chat schemas · Candidate **selection** (embeddings + search + ranking) · Co-traveller matching · Real-time layer (chat, presence, shared itinerary, approval) |
| **Ali** | Lead AI Intelligence | Trip/itinerary schemas · Pinecone vector database · All LLM clients + routing · Itinerary generation · RAG **explanation** ("Why this?") · Chat topics + icebreaker + persona reply |
| **Mushahid** | Lead Backend & Infrastructure | API + validation schemas · FastAPI app · Pipeline orchestrator · Validation + refinement loop · Firebase + Web Push real-time layer · Emotional signature inference · Deployment |

### Shreyas vs. Ali — the key distinction

Both Shreyas and Ali work with Pinecone and AI, but they do completely different things:

| | Shreyas | Ali |
|---|---|---|
| **Question answered** | Which destinations/activities/people should we show this user? | Why was this specific activity chosen? What should the itinerary say? |
| **Pinecone usage** | Query the index to **select** top-N candidates for ranking | Query the index to **fetch context** about an already-chosen activity |
| **Output** | Ranked candidate list → goes into the trip plan | LLM-generated text → shown to the user as "Why this?" or itinerary copy |
| **When it runs** | Pipeline steps 2, 3, 7 (before the itinerary exists) | After the itinerary is generated (one activity at a time) |

Ali's RAG retriever calls Shreyas's search functions — Shreyas provides the interface, Ali uses it for a different purpose.

---

## Architecture

### Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Framer Motion |
| Auth | Firebase Auth (Google + email/password) |
| Real-time DB | Cloud Firestore (named DB via `FIRESTORE_DATABASE_ID`) |
| Backend API | FastAPI (Python 3.11) on Render |
| Vector DB | Pinecone — owned and managed by Ali |
| AI — Small models | Per-provider config: `ANTHROPIC_SMALL_MODEL` / `OPENAI_SMALL_MODEL` (defaults baked in `shared/config.py`) |
| AI — Large models | Per-provider config: `ANTHROPIC_LARGE_MODEL` / `OPENAI_LARGE_MODEL` |
| AI — Validators | `SMALL_VALIDATOR_PROVIDER` + `LARGE_VALIDATOR_PROVIDER` (Mushahid) |
| AI — Image | OpenAI `gpt-image-1` (only used at seed time for synthetic co-traveller portraits) |
| AI — Voice (planned) | OpenAI TTS — voices pre-assigned per synthetic persona via deterministic hash |
| AI — Emotion classifier | GoEmotions 27-label cosine classifier (in-memory; backs the emotional-signature inferrer) |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) |
| Email | Resend / SendGrid / SES — set `EMAIL_PROVIDER` in `.env` |
| Web Push | Service worker (`public/sw.js`) + VAPID + `pywebpush` (backend) |
| Frontend hosting | Vercel |
| Backend hosting | Render |
| Monitoring | Sentry (errors) + PostHog (analytics) |

### Tier router

Provider selection per tier is independent from model name. `SMALL_MODEL_PROVIDER` / `LARGE_MODEL_PROVIDER` pick the primary (`anthropic` | `openai`); each provider client reads its own model name (`ANTHROPIC_SMALL_MODEL`, `OPENAI_SMALL_MODEL`, etc) so the engine can fall back to the alternate provider without leaking the wrong model id across vendors. Legacy single-name vars (`SMALL_MODEL_NAME` / `LARGE_MODEL_NAME`) are still honored for backward-compat as a fallback for the matching provider.

### Folder Structure

```
sonder/
├── shared/                  # Config, utilities, schema aggregator
│   ├── schemas.py           # Re-exports all models — import from here
│   ├── config.py            # All env var reads — never call os.getenv() outside here
│   ├── currency.py          # Multi-currency conversion (live rates + fallback)
│   └── email.py             # Transactional email
│
├── jahnvi/                  # User Pipeline + User Schemas + Frontend
│   ├── schemas/             # TripConstraints, PersonaQuestionAnswers, UserProfile
│   ├── pipeline/            # Modules 1–3: constraints → preferences → persona
│   ├── data/                # persona_labels.py, dimensions.py, emotions.py, classify_emotions.py
│   └── frontend/            # React + Vite app, hooks, Firebase client, service worker
│       └── public/sw.js     # Web Push service worker
│
├── shreyas/                 # Candidate Selection + Real-time
│   ├── schemas/             # CoTraveller + Chat models, ApprovalStatus enum
│   ├── retrieval/           # Embeddings + Pinecone search
│   ├── ranking/             # Filters, scores, ranks candidates
│   └── cotraveller/         # Matching, ConnectionManager (WS rooms + user channels),
│                            #   presence, shared itinerary, approval
│
├── ali/                     # AI Intelligence Layer
│   ├── schemas/             # Trip/Itinerary models, ModelTier enum
│   ├── vector/              # Pinecone index setup + batched embeddings
│   ├── clients/             # LLM provider wrappers
│   ├── routing/             # Task classifier + multi-model routing engine
│   ├── generation/          # Itinerary generation, chat topics/icebreaker/reply,
│   │                        #   PPM context engineering, output cleanup
│   └── rag/                 # retriever.py + explainer.py (Why this?)
│
├── mushahid/                # Backend API + Orchestration + Validation
│   ├── schemas/             # API request/response models, ValidationResult
│   ├── main.py              # FastAPI app entry point
│   ├── auth.py              # Firebase ID token verification (header + first-message WS)
│   ├── routes/              # All HTTP + WebSocket endpoints
│   ├── persona/             # taxonomy.py + emotional_signature.py — inference module
│   ├── pipeline/            # Orchestrator: runs all steps, streams SSE
│   ├── validation/          # LLM critic + deterministic rule checks
│   ├── refinement/          # Closed-loop regeneration until validator approves
│   └── realtime/            # firestore.py, sse.py, web_push.py (VAPID send helper)
│
├── scripts/
│   ├── seed_pinecone.py             # Destinations + activities (Ali's namespaces)
│   ├── seed_cotravellers.py         # LLM-designed personas + gpt-image-1 portraits
│   └── generate_vapid_keys.py       # One-time VAPID keypair generator for Web Push
│
├── .env.example
├── requirements.txt
└── TASKS.md
```

### Pipeline — How It All Connects

```
POST /persona-infer
│  embed user text  ┐
│  GoEmotions class ┴── asyncio.gather
│  emotion register injected into both LLM calls
│  ┌─ persona LLM (descriptor / paragraph / bullets / top_push / top_interests)
│  └─ emotional_signature inferrer (taxonomy × evidence × goemotions)
│  merge → compatibility_signals + emotional_tone surfaced to UI

POST /plan-trip
│
├── [Jahnvi]   Module 1 — capture_constraints()       convert budget to USD, parse dates
├── [Jahnvi]   Module 2 — parse_answers()             preference questions → PersonaQuestionAnswers
├── [Jahnvi]   Module 3 — infer_persona/emotion()     classify archetype + emotional intent
│                                                      → SSE: persona_inferring / persona_inferred
│
├── [Shreyas]  search_destinations/activities()        SELECTION — query Pinecone for candidates
│                                                      → SSE: retrieving / retrieval_done
├── [Shreyas]  rank_destinations/activities()          score + filter by budget/pace/persona
│                                                      → SSE: ranking / ranked
│
├── [Ali]      generate_itinerary()                    LARGE model — stream itinerary JSON tokens
│                                                      → SSE: generating / itinerary_generated
├── [Ali]      explain_itinerary()                     RAG — fetch context, write "Why this?"
│              retriever calls Shreyas's search.py     → SSE: explaining
│
├── [Mushahid] run_all_checks() + validate_large_output()  rule checks + Large Validator critic
│              → if REVISE: run_refinement_loop()      re-rank → re-generate → re-validate
│                                                      → SSE: validating / revision / validated
│
├── [Shreyas]  search_cotravellers() + get_top_matches()  match compatible users
│                                                      → SSE: matching_cotravellers / matched
│
└── → SSE: done { PlanTripResponse }   (auto-saved to trip history client-side)
```

### LLM Architecture

| Slot | Owner | Purpose | Config |
|---|---|---|---|
| **Small** | Ali | Chat topics, icebreaker, persona label, quick edits, emotional-signature inference, "Why this?" | `ANTHROPIC_SMALL_MODEL` or `OPENAI_SMALL_MODEL` |
| **Large** | Ali | Itinerary generation, complex refinement, chat reply (multi-turn persona) | `ANTHROPIC_LARGE_MODEL` or `OPENAI_LARGE_MODEL` |
| **Small Validator** | Mushahid | Verifies Small outputs (persona labels, topics) | `SMALL_VALIDATOR_PROVIDER` + `SMALL_VALIDATOR_MODEL_NAME` |
| **Large Validator** | Mushahid | Verifies Large outputs (full itineraries) | `LARGE_VALIDATOR_PROVIDER` + `LARGE_VALIDATOR_MODEL_NAME` |
| **Image** | seed-time only | Synthetic co-traveller portraits via `images.generate(model="gpt-image-1")` | `OPENAI_API_KEY` |

The router engine reads provider per tier from env; each provider client reads its own model name so cross-provider fallback can't 404.

### Real-Time Layer

| Feature | Transport | Owner |
|---|---|---|
| Itinerary generation progress | SSE (`/api/plan-trip`) | Mushahid |
| Real-time chat messages | WebSocket (`/api/ws/chat/{session_id}`, first-message auth) | Shreyas |
| Typing indicators + seen receipts | WebSocket | Shreyas |
| Co-traveller presence (TTL-based) | WebSocket broadcast + Firestore `presence/{uid}` | Shreyas |
| In-app banner notifications (any page, while app is open) | WebSocket (`/api/ws/notifications`) | Mushahid |
| OS / browser push notifications (closed tab or browser) | Web Push (VAPID + service worker + `pywebpush`) | Mushahid |
| Shared itinerary edits | Firestore + optimistic locking via `version` field | Shreyas |
| Approval status (live) | Firestore | Shreyas |

WebSocket auth uses the first-message pattern (token in initial JSON payload, never in query string). Web Push silently no-ops when VAPID keys aren't configured — the in-app banner + Notification API fallback still work.

### Synthetic Co-Travellers

The matching pool is seeded with LLM-designed personas (no randomuser.me / stock photos). For each diversity-matrix slot (emotional signature × age bracket × home city), the LARGE LLM writes a full persona JSON — all four PPM radio answers, the free-text `small_thing`, a recent-trip memory ("voice anchor" for chat grounding), 1–2 quirks. Each persona then gets:

- A stylised cinematic portrait from `gpt-image-1` (painterly, explicitly not photoreal, so the persona's syntheticness stays visible)
- A stable voice id from a deterministic hash of `profile_id` against the OpenAI TTS whitelist
- An emotional signature via the same inferrer real users hit
- A rich embedding text (PPM answers + voice anchor + quirks + signature/tone) upserted to the `cotravellers` Pinecone namespace

Every record carries `is_seed: True` for "Sonder Curated" disclosure. Seed cost is ~$2–4 for 50 personas (gpt-image-1 dominates).

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Firebase project (Auth + Firestore enabled)
- Pinecone account
- OpenAI + Anthropic API keys
- (Optional) VAPID keypair for Web Push

### Backend

```bash
git clone https://github.com/shreyast36/sonder
cd sonder
pip install -r requirements.txt

cp .env.example .env
# Fill in all keys

# (Optional) Generate VAPID keys for closed-browser push notifications:
python -m scripts.generate_vapid_keys
# Paste the printed VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY into .env

# Seed Pinecone destinations + activities (Ali runs this once per environment)
python -m scripts.seed_pinecone --namespace all

# Seed synthetic co-travellers (LLM personas + gpt-image-1 portraits)
python -m scripts.seed_cotravellers --count 50

uvicorn mushahid.main:app --reload --port 8000
```

### Frontend

```bash
cd jahnvi/frontend
npm install
cp ../../.env.example .env.local
# Fill in VITE_ prefixed Firebase config values
npm run dev
# → http://localhost:5173
```

Avatars generated by `seed_cotravellers.py` land under `seed_assets/cotraveller_avatars/` (gitignored). Point your static-file CDN at that directory in deployments — the `avatar_url` stored on each persona is a relative path you'll prefix with your CDN host.

---

## API Reference

### Auth / Users
| Method | Route | Returns |
|---|---|---|
| `GET` | `/api/users/profile` | `UserProfile` — 404 if not yet created |
| `POST` | `/api/users/profile` | Creates profile on first login |
| `POST` | `/api/auth/password-reset` (public) | Public — silently succeeds to prevent account enumeration |

### Trip planning
| Method | Route | Returns |
|---|---|---|
| `POST` | `/api/persona-infer` | Descriptor / paragraph / bullets + top_push / top_interests + `emotional_tone` |
| `POST` | `/api/plan-trip` | SSE stream → `PlanTripResponse` |
| `POST` | `/api/update-trip` | `UpdateTripResponse` — free-text or per-activity feedback |
| `GET`  | `/api/visa-check?destination_country=X&nationality=Y` (public) | `VisaInfo` |

### Itineraries / trip history
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/api/itineraries/current` | The user's active dashboard trip (or `{itinerary: null}`) |
| `GET`  | `/api/itineraries/list` | All saved trips, newest first (slim summaries) |
| `POST` | `/api/itineraries/{id}/save` | Append to history + mark current |
| `POST` | `/api/itineraries/set-current` | Switch hero trip (must already be saved) |
| `GET`  | `/api/itineraries/{id}/companion-prefs` | Per-trip companion intake answers |
| `POST` | `/api/itineraries/{id}/companion-prefs` | Persist intake answers (sanitised) |

### Journal + destination discovery
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/api/itineraries/{id}/journal` | All journal entries for a trip |
| `POST` | `/api/itineraries/{id}/journal` | Create/update an entry (private or public) |
| `DELETE` | `/api/journal/{entry_id}` | Soft-delete |
| `GET`  | `/api/destinations/{city}/journal` | Public entries from the destination feed |

### Co-traveller matching + chat
| Method | Route | Returns |
|---|---|---|
| `POST` | `/api/cotraveller` | `list[CoTravellerMatch]` |
| `POST` | `/api/cotraveller/regenerate` | Fresh matches, excludes prior profiles |
| `GET`  | `/api/cotraveller/profile/{profile_id}` | Single `CoTravellerMatch` for the detail page |
| `POST` | `/api/chat/start` | `ChatStartResponse` (session + icebreaker + 5 topics) |
| `GET`  | `/api/chat/session/{session_id}` | Session metadata |
| `GET`  | `/api/chat/{session_id}/messages` | Full message history |
| `GET`  | `/api/chat/{session_id}/presence/{user_id}` | Online + last_seen |
| `POST` | `/api/chat/approve` | `{"status": "approved" \| "pending"}` |
| `POST` | `/api/chat/deny` | `{"status": "denied"}` |
| `WS`   | `/api/ws/chat/{session_id}` | Chat stream — first-message auth |
| `WS`   | `/api/ws/notifications` | Global notification channel — first-message auth |

### Web Push
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/api/push/vapid-public-key` (public) | `{key}` — 503 when web push isn't configured |
| `POST` | `/api/push/subscribe` | Upserts the browser's `PushSubscription` for the user |
| `POST` | `/api/push/unsubscribe` | Drops a subscription by endpoint |

### Export
| Method | Route | Returns |
|---|---|---|
| `POST` | `/api/export/email` | `{"sent_to": [...]}` |
| `POST` | `/api/export/email/test` | Self-test send |
| `GET`  | `/api/export/pdf/{itinerary_id}?token=…` | PDF stream |

### Health
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/health` (public) | `{"status": "healthy" \| "degraded", "services": {...}}` |

---

## Key Design Decisions

### Persona inference — five oblique questions, no archetype labels

The trip-preferences form asks five questions designed to surface latent travel psychology without ever naming the dimensions:

| Field | Question | Surfaces |
|---|---|---|
| `social_role` | "On a trip, people usually end up relying on you for…" | social role + emotional regulation under chaos |
| `trip_feeling` | "The best trips usually leave you feeling…" | cleanest push/pull/motivation signal (stimulation / escape / narrative / reset) |
| `friction_response` | "Something goes wrong halfway through the day. Your instinct is to…" | resilience, control orientation, anxiety style |
| `ideal_atmosphere` | "You instantly feel at home in places that are…" | stimulation threshold, introversion/extroversion |
| `small_thing` | Free text — "a tiny thing that made life feel unusually good recently" | metaphor + aesthetic cadence ground truth |

The persona-infer endpoint runs the main LLM and the emotional-signature inferrer in parallel via `asyncio.gather`, both grounded in the same GoEmotions top-5 labels classified from the user's answers.

### Emotional signature — private framing for prompts, not user-facing vocabulary

`mushahid/persona/taxonomy.py` defines an 8-key closed taxonomy (`reset_seeker`, `stimulation_seeker`, `story_collector`, `connection_seeker`, `belonging_seeker`, `quiet_observer`, `aesthetic_hunter`, `self_expander`). The inferred signature lands on `user_profile.compatibility_signals` and feeds five downstream consumers — chat reply persona prompt, icebreaker, topic chips, "Why this?" explainer, persona reveal — as private framing. The raw key is **never** surfaced in user-facing text; the generated `emotional_tone` phrase ("soft afternoon energy") is the only thing the UI shows.

### Multi-currency

All internal cost fields (`budget_usd`, `cost_usd`, `avg_daily_cost_usd`) are always USD. Conversion happens once at the input boundary in `capture_constraints()` via `shared/currency.py`.

### Per-activity feedback

`POST /update-trip` accepts both free-text feedback and a list of `ActivityFeedback` objects `{activity_id, action: "swap"|"remove"|"adjust_time", reason?}`. The refinement loop applies targeted changes instead of rewriting the whole itinerary.

### Auto-save trips

Every generated trip persists to the user's `saved_itinerary_ids` list on the SSE `done` event (with a safety-net save on `itinerary_generated`). The dashboard's Past Trips carousel renders all saved trips; the explicit "Save itinerary" button stays as a re-save / set-as-current shortcut for switching between trips.

### Optimistic locking on shared itinerary

Every write to `shared_itineraries/{id}` checks `client_version == current_version` in Firestore. Mismatch returns HTTP 409 — client must re-fetch and re-apply. Prevents silent overwrites when both co-travellers edit simultaneously.

### Cross-provider model fallback safety

Per-provider model env vars (`ANTHROPIC_SMALL_MODEL` / `OPENAI_SMALL_MODEL` / etc) so the engine fallback can't accidentally send an Anthropic model id to OpenAI on retry. Defaults baked in `shared/config.py` so missing env still works.

---

## Deployment

### Backend → Render
1. Connect GitHub repo
2. Build: `pip install -r requirements.txt`
3. Start: `uvicorn mushahid.main:app --host 0.0.0.0 --port 8000`
4. Add all env vars from `.env.example` (including VAPID keys + per-provider model names)
5. Health check path: `/health`

### Frontend → Vercel
1. Root directory: `jahnvi/frontend`
2. Framework: Vite
3. Add all `VITE_` env vars
4. Update `vercel.json` API rewrite URL to your Render backend URL
5. **HTTPS required** for Web Push (localhost is exempt; Vercel / Render handle this by default)

### Cotraveller avatars
After running `seed_cotravellers.py`, upload `seed_assets/cotraveller_avatars/*.png` to your static host (Firebase Storage, Cloudfront, etc) and update the URL prefix in Pinecone metadata or serve `/seed_assets/` from your CDN.

---

See [TASKS.md](./TASKS.md) for the full task checklist and per-person build order.
