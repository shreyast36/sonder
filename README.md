# Sonder — AI Co-Traveller Trip Planner

> Plan smarter. Find your perfect co-traveller. Build the trip together in real time.

AI-powered trip planning, deep co-traveller matching, a live social surface, and a real-time shared-itinerary negotiation loop — all in one product.

---

## What It Does

Sonder takes a user from zero to a personalised, day-by-day itinerary, matches them with compatible co-travellers, and then lets the pair negotiate the actual trip together with a real-time, optimistic-locked shared itinerary. On the way it surfaces a live social feed and a discovery wall of trips other people are opening up to companions.

**Full user journey:**

1. **Persona reveal** — Enter trip basics (destination, dates, budget in any currency, must-haves) + five oblique persona questions. Get a descriptor, paragraph, bullets, emotional-tone subtitle, and inferred push/pull dimensions.
2. **Itinerary generation** — Live-streamed, day-by-day, with "Why this?" RAG explanations per activity. Auto-saved to your trip history.
3. **Trip vault** — Every saved trip on the dashboard. Switch the active one, open Journal entries, jump to the destination feed.
4. **Co-traveller matching** — Curated top-3 matches, scored on a transparent salience-weighted feature pipeline. Synthetic personas (LLM-designed) fill the pool until real-user density is there.
5. **Chat → mutual approval** — Real-time WebSocket chat with presence, typing, seen receipts, in-app banners, OS push. The persona's reciprocal approval is a coin flip weighted by the live match score (no hardcoded thresholds).
6. **Shared itinerary negotiation** — Once approved, a `/shared/{id}` page where both sides propose, counter, and accept activity changes. Persona evaluations run off the request path so the UI feels instant; verdicts arrive over WebSocket. Optimistic locking on `version` prevents silent overwrites.
7. **Sonder Pulse (Dashboard)** — A live two-column section showing **Open invitations** (trips other people opened for companions) and **The room** (a social feed of posts + threaded comments). Synthetic personas autonomously post and open trips every 15-50 seconds; real users join the room organically.
8. **Join-to-trip flow** — Click any open invitation → a detail modal with persona snapshot, match-preview percentage, and a colour-coded fit label. Synthetic trips auto-resolve instantly using the same compatibility signal that drives matching; approved requests add you to the trip's co-traveller list.
9. **Finalise** — Pair locks the itinerary in. Email it or download a PDF.

---

## Team Ownership

| Person | Role | Owns |
|---|---|---|
| **Jahnvi** | Lead Product, UX & Frontend | User input schemas (`UserProfile`, `TripConstraints`, `PersonaQuestionAnswers`) · User input pipeline · GoEmotions classifier · React frontend (Dashboard, Pulse, SharedItinerary, NotificationProvider) |
| **Shreyas** | Lead AI Systems & Real-time | Co-traveller + chat schemas · Candidate **selection** (embeddings + search + ranking) · Co-traveller matching · Real-time layer (WS rooms, presence, broadcast_global, shared itinerary state) |
| **Ali** | Lead AI Intelligence | Trip/itinerary schemas · Pinecone vector database · All LLM clients + routing · Itinerary generation · RAG **explanation** · Chat reply / opener / topics · Proposal evaluator · Synthetic-social content generators |
| **Mushahid** | Lead Backend & Infrastructure | API + validation schemas · FastAPI app · Pipeline orchestrator · Validation + refinement loop · Firebase + Web Push real-time layer · Emotional signature inference · Synthetic agents background loop · Deployment |

### Shreyas vs. Ali — the key distinction

Both work with Pinecone and AI, but do different things:

