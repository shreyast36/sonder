# Jahnvi — Lead Product, UX & Frontend Engineer

You define what the product looks like and how users interact with it. Everything starts with your schemas — the rest of the team builds on them.

---

## What You Own

| Folder | Responsibility |
|---|---|
| `schemas/` | All Pydantic models and enums — the single source of truth for data shapes |
| `pipeline/` | Modules 1–3: constraint capture, preference questions, persona & emotion inference |
| `frontend/` | React + Vite app — all 9 screens, Firebase Auth, Firestore listeners, SSE + WebSocket hooks |

**Also owns:** `shared/schemas.py` and `shared/config.py` — copy finalised models here so everyone can import them.

---

## Do This First

**The entire team is blocked until your schemas exist.** Before writing any pipeline or frontend code:

1. Finalise all models in `schemas/` (enums, user, trip, cotraveller, chat)
2. Copy them into `shared/schemas.py`
3. Announce in the group chat that schemas are ready

---

## Schema Contracts

### `schemas/enums.py` — already written, verify these match your design

```python
PacePreference:   relaxed | moderate | packed
BudgetStyle:      budget | mid_range | luxury
TravelStyle:      solo | couple | family | group
EmotionIntent:    tired | excited | relaxed | curious | adventurous
ValidationStatus: approved | revise
ApprovalStatus:   pending | approved | denied
ModelTier:        small | large | validator
```

### `schemas/user.py` — key shapes

```python
TripConstraints(
    destination_type = "beach",
    start_date       = date(2025, 6, 1),
    end_date         = date(2025, 6, 7),
    budget_usd       = 2000.0,
    group_size       = 2,
    pace_preference  = PacePreference.relaxed,
    must_haves       = ["snorkeling", "local food"],
    avoid_list       = ["nightclubs"]
)

UserProfile(
    user_id                = "firebase_uid_abc123",
    display_name           = "Arjun",
    constraints            = TripConstraints(...),
    persona_answers        = PersonaQuestionAnswers(...),
    emotion_intent         = EmotionIntent.excited,
    travel_style_embedding = [0.023, ...],  # set by module3
    compatibility_signals  = {"pace": "relaxed", "top_interests": ["food", "culture"]}
)
```

---

## Pipeline Module Contracts

### Module 1 — `capture_constraints`

```python
# Input (raw form from Screen 2)
{
    "destination_type": "beach",
    "start_date": "2025-06-01",
    "end_date": "2025-06-07",
    "budget_usd": 2000.0,
    "group_size": 2,
    "pace_preference": "relaxed",
    "must_haves": ["snorkeling", "local food"],
    "avoid_list": ["nightclubs"]
}

# Output
TripConstraints(destination_type="beach", start_date=date(2025,6,1), ...)
```

### Module 2 — `parse_answers`

```python
# Input (raw form from Screen 2, preference section)
{"food_interest": 5, "adventure_interest": 2, "culture_interest": 4, ...}

# Output
PersonaQuestionAnswers(food_interest=5, adventure_interest=2, culture_interest=4, ...)
```

### Module 3 — `infer_persona`

```python
# Input
PersonaQuestionAnswers(food_interest=5, culture_interest=4, adventure_interest=2, pace_preference="relaxed")

# Output
{
    "archetype":      "Cultural Explorer",
    "top_interests":  ["food", "culture"],
    "energy":         "low-moderate",
    "label":          "You love discovering local culture through food and art at a relaxed pace."
}
```

---

## Frontend — 9 Screens

Design in Figma first. Get sign-off before writing code.

| Screen | Route | Key interactions |
|---|---|---|
| 1. Welcome | `/` | Start Planning CTA → `/plan` |
| 2. Trip Preferences | `/plan` | Form submit → POST `/api/plan-trip` (SSE stream) |
| 3. Itinerary | `/itinerary` | Render SSE chunks live, day tabs, "Why this?" expand |
| 4. Match Detail | `/match/:id` | Compatibility breakdown, topics list, Start Chat → `/chat/:id` |
| 5. Chat | `/chat/:sessionId` | WebSocket messages, typing indicators, AI icebreakers |
| 6. Approve / Deny | `/approve/:id` | Two buttons, live status via Firestore listener |
| 7. Shared Itinerary | `/trip/:id` | Firestore real-time sync, "Added by" labels |
| 8. Notes | `/trip/:id/notes` | Firestore notes array, real-time updates |
| 9. Dashboard | `/dashboard` | Firestore trip list, active chats |

### SSE Events to Handle (Screen 3)

```javascript
// These arrive from POST /api/plan-trip as the pipeline runs
"persona_inferring"    → show "Understanding your travel style..."
"retrieving"           → show "Finding the best destinations..."
"ranking"              → show "Ranking options for you..."
"generating"           → show "Building your itinerary..." + skeleton cards
"explaining"           → show "Adding personalised insights..."
"validating"           → show "Checking everything looks right..."
"revision"             → show "Refining based on feedback..." (may repeat)
"matched"              → show "Finding your perfect travel buddy..."
"done"                 → render full PlanTripResponse
```

### Firebase Auth Pattern

```javascript
// src/lib/firebase.js
import { initializeApp } from 'firebase/app'
import { getAuth } from 'firebase/auth'
import { getFirestore } from 'firebase/firestore'

const app  = initializeApp({ /* VITE_ env vars */ })
export const auth = getAuth(app)
export const db   = getFirestore(app)

// Every API call must attach the ID token:
const token = await auth.currentUser.getIdToken()
fetch('/api/plan-trip', { headers: { Authorization: `Bearer ${token}` } })
```

---

## Build Order

1. `schemas/` — finish all models, copy to `shared/schemas.py`, tell the team
2. Figma designs — all 9 screens + component library
3. `pipeline/module1_constraints.py` → `module2_preferences.py` → `module3_persona.py`
4. Frontend foundation: Firebase init, auth hook, API client, Tailwind tokens
5. Screens in user journey order: Welcome → TripPreferences → Itinerary → ...
6. Wire up real-time features last (Firestore hooks, WebSocket hook)
