# Jahnvi — Lead Product, UX & Frontend Engineer

You define what the product looks like and how users interact with it. Everything starts with your schemas — the rest of the team builds on them.

---

## What You Own

| Folder | Responsibility |
|---|---|
| `schemas/` | All Pydantic models and enums — the single source of truth for data shapes |
| `pipeline/` | Modules 1–3: constraint capture, preference questions, persona & emotion inference |
| `data/` | Persona archetype templates — drives `infer_persona()` classification and Pinecone warm-start seeding |
| `frontend/` | React + Vite app — all 9 screens, Firebase Auth, Firestore listeners, SSE + WebSocket hooks |

**Also owns:** `shared/schemas.py`, `shared/config.py`, and `shared/currency.py` — copy finalised models here so everyone can import them.

---

## Your Decisions

### Image source
Activity cards and destination cards need images. You decide the source and add `image_url: Optional[str]` to `Destination` and `Activity` in `jahnvi/schemas/trip.py` (and copy to `shared/schemas.py`).

| Option | Notes |
|---|---|
| **Unsplash API** | Free, high quality, easy to integrate. Query by destination or activity name. Rate-limited to 50 requests/hour on the free tier — cache aggressively. |
| **Pexels API** | Free, no rate limit on standard plan, good travel photo coverage. Slightly lower quality than Unsplash. |
| **Cloudinary** | Paid CDN + image transformation. Best for performance — resize, compress, and serve optimised images at the edge. Worth it if you're worried about mobile load times. |
| **Static placeholder URLs** | Fastest to ship — hard-code a Unsplash URL per destination for the demo, replace later. Zero API dependency. |

Recommended for launch: static placeholder URLs per destination in the seeding script, switch to Unsplash API once the rest of the product is stable.

Add to `.env`:
```bash
UNSPLASH_ACCESS_KEY=your-key     # if using Unsplash
PEXELS_API_KEY=your-key          # if using Pexels
CLOUDINARY_URL=cloudinary://...  # if using Cloudinary
```

---

## Dependencies

### What I need from others

| From | What exactly | Where I use it | Status needed by |
|---|---|---|---|
| **Shreyas** | `shreyas/retrieval/embeddings.embed_text(text)` working — accepts a string, returns `list[float]` | `pipeline/module3_persona.build_travel_style_embedding()` | Before I can finish Module 3 |
| **Mushahid** | Backend running locally on port 8000 | Testing all frontend API calls | Before Screen 2 |
| **Mushahid** | `POST /plan-trip` SSE stream firing named events in sequence | Screen 2 → Screen 3 loading states | Before I build the Itinerary screen |
| **Mushahid** | `POST /cotraveller` returning `list[CoTravellerMatch]` | Screen 4 Match Detail | Before I build match screens |
| **Mushahid** | `POST /chat/start`, `WS /ws/chat/{id}` working | Screen 5 Chat | Before I build chat screen |
| **Mushahid** | `POST /chat/approve` and `POST /chat/deny` | Screen 6 Approve/Deny | Before I build approval screen |
| **Mushahid** | Render backend URL once deployed | `frontend/vercel.json` API rewrite | Before deploying to Vercel |
| **Ali** | Decision on `EMBED_MODEL` and `EMBED_DIMENSIONS` | Goes into `shared/config.py` so Shreyas can configure Pinecone | Before Shreyas starts retrieval |

### What others need from me

| Who | What exactly | Which file | When they're blocked |
|---|---|---|---|
| **Everyone** | `shared/schemas.py` finalised and announced | `shared/schemas.py` | **Right now — blocks the entire team** |
| **Shreyas** | `UserProfile` shape with `compatibility_signals` and `travel_style_embedding` fields | `jahnvi/schemas/user.py` | Before he builds co-traveller matching |
| **Shreyas** | `CoTravellerProfile` and `CoTravellerMatch` shapes | `jahnvi/schemas/cotraveller.py` | Before he builds matching |
| **Shreyas** | `module3_persona.build_compatibility_signals(user_profile)` returning a populated dict | `jahnvi/pipeline/module3_persona.py` | Before his scoring algorithm can read signals |
| **Shreyas** | `module3_persona.build_travel_style_embedding(user_profile)` returning a `list[float]` | `jahnvi/pipeline/module3_persona.py` | Before his Pinecone co-traveller search works |
| **Ali** | `Itinerary`, `ItineraryDay`, `ItineraryActivity` shapes | `jahnvi/schemas/trip.py` | Before he can write the output parser |
| **Ali** | `UserProfile` shape finalised | `jahnvi/schemas/user.py` | Before he can write itinerary prompt builders |
| **Mushahid** | `PlanTripRequest`, `PlanTripResponse`, `UpdateTripRequest`, `UpdateTripResponse` shapes | `shared/schemas.py` | Before he can define route handlers |
| **Mushahid** | `module1_constraints.capture_constraints(raw)` working | `jahnvi/pipeline/module1_constraints.py` | Orchestrator step 1 calls this |
| **Mushahid** | `module2_preferences.parse_answers(raw)` working | `jahnvi/pipeline/module2_preferences.py` | Orchestrator step 1 calls this |
| **Mushahid** | `module3_persona.infer_persona()`, `infer_emotion()` working | `jahnvi/pipeline/module3_persona.py` | Orchestrator step 1 calls these |