| | Shreyas | Ali |
|---|---|---|
| **Question answered** | Which destinations / activities / people should we show this user? | Why was this chosen? What should the persona / itinerary actually say? |
| **Pinecone usage** | Query the index to **select** top-N candidates for ranking | Query the index to **fetch context** for already-chosen activities |
| **Output** | Ranked candidate list → goes into the trip plan | LLM-generated text → shown to the user as "Why this?" / chat replies / persona-voiced posts |
| **When it runs** | Pipeline steps 2, 3, 7 (before the itinerary exists) | After the itinerary is generated AND on every chat / negotiation turn |

---

## Architecture

### Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Framer Motion |
| Auth | Firebase Auth (Google + email/password) |
| Real-time DB | Cloud Firestore (named DB via `FIRESTORE_DATABASE_ID`) |
| Backend API | FastAPI (Python 3.11) on Render |
| Vector DB | Pinecone — owned and managed by Ali |
| AI — Small models | Per-provider config: `ANTHROPIC_SMALL_MODEL` / `OPENAI_SMALL_MODEL` (defaults in `shared/config.py`) |
| AI — Large models | Per-provider config: `ANTHROPIC_LARGE_MODEL` / `OPENAI_LARGE_MODEL` |
| AI — Validators | `SMALL_VALIDATOR_PROVIDER` + `LARGE_VALIDATOR_PROVIDER` |
| AI — Image | OpenAI `gpt-image-1` (seed time only, for synthetic persona portraits) |
| AI — Emotion classifier | GoEmotions 27-label cosine classifier (in-memory) |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) |
| Email | Resend / SendGrid / SES — `EMAIL_PROVIDER` |
| Web Push | Service worker (`public/sw.js`) + VAPID + `pywebpush` |
| Frontend hosting | Vercel |
| Backend hosting | Render |
| Monitoring | Sentry (errors) + PostHog (analytics) |

### Folder Structure

```
sonder/
├── shared/                  # Config, utilities, schema aggregator
│   ├── schemas.py           # Re-exports all models — import from here
│   ├── config.py            # All env var reads — never call os.getenv() outside here
│   ├── currency.py          # Multi-currency conversion
│   └── email.py             # Transactional email
│
├── jahnvi/                  # User pipeline + schemas + frontend
│   ├── schemas/             # TripConstraints, PersonaQuestionAnswers, UserProfile, social
│   ├── pipeline/            # Modules 1–3: constraints → preferences → persona
│   ├── data/                # persona_labels.py, dimensions.py, emotions.py
│   └── frontend/            # React + Vite app
│       ├── public/sw.js     # Web Push service worker
│       └── src/
│           ├── pages/       # Dashboard, SharedItinerary, Chat, MatchDetail, ...
│           ├── components/  # DashboardPulse, NotificationProvider, SonderMark3D, ...
│           └── hooks/       # useWebSocket, useAuth, useSSE
│
├── shreyas/                 # Candidate selection + real-time
│   ├── schemas/             # CoTraveller + Chat models, ApprovalStatus enum
│   ├── retrieval/           # Embeddings + Pinecone search
│   ├── ranking/             # Generic engine, stages, policies (cotraveller/destination/activity)
│   └── cotraveller/         # Matching, ConnectionManager (rooms + user channels + broadcast_global),
│                            #   presence, shared itinerary, approval
│
├── ali/                     # AI intelligence layer
│   ├── schemas/             # Trip/Itinerary models, ModelTier enum, is_open_to_join / join_capacity
│   ├── vector/              # Pinecone index setup + batched embeddings
│   ├── clients/             # LLM provider wrappers
│   ├── routing/             # Task classifier + multi-model routing engine
│   ├── generation/          # Itinerary, chat (topics/icebreaker/reply), proposal_evaluator,
│   │                        #   synthetic_social (persona-voiced posts + open-trip notes)
│   └── rag/                 # retriever.py + explainer.py
│
├── mushahid/                # Backend API + orchestration + validation
│   ├── schemas/             # API request/response models, ValidationResult
│   ├── main.py              # FastAPI app entry; lifespan kicks off synthetic_agents_loop
│   ├── auth.py              # Firebase ID token verification (header + first-message WS)
│   ├── routes/              # All HTTP + WebSocket endpoints
│   │   ├── shared.py        # Shared itinerary propose/respond/withdraw/finalize + async eval
│   │   ├── discover.py      # Open trips, join requests, trip preview, instant-resolve synthetic
│   │   └── feed.py          # Posts + comments + web push fan-out
│   ├── background/
│   │   └── synthetic_agents.py  # Forever-loop: personas post + open trips
│   ├── persona/             # taxonomy.py + emotional_signature.py
│   ├── pipeline/            # Orchestrator: runs all steps, streams SSE
│   ├── validation/          # LLM critic + rule checks
│   ├── refinement/          # Closed-loop regeneration
│   └── realtime/            # firestore.py, sse.py, web_push.py
│
├── scripts/
│   ├── seed_pinecone.py             # Destinations + activities
│   ├── seed_cotravellers.py         # LLM-designed personas + gpt-image-1 portraits
│   └── generate_vapid_keys.py       # One-time VAPID keypair generator
│
├── .env.example
├── requirements.txt
└── TASKS.md
```

