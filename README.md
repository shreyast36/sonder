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

### Chat latency engineering (<5s target)

The persona-chat round-trip was 5-9s on the LARGE tier; it now lands in ~1-2s:

- **Routed `chat_reply` to the SMALL tier** in `ali/routing/classifier.py`. 1-3 sentence text-message responses don't need Sonnet/GPT-4o for persona voice; Haiku/4o-mini gives the same quality 3× faster, which the user actively feels under the live typing indicator.
- **Parallel I/O** in `_send_synthetic_reply`. The three pre-LLM fetches (Pinecone candidate, Firestore itinerary, Firestore message history) used to serialise via `await` for ~0.6-1s of cumulative round-trip. Now `await asyncio.gather(...)` runs them concurrently; total wait = the slowest single call.
- **History window cap** — `_CHAT_HISTORY_TURN_CAP = 20` (was 40 implicitly). Half is enough for multi-turn persona consistency and roughly halves prompt-token latency.
- **Trimmed cosmetic delays** — `_REPLY_BEFORE_TYPING_S = (0.1, 0.25)` and `_REPLY_AFTER_REPLY_S = (0.05, 0.15)` (was 0.6-1.8s). With the LLM call now sub-2s, longer pacing felt like lag rather than realism. A `_TYPING_KEEPALIVE_S = 2.0` task re-emits typing every 2s so the indicator doesn't vanish mid-call (frontend clears typing after 3.5s).

### Chat signal scanner — live match-score updates from conversation

`_apply_chat_signals` is a fire-and-forget task that runs after every user message in the chat WS handler. It:

1. Scans the message for PPM-keyword cues via `shreyas/cotraveller/chat_signal_scanner.py` (`scan_and_apply`).
2. If any signals fire, updates the session's `live_weights` (a per-session weight overlay).
3. Re-runs `score_compatibility(viewer, candidate)` against the persona with the new weights spliced into `compatibility_signals.ranker_weights["cotraveller"]`.
4. Writes the refreshed `match_score` back onto the `ChatSession`.

This is the same number that drives the persona's reciprocal approval (`p_approve = match_score`) and the synthetic-trip auto-resolve verdict — so as the user reveals more in chat, both calibrations track the live conversation instead of a frozen prior. Failures are swallowed; the chat reply itself is never blocked on the scan.

### Activity feed dedupe (shared itinerary)

The raw `activity_log` accumulates `evaluating` entries every time someone proposes — they're useful for "X is reviewing your proposal" but become noise once the verdict lands. `<ActivityFeed>` runs three filters before render:

1. **Per-session filter** — drop entries created before `pageOpenedAtRef`. Reload = clean slate.
2. **Resolution dedupe** — strip `evaluating` entries that have a follow-up resolution (`accepted` / `countered` / `proposed`) from the same actor within 90s. The verdict line carries the same information.
3. **Orphan timeout** — strip `evaluating` entries older than 60s with no follow-up. These are dropped LLM calls (`suggest_proposal` returning None, etc) that would otherwise linger forever.

Persona-suggest also tracks its `evaluating` entry by ID and `_drop_evaluating()` removes it on the two no-result paths (no suggestion / dedupe rejection) so the no-op cases never leave orphan rows server-side either.

### Matches list — top 3, denied filter, paired suppression

- **Capped at top 3** — denser quality bar than the old top-10. When the user denies one, the next regenerate call slots in a fresh candidate so the list always shows 3.
- **Denied profiles filtered** — `cotraveller` route excludes any `profile_id` that's appeared in a `denied` `ChatSession` for the viewer. Prevents the same persona showing up two days after you said no.
- **Already-paired suppression** — if the viewer has an `approved` chat session for the current trip, the matches list returns `{ matches: [], active_pair: {...} }` and the dashboard renders an "Open your shared itinerary" card instead of the carousel. Avoids the awkward "match with someone else while you're mid-negotiation" UX.
- **Auto-redirect after denial** — denying a match triggers a regenerate + redirect on the dashboard so the user lands on the fresh matches view instead of staring at an empty slot.

### Dashboard reorganisation

The dashboard reads top-to-bottom as a single editorial scroll, every section sharing the same visual rhythm:

