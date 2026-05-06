# Mushahid — Backend, Orchestration, Validation & Real-time

Read `mushahid/README.md` for the full picture. This file is a quick-reference for Claude Code.

---

## What lives here

| File / Folder | Purpose |
|---|---|
| `main.py` | FastAPI app entry — CORS, lifespan, router registration (all commented-out until ready) |
| `auth.py` | `verify_token` (Header) + `verify_ws_token` (Query) — FastAPI dependencies |
| `utils/sanitize.py` | `sanitize_user_input()` — strip prompt injection before any user text hits the LLM |
| `routes/` | One file per endpoint group: `plan_trip`, `update_trip`, `cotraveller`, `chat`, `users`, `visa`, `health` |
| `pipeline/orchestrator.py` | Runs all 6 pipeline modules in sequence, emits SSE events |
| `validation/rules.py` | Deterministic rule checks — budget, duration, pace, must-haves, avoid list |
| `validation/critic.py` | LLM critic — calls `ali/routing/engine.py`, returns `ValidationResult` |
| `refinement/loop.py` | Closed-loop regeneration, up to `MAX_REFINEMENT_ATTEMPTS` |
| `realtime/sse.py` | `format_event(name, data)` — the only way to emit SSE events |
| `realtime/firestore.py` | `get_db()` + all Firestore read/write helpers |
| `realtime/notifications.py` | In-app + push notifications |

---

## Auth — mandatory on every protected route

```python
from mushahid.auth import verify_token, verify_ws_token
from fastapi import Depends

@router.post("/plan-trip")
async def plan_trip(uid: str = Depends(verify_token)):
    ...

@router.websocket("/ws/chat/{session_id}")
async def chat_ws(websocket: WebSocket, uid: str = Depends(verify_ws_token)):
    ...
```

`/health` and `/visa-check` are the only public routes (no auth).

---

## Prompt injection — mandatory before LLM

```python
from mushahid.utils.sanitize import sanitize_user_input

feedback = sanitize_user_input(request.feedback)   # before refinement loop
message  = sanitize_user_input(msg["content"])     # before chat relay
```

Call this on: feedback strings, chat messages, notes, any other free-text user input.

---

## SSE event sequence

```
persona_inferring → persona_inferred
retrieving → retrieval_done
ranking → ranked
generating → (token chunks) → itinerary_generated
explaining
validating → revision (may repeat) → validated
matching_cotravellers → matched
done
error  ← emitted on any exception, carries {step, message}
```

`generating` events carry `{"chunk": "...token..."}` — the frontend appends, not replaces.

---

## Imports from other modules

```python
# Jahnvi
from jahnvi.pipeline.module3_persona import infer_persona, infer_emotion, update_profile_from_feedback

# Shreyas
from shreyas.retrieval.search import search_destinations, search_activities
from shreyas.ranking.destination_ranker import rank_destinations
from shreyas.cotraveller.chat import ConnectionManager
from shreyas.cotraveller.approval import approve_match, deny_match

# Ali
from ali.routing.engine import route_request, stream_request
from ali.generation.itinerary_generator import generate_itinerary
from ali.rag.explainer import explain_itinerary
```

---

## What not to do

- Do not call `os.getenv()` — use `shared/config.py`
- Do not import schema classes directly from `jahnvi/schemas/` — use `shared/schemas.py`
- Do not buffer SSE token chunks — forward immediately as they arrive from Ali's generator
- Do not catch exceptions silently — always emit a `format_event("error", {...})` before raising
- Do not hard-code model names, provider names, or API keys anywhere
