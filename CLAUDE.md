# Sonder — AI Co-Traveller Trip Planner

## Team

| Lead | Folder | Owns |
|---|---|---|
| Jahnvi | `jahnvi/` | Schemas, pipeline modules 1–3, React frontend |
| Mushahid | `mushahid/` | FastAPI backend, orchestrator, validation, real-time infra |
| Ali | `ali/` | Multi-model routing, itinerary generation, RAG explainer |
| Shreyas | `shreyas/` | Pinecone retrieval, ranking, co-traveller matching, WebSocket chat |

Never edit another lead's folder without their knowledge. Cross-module calls are documented in each folder's `README.md`.

---

## Scaffolding Rule

This codebase is a scaffold — every function has a docstring and a `raise NotImplementedError` (or `# TODO:` comment). Do not write real implementations unless a lead has explicitly asked you to implement a specific function. Add stubs, not code.

---

## Imports

All data models live in `shared/schemas.py` (re-exported from `jahnvi/schemas/`).

```python
from shared.schemas import Itinerary, UserProfile, ValidationResult  # always use this
```

All environment variables live in `shared/config.py`.

```python
from shared.config import MAX_REFINEMENT_ATTEMPTS, PINECONE_INDEX_NAME  # always use this
```

Never call `os.getenv()` directly anywhere outside `shared/config.py`.

---

## Key Contracts

- **Auth**: every protected route uses `Depends(verify_token)` from `mushahid/auth.py`
- **Sanitize**: `sanitize_user_input()` in `mushahid/utils/sanitize.py` must be called before any free-text field enters an LLM prompt
- **SSE**: `format_event()` in `mushahid/realtime/sse.py` is the only way to emit SSE events
- **Embeddings**: `embed_text()` in `shreyas/retrieval/embeddings.py` — provider and model set by Shreyas via env; vectors always go to Pinecone
- **LLM calls**: always go through `ali/routing/engine.py` — never call a provider SDK directly from outside `ali/`

---

## Running locally

```bash
# Backend
uvicorn mushahid.main:app --reload --port 8000

# Frontend
cd jahnvi/frontend && npm run dev

# Seed Pinecone
python -m scripts.seed_pinecone --namespace all
```

Copy `.env.example` to `.env` and fill in your keys before starting.

---

## Production

ECS Fargate on AWS. Secrets come from AWS Secrets Manager (auto-injected). See `infra/README.md`.