| Section | What |
|---|---|
| Greeting | Time-of-day greeting + serif italic first name in gold gradient with breathing drop-shadow |
| **Live stats strip** | Glass pill — `{n} trips planned · {n} curated matches · {n} awaiting you` (pulsing violet when join requests are pending) |
| **Top nav** | Always-visible amber-gradient **"Plan a trip"** CTA |
| LEFT col | Trip hero card (destination photo bg, dates, days-away) + action row (Journal / Notes / Open to companions) + incoming join-requests panel |
| RIGHT col | Curated matches with the same pulsing-dot eyebrow + serif italic headline as Pulse |
| **Trip vault** | Full-width section, gold gradient hairline ornament centred above. Carousel of every saved trip with the current one badged. To the right of the header: **LiveTravellersStrip** — avatars that bubble in for each `discover_trip_open` / `discover_post_new` event (violet for trips, gold for posts). Hover for `name · city · action`, click to smooth-scroll to Pulse. |
| **Sonder Pulse** | Full-width discovery section with hero header (live-status pill, breathing drop-shadow on the 52px serif headline, glass live-counts strip) |

Each major section opens with the same pulsing-dot ornament + uppercase tracked eyebrow + serif italic headline so the rhythm is consistent across the entire page.

### Past-trips fallback (defensive)

