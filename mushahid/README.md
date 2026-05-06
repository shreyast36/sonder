# Mushahid — Lead Backend, Validation & Infrastructure Engineer

You own the API, the pipeline that ties all modules together, the validation loop, and all the real-time infrastructure that makes things feel instant.

---

## What You Own

| Folder | Responsibility |
|---|---|
| `main.py` | FastAPI app entry point — CORS, lifespan, router registration |
| `routes/` | All HTTP + WebSocket endpoints |
| `pipeline/orchestrator.py` | Runs all 6 modules in sequence, streams SSE events |
| `validation/` | Deterministic rule checks + LLM critic validation |
| `refinement/loop.py` | Closed-loop regeneration until validator approves |
| `realtime/` | Firestore state management, SSE helpers, push notifications |

---

## API Surface

### HTTP Endpoints

| Method | Route | Auth | Returns |
|---|---|---|---|
| `GET` | `/health` | None | Service status dict |
| `GET` | `/visa-check?destination_country=X&nationality=Y` | None | `VisaInfo` |
| `POST` | `/plan-trip` | Firebase token | SSE stream → `PlanTripResponse` |
| `POST` | `/update-trip` | Firebase token | `UpdateTripResponse` |
| `POST` | `/cotraveller` | Firebase token | `list[CoTravellerMatch]` |
| `POST` | `/chat/start` | Firebase token | `ChatSession` |
| `POST` | `/chat/approve` | Firebase token | `{"status": "approved" \| "pending"}` |
| `POST` | `/chat/deny` | Firebase token | `{"status": "denied"}` |
| `WS` | `/ws/chat/{session_id}` | Firebase token | Real-time chat stream |

### Auth Pattern — every protected route

```python
from firebase_admin import auth as firebase_auth
from fastapi import Header, HTTPException

async def verify_token(authorization: str = Header(...)) -> str:
    token = authorization.replace("Bearer ", "")
    decoded = firebase_auth.verify_id_token(token)
    return decoded["uid"]
```

---

## Pipeline Orchestrator — SSE Event Sequence

```
POST /plan-trip
    │
    └── orchestrator.run_plan_trip_pipeline(user_profile)
            │
            ├── [Jahnvi] infer_persona + infer_emotion
            │       → emit "persona_inferring" → "persona_inferred"
            │
            ├── [Shreyas] search_destinations + search_activities
            │       → emit "retrieving" → "retrieval_done"
            │
            ├── [Shreyas] rank_destinations + rank_activities
            │       → emit "ranking" → "ranked"
            │
            ├── [Ali] generate_itinerary (streaming tokens)
            │       → emit "generating" → token chunks → "itinerary_generated"
            │
            ├── [Ali] explain_itinerary (populate why_this fields)
            │       → emit "explaining"
            │
            ├── [Mushahid] run_all_checks + validate_with_llm
            │       → emit "validating"
            │       → if REVISE: run_refinement_loop → emit "revision" (may repeat)
            │       → emit "validated"
            │
            ├── [Shreyas] search_cotravellers + get_top_matches
            │       → emit "matching_cotravellers" → "matched"
            │
            └── emit "done" with full PlanTripResponse
```

### SSE Event Format

```python
# format_event("persona_inferred", {"archetype": "Cultural Explorer", "emotion": "excited"})
# produces:
"event: persona_inferred\ndata: {\"archetype\": \"Cultural Explorer\", \"emotion\": \"excited\"}\n\n"
```

---

## Validation Contracts

### Rule Checks — `validation/rules.py`

```python
# run_all_checks — output
ConstraintSatisfaction(
    budget_ok     = True,
    duration_ok   = True,
    pace_ok       = False,  # 4.2 avg activities/day exceeds relaxed threshold of 3
    must_haves_ok = True,
    avoid_list_ok = True
)
```

### LLM Critic — `validation/critic.py`

