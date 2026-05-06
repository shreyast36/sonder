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

## Do This First — Schemas (Team is Blocked Until Done)

**The entire team cannot write a single function until your schemas exist.** Before writing any pipeline or frontend code:

1. Finalise all models in `schemas/` (enums, user, trip, cotraveller, chat)
2. Copy them into `shared/schemas.py`
3. Tell Shreyas, Ali, and Mushahid in the group chat — they can start immediately after

---

## Figma Make → React Workflow

Use **Figma Make** to generate your React components directly from your Figma designs. This saves you from writing boilerplate UI code manually.

**Recommended workflow:**
1. Design all 9 screens in Figma using the dark purple design system (reference: the Tripora mockup shared in the group)
2. Use **Figma Make** to generate the initial React/JSX component code from your designs
3. Export the generated components into `frontend/src/pages/` and `frontend/src/components/`
4. Clean up the generated code — wire up real props, hooks, and API calls
5. Do **not** skip the Figma step and code directly — Figma Make only works well from a real design

**Design tokens to define in Figma before generating:**
- Background: deep dark purple/navy (~`#0a0a1a`)
- Primary: purple accent (~`#7C3AED`)
- Surface: glass-morphism cards with subtle borders
- Text: white primary, muted secondary
- Match badge: green gradient for high scores
- Buttons: rounded, purple primary / red destructive

Once generated, paste the Tailwind color tokens into `frontend/tailwind.config.js` so everything stays consistent.

---

## Dependencies — What You Need From Others

These are the things **you cannot build until someone else delivers them**. Chase these early.

### From Shreyas

| What you need | Where it's used | File to call |
|---|---|---|
| `embed_text(text)` working | `pipeline/module3_persona.py` — `build_travel_style_embedding()` calls this | `shreyas/retrieval/embeddings.py` |

> **What to tell Shreyas:** "I need `embed_text()` to work before I can finish module3. It just needs to accept a string and return a list of floats — the model choice is yours."

### From Mushahid

| What you need | Where it's used | When you need it |
|---|---|---|
| Backend running locally on port 8000 | All API calls from the frontend | Before you start Screen 2 |
| `POST /plan-trip` SSE stream working | Screen 2 → Screen 3 transition | Before implementing Itinerary screen |
| `POST /cotraveller` returning matches | Screen 4 (Match Detail) | Before implementing match screens |
| `POST /chat/start`, `WS /ws/chat/:id` | Screen 5 (Chat) | Before implementing chat screen |
| `POST /chat/approve`, `POST /chat/deny` | Screen 6 (Approve/Deny) | Before implementing approval screen |
| Render backend URL | `frontend/vercel.json` API rewrite | Before deploying to Vercel |

> **What to tell Mushahid:** "I need `/health` and `/plan-trip` working first so I can test the itinerary flow end-to-end. The SSE events don't all need real data initially — I just need the event names to fire in sequence so I can build the loading states."

### From Ali

| What you need | Where it's used | When you need it |
|---|---|---|
| `EMBED_MODEL` and `EMBED_DIMENSIONS` decided | `shared/config.py` needs real values | Before Shreyas can run embeddings |

> **What to tell Ali:** "What embedding model are you using? Shreyas needs `EMBED_MODEL` and `EMBED_DIMENSIONS` set in `.env` before he can build the retrieval layer, which I depend on for module3."

### From the whole team

| What you need | When |
|---|---|
| Firebase project created (Auth + Firestore enabled) | Before you can test `firebase.js` locally |
| Firebase config values (API key, project ID, etc.) | Fill in `VITE_FIREBASE_*` in `.env.local` |

---

## What Others Need From You — Your Output Is Their Input

### Shreyas needs from you

| What | When | Why |
|---|---|---|
| `shared/schemas.py` finalised | **Immediately — he's blocked** | All his type annotations import from here |
| `UserProfile` shape finalised | Before he builds ranking | His scoring functions take `UserProfile` as input |
| `CoTravellerProfile` shape finalised | Before he builds matching | His `score_compatibility()` takes this |
| `module3_persona.py` → `build_compatibility_signals()` working | Before co-traveller matching | His matching algorithm reads `user_profile.compatibility_signals` |
| `module3_persona.py` → `build_travel_style_embedding()` working | Before co-traveller search | His Pinecone query uses `user_profile.travel_style_embedding` |

### Ali needs from you

| What | When | Why |
|---|---|---|
| `shared/schemas.py` finalised | **Immediately — he's blocked** | All his prompt builders and parsers use these models |
| `Itinerary`, `ItineraryDay`, `ItineraryActivity` shapes | Before he builds the output parser | His parser maps LLM JSON → these models |
| `UserProfile` shape finalised | Before he writes itinerary prompts | His prompt builder reads `persona_answers`, `constraints`, `emotion_intent` |

### Mushahid needs from you

| What | When | Why |
|---|---|---|
| `shared/schemas.py` finalised | **Immediately — he's blocked** | All route request/response types come from here |
| `PlanTripRequest`, `PlanTripResponse` shapes | Before he builds `/plan-trip` route | His route handler uses these as input/output |
| `module1_constraints.py` working | Before orchestrator step 1 | Orchestrator calls `capture_constraints()` on raw request data |
| `module2_preferences.py` working | Before orchestrator step 1 | Orchestrator calls `parse_answers()` |
| `module3_persona.py` → `infer_persona()`, `infer_emotion()` working | Before orchestrator step 1 | Orchestrator calls these in the first pipeline step |

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
    travel_style_embedding = [0.023, ...],  # set by module3 — Shreyas reads this
    compatibility_signals  = {"pace": "relaxed", "top_interests": ["food", "culture"]}  # Shreyas reads this
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

Design all 9 in Figma → generate with Figma Make → customise in React.

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

1. **`schemas/`** — finish all models, copy to `shared/schemas.py`, tell the team ← **do this today**
2. **Figma** — design all 9 screens + component library, share link with team
3. **`pipeline/module1_constraints.py`** → **`module2_preferences.py`** (no dependencies, build in parallel with Figma)
4. **`pipeline/module3_persona.py`** ← needs `embed_text()` from Shreyas first
5. **Frontend foundation** — Firebase init, auth hook, API client, Tailwind tokens from Figma
6. **Figma Make** → generate component code from Figma screens, drop into `pages/` and `components/`
7. **Screens 1–2** (Welcome, TripPreferences) — can test without backend
8. **Screen 3** (Itinerary) ← needs Mushahid's `/plan-trip` SSE working
9. **Screens 4–6** (Match, Chat, Approve) ← needs Mushahid's `/cotraveller` + `/chat/*` + Shreyas's WebSocket
10. **Screens 7–9** (Shared Itinerary, Notes, Dashboard) ← needs Shreyas's Firestore sync
11. Update `vercel.json` with Mushahid's Render URL → deploy to Vercel
