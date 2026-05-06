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

## Architecture

### Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + Tailwind CSS + shadcn/ui + framer-motion |
| Auth | Firebase Auth |
| Real-time DB | Cloud Firestore |
| Backend API | FastAPI (Python) on Render |
| Vector DB | Pinecone |
| AI — Small LLMs | Ali's decision — set via `SMALL_MODEL_PROVIDER` + `SMALL_MODEL_NAME` |
| AI — Large LLMs | Ali's decision — set via `LARGE_MODEL_PROVIDER` + `LARGE_MODEL_NAME` |
| AI — Validator LLM | Ali's decision — set via `VALIDATOR_MODEL_PROVIDER` + `VALIDATOR_MODEL_NAME` |
| Storage | Firebase Storage / AWS S3 |
| Real-time Comms | WebSockets + Firestore Listeners + Cloud Functions |
| Frontend Hosting | Vercel |
| Backend Hosting | Render |
| Monitoring | Sentry (errors), PostHog (analytics) |

### Folder Structure

```
sonder/
├── shared/                  # Pydantic schemas + config + utilities — owned by Jahnvi
│   ├── schemas.py           # Re-exports all models from jahnvi/schemas/
│   ├── config.py            # All env var reads — never call os.getenv() outside here
│   ├── currency.py          # Multi-currency conversion (live rates + 30-currency fallback)
│   └── email.py             # Transactional email — Resend / SendGrid / SES
│
├── shreyas/                 # Retrieval, Ranking, Co-traveller Real-time
│   ├── retrieval/           # Pinecone vector search + embeddings
│   ├── ranking/             # Destination & activity scoring + filters
│   └── cotraveller/         # Matching, WebSocket chat, presence, shared itinerary, approval
│
├── jahnvi/                  # User Pipeline, Schemas, Frontend
│   ├── schemas/             # All user-facing Pydantic models
│   ├── pipeline/            # Modules 1–3: constraints, preferences, persona/emotion
│   ├── data/                # Persona archetype templates — drives infer_persona() + seeding
│   └── frontend/            # React + Vite app (9 screens, hooks, Firebase client)
│
├── ali/                     # AI Intelligence Layer
│   ├── routing/             # Multi-model routing engine + intent classifier
│   ├── clients/             # LLM provider client wrappers
│   ├── generation/          # Itinerary generation, output parsing, prompts, chat topics
│   └── rag/                 # RAG retriever + "Why this?" explainer
│
├── mushahid/                # Backend API, Validation, Orchestration
│   ├── main.py              # FastAPI app entry point
│   ├── routes/              # All HTTP + WebSocket endpoints
│   ├── pipeline/            # Orchestrator: runs modules 1–6 in sequence, streams SSE
│   ├── validation/          # LLM critic + deterministic rule checks
│   ├── refinement/          # Closed-loop regeneration (re-rank → re-query → re-validate)
│   └── realtime/            # Firestore state, SSE helpers, push notifications
│
├── scripts/
│   ├── seed_pinecone.py     # One-time Pinecone seeding (destinations, activities, co-travellers)
│   └── progress.py          # Dev tracker — auto-checks TASKS.md on every push
│
├── .env.example
├── requirements.txt
└── TASKS.md
```

### Core System Pipeline

```
User Input (Module 1) — budget converted to USD at boundary
    → Preferences & Persona (Modules 2–3)           [Jahnvi]
    → Vector Retrieval — Pinecone (Module 4)         [Shreyas]
    → Ranking & Filtering (Module 5)                 [Shreyas]
    → Itinerary Generation — Multi-model (Module 6)  [Ali]
    → RAG Explanations ("Why this?" per activity)    [Ali]
    → Validation — Critic + Rules                    [Mushahid]
    → Refinement Loop (if REVISE)                    [Mushahid]
    → Co-Traveller Matching                          [Shreyas]
    → Real-time Delivery via SSE + Firestore         [Mushahid]
```

### Multi-Model AI Architecture

Every AI request is routed to the right model based on complexity, latency, and cost:

| Tier | Used For |
|---|---|
| **Small** | Chat topics, icebreakers, persona labels, quick edits |
| **Large** | Full itinerary generation, RAG explanations, conflict resolution |
| **Validator** | Feasibility checks, constraint scoring, improvement suggestions |

Model names and providers are Ali's decision — set via env vars, never hardcoded.

### Real-Time Experience Layer

Powered by **Firestore + WebSockets**:

