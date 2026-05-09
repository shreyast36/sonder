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

## Dependencies

### What I need from others

| From | What exactly | Where I use it | Status needed by |
|---|---|---|---|
| **Jahnvi** | `shared/schemas.py` finalised | Every route handler and model imports from here | **Right now — blocks everything** |
| **Jahnvi** | `PlanTripRequest`, `PlanTripResponse`, `UpdateTripRequest`, `UpdateTripResponse` shapes | Route handler type annotations | Before I can define route handlers |
| **Jahnvi** | `module1_constraints.capture_constraints(raw)` working | `pipeline/orchestrator.py` step 1a | Before orchestrator runs |
| **Jahnvi** | `module2_preferences.parse_answers(raw)` working | `pipeline/orchestrator.py` step 1b | Before orchestrator runs |
| **Jahnvi** | `module3_persona.infer_persona()` + `infer_emotion()` working | `pipeline/orchestrator.py` step 1c | Before orchestrator runs |
| **Shreyas** | `search_destinations()` + `search_activities()` | `pipeline/orchestrator.py` step 2 | Before retrieval step runs |
| **Shreyas** | `rank_destinations()` + `rank_activities()` | `pipeline/orchestrator.py` step 3 | Before ranking step runs |
| **Shreyas** | `search_cotravellers()` + `get_top_matches()` | `pipeline/orchestrator.py` step 7 + `routes/cotraveller.py` | Before co-traveller step runs |
| **Shreyas** | `ConnectionManager` from `cotraveller/chat.py` | `routes/chat.py` WebSocket handler | Before `/ws/chat/{session_id}` works |
| **Shreyas** | `approve_match()` + `deny_match()` from `cotraveller/approval.py` | `routes/chat.py` approve/deny routes | Before Screen 6 works end-to-end |
| **Ali** | `generate_itinerary()` + `stream_request()` from `routing/engine.py` | `refinement/loop.py` (re-generation on each loop iteration) | Before refinement loop works |
| **Ali** | `generate_itinerary()` streaming generator | `pipeline/orchestrator.py` step 4 | Before itinerary generation runs |
| **Ali** | `explain_itinerary()` — populates `why_this` fields | `pipeline/orchestrator.py` step 5 | Before explainer step runs |

### What others need from me

| Who | What exactly | Which file | When they're blocked |
|---|---|---|---|
| **Shreyas** | `get_db()` in `realtime/firestore.py` working | `shreyas/cotraveller/presence.py`, `shared_itinerary.py`, `approval.py` | Before Shreyas builds real-time features |
| **Shreyas** | `notify_co_traveller_approved()` in `realtime/notifications.py` | `shreyas/cotraveller/approval.py` calls this on mutual approval | Before approval flow is complete |
| **Jahnvi** | Backend running locally on `http://localhost:8000` | Testing all frontend API calls | Before Screen 2 can be tested |
| **Jahnvi** | `POST /plan-trip` SSE stream firing named events in sequence | Screen 2 → Screen 3 loading states | Before the Itinerary screen is built |
| **Jahnvi** | `POST /cotraveller` returning `list[CoTravellerMatch]` | Screen 4 Match Detail | Before match screens are built |
| **Jahnvi** | `POST /chat/start` + `WS /ws/chat/{id}` working | Screen 5 Chat | Before chat screen is built |
| **Jahnvi** | `POST /chat/approve` + `POST /chat/deny` | Screen 6 Approve/Deny | Before approval screen is built |
| **Jahnvi** | Render backend URL once deployed | `frontend/vercel.json` API rewrite | Before deploying to Vercel |

---

## Your Decisions

### Push notifications
`realtime/notifications.py` currently writes to Firestore only — users only see notifications when the app is open. You need to extend this with real push delivery.

| Option | Notes |
|---|---|
| **Firebase Cloud Messaging (FCM)** | Already using Firebase — natural choice, zero new dependencies. Works for web (PWA), Android, and iOS. Store the FCM device token on `UserProfile` at login. Free. |
| **Amazon SNS** | AWS-native if you want to avoid another Firebase dependency. More complex setup. Only worth it if you move away from Firebase entirely. |

**Recommended: FCM.** Steps:
1. Add `fcm_token: Optional[str]` to `UserProfile` in `jahnvi/schemas/user.py`
2. Frontend sends FCM token to `POST /users/profile` on login
3. `push_notification()` in `notifications.py` calls `firebase_admin.messaging.send()` using the stored token
4. Add `FIREBASE_VAPID_KEY` to `.env` for web push

---

### Email notifications + itinerary export
Email is used for two purposes: (1) event notifications when the app is closed, (2) user-triggered itinerary delivery via `POST /export/email`.

The provider is unified via `shared/email.py` — set `EMAIL_PROVIDER` in `.env` to switch:

| Option | Notes |
|---|---|
| **Resend** | Best developer experience, generous free tier (3k/month), modern API. Recommended for getting started fast. |
| **SendGrid** | Good free tier (100/day), rich templates, broad deliverability tooling. |
| **AWS SES** | Cheapest at scale ($0.10/1k), best deliverability. Requires domain verification + production access request. |

Add to `.env`:
```bash
EMAIL_PROVIDER=resend        # resend | sendgrid | ses
EMAIL_API_KEY=               # API key for chosen provider
EMAIL_FROM=itinerary@sonder.app  # verified sender address
```

PDF export uses `weasyprint` to render the same HTML template as the email — add it to `requirements.txt`.

---

### Visa check data source
`routes/visa.py` is stubbed. You decide where the data comes from.