### Generation Pipeline

```
POST /persona-infer
│  embed user text + GoEmotions classify ── asyncio.gather ──┐
│  ┌─ persona LLM (descriptor / paragraph / bullets / push / pull)
│  └─ emotional_signature inferrer (taxonomy × evidence × goemotions)
│  merge → compatibility_signals + emotional_tone surfaced to UI

POST /plan-trip
│
├── [Jahnvi]   Module 1 — capture_constraints()       → SSE: persona_inferring
├── [Jahnvi]   Module 2 — parse_answers()
├── [Jahnvi]   Module 3 — infer_persona / infer_emotion → SSE: persona_inferred
│
├── [Shreyas]  search_destinations / search_activities  → SSE: retrieving / retrieval_done
├── [Shreyas]  rank_destinations / rank_activities      → SSE: ranking / ranked
│
├── [Ali]      generate_itinerary  (LARGE, streamed)    → SSE: generating / itinerary_generated
├── [Ali]      explain_itinerary  (RAG, parallel)       → SSE: explaining
│
├── [Mushahid] run_all_checks + validate_large_output   → SSE: validating
│              REVISE → run_refinement_loop             → SSE: revision / validated
│
├── [Shreyas]  search_cotravellers + get_top_matches    → SSE: matching_cotravellers / matched
│
└── → SSE: done { PlanTripResponse }
```

### LLM Architecture

| Slot | Owner | Purpose | Config |
|---|---|---|---|
| **Small** | Ali | Chat topics, opener, persona label, quick edits, emotional-signature inference, "Why this?", **synthetic post / open-trip notes**, **proposal evaluator**, **chat reply** | `*_SMALL_MODEL` |
| **Large** | Ali | Itinerary generation, complex refinement | `*_LARGE_MODEL` |
| **Small Validator** | Mushahid | Verifies Small outputs + **async chat-reply validator (edit-in-place)** | `SMALL_VALIDATOR_*` |
| **Large Validator** | Mushahid | Verifies full itineraries | `LARGE_VALIDATOR_*` |
| **Image** | seed-time only | gpt-image-1 portraits | `OPENAI_API_KEY` |

The router engine reads provider per tier from env; each provider client reads its own model name so cross-provider fallback can't 404.

### Real-Time Layer