| Feature | Transport | Owner |
|---|---|---|
| Itinerary status (Generating → Ready) | SSE | Mushahid |
| Instant notifications | Firestore triggers | Mushahid |
| Co-traveller live match updates | Firestore | Shreyas |
| Real-time chat | WebSockets | Shreyas |
| Typing indicators / seen receipts | WebSockets | Shreyas |
| Approval status (live) | Firestore | Shreyas |
| Shared itinerary edits | Firestore | Shreyas |
| Presence / online status | Firestore | Shreyas |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Firebase project (Auth + Firestore enabled)
- Pinecone account
- LLM API keys for whichever providers Ali selects

### Backend Setup

```bash
# 1. Clone and install
git clone https://github.com/shreyast36/sonder
cd sonder
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in all API keys in .env

# 3. Seed Pinecone (first time only)
python -m scripts.seed_pinecone --namespace all

# 4. Run backend
uvicorn mushahid.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd jahnvi/frontend
npm install

# Copy env for frontend
cp ../../.env.example .env.local
# Fill in VITE_ prefixed Firebase config values

npm run dev
# Opens on http://localhost:5173
```

### API Endpoints

| Method | Route | Auth | Returns |
|---|---|---|---|
| `GET` | `/health` | None | Service status + Firestore/Pinecone ping |
| `GET` | `/visa-check` | None | `VisaInfo` |
| `POST` | `/plan-trip` | Firebase token | SSE stream → `PlanTripResponse` |
| `POST` | `/update-trip` | Firebase token | `UpdateTripResponse` — accepts free-text or per-activity `ActivityFeedback` |
| `POST` | `/cotraveller` | Firebase token | `list[CoTravellerMatch]` |
| `POST` | `/cotraveller/regenerate` | Firebase token | `list[CoTravellerMatch]` — new matches excluding prior profiles |
| `POST` | `/chat/start` | Firebase token | `ChatStartResponse` (session + icebreaker + 5 topics) |
| `POST` | `/chat/approve` | Firebase token | `{"status": "approved" \| "pending"}` |
| `POST` | `/chat/deny` | Firebase token | `{"status": "denied"}` |
| `WS` | `/ws/chat/{session_id}` | Firebase token (query param) | Real-time chat stream |
| `POST` | `/export/email` | Firebase token | `{"sent_to": [...]}` — emails itinerary to co-travellers |
| `GET` | `/export/pdf/{itinerary_id}` | Firebase token (query param) | PDF stream download |

### SSE Event Sequence (`/plan-trip`)

```
persona_inferring → persona_inferred
→ retrieving → retrieval_done
→ ranking → ranked
→ generating → itinerary_generated
→ explaining
→ validating → (revision →)* validated
→ matching_cotravellers → matched
→ done { PlanTripResponse }
```

---

## Key Design Decisions

### Multi-currency
All internal cost fields (`budget_usd`, `cost_usd`, `avg_daily_cost_usd`, etc.) are always USD. Conversion happens once at the input boundary in `capture_constraints()` via `shared/currency.py`. The frontend sends `budget_amount` + `budget_currency` (ISO 4217), never `budget_usd` directly.

### Per-activity feedback
`POST /update-trip` accepts both free-text feedback and a list of `ActivityFeedback` objects `{activity_id, action: "swap"|"remove"|"adjust_time", reason?}`. The refinement loop applies targeted changes rather than rewriting the whole itinerary.

### Persona archetypes
Five canonical archetypes (Cultural Explorer, Adventure Seeker, Relaxed Wanderer, Party Traveller, Foodie) are defined in `jahnvi/data/persona_templates.py`. This drives `infer_persona()` classification and the Pinecone co-traveller seeding script — both use the same vocabulary so embeddings are consistent.

### Chat prompt suggestions
`POST /chat/start` returns a `ChatStartResponse` with the new session, a personalised icebreaker message, and 5 AI-generated conversation topics. Both are generated by the SMALL model tier in `ali/generation/topics.py`.

---

## Deployment

### Backend → Render

1. Connect GitHub repo to Render
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn mushahid.main:app --host 0.0.0.0 --port 8000`
4. Add all environment variables from `.env.example`
5. Set health check path to `/health`

### Frontend → Vercel

1. Set root directory to `jahnvi/frontend`
2. Framework preset: Vite
3. Add all `VITE_` environment variables
4. Update `vercel.json` API rewrite URL to your Render backend URL

---

## Team

See [TASKS.md](./TASKS.md) for full task breakdown and ownership.
