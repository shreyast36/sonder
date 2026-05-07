# Jahnvi — Lead Product, UX & Frontend Engineer

You own the user-facing layer end to end: schemas that every teammate imports, the pipeline modules that turn raw user input into a persona, and the entire React frontend.

---

## What You Own

| Area | Folder / File | Status |
|---|---|---|
| **Schemas** | `jahnvi/schemas/` + `shared/schemas.py` re-exports | Pending |
| **Persona templates** | `jahnvi/data/persona_templates.py` | Pending |
| **Pipeline module 1** | `jahnvi/pipeline/module1_constraints.py` | Pending |
| **Pipeline module 2** | `jahnvi/pipeline/module2_preferences.py` | Pending |
| **Pipeline module 3** | `jahnvi/pipeline/module3_persona.py` | Pending |
| **Multi-currency** | `shared/currency.py` | Pending |
| **Frontend** | `jahnvi/frontend/` — 10 screens, all components, design tokens | ✅ Done |

---

## Frontend — Done

All 10 screens are built and live at `jahnvi/frontend/src/pages/`:

| Screen | Route | Accent colour |
|---|---|---|
| Welcome | `/` | Gold |
| TripPreferences | `/preferences` | Orange `#F97316` |
| Itinerary | `/itinerary` | Sky `#38BDF8` |
| MatchDetail | `/match/:id` | Violet `#8B5CF6` |
| Chat | `/chat/:sessionId` | Rose `#F43F5E` |
| ApproveDeny | `/approve/:sessionId` | Violet + Green |
| SharedItinerary | `/shared/:id` | Cyan `#06B6D4` |
| Notes | `/notes/:id` | Teal `#14B8A6` |
| Dashboard | `/dashboard` | Amber `#F59E0B` |
| Discover | `/discover` | Pink `#EC4899` |

Components in `src/components/`: `ActivityCard`, `MatchCard`, `ChatBubble`, `BottomNav`, `AppBackground`, `SonderMark3D`.

Design tokens in `src/lib/tokens.js`.

**Firebase auth not yet wired** — waiting on Mushahid's Firebase project config. The "Join Sonder" CTA on Welcome will trigger Google OAuth once the config is available.

---

## What's Blocking You

| Blocked task | Waiting on |
|---|---|
| `src/lib/firebase.js` + `useAuth.js` | Mushahid — Firebase project config (apiKey, authDomain, projectId, etc.) and Google OAuth enabled in Firebase console |
| Module 3 — `build_travel_style_embedding()` | Shreyas — `embed_text()` from `shreyas/retrieval/embeddings.py` |
| Any live API integration | Mushahid — backend running locally + eventual Render URL |

---

## Schema Rule

Define all models in `jahnvi/schemas/<file>.py`. Never define them in `shared/schemas.py` — that file only re-exports. When you change a field on `UserProfile`, `Itinerary`, or `CoTravellerProfile`, announce it to Shreyas and Ali — they import from `shared/schemas.py`.

---

## See Also

- `jahnvi/CLAUDE.md` — frontend conventions: auth headers, SSE pattern, WebSocket heartbeat, 409 conflict handling, profile creation on first login
- `TASKS.md` — full task checklist with ownership