| Feature | Transport | Direction | Owner |
|---|---|---|---|
| Itinerary generation progress | SSE (`/api/plan-trip`) | Server → user | Mushahid |
| Chat messages + typing + seen | WebSocket (`/api/ws/chat/{session_id}`) | Bidirectional | Shreyas |
| Co-traveller presence (TTL) | WS broadcast + Firestore `presence/{uid}` | Bidirectional | Shreyas |
| Chat-reply edit-in-place (validator repair) | WS `message_edited` event | Server → user | Mushahid + Shreyas |
| In-app banners | WebSocket (`/api/ws/notifications`) | Server → user | Mushahid |
| **Discover broadcasts** (`discover_trip_open` / `_close` / `discover_post_new`) | `ConnectionManager.broadcast_global` over `/ws/notifications` | Server → all users | Shreyas |
| **Targeted social events** (`join_request_new`, `join_request_resolved`, `comment_new`) | `notify_user` over `/ws/notifications` | Server → one user | Mushahid |
| **Web Push (offline-capable)** | VAPID + service worker | Server → device | Mushahid |
| Shared itinerary edits | Firestore + optimistic locking via `version` | Bidirectional | Shreyas |
| Async persona evaluation result | WS `shared_responded` event | Server → user | Mushahid |
| Approval status (live) | Firestore | Bidirectional | Shreyas |

**Web push fans out for:**
- New chat message (when tab is closed)
- Join request received → trip owner
- Join verdict → requester (deep-links to `/shared/{id}` on approve)
- Comment on your post → post author

WebSocket auth uses the first-message pattern (token in initial JSON payload, never in query string). Web push silently no-ops when VAPID keys aren't configured; in-app banners still work.

### Shared Itinerary Negotiation

Both participants edit one `SharedItinerary` doc; every change goes through the proposal/counter loop:

```
POST /shared/{id}/propose      user proposes add | replace | move
   │
   ├─ writes ProposedChange (status="proposed") + "evaluating" activity entry
   ├─ broadcasts shared_proposed
   ├─ returns IMMEDIATELY (HTTP response doesn't block on LLM)
   │
   └─ asyncio.create_task(_evaluate_proposal_async)
        ├─ runs evaluate_proposal (SMALL tier, persona-voiced JSON)
        ├─ accept → commit change to itinerary, log "accepted"
        ├─ counter → mark user's change as "countered", mint persona ProposedChange
        └─ broadcasts shared_responded   (frontend polls + WS handler converge)

POST /shared/{id}/respond      user accepts or counters a persona's change
POST /shared/{id}/withdraw     proposer retracts their own pending change
POST /shared/{id}/persona-suggest   persona proposes spontaneously (also async)
POST /shared/{id}/finalize     locks the itinerary (no more changes)
```

Optimistic locking: every write checks `client_version == current_version`. Mismatch returns HTTP 409 — the client re-fetches and lets the user retry.

The frontend `/shared/{id}` page renders a live activity feed (filtered to entries created after the page mounted, so reload gives a clean slate) and a per-day card grid with inline Accept / Counter / Replace / Move actions.

### Sonder Pulse (Dashboard discovery surface)

The former standalone `/discover` page is folded into Dashboard as a full-width section under the trip grid. Two columns:

- **Open invitations** — `listOpenTrips(24)` + `discover_trip_open` / `_close` WS push. Owner's own trips show with a "Your trip · live" badge.
- **The room** — social feed with composer + threaded comments. `listFeed(20)` + `discover_post_new` WS push.

Both lists are **hard-capped at `PULSE_MAX = 10`** at every entry point (poll, WS push, optimistic composer insert) so a long session can't grow the arrays unbounded.

A **LiveTravellersStrip** in the trip-vault header subscribes to the same events and pops an avatar bubble for each new action — violet for trips, gold for posts. Hover for `name · city · action`, click to smooth-scroll to Pulse.

### Synthetic Agents

`mushahid/background/synthetic_agents.py` runs a forever-loop kicked off in the FastAPI lifespan:

- Every `SYNTHETIC_AGENTS_MIN_INTERVAL`..`MAX_INTERVAL` seconds (default 15-50s) picks a random persona and fires one action.
- 65% chance → social post via `generate_synthetic_post` (SMALL-tier LLM, persona-voiced).
- 35% chance → open a trip via `generate_synthetic_open_trip_note` against a curated destination pool. Mints a minimal `Itinerary` doc with the persona's `profile_id` as `user_id`, flips `is_open_to_join=True`.
- **Cold-start seed burst** (`SYNTHETIC_AGENTS_SEED_COUNT`, default 6) fires actions in parallel via `asyncio.gather` so the first user to land sees a populated feed.
- **Persona fallback pool** — if Pinecone returns no seeded `CoTravellerProfile`s, falls back to a hardcoded 10-persona inline set (`Mira/Berlin`, `Theo/Lisbon`, `Aiko/Kyoto`, ...) so the loop always has someone to act as.
- Persona snapshot (`synthetic_owner` dict) is denormalised onto the itinerary doc when opening a trip, so the join-request route can score the user against the persona without re-hitting Pinecone.

### Synthetic-trip Join Flow (instant verdict)

When a user requests to join a synthetic trip, the backend detects the snapshot and resolves the request **immediately** using the same compatibility engine that drives `/match`:

```
POST /discover/trips/{id}/join-request
  ├─ if synthetic:
  │     match_score = score_compatibility(viewer, snapshotted_persona)
  │     verdict = "approved" if random() < match_score else "denied"
  │     ── approved → append uid to itinerary.co_traveller_ids
  │     ── broadcast join_request_resolved + web push
  │     return { request, auto_resolved: true }
  │
  └─ else: persist as proposed, ping the human owner
```

`p_approve = match_score` directly — same calibration as chat-side mutual approval. No hardcoded thresholds. The frontend `TripDetailModal` shows the persona snapshot + match-preview percentage with a colour-coded fit label ("Strong fit" / "Good fit" / "Borderline" / "Long shot"), then flips to a verdict screen with a deep-link to `/shared/{id}` on approve.

### Synthetic Co-Travellers (Pinecone seed pool)

The matching pool is seeded with LLM-designed personas (no randomuser.me / stock photos). For each diversity-matrix slot (emotional signature × age bracket × home city), the LARGE LLM writes a full persona JSON. Each persona gets:

- A stylised cinematic portrait from `gpt-image-1` (painterly, explicitly not photoreal)
- A stable voice id from a deterministic hash of `profile_id` against the OpenAI TTS whitelist
- An emotional signature via the same inferrer real users hit
- A rich embedding text upserted to the `cotravellers` Pinecone namespace

Every record carries `is_seed: True` for "Sonder Curated" disclosure. Seed cost is ~$2–4 for 50 personas (gpt-image-1 dominates).

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Firebase project (Auth + Firestore enabled)
- Pinecone account
- OpenAI + Anthropic API keys
- (Optional) VAPID keypair for Web Push

### Backend

```bash
git clone https://github.com/shreyast36/sonder
cd sonder
pip install -r requirements.txt

cp .env.example .env
# Fill in all keys

# (Optional) Generate VAPID keys for closed-browser push:
python -m scripts.generate_vapid_keys
# Paste VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY into .env

# Seed Pinecone destinations + activities
python -m scripts.seed_pinecone --namespace all

# Seed synthetic co-travellers (LLM personas + gpt-image-1 portraits)
python -m scripts.seed_cotravellers --count 50

uvicorn mushahid.main:app --reload --port 8000
```

The synthetic-agents background loop auto-starts in the lifespan. Watch for `[synthetic_agents] LOOP STARTED` then `[synthetic_agents] posted as ...` / `opened trip ...` lines to confirm it's firing. Disable with `SYNTHETIC_AGENTS_ENABLED=false`.

### Frontend

```bash
cd jahnvi/frontend
npm install
cp ../../.env.example .env.local
# Fill in VITE_ prefixed Firebase config values
npm run dev
# → http://localhost:5173
```

---

## API Reference