---

## Figma Make → React Workflow

Use **Figma Make** to generate your React components directly from your Figma designs.

**Recommended workflow:**
1. Design all 9 screens in Figma using the dark purple design system (reference: Tripora mockup)
2. Use **Figma Make** to generate the initial React/JSX component code from your designs
3. Export generated components into `frontend/src/pages/` and `frontend/src/components/`
4. Clean up the generated code — wire up real props, hooks, and API calls
5. Do not skip the Figma step and code directly — Figma Make only works well from a real design

**Design tokens to define in Figma first:**
- Background: deep dark purple/navy (`~#0a0a1a`)
- Primary: purple accent (`~#7C3AED`)
- Surface: glass-morphism cards with subtle borders
- Match badge: green gradient for high scores
- Buttons: rounded, purple primary / red destructive

Once generated, paste Tailwind color tokens into `frontend/tailwind.config.js`.

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
    budget_usd       = 1796.41,   # always USD — converted at capture time
    budget_currency  = "INR",     # kept for display purposes
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
    travel_style_embedding = [0.023, ...],  # Shreyas reads this for co-traveller search
    compatibility_signals  = {"pace": "relaxed", "top_interests": ["food", "culture"]}  # Shreyas reads this for matching
)
```

---

## Pipeline Module Contracts

### Module 1 — `capture_constraints`

`capture_constraints` is `async` — it calls `convert_to_usd()` which may hit the exchange rate API.

```python
# Input (raw form from Screen 2)
# Frontend sends budget_amount + budget_currency — never budget_usd directly
{
    "destination_type":  "beach",
    "start_date":        "2025-06-01",
    "end_date":          "2025-06-07",
    "budget_amount":     150000.0,
    "budget_currency":   "INR",    # ISO 4217 — defaults to "USD" if omitted
    "group_size":        2,
    "pace_preference":   "relaxed",
    "must_haves":        ["snorkeling", "local food"],
    "avoid_list":        ["nightclubs"]
}

# Output — budget_usd is always USD; budget_currency kept for display
TripConstraints(
    destination_type = "beach",
    start_date       = date(2025, 6, 1),
    end_date         = date(2025, 6, 7),
    budget_usd       = 1796.41,   # converted from 150000 INR
    budget_currency  = "INR",
    group_size       = 2,
    pace_preference  = PacePreference.relaxed,
    must_haves       = ["snorkeling", "local food"],
    avoid_list       = ["nightclubs"]
)
```

### Module 2 — `parse_answers`

```python
# Input
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
    "archetype":     "Cultural Explorer",
    "top_interests": ["food", "culture"],
    "energy":        "low-moderate",
    "label":         "You love discovering local culture through food and art at a relaxed pace."
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
| 7. Shared Itinerary | `/trip/:id` | Firestore real-time sync, "Added by" labels, email/PDF export |
| 8. Notes | `/trip/:id/notes` | Firestore notes array, real-time updates |
| 9. Dashboard | `/dashboard` | Firestore trip list, active chats |

### SSE Events to Handle (Screen 3)

```javascript
"persona_inferring"  → "Understanding your travel style..."
"retrieving"         → "Finding the best destinations..."
"ranking"            → "Ranking options for you..."
"generating"         → "Building your itinerary..." + skeleton cards
"explaining"         → "Adding personalised insights..."
"validating"         → "Checking everything looks right..."
"revision"           → "Refining based on feedback..." (may repeat)
"matched"            → "Finding your perfect travel buddy..."
"done"               → render full PlanTripResponse
```

### Firebase Auth Pattern

```javascript
const app  = initializeApp({ /* VITE_ env vars */ })
export const auth = getAuth(app)
export const db   = getFirestore(app)

// Attach ID token to every backend request
const token = await auth.currentUser.getIdToken()
fetch('/api/plan-trip', { headers: { Authorization: `Bearer ${token}` } })
```

---

## Build Order

1. **`schemas/`** → copy to `shared/schemas.py` → tell the team ← **do this first**
2. **Figma** — all 9 screens + component library
3. **`pipeline/module1_constraints.py`** + **`module2_preferences.py`** (no external deps)
4. **`pipeline/module3_persona.py`** ← needs `embed_text()` from Shreyas first
5. **Frontend foundation** — Firebase init, auth hook, API client, Tailwind tokens
6. **Figma Make** → generate components → drop into `pages/` and `components/`
7. **Screens 1–2** (can test without backend)
8. **Screen 3** ← needs Mushahid's `/plan-trip` SSE
9. **Screens 4–6** ← needs Mushahid's `/cotraveller` + Shreyas's WebSocket
10. **Screens 7–9** ← needs Shreyas's Firestore sync
11. Update `vercel.json` with Mushahid's Render URL → deploy