`listSavedItineraries` returns the user's `saved_itinerary_ids` — empty for brand-new profiles or transient Firestore reads. The dashboard catches this and synthesises a single vault entry from, in order: the just-fetched `getCurrentItinerary` result → `storedItinerary` React state → `localStorage['sonder_last_itinerary']` cache. So if there's any itinerary anywhere, the vault renders. Crucial subtlety: uses a local `currentIt` variable instead of the closure value (which would be stale — `setStoredItinerary` doesn't update the closure that ran `refresh`).

### Incoming join requests panel

Trip owners see a panel on Dashboard between the trip-action row and the past trips, listing every pending request on their open trips (`listMyJoinRequests({asOwner: true})`). Each row: requester avatar + name + message + Approve / Pass buttons. The panel listens for `sonder:join_request:new` window events from NotificationProvider, so requests pop in real-time without a refresh. Approving a request triggers the same write_itinerary + co_traveller_ids append as the synthetic auto-resolve path.

### NotificationProvider — fan-out hub

The single global `/ws/notifications` socket lives in `NotificationProvider` (mounted at App root). Its job is two things:

1. **Show banners** for chat messages (rose), discover trip opens (violet, suppressed on /dashboard), new posts (gold, suppressed on /dashboard). Each kind has its own icon (`MessageCircle` / `MapPin` / `Sparkles`), accent colour, and deep-link URL.
2. **Re-dispatch WS events as window `CustomEvent`s** so every page can listen without coupling to the provider:
   - `join_request_new` → `sonder:join_request:new`
   - `join_request_resolved` → `sonder:join_request:resolved`
   - `comment_new` → `sonder:comment:new`
   - `discover_trip_open` → `sonder:discover:trip_open`
   - `discover_trip_close` → `sonder:discover:trip_close`
   - `discover_post_new` → `sonder:discover:post_new`

This pattern lets DashboardPulse / SharedItinerary / Discover panels each attach their own listeners with one-line `useEffect` hooks. The provider itself stays focused on WS connection management + banner rendering.

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

### New schemas + extensions

| Schema | Where | Why |
|---|---|---|
| `SocialPost`, `SocialComment` | `jahnvi/schemas/social.py` | Feed posts + threaded comments — denormalised `author_name` / `author_avatar` so the feed reader doesn't N+1 join against user profiles |
| `JoinRequest` | `jahnvi/schemas/social.py` | Join-to-trip flow — `proposed` / `approved` / `denied` / `withdrawn` status, `auto_resolved` + `match_score` populated by the synthetic auto-resolve path |
| `OpenTripCard` | `jahnvi/schemas/social.py` | Discover card payload — `is_yours`, `your_request_status`, `confirmed_companions / join_capacity` |
| `Itinerary.is_open_to_join` + `Itinerary.join_capacity` + `Itinerary.co_traveller_ids` | `ali/schemas/trip.py` | Open-to-companions flag and confirmed-companion list; capacity independent of how many are confirmed |
| `is_synthetic`, `synthetic_owner`, `open_join_note` on itinerary doc | raw Firestore merge | Not in Pydantic schema (they sidecar the model) — flags synthetic-agent-created trips and stores the persona snapshot for instant-resolve scoring |
| `ChatSession.match_score`, `ChatSession.live_weights` | `jahnvi/schemas/chat.py` | Persisted match score (live-updated by chat signal scanner) + per-session weight overlay |

### Frontend hooks + helpers

| File | Purpose |
|---|---|
| `hooks/useWebSocket.js` | Drives the chat WS — first-message auth, ping every 30s, typing/seen/presence/message/`message_edited` handlers. Auto-reconnect on close. |
| `components/NotificationProvider.jsx` | Single global `/ws/notifications` socket; fan-out to banners + window CustomEvents |
| `components/DashboardPulse.jsx` | The Pulse section — trips + feed + composer + TripDetailModal + realtime subscriptions |
| `pages/Dashboard.jsx :: PastTripsRow` | Trip vault carousel with current-trip badge |
| `pages/Dashboard.jsx :: LiveTravellersStrip` | Avatar bubbles for live discover events, hover tooltips, smooth-scroll-to-pulse |
| `pages/SharedItinerary.jsx :: ActivityFeed` | Per-session activity log with resolution dedupe + orphan timeout |
| `lib/push.js` | `ensurePushSubscribed` / `dropPushSubscription` / `pushSupported` — service worker subscription lifecycle |

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

### Prompt engineering

Every persona-voiced surface (chat replies, proposal accept/counter, persona-initiated suggestions, synthetic posts + open-trip notes, topic chips, opener) shares the same anti-assistant doctrine: **the model is a person with taste, not a helper**. Concretely:

**Persona chat system prompt** (`ali/generation/topics.py::_build_persona_system`) layers three scope blocks before the style rules:

1. **Hard trip scope** — `STAY INSIDE THIS TRIP. The trip is to {dest}.` plus the itinerary digest. Explicit prohibitions: no mentioning the persona's home city, no past trips, no alternative destinations. Without this the model drifts into a Paris persona opening with "I see you're interested in Lisbon too?" on a Japan trip.
2. **PPM private psychology** — push / pull / motivation passed as private framing, with `Never say "push", "pull", "motivation", "alignment", or "friction". Turn those into concrete behaviors, opinions, scenes, and instincts.`
3. **Emotional signature** — the closed-taxonomy key + emotional tone, framed as `PRIVATE EMOTIONAL FRAMING (never expose these words). Let this shape cadence, warmth, pacing, what you notice — never the vocabulary.`

**Chat-reply style rules** — a rotation of reply shapes (reaction, agreement-with-twist, tiny self-detail, observation, soft pushback, half-sentence, occasional question) plus an extensive banned-filler list (`oh nice`, `that's amazing`, `love that`, `honestly`, `bucket list`, `travel buddy`, em dashes...). Format hard caps: 1-2 short sentences, never more than 35 words, texting register, lowercase `i` fine, contractions yes.

**Per-turn `breathe_hint`** — `generate_chat_reply` counts how many of the persona's recent turns ended with `?`. If 2+ in a row, the prompt injects "Your last few turns have been mostly questions — this one should react, observe, or share something small instead." Stops the model interrogating the user across long sessions.

**Proposal evaluator** (`ali/generation/proposal_evaluator.py::_SYSTEM_PROMPT`) — the persona accepts or counters one user proposal. Key rules:

- **No hard rejection state** — if you dislike a proposal you MUST offer a counterproposal, or accept. This keeps the negotiation always-collaborative instead of stuck.
- **Reason-in-message rule** — every counter must surface a brief, conversational reason ("hakone feels far after the museum day"). Without a reason the counter reads arbitrary; the user can't engage.
- **Dedupe rule** — never counter with an activity already on the itinerary, already accepted, or already rejected. Caller still runs a backend dedupe pass as the second safeguard.
- **Five voice-calibrated few-shot examples** showing exact JSON shape + texting register, mapped to common scenarios (clean accept, too-packed counter, tone-mismatch counter, flexibility-after-recent-counter, etc).

**Persona-initiated suggestion** (`suggest_proposal::_SUGGEST_SYSTEM_PROMPT`) — the persona proactively suggests ONE activity. Includes the trip rhythm, the dedupe constraint, and the cross-tastes pass: the user's profile is rendered into the prompt so the suggestion lands at the intersection of both parties' tastes rather than the persona's preferences in a vacuum.

**Synthetic-social prompts** (`ali/generation/synthetic_social.py`):

- `_POST_SYSTEM_PROMPT` — picks ONE of five post shapes (tiny memory / half-formed plan / small recommendation / candid observation / soft question) with examples for each. Forbids the same filler list as chat. Caps at 1-3 sentences.
- `_OPEN_TRIP_SYSTEM_PROMPT` — one-line "open to companions" note. Bad examples shown explicitly (`"Join me for an unforgettable adventure!"`, `"Looking for like-minded travel buddies"`) to prevent sales-language regression.

**"You ARE this person" framing** — every persona prompt opens with `You ARE {display_name}. You are NOT an assistant.` followed by the profile snapshot. Combined with the banned-filler list this keeps the model out of customer-service register on every surface.

**Output shape discipline** — all structured outputs (proposal verdict, suggestion, post body, opener) require `Return ONLY valid JSON. No markdown fences.` plus a balanced-brace fallback parser in `_parse_json_object` for the inevitable code-fenced output. Posts and opener strip quote-wrapping defensively.

### Validator engine — pluggable critic + repair stack

`mushahid/validation/validator_engine.py` ships a fully-configurable critic / repair stack. Every threshold, prompt, taxonomy stem, regex, and structure lives in one frozen `ValidatorEngineConfig` dataclass so the engine itself stays generic and reviewable from a single file.

**Five separate validator prompts** — each strict and category-scoped:

| Validator | Categories it checks |
|---|---|
| `itinerary_critic_system` | budget_fit · pacing_realism · must_haves_covered · avoid_list_respected · day_sequence_logic · activity_specificity · feasibility_risk |
| `persona_reveal_validator_system` | concrete_observation · evidence_fidelity · no_itinerary_content · specificity · internal_label_leakage |
| `cotraveller_match_validator_system` | ranking_grounding · evidence_fidelity · specificity · tension_awareness · internal_label_leakage · tone |
| `chat_reply_validator_system` | assistant_voice · ai_leakage · semantic_drift · token_stutter · empty_token_generation · romantic_vibes · taxonomy_leakage · unsafe_or_weird · bad_conversation_dynamics · contradiction_memory |
| `chat_reply_repair_system` | Rewrite-once instruction — under 50 words, preserve context, no quotes / preamble / helper speech / loops |

**Every validator returns the same shape** — `{"valid": bool, "issues": [{"category", "severity": "low|medium|high", "evidence", "fix"}]}` — so severity-based decisioning and repair routing is generic across surfaces.

**Itinerary critic — Swapability Test**: the user template ends with `"If an activity description applies anywhere else without changing context, it fails specificity"`. Combined with the explicit instruction `"Penalize generic activities heavily unless they include enough detail to be actionable"`, this catches Sonnet's tendency to write "explore the Old Town" instead of "the rosé-coloured cafés on Largo do Carmo at golden hour."

**Local pre-check before the LLM call** — `chat_reply_local_precheck` runs fast deterministic checks first:

- `min_acceptable_reply_length` (`< 3` chars → `empty_token_generation` issue, return immediately, never even hit the LLM).
- `has_repetition` → `token_stutter` issue.
- `evaluate_semantic_genericity` — counts hits against a 15-stem set (`"sounds amazing"`, `"hidden gem"`, `"bucket list"`, `"fellow traveler"`, etc), scores `base + matches × multiplier`, fires if above `genericity_threshold (0.80)`. The score is also surfaced in telemetry per-event so PostHog can watch the genericity distribution drift over time.

This local pass either kills the bad reply outright (no LLM cost) or feeds its `issues` list to the LLM repair prompt as concrete `VALIDATION ISSUES` context, so the rewrite is grounded rather than blind.

**Memory contradiction detection** — `evaluate_memory_contradictions` parses the chat history with two regex templates (`past_destinations` matches `"i've been to X"` / `"visited X"`; `past_negations` matches `"never been to X"` / `"haven't visited X"`) and flags any reply that contradicts the established timeline. Catches a real failure mode where the persona "remembers" trips that never happened or denies trips it just claimed.

**Telemetry per execution** — every validator run emits a `TelemetryEvent` to PostHog with `validator_passed_first_try`, `repair_triggered`, `repair_count`, `regex_precheck_hit`, `total_latency_ms`, `semantic_genericity_score`, `execution_log`, and `detected_anomalies`. Lets us watch validator behaviour empirically rather than trusting the prompts to keep working as the underlying models drift.

**Async edit-in-place (chat reply only)** — the validator is fully off the critical path; the unvalidated reply is broadcast immediately, then `_validate_async` runs in `asyncio.create_task`. If the repair changes the text, `update_chat_message_content` patches the persisted doc and the WS broadcasts a `message_edited` event; `useWebSocket`'s handler swaps the bubble text in place. Users see the reply land instantly and watch it quietly self-correct a moment later when needed — quality without latency cost.

### Ranking architecture — pipeline of stages, equal-weight priors, observability built in

All three rankers (co-traveller, destination, activity) run through one generic engine in `shreyas/ranking/engine.py`. The engine knows nothing about specific features, weights, or taxonomies — it executes the policy's declared `pipeline = [FeatureScoringStage, InteractionStage, WeightedCombinerStage, RerankerStage]`. **`InteractionStage` and `RerankerStage` are no-ops in V1 but live in the pipeline now so adding cross-candidate features / diversity / fatigue / sequencing later doesn't require an engine rewrite.**

**Policy = declarative config, not code paths.** Each policy file (`policies/cotraveller.py`, `destination.py`, `activity.py`) is just a module exposing:

```python
features: list[str]           # which feature functions to score
weights: dict[str, float]     # currently {f: 1/N for f in features}
pipeline: list                # stage instances in order
feedback_policy: dict         # boost/reduce/min_weight/renormalization hyperparams
include_retrieval_in_sum: bool   # avoids double-counting pinecone_passthrough in V1
```

**`FEATURE_REGISTRY` — 10 reusable scoring functions** in `shreyas/ranking/features.py`:

| Feature | Signal |
|---|---|
| `pinecone_passthrough` | Raw cosine retrieval score |
| `salience_weighted_question_overlap` | Per-question PPM-keyword alignment × the viewer's `answer_salience` (so users who wrote more revealing free text get `small_thing` weighted higher automatically) |
| `signature_proximity` | Identity (1.0 if same emotional signature, else 0.0) — no hand-picked similarity matrix until feedback can learn one |
| `pace_ordinal_fit` / `budget_ordinal_fit` | Ordinal distance on the enum |
| `style_match` | Travel-style exact match |
| `interest_jaccard` / `tag_interest_overlap` | Two flavours of interest overlap |
| `activity_cost_fit` / `pace_duration_fit` | Activity-only fits |

Every policy ships with `weights = {f: 1/N for f in features}` — **equal-weight priors expressing honest uncertainty**. We haven't earned any confidence in feature importance yet; per-user weights override the policy defaults via `compatibility_signals.ranker_weights[surface]` once feedback has shaped them. Budget acts as a feasibility gate (raw `budget_usd / trip_days` cutoff in `filters.py`, no fudge multipliers), not a positive ranker signal.

**`ScoreSheet` separates retrieval from features from rerank.** Threaded through every stage:

```python
candidate          # underlying object (CoTravellerProfile / Destination / Activity)
retrieval_score    # pinecone cosine, set once at engine entry, never modified
feature_scores     # {name: (raw, weighted)}  — both kept so observability can see raw distributions
feature_snippets   # {name: "human explanation"} — feeds the match_reasons UI
rerank_adjustments # {name: float}  — empty in V1, reserved for MMR / fatigue / sequencing
final_score        # retrieval (if include_retrieval_in_sum) + Σ(weighted) + Σ(rerank), clipped to [0,1]
```

V1 has `include_retrieval_in_sum: False` because `pinecone_passthrough` is in `features` — including both would double-count. V2 will drop `pinecone_passthrough` from the feature list and give retrieval its own weight slot via the flag.

**Per-question salience drives the overlap feature.** `compute_answer_salience` counts PPM-keyword density across each persona answer (chip + free text), normalising to a distribution summing to 1.0. The `salience_weighted_question_overlap` feature multiplies per-question answer alignment by the viewer's salience — so users who wrote more revealing free text get their `small_thing` weighted higher automatically. Persisted on `compatibility_signals.answer_salience` at persona-infer time so the feature is deterministic across runs.

**Deterministic text-feedback learning.** `apply_text_feedback` in `feedback.py` runs a regex `TEXT_FEEDBACK_KEYWORDS` map — `\bcheap(?:er)?\b` → `[budget_ordinal_fit, activity_cost_fit]`, `\bless\s+packed\b` → `[pace_ordinal_fit, pace_duration_fit]`, `\blocal|authentic|touristy\b` → `[tag_interest_overlap]`, interest words → `[tag_interest_overlap, interest_jaccard]`. Multiple matches stack additively. Boost / reduce / clamp / renormalization hyperparameters come from the policy's `feedback_policy` dict, NOT the keyword map — so the same map can drive different learning rates per surface.

**Structured per-activity edits go to `feature_logging`.** `POST /update-trip` accepts `ActivityFeedback[]` (`{activity_id, action: "swap"|"remove"|"adjust_time", reason?}`). Each event lands in Firestore with the candidate's feature breakdown at the time of the action. V2 will compute replacement gradients (`accepted.features - rejected.features`) once delta data accumulates — until then, the structured stream is the data substrate that lets us bootstrap real learning later.

**Feature-stats observability built in.** `feature_stats.py` records every feature observation (mean / variance / count, p50/p95 later) per `surface × feature` so silent scale domination is visible — e.g. if `pinecone_passthrough` is winning 80% of the combined score because its raw distribution sits at 0.78 while ordinal fits sit at 0.5, you see it in Firestore aggregates rather than discovering it via empty engagement metrics three months in. Same flow per ranking surface, same dashboard.

**Cross-candidate live updates via chat signal scanner.** The match-score isn't frozen at retrieval time — `_apply_chat_signals` runs after every user message, calls `scan_and_apply` over the message text, updates the session's `live_weights`, and re-runs `score_compatibility(viewer, candidate)` with those weights spliced into `ranker_weights["cotraveller"]`. The refreshed `match_score` is what the persona's reciprocal-approval threshold reads at decision time.

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

### Token-Jaccard dedupe on proposals

Both the LLM prompt rule and a backend pass guard against duplicate proposals. `_is_duplicate(title, existing, accepted, rejected)` normalises titles to lowercase tokens and runs Jaccard similarity (default threshold 0.6) against every item already on the itinerary, every previously accepted change, and every previously rejected one. If the persona LLM still returns a near-duplicate counter despite the dedupe rule in the prompt, the verdict gets flipped to `accept` with a fallback message ("yeah okay, let's go with yours") rather than circulating the same idea with slightly different wording.

### Notable bug-fix patterns

A handful of bugs kept recurring and shaped how new UI work gets reviewed:

- **`<Navigate>` inside `<AnimatePresence mode="wait">`** leaves the screen blank because the redirect target isn't wrapped in `<Page>`, so the exit/enter cycle stalls. Fix: render the same component for both routes instead of `<Navigate to=...>`.
- **Stale closure on `setState` then read** — code like `setStoredItinerary(it); if (storedItinerary) { ... }` reads the OLD value because `setState` doesn't update local closure scope. Always use a local variable for the just-fetched value.
- **Conditionally rendered sections hide adjacent content** — wrapping a section in `{data.length > 0 && ...}` can also hide non-data-driven UI rendered inside it (headers, action strips). Render the section unconditionally and let the inner row return null.
- **Stale React state inside `useCallback` deps** — `fetchTrips` / `fetchFeed` use empty-deps `useCallback` to keep references stable; that means anything they close over must come from the API response, not React state.
- **`LOCAL_MODE` is dead** in this repo. The branch still exists in `mushahid/realtime/firestore.py` helpers for compatibility, but new code should treat Firestore as the only persistence layer.

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