### Auth / Users
| Method | Route | Returns |
|---|---|---|
| `GET` | `/api/users/profile` | `UserProfile` — 404 if not yet created |
| `POST` | `/api/users/profile` | Creates profile on first login |
| `POST` | `/api/auth/password-reset` (public) | Silently succeeds (prevents account enumeration) |

### Trip planning
| Method | Route | Returns |
|---|---|---|
| `POST` | `/api/persona-infer` | Descriptor / paragraph / bullets + push / pull + `emotional_tone` |
| `POST` | `/api/plan-trip` | SSE stream → `PlanTripResponse` |
| `POST` | `/api/update-trip` | `UpdateTripResponse` — free-text or per-activity feedback |
| `GET`  | `/api/visa-check?destination_country=X&nationality=Y` (public) | `VisaInfo` |

### Itineraries / trip history
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/api/itineraries/current` | Active dashboard trip (or `{itinerary: null}`) |
| `GET`  | `/api/itineraries/list` | All saved trips, newest first |
| `POST` | `/api/itineraries/{id}/save` | Append to history + mark current |
| `POST` | `/api/itineraries/set-current` | Switch hero trip |
| `GET`  | `/api/itineraries/{id}/companion-prefs` | Per-trip companion intake answers |
| `POST` | `/api/itineraries/{id}/companion-prefs` | Persist intake answers |

### Co-traveller matching + chat
| Method | Route | Returns |
|---|---|---|
| `POST` | `/api/cotraveller` | `list[CoTravellerMatch]` (top 3) |
| `POST` | `/api/cotraveller/regenerate` | Fresh matches, excludes prior profiles |
| `GET`  | `/api/cotraveller/profile/{profile_id}` | Single `CoTravellerMatch` |
| `POST` | `/api/chat/start` | `ChatStartResponse` (session + opener + 5 topics) |
| `GET`  | `/api/chat/session/{session_id}` | Session metadata |
| `GET`  | `/api/chat/{session_id}/messages` | Full message history |
| `GET`  | `/api/chat/{session_id}/presence/{user_id}` | Online + last_seen |
| `POST` | `/api/chat/approve` | User approves → schedules persona's reciprocal decision (p = `match_score`) |
| `POST` | `/api/chat/deny` | Both sides stamped denied (terminal) |
| `WS`   | `/api/ws/chat/{session_id}` | Chat stream — first-message auth |
| `WS`   | `/api/ws/notifications` | Global notification channel — first-message auth |

### Shared itinerary
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/api/shared/{id}` | Full `SharedItinerary` (bootstraps on first read) |
| `POST` | `/api/shared/{id}/propose` | Returns instantly; persona eval runs async |
| `POST` | `/api/shared/{id}/respond` | Accept or counter a pending change |
| `POST` | `/api/shared/{id}/withdraw` | Retract your own pending change |
| `POST` | `/api/shared/{id}/persona-suggest` | Persona proposes spontaneously (async) |
| `POST` | `/api/shared/{id}/finalize` | Lock the itinerary |

### Discover (open trips + join requests)
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/api/discover/trips` | Cards of every trip with `is_open_to_join=true`; viewer's own marked `is_yours=true` |
| `POST` | `/api/itineraries/{id}/open` | Owner flips trip open with capacity + note |
| `POST` | `/api/itineraries/{id}/close` | Owner takes trip off the feed |
| `POST` | `/api/discover/trips/{id}/join-request` | Request to join; synthetic trips auto-resolve inline |
| `GET`  | `/api/discover/trips/{id}/preview` | Persona snapshot + match-score preview for TripDetailModal |
| `GET`  | `/api/discover/join-requests?as=requester\|owner` | List your join requests |
| `POST` | `/api/discover/join-requests/{id}/respond` | Owner approves / denies (non-synthetic only) |

### Social feed
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/api/feed?limit=N&before=ISO` | Newest-first posts page (keyset pagination) |
| `POST` | `/api/feed/posts` | Create a post |
| `GET`  | `/api/feed/posts/{id}` | Single post |
| `DELETE` | `/api/feed/posts/{id}` | Author-only delete (cascades comments) |
| `GET`  | `/api/feed/posts/{id}/comments` | Thread, oldest first |
| `POST` | `/api/feed/posts/{id}/comments` | Append comment + push to post author |

