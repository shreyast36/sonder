# Sonder — AI Co-Traveller Trip Planner

> Plan smarter. Find your perfect co-traveller.

AI-powered trip planning, smart co-traveller matching, and real-time collaboration — all in one product.

---

## What It Does

Sonder takes a user from zero to a fully personalised, day-by-day itinerary and then matches them with a compatible co-traveller to plan, chat, and travel together in real time.

**User journey:**
1. Enter trip basics (destination, dates, budget in any currency, must-haves)
2. Answer preference questions (travel style, pace, interests)
3. Receive a live-generated itinerary with "Why this?" explanations per activity
4. Refine with free-text feedback or tap individual activities to swap/remove them
5. Get matched with a compatible co-traveller (AI scoring + persona archetypes)
6. Chat with AI-generated icebreakers and conversation starters
7. Approve, build a shared itinerary together in real time, then email or download it as PDF

---

## Team Ownership

| Person | Role | Owns |
|---|---|---|
| **Jahnvi** | Lead Product, UX & Frontend | All schemas · User input pipeline (constraints → preferences → persona) · 10-screen React frontend |
| **Shreyas** | Lead AI Systems & Real-time | Candidate **selection** (embeddings + search + ranking) · Co-traveller matching algorithms · Real-time layer (chat, presence, shared itinerary, approval) |
| **Ali** | Lead AI Intelligence | Pinecone vector database · All LLM clients + routing · Itinerary generation · RAG **explanation** ("Why this?") · Chat topics |
| **Mushahid** | Lead Backend & Infrastructure | FastAPI app · Pipeline orchestrator · Validation + refinement loop · Firebase real-time layer · Deployment |

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
| Frontend | React 18 + Vite + Tailwind CSS + Framer Motion |
| Auth | Firebase Auth (Google OAuth) |
| Real-time DB | Cloud Firestore |
| Backend API | FastAPI (Python 3.11) on Render |
| Vector DB | Pinecone — owned and managed by Ali |
| AI — Small models | Ali's decision (`SMALL_MODEL_PROVIDER` + `SMALL_MODEL_NAME` in `.env`) |
| AI — Large models | Ali's decision (`LARGE_MODEL_PROVIDER` + `LARGE_MODEL_NAME` in `.env`) |
| AI — Validator | Ali's decision (`VALIDATOR_MODEL_PROVIDER` + `VALIDATOR_MODEL_NAME` in `.env`) |
| Email | Resend / SendGrid / SES — set `EMAIL_PROVIDER` in `.env` |
| Frontend hosting | Vercel |
| Backend hosting | Render |
| Monitoring | Sentry (errors) + PostHog (analytics) |

### Folder Structure

```
sonder/
├── shared/                  # Schemas, config, utilities — owned by Jahnvi
│   ├── schemas.py           # Re-exports all models from jahnvi/schemas/
│   ├── config.py            # All env var reads — never call os.getenv() outside here
│   ├── currency.py          # Multi-currency conversion (live rates + fallback)
│   └── email.py             # Transactional email (Resend / SendGrid / SES)
│
├── jahnvi/                  # User Pipeline + Schemas + Frontend
│   ├── schemas/             # All Pydantic models (source of truth)
│   ├── pipeline/            # Modules 1–3: constraints → preferences → persona/emotion
│   ├── data/                # Persona archetype templates
│   └── frontend/            # React + Vite app (10 screens, hooks, Firebase client)
│
├── shreyas/                 # Candidate Selection + Real-time
│   ├── retrieval/           # Embeddings + Pinecone search (SELECTION — finds candidates)
│   ├── ranking/             # Filters, scores, and ranks candidates
│   └── cotraveller/         # Matching algorithms, WebSocket chat, presence,
│                            #   shared itinerary sync, approval
│
├── ali/                     # AI Intelligence Layer
│   ├── vector/              # Pinecone index setup — get_pinecone_index() used by Shreyas
│   ├── clients/             # LLM provider wrappers (one file per provider)
│   ├── routing/             # Task classifier + multi-model routing engine
│   ├── generation/          # Itinerary generation, prompts, output parser, chat topics
│   └── rag/                 # retriever.py fetches context about chosen activities;
│                            #   explainer.py passes that context to LLM → "Why this?" text
│
├── mushahid/                # Backend API + Orchestration + Validation
│   ├── main.py              # FastAPI app entry point
│   ├── auth.py              # Firebase ID token verification
│   ├── routes/              # All HTTP + WebSocket endpoints
│   ├── pipeline/            # Orchestrator: runs all steps in sequence, streams SSE
│   ├── validation/          # LLM critic + deterministic rule checks
│   ├── refinement/          # Closed-loop regeneration until validator approves
│   └── realtime/            # Firestore state, SSE helpers, push notifications
│
├── scripts/
│   └── seed_pinecone.py     # Seeds Pinecone with destination + activity data (Ali runs this)
│
├── .env.example
├── requirements.txt
└── TASKS.md                 # Full task checklist with per-person ownership
```

### Pipeline — How It All Connects

