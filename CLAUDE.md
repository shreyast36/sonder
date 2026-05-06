# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

```bash
# Backend — install deps
pip install -r requirements.txt

# Backend — run locally
uvicorn mushahid.main:app --reload --port 8000

# Backend — lint
ruff check .
black --check .

# Backend — format
black .
ruff check --fix .

# Backend — tests
pytest
pytest --asyncio-mode=auto          # all async tests
pytest -k "test_name"               # single test
pytest mushahid/tests/              # one folder

# Frontend — install + run
cd jahnvi/frontend && npm install
npm run dev                         # dev server on :5173
npm run build                       # production build
npm run preview                     # preview production build

# Seed Pinecone (first-time setup)
python -m scripts.seed_pinecone --namespace all
python -m scripts.seed_pinecone --namespace destinations
```

Copy `.env.example` → `.env` and fill keys before running anything.

---

## Scaffolding Rule

Every function is a stub (`raise NotImplementedError` or `# TODO:`). Do not write real implementations unless a lead has explicitly asked. Add stubs, not code.

---

## Architecture

Four leads own four folders. The backend (`mushahid/`) is the only entry point — it calls into the other three.

```
POST /plan-trip  (Mushahid — routes/)
    │
    └── orchestrator.py (Mushahid — pipeline/)
            │
            ├── [Jahnvi]  pipeline/module1-3  →  TripConstraints, UserProfile, persona
            ├── [Shreyas] retrieval/ + ranking/  →  Destination + Activity candidates
            ├── [Ali]     generation/  →  streams Itinerary token-by-token (SSE)
            ├── [Ali]     rag/explainer.py  →  populate why_this on each activity
            ├── [Mushahid] validation/  →  rules check → LLM critic → refinement loop
            └── [Shreyas] cotraveller/  →  CoTravellerMatch list
```

The orchestrator emits named SSE events at each step. The frontend (`jahnvi/frontend/`) consumes them via a `fetch()` ReadableStream (not `EventSource` — auth headers require this).

Real-time after the trip is planned uses two transports:
- **WebSocket** (`/ws/chat/{session_id}`) — chat messages, typing indicators, pings
- **Firestore listeners** — presence, shared itinerary sync, approval state

---

## Imports

```python
# All data models — always import from here, never from jahnvi/schemas/ directly
from shared.schemas import Itinerary, UserProfile, ValidationResult

# All env vars — never call os.getenv() outside this file
from shared.config import MAX_REFINEMENT_ATTEMPTS, PINECONE_INDEX_NAME
```

---

## Key Contracts

- **Auth**: every protected route uses `Depends(verify_token)` from `mushahid/auth.py`; WebSocket uses `Depends(verify_ws_token)` (query param, not header)
- **Sanitize**: call `sanitize_user_input()` (`mushahid/utils/sanitize.py`) before any free-text reaches an LLM
- **SSE**: `format_event(name, data)` in `mushahid/realtime/sse.py` is the only way to emit events; never buffer token chunks
- **LLM calls**: always go through `ali/routing/engine.py`; never call a provider SDK directly from outside `ali/`
- **Embeddings**: always call `embed_text()` in `shreyas/retrieval/embeddings.py`; provider is set by Shreyas via env, vectors always go to Pinecone
- **WebSocket presence**: clients send `{"type": "ping"}` every 30s; backend TTL is 90s (`PRESENCE_TTL_SECONDS`)
- **Shared itinerary edits**: use optimistic locking (`version` field); raise HTTP 409 on conflict, never silently retry

---

## Team Boundaries

| Lead | Folder | Critical path |
|---|---|---|
| Jahnvi | `jahnvi/` | Schemas must be finalised first — the whole team imports from `shared/schemas.py` |
| Mushahid | `mushahid/` | Orchestrator calls everyone; `get_db()` in `realtime/firestore.py` unblocks Shreyas |
| Ali | `ali/` | Must announce `EMBED_DIMENSIONS` early — Shreyas needs it to create the Pinecone index |
| Shreyas | `shreyas/` | `embed_text()` unblocks Jahnvi's Module 3; `ConnectionManager` is in-memory locally but needs Redis on ECS |

Never edit another lead's folder. Cross-module import paths are documented in each folder's `CLAUDE.md`.

---

## Production

ECS Fargate on AWS. Secrets come from AWS Secrets Manager (auto-injected at runtime — no `.env` on ECS). `ConnectionManager` requires ElastiCache Redis when running more than one container. See `infra/README.md`.