| Option | Notes |
|---|---|
| **Sherpa API** | Best coverage, real-time visa requirements, entry restrictions. Paid (~$200/month). Most reliable for production. |
| **VisaHQ API** | Good coverage, paid. Slightly cheaper than Sherpa. |
| **Static JSON dataset** | Fastest to ship — a curated JSON file mapping (nationality, destination) → visa requirement. Maintained manually. Use for demo launch; switch to Sherpa later. Free. |
| **IATA Timatic** | The authoritative source airlines use. Enterprise pricing. Overkill unless you have serious compliance needs. |

**Recommended for launch: static JSON dataset** covering the top 20 nationality/destination combinations. Add `data/visa_requirements.json` and read from it in `routes/visa.py`. Upgrade to Sherpa once you have paying users.

Add to `.env`:
```bash
SHERPA_API_KEY=your-key          # if using Sherpa
```

---

## API Surface

### HTTP Endpoints

| Method | Route | Auth | Returns |
|---|---|---|---|
| `GET` | `/health` | None | `{"status": "healthy"\|"degraded", "services": {...}}` |
| `GET` | `/visa-check?destination_country=X&nationality=Y` | None | `VisaInfo` |
| `GET` | `/users/profile` | Firebase token | `UserProfile` — 404 if not yet created |
| `POST` | `/users/profile` | Firebase token | `UserProfile` — creates profile on first login; accepts `{ display_name, fcm_token? }` |
| `POST` | `/plan-trip` | Firebase token | SSE stream → `PlanTripResponse` |
| `POST` | `/update-trip` | Firebase token | `UpdateTripResponse` — accepts `activity_feedback` for targeted swaps |
| `POST` | `/cotraveller` | Firebase token | `list[CoTravellerMatch]` |
| `POST` | `/cotraveller/regenerate` | Firebase token | `list[CoTravellerMatch]` — excludes prior profiles |
| `POST` | `/chat/start` | Firebase token | `ChatStartResponse` (session + icebreaker + 5 topics) |
| `POST` | `/chat/approve` | Firebase token | `{"status": "approved" \| "pending"}` |
| `POST` | `/chat/deny` | Firebase token | `{"status": "denied"}` |
| `WS` | `/ws/chat/{session_id}` | Firebase token (query param) | Real-time chat stream |
| `POST` | `/export/email` | Firebase token | `{"sent_to": [...]}` |
| `GET` | `/export/pdf/{itinerary_id}` | Firebase token (query param) | PDF stream |

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
            ├── [Mushahid] run_all_checks + validate_large_output
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

You own two validator LLMs — one that checks Small model outputs (e.g. persona labels, chat topics), one that checks Large model outputs (e.g. full itineraries). Configure them independently in `.env`:

```bash
SMALL_VALIDATOR_PROVIDER=   # openai | anthropic | google | groq | mistral | bedrock
SMALL_VALIDATOR_MODEL_NAME= # model that validates small-task outputs

LARGE_VALIDATOR_PROVIDER=   # openai | anthropic | google | groq | mistral | bedrock
LARGE_VALIDATOR_MODEL_NAME= # model that validates itinerary + large-task outputs
```

Both validators use Ali's `BaseLLMClient` interface but are instantiated and called directly from `critic.py` — they do not go through Ali's routing engine.

```python
# validate_large_output — approved
ValidationResult(
    itinerary_id            = "itin_abc123",
    status                  = ValidationStatus.approved,
    score                   = 0.94,
    feedback                = "Well-paced itinerary with great cultural balance.",
    improvement_suggestions = []
)

# validate_large_output — output (revise)
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
| `ali/routing/engine.py` | `refinement/loop.py` | Re-generation during refinement (via `generate_itinerary()`) |
| `shreyas/cotraveller/chat.py` | `routes/chat.py` | WebSocket proxy |
| `shreyas/cotraveller/approval.py` | `routes/chat.py` | Approve/deny |
| `shreyas/cotraveller/matching.py` | `routes/cotraveller.py` | Match scoring |

---

## Build Order

1. `main.py` + Firebase Admin init in `realtime/firestore.py`
2. `realtime/sse.py` — needed by orchestrator
3. `routes/health.py` + `routes/visa.py` — verify server is running
4. `validation/rules.py` (no LLM dependency, easy to test)
5. `validation/critic.py` (depends on Ali's routing engine)
6. `realtime/notifications.py`
7. `routes/chat.py` — `start_chat` calls `generate_topics()` + `generate_icebreaker()` concurrently via `asyncio.gather`
8. `pipeline/orchestrator.py` (depends on everyone else — build last)
9. All remaining routes
10. `refinement/loop.py` — accepts `activity_feedback` in addition to free-text
11. `routes/export.py` — email + PDF; add `weasyprint` to `requirements.txt`

## Deployment

```bash
# Run locally
uvicorn mushahid.main:app --reload --port 8000

# Production start command (ECS Fargate + Render both use this)
uvicorn mushahid.main:app --host 0.0.0.0 --port 8000
```

### Local vs Production

| Concern | Local | Production (ECS) |
|---|---|---|
| Secrets | `.env` file | AWS Secrets Manager (auto-injected by ECS) |
| LLM inference | Direct API keys | Bedrock via IAM task role (no keys needed if `*_PROVIDER=bedrock`) |
| WebSocket sessions | In-memory dict (Shreyas's `ConnectionManager`) | ElastiCache Redis — required when running >1 container |
| Logs | stdout | CloudWatch `/ecs/sonder-backend` |

See `infra/README.md` for full AWS setup steps, IAM roles, and the ECS task definition.
