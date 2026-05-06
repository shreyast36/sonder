# Sonder — AI Co-Traveller Trip Planner

> Plan smarter. Find your perfect co-traveller.

AI-powered trip planning, smart co-traveller matching, and real-time collaboration — all in one product.

---

## What It Does

Sonder takes a user from zero to a fully personalised, day-by-day itinerary and then matches them with a compatible co-traveller to plan, chat, and travel together in real time.

**User journey:**
1. Enter trip basics (destination, dates, budget, must-haves)
2. Answer preference questions (travel style, pace, interests)
3. Receive a live-generated itinerary with "Why this?" explanations
4. Refine with free-text feedback — the system adapts automatically
5. Get matched with a compatible co-traveller (AI scoring)
6. Chat, approve, and build a shared itinerary together in real time

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
├── shared/                  # Pydantic schemas + config — owned by Jahnvi, imported by all
│   ├── schemas.py
│   └── config.py
│
├── shreyas/                 # Retrieval, Ranking, Co-traveller Real-time
│   ├── retrieval/           # Pinecone vector search + embeddings
│   ├── ranking/             # Destination & activity scoring + filters
│   └── cotraveller/         # Matching, WebSocket chat, presence, shared itinerary, approval
│
├── jahnvi/                  # User Pipeline, Schemas, Frontend
│   ├── schemas/             # All user-facing Pydantic models
│   ├── pipeline/            # Modules 1–3: constraints, preferences, persona/emotion
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
├── .env.example
├── requirements.txt
└── TASKS.md
```

### Core System Pipeline

```
User Input (Module 1)
    → Preferences & Persona (Modules 2–3)           [Jahnvi]
    → Vector Retrieval — Pinecone (Module 4)         [Shreyas]
    → Ranking & Filtering (Module 5)                 [Shreyas]
    → Itinerary Generation — Multi-model (Module 6)  [Ali]
    → RAG Explanations                               [Ali]
    → Validation — Critic + Rules                    [Mushahid]
    → Refinement Loop (if REVISE)                    [Mushahid]
    → Co-Traveller Matching                          [Shreyas]
    → Real-time Delivery via SSE + Firestore         [Mushahid]
```

### Multi-Model AI Architecture

Every AI request is routed to the right model based on complexity, latency, and cost:

| Tier | Task Types | Used For |
|---|---|---|
| **Small** | Ali's decision | Chat topics, persona labels, quick edits, notifications |
| **Large** | Ali's decision | Full itinerary generation, RAG explanations, conflict resolution |
| **Validator** | Ali's decision | Feasibility checks, constraint scoring, improvement suggestions |

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
git clone https://github.com/shreyast36/pearl-travel-planner
cd pearl-travel-planner
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in all API keys in .env

# 3. Run backend
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

| Method | Route | Description |
|---|---|---|
| `POST` | `/plan-trip` | Generate itinerary — returns SSE stream |
| `POST` | `/update-trip` | Refine itinerary with user feedback |
| `POST` | `/cotraveller` | Get top-3 co-traveller matches |
| `POST` | `/chat/start` | Start a chat session |
| `POST` | `/chat/approve` | Approve a co-traveller match |
| `POST` | `/chat/deny` | Deny a co-traveller match |
| `WS` | `/ws/chat/{session_id}` | Real-time chat WebSocket |
| `GET` | `/visa-check` | Visa requirement lookup |
| `GET` | `/health` | Service health check |

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

## Deployment

### Backend → Render

1. Connect GitHub repo to Render
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn mushahid.main:app --host 0.0.0.0 --port 8000`
4. Add all environment variables from `.env.example`

### Frontend → Vercel

1. Set root directory to `jahnvi/frontend`
2. Framework preset: Vite
3. Add all `VITE_` environment variables
4. Update `vercel.json` API rewrite URL to your Render backend URL

---

## Team

See [TASKS.md](./TASKS.md) for full task breakdown and ownership.
