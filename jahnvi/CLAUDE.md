# Jahnvi — Schemas, Pipeline Modules 1–3 & React Frontend

Read `jahnvi/README.md` for the full picture. This file is a quick-reference for Claude Code.

---

## What lives here

| File / Folder | Purpose |
|---|---|
| `schemas/` | Single source of truth for all data models — re-exported via `shared/schemas.py` |
| `schemas/enums.py` | All enums: `PacePreference`, `BudgetStyle`, `TravelStyle`, `EmotionIntent`, `ValidationStatus`, `VisaRequirement`, `ModelTier`, `ApprovalStatus` |
| `schemas/user.py` | `TripConstraints`, `PersonaQuestionAnswers`, `UserProfile` |
| `schemas/trip.py` | `Destination`, `Activity`, `ItineraryActivity`, `ItineraryDay`, `Itinerary` |
| `schemas/validation.py` | `ConstraintSatisfaction`, `ValidationResult` |
| `schemas/cotraveller.py` | `CoTravellerProfile`, `CoTravellerMatch` |
| `schemas/chat.py` | `ChatMessage`, `ChatSession`, `SharedItinerary`, `ItineraryUpdateEvent` |
| `schemas/api.py` | `VisaInfo`, `PlanTripRequest`, `PlanTripResponse`, `UpdateTripRequest`, `UpdateTripResponse` |
| `pipeline/module1_constraints.py` | `capture_constraints(raw)` → `TripConstraints` |
| `pipeline/module2_preferences.py` | `parse_answers(raw)` → `PersonaQuestionAnswers` |
| `pipeline/module3_persona.py` | `infer_persona()`, `infer_emotion()`, `build_travel_style_embedding()`, `build_compatibility_signals()`, `update_profile_from_feedback()` |
| `frontend/` | React + Vite app — 9 screens, Firebase Auth, Firestore listeners, SSE + WebSocket |

---

## Schema ownership rule

When a schema changes, update it in `jahnvi/schemas/<file>.py` and announce it to the team. `shared/schemas.py` re-exports everything — do not define models there, only re-export.

If you add or rename a field on `UserProfile`, `Itinerary`, or `CoTravellerProfile`, check what Shreyas and Ali import from those models and update their docstrings accordingly.

---

## Frontend conventions

**Auth header on every backend call:**
```javascript
const token = await auth.currentUser.getIdToken()
fetch('/api/...', { headers: { Authorization: `Bearer ${token}` } })
```

**SSE — use fetch ReadableStream, not EventSource** (EventSource can't set custom headers):
```javascript
const res = await fetch('/api/plan-trip', { method: 'POST', headers: await authHeaders(), body: ... })
// parse via useSSE.js
```

**WebSocket presence heartbeat — required:**
```javascript
const ws = openChatSocket(sessionId, token)
const ping = setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }))
}, 30_000)
ws.addEventListener("close", () => clearInterval(ping))
```
Backend TTL is 90 seconds — 3 missed pings marks the user offline.

**409 conflict on shared itinerary edits:**
Do not silently retry. Re-fetch the latest state, show a toast ("Someone else made a change — here's the latest"), then let the user retry with the updated version.

---

## Profile creation on first login — required

```javascript
// In onAuthStateChanged (useAuth.js):
const profile = await getUserProfile()  // GET /api/users/profile
if (profile.status === 404) {
  await createUserProfile(firebaseUser.displayName || "Traveller")  // POST /api/users/profile
}
```

Every other API call assumes the profile exists. Skipping this causes silent 404s everywhere.

---

## Module 3 depends on Shreyas

`build_travel_style_embedding()` calls `embed_text()` from `shreyas/retrieval/embeddings.py`. This function is not implemented until Shreyas wires it. Keep Module 3 as a stub until then.

---

## What not to do

- Do not call `os.getenv()` — all config comes from `shared/config.py`
- Do not import schemas from `jahnvi/schemas/` inside other modules — always import from `shared/schemas.py`
- Do not define schema models in `shared/schemas.py` — define in `jahnvi/schemas/`, re-export only
- Do not use `EventSource` for SSE — use `fetch()` + `ReadableStream`
- Do not add model names to any schema or config — Ali and Shreyas own model selection