```
POST /plan-trip
│
├── [Jahnvi]   Module 1 — capture_constraints()       convert budget to USD, parse dates
├── [Jahnvi]   Module 2 — parse_answers()             preference questions → PersonaQuestionAnswers
├── [Jahnvi]   Module 3 — infer_persona/emotion()     classify archetype + emotional intent
│                                                      → SSE: persona_inferring / persona_inferred
│
├── [Shreyas]  search_destinations/activities()        SELECTION — query Pinecone for top candidates
│                                                      → SSE: retrieving / retrieval_done
├── [Shreyas]  rank_destinations/activities()          score + filter candidates by budget/pace/persona
│                                                      → SSE: ranking / ranked
│
├── [Ali]      generate_itinerary()                    LARGE model — stream itinerary JSON tokens
│                                                      → SSE: generating / itinerary_generated
├── [Ali]      explain_itinerary()                     RAG — fetch context per activity, write Why This
│              retriever calls Shreyas's search.py     → SSE: explaining
│
├── [Mushahid] run_all_checks() + validate_with_llm()  rule checks + VALIDATOR model critic
│              → if REVISE: run_refinement_loop()      re-rank → re-generate → re-validate
│                                                      → SSE: validating / revision / validated
│
├── [Shreyas]  search_cotravellers() + get_top_matches()  match compatible users
│                                                      → SSE: matching_cotravellers / matched
│
└── → SSE: done { PlanTripResponse }
```

### Multi-Model Routing (Ali)

Every LLM call is routed by task type — no model names are hardcoded anywhere:

| Tier | Task types | Characteristics |
|---|---|---|
| **Small** | chat_topics, icebreaker, persona_label, quick_edit | Fast + cheap |
| **Large** | itinerary_generation, rag_explanation, conflict_resolution | High quality, longer context |
| **Validator** | validate_itinerary, critic_check | Structured output, scoring |

### Real-Time Layer

| Feature | Transport | Owner |
|---|---|---|
| Itinerary generation progress | SSE | Mushahid |
| Push notifications (match found, itinerary ready) | Firestore | Mushahid |
| Real-time chat | WebSockets | Shreyas |
| Typing indicators + seen receipts | WebSockets | Shreyas |
| Co-traveller presence / online status | Firestore | Shreyas |
| Approval status (live) | Firestore | Shreyas |
| Shared itinerary edits | Firestore | Shreyas |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Firebase project (Auth + Firestore enabled)
- Pinecone account
- LLM API keys (Ali's choice of providers)

### Backend

```bash
git clone https://github.com/shreyast36/sonder
cd sonder
pip install -r requirements.txt

cp .env.example .env
# Fill in all keys

# Seed Pinecone (Ali runs this once)
python -m scripts.seed_pinecone --namespace all

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

---

## API Reference

| Method | Route | Auth | Returns |
|---|---|---|---|
| `GET` | `/health` | None | `{"status": "healthy"\|"degraded", "services": {...}}` |
| `GET` | `/visa-check?destination_country=X&nationality=Y` | None | `VisaInfo` |
| `GET` | `/users/profile` | Firebase token | `UserProfile` — 404 if not yet created |
| `POST` | `/users/profile` | Firebase token | `UserProfile` — creates on first login |
| `POST` | `/plan-trip` | Firebase token | SSE stream → `PlanTripResponse` |
| `POST` | `/update-trip` | Firebase token | `UpdateTripResponse` — free-text or per-activity `ActivityFeedback` |
| `POST` | `/cotraveller` | Firebase token | `list[CoTravellerMatch]` |
| `POST` | `/cotraveller/regenerate` | Firebase token | `list[CoTravellerMatch]` — excludes prior profiles |
| `POST` | `/chat/start` | Firebase token | `ChatStartResponse` (session + icebreaker + 5 topics) |
| `POST` | `/chat/approve` | Firebase token | `{"status": "approved"\|"pending"}` |
| `POST` | `/chat/deny` | Firebase token | `{"status": "denied"}` |
| `WS` | `/ws/chat/{session_id}` | Firebase token (query param) | Real-time chat stream |
| `POST` | `/export/email` | Firebase token | `{"sent_to": [...]}` |
| `GET` | `/export/pdf/{itinerary_id}` | Firebase token (query param) | PDF stream |

---

## Key Design Decisions

### Multi-currency
All internal cost fields (`budget_usd`, `cost_usd`, `avg_daily_cost_usd`) are always USD. Conversion happens once at the input boundary in `capture_constraints()` via `shared/currency.py`. The frontend sends `budget_amount` + `budget_currency` (ISO 4217).

### Per-activity feedback
`POST /update-trip` accepts both free-text feedback and a list of `ActivityFeedback` objects `{activity_id, action: "swap"|"remove"|"adjust_time", reason?}`. The refinement loop applies targeted changes instead of rewriting the whole itinerary.

### Persona archetypes
Five archetypes (Cultural Explorer, Adventure Seeker, Relaxed Wanderer, Party Traveller, Foodie) defined in `jahnvi/data/persona_templates.py`. Used by both `infer_persona()` and the Pinecone seeding script — same vocabulary ensures embedding consistency.

### Optimistic locking on shared itinerary
Every write to `shared_itineraries/{id}` checks `client_version == current_version` in Firestore. Mismatch returns HTTP 409 — client must re-fetch and re-apply. Prevents silent overwrites when both co-travellers edit simultaneously.

---

## Deployment

### Backend → Render
1. Connect GitHub repo
2. Build: `pip install -r requirements.txt`
3. Start: `uvicorn mushahid.main:app --host 0.0.0.0 --port 8000`
4. Add all env vars from `.env.example`
5. Health check path: `/health`

### Frontend → Vercel
1. Root directory: `jahnvi/frontend`
2. Framework: Vite
3. Add all `VITE_` env vars
4. Update `vercel.json` API rewrite URL to your Render backend URL once Mushahid has it

---

See [TASKS.md](./TASKS.md) for the full task checklist and per-person build order.