```python
# validate_with_llm — output (approved)
ValidationResult(
    itinerary_id            = "itin_abc123",
    status                  = ValidationStatus.approved,
    score                   = 0.94,
    feedback                = "Well-paced itinerary with great cultural balance.",
    improvement_suggestions = []
)

# validate_with_llm — output (revise)
ValidationResult(
    itinerary_id            = "itin_abc123",
    status                  = ValidationStatus.revise,
    score                   = 0.61,
    feedback                = "Day 3 has 6 activities — too many for a relaxed pace.",
    improvement_suggestions = ["Reduce Day 3 to 3 activities", "Move Tanah Lot to Day 4"]
)
```

---

## Refinement Loop Contract

```python
# run_refinement_loop — output
UpdateTripResponse(
    itinerary           = Itinerary(...),                        # approved itinerary
    validation          = ValidationResult(status=approved, score=0.96, ...),
    refinement_attempts = 2                                      # took 2 tries
)
```

Loop logic:
1. Re-rank (Shreyas) with adjusted context
2. Re-generate (Ali) with feedback + validation issues in prompt
3. Re-validate (rules → LLM critic)
4. Write to Firestore after each attempt so user sees live updates
5. Break on approval or after `MAX_REFINEMENT_ATTEMPTS` (from `.env`)

---

## Firestore Collections

```
itineraries/{itinerary_id}          ← full Itinerary object
itinerary_status/{user_id}          ← { "status": "generating" | "ready" | "error" }
shared_itineraries/{itinerary_id}   ← SharedItinerary (Shreyas writes, you init)
chat_sessions/{session_id}          ← ChatSession + approval state
notifications/{user_id}/items/{id}  ← in-app notification docs
presence/{user_id}                  ← { "online": true, "last_seen": "..." }
```

---

## Real-time Layer Split

| Feature | Who writes | Transport |
|---|---|---|
| Itinerary status (Generating → Ready) | **Mushahid** | SSE + Firestore |
| Push notifications (match found, ready, approved) | **Mushahid** | Firestore |
| Co-traveller presence | **Shreyas** | Firestore |
| Chat messages | **Shreyas** | WebSockets |
| Shared itinerary sync | **Shreyas** | Firestore |
| Approval status | **Shreyas** | Firestore |

---

## How Your Code Connects to Others

| You call | From | Purpose |
|---|---|---|
| `jahnvi/pipeline/module3_persona.py` | `orchestrator.py` | Step 1 — persona inference |
| `shreyas/retrieval/search.py` | `orchestrator.py`, `routes/cotraveller.py` | Steps 2, 7 |
| `shreyas/ranking/` | `orchestrator.py` | Step 3 |
| `ali/generation/itinerary_generator.py` | `orchestrator.py` | Step 4 |
| `ali/rag/explainer.py` | `orchestrator.py` | Step 5 |
| `ali/routing/engine.py` | `validation/critic.py` | Validator LLM calls |
| `shreyas/cotraveller/chat.py` | `routes/chat.py` | WebSocket proxy |
| `shreyas/cotraveller/approval.py` | `routes/chat.py` | Approve/deny |
| `shreyas/cotraveller/matching.py` | `routes/cotraveller.py` | Match scoring |

---

## Build Order

1. `main.py` + Firebase Admin init in `realtime/firestore.py`
2. `realtime/sse.py` — needed by orchestrator
3. `routes/health.py` + `routes/visa.py` — test the server is running
4. `validation/rules.py` (no LLM dependency, easy to test)
5. `validation/critic.py` (depends on Ali's routing engine being ready)
6. `realtime/notifications.py`
7. `pipeline/orchestrator.py` (depends on everyone else — build last)
8. All remaining routes
9. `refinement/loop.py`

## Deployment

```bash
# Run locally
uvicorn mushahid.main:app --reload --port 8000

# Render start command
uvicorn mushahid.main:app --host 0.0.0.0 --port 8000
```