### Web Push
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/api/push/vapid-public-key` (public) | `{key}` — 503 when web push isn't configured |
| `POST` | `/api/push/subscribe` | Upserts the browser's `PushSubscription` |
| `POST` | `/api/push/unsubscribe` | Drops a subscription by endpoint |

### Export
| Method | Route | Returns |
|---|---|---|
| `POST` | `/api/export/email` | `{"sent_to": [...]}` |
| `POST` | `/api/export/email/test` | Self-test send |
| `GET`  | `/api/export/pdf/{itinerary_id}?token=…` | PDF stream |

### Journal + destination discovery
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/api/itineraries/{id}/journal` | All journal entries for a trip |
| `POST` | `/api/itineraries/{id}/journal` | Create / update entry (private or public) |
| `DELETE` | `/api/journal/{entry_id}` | Soft delete |
| `GET`  | `/api/destinations/{city}/journal` | Public entries from the destination feed |

### Health
| Method | Route | Returns |
|---|---|---|
| `GET`  | `/health` (public) | `{"status": "healthy" \| "degraded", "services": {...}}` |

---

## Key Design Decisions

### Mutual approval = `p_approve = match_score`

Both the chat-side persona reciprocal decision AND the synthetic-trip join verdict use the same calibration: a coin flip weighted by the live `match_score`. No hardcoded thresholds, no piecewise tables — the ranker's own number IS the probability. Score nudges up during chat via `_apply_chat_signals` as compatibility cues fire, so the verdict tracks the real conversation rather than a frozen prior.

### Async persona evaluation (proposal + suggest)

`/shared/{id}/propose` and `/shared/{id}/persona-suggest` write the user-visible state + return immediately, then run the LLM eval in `asyncio.create_task`. Result lands via `broadcast_global` over `/ws/notifications` and the frontend's `useWebSocket` plus 1.5s adaptive polling converge. Users feel an instant click rather than waiting 2-4s on the request thread.

### Edit-in-place chat validator

The reply broadcast is unblocked; a fire-and-forget validator task runs `validate_and_repair_chat_reply_wired` after broadcast. If it repairs the text, `update_chat_message_content` patches the persisted doc and a `message_edited` WS event tells connected clients to swap the bubble text in place. Users see the reply instantly and watch it self-correct a moment later when needed.

### Per-session activity feed (shared itinerary)

The `SharedItinerary.activity_log` is persisted in full server-side, but the frontend's `<ActivityFeed>` filters entries by `created_at >= pageOpenedAtRef`. Reloading gives a clean visual slate without touching the persistent log — the user controls what's "noise".

### `broadcast_global` for app-wide signals

`ConnectionManager.broadcast_global(event, exclude_user=...)` fans an event to every connected notification socket. Used for `discover_trip_open` / `_close` / `discover_post_new` so opening a trip surfaces it on every active dashboard in real time. Personally-directed events (`join_request_new`, `_resolved`, `comment_new`) use `notify_user` instead.

### Web push for offline events

Chat messages, join requests received, join verdicts, and comments on your posts ALL fire web push in addition to WS notify. The service worker (`public/sw.js`) renders an OS notification with the right deep-link. Broadcast events deliberately NOT pushed — fan-out × user_count would be spammy.

### Persona inference — five oblique questions

Five questions designed to surface latent travel psychology without ever naming the dimensions:

| Field | Question | Surfaces |
|---|---|---|
| `social_role` | "On a trip, people usually end up relying on you for…" | social role + emotional regulation |
| `trip_feeling` | "The best trips usually leave you feeling…" | push / pull / motivation |
| `friction_response` | "Something goes wrong halfway through the day. Your instinct is to…" | resilience, control orientation |
| `ideal_atmosphere` | "You instantly feel at home in places that are…" | stimulation threshold, introversion |
| `small_thing` | Free text — "a tiny thing that made life feel unusually good" | metaphor + aesthetic cadence |

### Emotional signature — private framing, not user-facing vocabulary

`mushahid/persona/taxonomy.py` defines an 8-key closed taxonomy. The signature feeds five downstream consumers (chat reply, opener, topics, "Why this?", persona reveal) as private prompt context. The raw key is **never** surfaced; the generated `emotional_tone` phrase ("soft afternoon energy") is the only thing the UI shows.

### Ranking architecture — generic engine, equal-weight priors

All three rankers (co-traveller, destination, activity) run through one engine in `shreyas/ranking/engine.py`. Every policy ships with `weights = {f: 1/N for f in features}` — equal-weight priors expressing honest uncertainty. Budget is a feasibility gate (`filters.py`), not a ranker signal. `RankedCandidate` separates retrieval score from feature scores from rerank adjustments. Per-question salience drives the overlap feature: users who wrote more revealing free text get their `small_thing` weighted higher automatically.

### Auto-save trips + cache fallback

Every generated trip persists to the user's `saved_itinerary_ids` on the SSE `done` event. Dashboard's trip vault renders all saved trips, current one badged. If `listSavedItineraries` returns empty (brand-new profile or transient Firestore hiccup), the dashboard synthesises a single vault entry from `getCurrentItinerary` → `localStorage` cache, so the vault never silently empties on the user.

### Optimistic locking on shared itinerary

Every write to `shared_itineraries/{id}` checks `client_version == current_version`. Mismatch → HTTP 409, client re-fetches and retries. Prevents silent overwrites when both sides edit simultaneously.

### Cross-provider model fallback safety

Per-provider model env vars (`ANTHROPIC_SMALL_MODEL` / `OPENAI_SMALL_MODEL`) so the engine fallback can't accidentally send an Anthropic model id to OpenAI on retry.

### Multi-currency

All internal cost fields (`budget_usd`, `cost_usd`, `avg_daily_cost_usd`) are always USD. Conversion happens once at the input boundary in `capture_constraints()` via `shared/currency.py`.

---

## Deployment

### Backend → Render
1. Connect GitHub repo
2. Build: `pip install -r requirements.txt`
3. Start: `uvicorn mushahid.main:app --host 0.0.0.0 --port 8000`
4. Add all env vars from `.env.example` (Firebase, OpenAI, Anthropic, Pinecone, VAPID, Sentry, PostHog, per-provider model names, synthetic-agent knobs)
5. Health check path: `/health`

`ConnectionManager` and the synthetic-agents loop both hold in-memory state. Single-container is fine; multi-container production needs Redis pub/sub for both (the `REDIS_URL` config is already in `shared/config.py`).

### Frontend → Vercel
1. Root directory: `jahnvi/frontend`
2. Framework: Vite
3. Add all `VITE_` env vars
4. Update `vercel.json` API rewrite URL to your Render backend URL
5. **HTTPS required** for Web Push (Vercel + Render handle this by default)

### Synthetic-agents tuning on prod
- Default cadence (15-50s) is built for "feels alive" demo state. For prod with real users, raise `SYNTHETIC_AGENTS_MIN_INTERVAL` / `MAX_INTERVAL` to thin the feed once organic content exists.
- `SYNTHETIC_AGENTS_ENABLED=false` disables the loop entirely.

### Cotraveller avatars
After running `seed_cotravellers.py`, upload `seed_assets/cotraveller_avatars/*.png` to your static host and update the URL prefix in Pinecone metadata or serve `/seed_assets/` from your CDN.

---

See [TASKS.md](./TASKS.md) for the per-person build checklist.
