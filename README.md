# Sonder — AI Co-Traveller Trip Planner

> Plan smarter. Find your perfect co-traveller. Build the trip together in real time.

AI-powered trip planning, deep co-traveller matching, a live social surface, and a real-time shared-itinerary negotiation loop — all in one product.

---

## What It Does

Sonder takes a user from zero to a personalised, day-by-day itinerary, matches them with compatible co-travellers, and then lets the pair negotiate the actual trip together with a real-time, optimistic-locked shared itinerary. On the way it surfaces a live social feed and a discovery wall of trips other people are opening up to companions.

**Full user journey:**

1. **Persona reveal** — Enter trip basics (destination, dates, budget in any currency, must-haves) + five oblique persona questions. Get a descriptor, paragraph, bullets, emotional-tone subtitle, and inferred push/pull dimensions.
2. **Itinerary generation** — Live-streamed, day-by-day, with "Why this?" RAG explanations per activity. Auto-saved to your trip history. View it in **Both / Desktop / Mobile** tabs — the bi-view shows the editorial desktop layout alongside the phone mockup, cross-view scroll sync keeps the active activity in frame as you switch.
3. **Approve or revise** — Trip lands in `draft` state. Approve locks it in; revise streams a regenerated trip back day-by-day via SSE with a live diff toast (`Swapped Freehand Chicago → St. Jane Chicago`). Per-revise per-user ranker weight delta with reinforcement decay so repeated similar feedback doesn't oscillate the weights.
4. **Trip vault** — Every saved trip on the dashboard. Switch the active one, open Journal entries, jump to the destination feed.
5. **Co-traveller matching** — Curated top-3 matches, scored on a transparent salience-weighted feature pipeline. Synthetic personas (LLM-designed) fill the pool until real-user density is there.
6. **Chat → mutual approval** — Real-time WebSocket chat with presence, typing, seen receipts, in-app banners, OS push. The persona's reciprocal approval is a coin flip weighted by the live match score (no hardcoded thresholds).
7. **Shared itinerary negotiation** — Once approved, a `/shared/{id}` page where both sides propose, counter, and accept activity changes. Persona evaluations run off the request path so the UI feels instant; verdicts arrive over WebSocket. Optimistic locking on `version` prevents silent overwrites.
8. **Sonder Pulse (Dashboard)** — A live two-column section showing **Open invitations** (trips other people opened for companions) and **The room** (a social feed of posts + threaded comments). Synthetic personas autonomously post and open trips every 15-50 seconds; real users join the room organically.
9. **Join-to-trip flow** — Click any open invitation → a detail modal with persona snapshot, match-preview percentage, and a colour-coded fit label. Synthetic trips auto-resolve instantly using the same compatibility signal that drives matching; approved requests add you to the trip's co-traveller list.
10. **Finalise** — Pair locks the itinerary in. Email it or download a PDF.

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
| AI — Voice | **ElevenLabs TTS** via `ali/voice/elevenlabs.py` — persona voice_id assigned via deterministic `profile_id` hash. Output MP3s cached in Firebase Storage keyed by `sha256(text + voice_id)` so re-plays are free |
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
│       ├── functions/api/[[path]].js   # Cloudflare Pages Function: proxies
│       │                    #   every /api/* request to the Render backend
│       │                    #   (Pages _redirects can't proxy to external origins)
│       └── src/
│           ├── pages/       # Dashboard, SharedItinerary, Chat, MatchDetail, ...
│           ├── components/  # DashboardPulse, InboxStrip, NotificationProvider,
│           │                #   TripDetailModal, SonderMark3D, LuxCursor, ...
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
│   └── realtime/            # firestore.py, sse.py, web_push.py,
│                            #   notify.py (WS + push + email fan-out helper)
│
├── scripts/
│   ├── seed_pinecone.py             # Destinations + activities
│   ├── seed_cotravellers.py         # Singles: LLM-designed personas + gpt-image-1
│   ├── seed_couple_cotravellers.py  # Couples: same blind-writer pipeline, ctcp_* IDs,
│   │                                #   uploads to Firebase 'couples/' folder
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
| Itinerary revision progress | SSE (`/api/itineraries/{id}/revise`) | Server → user | Mushahid |
| Chat messages + typing + seen | WebSocket (`/api/ws/chat/{session_id}`) | Bidirectional | Shreyas |
| Co-traveller presence (TTL) | WS broadcast + Firestore `presence/{uid}` | Bidirectional | Shreyas |
| Chat-reply edit-in-place (validator repair) | WS `message_edited` event | Server → user | Mushahid + Shreyas |
| In-app banners | WebSocket (`/api/ws/notifications`) | Server → user | Mushahid |
| **Discover broadcasts** (`discover_trip_open` / `_close` / `discover_post_new`) | `ConnectionManager.broadcast_global` over `/ws/notifications` | Server → all users | Shreyas |
| **Targeted social events** (`join_request_new`, `join_request_resolved`, `comment_new`) | `notify_user` over `/ws/notifications` | Server → one user | Mushahid |
| **Web Push (offline-capable)** | VAPID + service worker | Server → device | Mushahid |
| **Email** | Resend / SendGrid / SES via `shared/email.py` | Server → inbox | Mushahid |
| Shared itinerary edits | Firestore + optimistic locking via `version` | Bidirectional | Shreyas |
| Async persona evaluation result | WS `shared_responded` event | Server → user | Mushahid |
| Approval status (live) | Firestore | Bidirectional | Shreyas |

**Every targeted user-facing event fans out via `mushahid/realtime/notify.notify_event`** through all three channels — WS (in-app banner) + Web Push (OS notification when tab closed) + Email (fallback). Events covered: chat messages, join requests received, join verdicts, comments on your post, **shared-itinerary proposals**, **shared-itinerary responses (accept/counter)**, **shared-itinerary finalize**. All three channels fire-and-forget; failure of one never blocks the others.

| Channel | Best for | Throttling |
|---|---|---|
| WS notify_user | Instant in-app banner while a tab is open | None — every event delivers |
| Web Push | OS notification with no Sonder tab open | Browser-side de-dup via `tag` field |
| Email | Catching missed in-app + push, inbox archive | **5-min cool-down per `(uid, kind)`** so chatty threads don't flood inboxes |

Email lookup uses the Firebase Admin SDK (cached 1h in-process). **Unverified Firebase emails are skipped** as an abuse + deliverability defense. Synthetic personas have no Firebase user record, so the email step silently no-ops for them while push + WS still fire.

WebSocket auth uses the first-message pattern (token in initial JSON payload, never in query string). Web push silently no-ops when VAPID keys aren't configured; in-app banners still work. Same for email when `EMAIL_PROVIDER` / `EMAIL_API_KEY` isn't set.

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

### Itinerary approval lifecycle & user-initiated revision

The initial generation pipeline (`run_refinement_loop` inside `/plan-trip`) is a quality gate — the validator can request up to `MAX_REFINEMENT_ATTEMPTS` rewrites before the trip lands on screen. After that, every itinerary lands in **draft** state. The user explicitly approves or asks for changes before the trip leaves draft and becomes the basis of any shared-itinerary or co-traveller activity.

```
generated itinerary (draft)
   │
   ├── POST /api/itineraries/{id}/approve       → status flips to 'finalized'
   │                                              409 if already finalized
   │
   └── POST /api/itineraries/{id}/revise        → SSE stream (see below)
                                                  409 if already finalized
```

The approval state lives on `Itinerary.approval_status` (`"draft"` | `"finalized"`) with `finalized_at` timestamp and a full `revision_history` array — one entry per revise turn carrying `feedback`, `scope`, `target_days`, `dropped_titles`, `added_titles`, `boosted_features`, `boost_multiplier`, `validation_*`, `created_at`.

#### `/revise` — single-pass, streaming, day-targeted

The /revise route does **not** reuse `run_refinement_loop`. The orchestrator loop iterates up to 3× trying to satisfy the LLM critic — fine on first-time generation, but on a user-initiated revise it amplifies wall time 3× while the user watches a frozen modal. Instead:

1. **Classify the feedback** via `mushahid/refinement/classifier.py` — emits `{scope: "small"|"large", target_day_numbers: [int], target_categories: [str], preserve: [str], summary: str}`. Falls back to scope=large on parse failure.
2. **Build dedupe blacklist** — every title the user has rejected on prior turns is appended to the prompt as `DO NOT RE-INTRODUCE`. Stops the LLM offering "Freehand Chicago" again on turn 3.
3. **Single regen pass** via `stream_single_revision` in `mushahid/refinement/loop.py`:
   - If `target_day_numbers` is set → uses the **targeted-day prompt** (`build_targeted_day_refinement_prompt` in `ali/generation/prompts.py`) that asks for a bare JSON array of just the affected days. Output tokens drop from ~10k (whole itinerary) to ~1-2k (one day).
   - Otherwise → full-itinerary refinement prompt.
   - Always uses the **LARGE tier** (`complex_refinement`). Routing SMALL-scope edits to the small tier caused silent truncation — the small client caps `max_tokens` at 512-1024, the regen output is 3-8k, so the stream got cut, parse failed, and the user saw the approve gate again with zero changes. Fast path = day-targeting, not model-downgrading.
4. **Single validate pass** — same gates as the orchestrator loop (deterministic `run_all_checks` first, then `validate_large_output` if those pass). **No retry**. If the validator flags a constraint violation, the verdict comes back in the response — the user already asked for the change; we don't burn another minute trying to outsmart them. They can revise again.
5. **Per-user ranker weight delta** with **decay** — `apply_text_feedback` boosts features the feedback text implies (`"cheaper"` → `budget_ordinal_fit`, `activity_cost_fit`; `"less packed"` → `pace_ordinal_fit`, `pace_duration_fit`). Turn 1 = full strength; turn 2 = ½; turn 3 = ¼; floor at ⅛. Stops weights oscillating when the user keeps pushing back on similar things.
6. **`itinerary_id` is preserved** across revisions — `parse_itinerary` mints a fresh UUID on every call, so we explicitly overwrite it post-parse. Without this, history append + current-trip pointer + dedupe blacklist would fragment across new IDs every turn.

#### SSE event sequence

`/itineraries/{id}/revise` returns `text/event-stream` so the frontend sees changes as they land, not 60s later:

```
revising            { scope, target_days, hint: "Rewriting day 3…" }
day_revised         { day_number, day }   ← one per day as its JSON closes
validating          {}
revision_done       { itinerary, validation, dropped_titles, added_titles, scope }
revision_persisted  { turn }              ← history + weight delta written
revision_failed     { message }           ← terminal error path
```

`stream_refined_itinerary_by_day` and `stream_refined_days_by_day` in `ali/generation/itinerary_generator.py` reuse the same forward-only brace-counter pattern as `generate_itinerary_by_day` — the full-itinerary stream waits for the `"days"` key, the targeted-day stream parses bare-array form from the first `{`. If the streaming detector misses everything (markdown fences, key-order quirks), a whole-buffer `parse_itinerary` fallback runs so we never silently no-op.

The route returns immediately via `StreamingResponse`. Post-stream bookkeeping (history append, weight delta, monitoring `capture`, persist with `approval_status="draft"`) happens **after** the user already has the visible diff, then emits `revision_persisted`. If anything in bookkeeping fails the user still has the regenerated itinerary on screen — the failure is logged but doesn't break the visible flow.

#### Frontend consumption

`streamReviseItinerary` in `jahnvi/frontend/src/lib/api.js` takes a `handlers` object and consumes the SSE stream via `fetch` + `ReadableStream` (same pattern as `useSSE` for `/plan-trip`). 120s client-side timeout via `AbortController` — generous since the stream surfaces progress along the way, so a hung backend doesn't disguise itself as a working one.

`handleRevise` in `Itinerary.jsx`:
- Closes the modal immediately — progress shows as a top-of-screen toast so the user can watch the days update live.
- On `day_revised`: splices the revised day into local `itinerary.days[]` by `day_number` so the currently-visible day re-renders the moment the LLM finishes it.
- On `revision_done`: builds a friendly diff line — "Swapped Freehand Chicago → St. Jane Chicago" when exactly 1 in / 1 out, otherwise "Updated N activities" with truncated lists.
- On `revision_failed`: red toast + records the message on `approveError`.

Toast component supports `progress` / `done` / `error` styles; progress sticks until the next event lands, done auto-dismisses in 6.5s, error in 5s.

### Bi-view itinerary surface

The Itinerary page now has a three-way view toggle — **Both / Desktop / Mobile** — at the top of `<main>`. Defaults adapt to viewport: `≥1180px → both`, `≥900px → desktop`, `<900px → mobile`. Stored in `localStorage['sonder:itinerary:view']`.

- **Both** — desktop editorial layout takes the main column, the phone mockup is sticky-pinned on the right at ~`(320..420)/PHONE_W` scale. Both surfaces visible at once.
- **Desktop** — desktop layout full-width, no phone.
- **Mobile** — phone mockup centred, no desktop layout.

**Cross-view focus state**: a single `activeActivityIdx` is held in the parent and passed to both `PhoneItinerary` and `DesktopItinerary`. Each view runs an `IntersectionObserver` on its activity rows / cards and pushes the most-visible index up to the parent as you scroll. On view switch, the active view's `scrollIntoView({block: 'center'})` lands the same activity in its viewport — so flipping Mobile ↔ Desktop preserves not just the active day but which specific activity you were looking at.

**Mouse-scrollable phone**: the wheel router (`onWheel` on `window`) gets a hit-test against `phoneSurfaceRef` — if the cursor is over the phone bounds, wheel always scrolls the phone's internal `phoneScrollRef`, even when the page itself can scroll. Needed for the bi-view, where the desktop column is tall (so `main.scrollHeight > clientHeight`) and the old "only hijack when page can't scroll" rule meant you could never mouse-wheel the phone preview alongside it.

### Persona-first CTA labels

The button labels follow the actual next step instead of the eventual destination:
- TripPreferences final step: **"Determine your persona"** (next stop is `/persona-reveal`, not the itinerary).
- PersonaReveal CTA: **"Plan your trip"** (the button that actually fires generation).

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
- **Action mix: 50% posts / 25% open-trips / 25% outreach** (falls back to a post if no eligible outreach target exists, so cycles aren't wasted).
- `_emit_post` → persona-voiced social post via `generate_synthetic_post` (SMALL tier).
- `_emit_open_trip` → mints a minimal `Itinerary` doc with the persona's `profile_id` as `user_id`, flips `is_open_to_join=True`, generates a one-line "open to companions" note via `generate_synthetic_open_trip_note`.
- `_emit_outreach_chat` (**NEW**) → picks a real user from `list_outreach_eligible_users` (filtered to `who_travelling_with in (solo, couple)` with a `current_itinerary_id`), generates a cold-open message anchored on one specific thing about the user's trip via `generate_outreach_opener`, creates a `ChatSession` + first message via the same path real chats use, fires WS `chat_notification` + web push + email. Skips users who already have a session with this persona — no spam.
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

### Group selection & party-size logic

`TripConstraints.who_travelling_with` (`solo | couple | family | friends`) and `TripConstraints.group_size` are bound by a pydantic `@model_validator` at the API boundary so downstream code can trust the pair:

| Style | `group_size` | Matching pool | Persona / Itinerary framing |
|---|---|---|---|
| solo    | locked at 1 | active (solo↔solo) | Second-person singular; isolated instincts |
| couple  | locked at 2 | active (couple↔couple) | "You both" framing; partner present in copy |
| family  | 2..8 user-picked | **disabled** — surfaces straight to shared-itinerary | **Assumes kids present**: kids-friendly menus, dinner by 7pm, mid-day nap window, ≥1 kid-facing activity per day, apartment lodging, no bars / 21+ venues |
| friends | 2..8 user-picked | **disabled** — friend-group persona is too hard to write as one voice in V1 | "Your group" framing; split-and-rejoin activities, nightlife on the table |

**Cap is `MAX_PARTY_SIZE = 8`** — past that the trip-planning shape changes (multi-room logistics, separate itinerary tracks) and the generator + ranker aren't tuned for it. Mismatched values rewritten silently rather than 400'd: passing `solo` + size 5 coerces size to 1.

**Cotraveller matching is hard-filtered by style.** The `style_match` ranker feature only nudges the score; without a hard filter cross-style candidates slipped through because of high embedding similarity on other axes (couples were seeing solo personas). `/cotraveller` and `/cotraveller/regenerate` now drop any candidate whose `travel_style` doesn't match the viewer's `who_travelling_with`. Regenerate over-fetches `top_n=12` then filters down to 3 so the cap still holds when seed-pool density is low. Family / friends short-circuit upstream with `matching_disabled: true` + a reason code the frontend renders into a dedicated empty-state card.

**Per-group itinerary planning hints** — `ali/generation/prompts._group_planning_hints(style, party_size)` injects concrete activity-shaping rules into the itinerary prompt:

| Style | Selected rules |
|---|---|
| solo    | counter-seating venues, walking-distance stops, no wasted-seat private transfers, 1-2 meet-others activities/day without forcing it |
| couple  | every overnight private (no dorms), ≥1 slow shared activity/day, tables for two not bar-only, one shared-first experience as memory anchor |
| family  | ALL restaurants seat full party at ONE table with kids-friendly menus, walking blocks <30 min, dinner by 7pm, mid-day reset window, ≥1 KID-FACING activity/day, no clubs / fine dining / min-age-fail activities, apartment with kitchen access |
| friends | one-table reservations for N, ≥1 split-and-rejoin activity/day, nightlife on the table, apartment / villa over N separate rooms |

### Inbox

`GET /api/inbox` returns every chat session the user is in, persona-resolved into UI-ready cards. Each row: persona avatar (Pinecone-resolved with seed badge), last-message preview (with `you:` prefix on outbound), `timeAgo` timestamp, approval-status pill (green "Matched" / rose pending / muted denied), message count. Sorted newest-activity first.

**Frontend `<InboxStrip>`** lives in the dashboard right column above matches. Polls every 25s and subscribes to a `sonder:inbox:refresh` window event that `NotificationProvider` dispatches on every `chat_notification`, so new sessions appear instantly without waiting for the poll.

### Synthetic outreach chats — solo / couple only

Beyond posts + open trips, synthetic personas now spontaneously start chat sessions with real users. Cadence: 25% of synthetic-agent cycles. Filters:

- Target user must have `who_travelling_with in (solo, couple)` (family + friends already have their party)
- Target user must have a `current_itinerary_id` (something for the persona to anchor on)
- Persona must NOT already have a session with this user (no spam)
- LLM-generated opener anchors on ONE specific thing about the user's trip (city + dates) — generic openers ("your trip sounds amazing!!", "travel buddy") are forbidden in the system prompt
- Persists via the same `ChatSession` + message path real chats use, then fires WS + web push + email through `notify_event`

Result: a real user logged in with an upcoming trip can land their inbox + dashboard + OS notifications populating with "hey, saw you're going to lisbon — i was there in feb, the rain was lighter than i expected" within seconds of opening the app.

### Synthetic Co-Travellers (Pinecone seed pool)

The matching pool is seeded with LLM-designed personas (no randomuser.me / stock photos). For each diversity-matrix slot (emotional signature × age bracket × home city), the LARGE LLM writes a full persona JSON. Each persona gets:

- A stylised cinematic portrait from `gpt-image-1` (painterly, explicitly not photoreal)
- A stable voice id from a deterministic hash of `profile_id` against the ElevenLabs voice whitelist (audio synthesised on-demand via `/api/voice/synthesize`, MP3s cached in Firebase Storage)
- An emotional signature via the same inferrer real users hit
- A rich embedding text upserted to the `cotravellers` Pinecone namespace

Every record carries `is_seed: True` for "Sonder Curated" disclosure. Seed cost is ~$2–4 for 50 personas (gpt-image-1 dominates).

**Two seed scripts, same architecture:**

| Script | Pool | Cohort | Matrix |
|---|---|---|---|
| `scripts/seed_cotravellers.py` | Singles (`travel_style="solo"` default) | 96 personas | 16 cities × 3 ages × 2 genders |
| `scripts/seed_couple_cotravellers.py` | Couples (`travel_style="couple"` hard-locked) | 18 couples | 6 cities × 3 ages, primary-gender (chatter) alternates |

Couples are male+female pairs by design. The couple LLM-A system prompt mirrors the singles prompt structure verbatim (Rules block, full `visual_cue` ban list including `golden hour` / `cherry blossoms` / `iconic landmark` / engagement framing, `NEVER` block) with couple-specific layering: `display_name` = "X & Y", `voice_anchor` in WE voice, `quirks` describe the COUPLE'S DYNAMIC ("she plans, he wings it"), `appearance_descriptor` in PROTAGONIST + PARTNER order. Portrait prompt prepends a couple-specific header (two people in the frame, candid not engagement-shoot). Profile IDs use `ctcp_` prefix so re-runs don't collide with singles. Avatars upload to a separate Firebase Storage folder (`couples/{pid}.png` vs `cotraveller_avatars/{pid}.png`).

This pool exists so the cotraveller route's **hard style filter** (couple↔couple, solo↔solo) has real candidates to return for couple users — without it, a couple would see zero matches since the singles pool defaults to `travel_style="solo"`.

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
| `POST` | `/api/itineraries/{id}/approve` | Flip `approval_status` → `"finalized"`. 409 if already finalized. Triggers downstream lock — no more revises after this. |
| `POST` | `/api/itineraries/{id}/revise` | **SSE stream** — `revising` → `day_revised`* → `validating` → `revision_done` → `revision_persisted`. Body: `{feedback: str, targets?: ActivityFeedback[]}`. 409 if already finalized. 502 on regen failure. |
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
| `GET`  | `/api/inbox` | Every chat session the user is in, persona-resolved (display name, avatar, seed badge, last-message preview, last-activity time, approval status, message count). Sorted newest-activity first. Drives the dashboard inbox strip. |
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
| `POST` | `/api/push/test` | Diagnostic: fires a test push to the caller's own browser. Returns `{vapid_configured, subscription_count, send_attempted, send_error}` so you can pinpoint which layer is broken when desktop pushes aren't arriving |

### Voice (TTS)
| Method | Route | Returns |
|---|---|---|
| `POST` | `/api/voice/synthesize` | `{audio_url, cached: bool}` — ElevenLabs MP3 for a persona's message; Firebase Storage cache keyed by `sha256(text + voice_id)`. 600-char input cap |

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
- `evaluate_semantic_genericity` — counts hits against a 14-stem set (`"sounds amazing"`, `"hidden gem"`, `"bucket list"`, `"fellow traveler"`, etc), scores `base + matches × multiplier`, fires if above `genericity_threshold (0.80)`. The score is also surfaced in telemetry per-event so PostHog can watch the genericity distribution drift over time.

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

### Persona generation — deliberate information starvation

The core architectural decision behind every persona-generating LLM call (both real-user inference at `/persona-infer` and synthetic-persona seeding in `scripts/seed_cotravellers.py`) is **the LLM never sees the full picture**. Each generation step gets only the slice of context relevant to its narrow task. The reasoning: an LLM with the answer key in front of it writes to that key. An LLM that has to guess writes something honest.

**Real-user `/persona-infer`** (`mushahid/routes/persona.py`)

The module docstring states the rule plainly: `"The LLM never sees Pinecone, never plans a trip."` Concretely:

- The persona LLM gets ONLY the persona signals — radio answers (rendered as human-readable labels via `label_for()`, never raw snake_case keys), `small_thing` free text, travel-style chips, pace, who-with. It never sees the user's destination, dates, budget, prior trips, candidate matches, ranker weights, or other users' personas.
- **Closed dimension vocabulary** — the prompt embeds the full `PUSH_DIMENSIONS` + `PULL_DIMENSIONS` keyword lists as the ONLY allowed labels. `"Never invent a label that isn't in this list."` Pool separation is enforced both in the prompt (`"never put a PULL id into top_push"`) and in `_redistribute_pools` post-hoc as the structural safety net.
- **Three pipelines run in parallel**, each blind to the others' outputs:
  1. **Embedder** (`embed_persona`) — produces the durable `user_vector`. Sees the persona text, never the LLM's labels or reveal copy.
  2. **GoEmotions classifier** — scores 27 emotion glosses. Sees the user text, never the LLM output.
  3. **Persona LLM** (`route_request_structured` with Anthropic tool-use for enum-constrained dimension IDs) — produces `top_push` / `top_interests` / `descriptor` / `paragraph` / `bullets`. Sees the answers, never the embedding vector or the goemotions distribution.
- **Validator runs AFTER** as a separate stage, given ONLY the LLM output — no user context at all. So even if the LLM leaks something, the validator can't be biased by knowing what to look for. Checks: schema · allowed-dim · echo (LLM repeating the user's exact words back) · tone · scope.
- **Outputs are merged downstream, not co-prompted upstream** — `compatibility_signals` is assembled from the three parallel streams. None of the three generators ever sees another's result. This is what keeps the signal independent.

**Synthetic persona seeding** (`scripts/seed_cotravellers.py`) uses a two-stage blind-writer design that mirrors the real-user path:

- **Stage 1 — LLM-A (blind persona writer)**. The system prompt has a `CRITICAL: This system prompt MUST NOT mention:` comment block listing PUSH/PULL labels, emotional_signature taxonomy, top_push/top_interests vocabulary, matching feature names. Quote from the file: `"The blindness is the whole point of the two-stage design — it prevents the writer from 'knowing the answer key' while constructing the character."` LLM-A only knows: city, age bucket, gender, the 4 persona question option keys to pick from. It writes the character — name, voice_anchor, small_thing, quirks, visual_cue — as a person, not as a profile.
- **Stage 2 — Inference via the same machinery real users hit**. The written persona is then fed through `infer_emotional_signature` (parallel) AND the same persona-infer LLM (which assigns dimension labels). So the synthetic persona gets the same blind label assignment a real user would — the writer doesn't pre-pick the labels.
- This is what keeps the synthetic pool honest: the diversity matrix (city × age × gender) shapes the slot, the writer fills it in character, and the inferrer-as-separate-stage assigns the matching primitives. No single LLM call has both the persona AND its own classification.

**Why this matters**: if you let the persona LLM see ranker weights, it writes to the weights. If you let it see other users' personas, it averages toward them. If you tell it which dimension you want it to pick, it picks that dimension regardless of the user. Information-starvation is the only way to keep the persona authentic rather than a function of what the system would prefer the user to be.

**Same pattern shows up elsewhere:**

- The chat-reply persona prompt (`_build_persona_system`) hides the trip's matching score, the ranker's feature breakdown, the user's full chat history beyond the cap, and the persona's own `match_score`. Persona just talks; scorers just score.
- The proposal evaluator gets the persona + the user's profile + the current itinerary + recent history — but never the match score, the ranker weights, or what counter-titles other personas have suggested elsewhere.
- The shared-itinerary validator gets the proposed change + the itinerary state, never the negotiation history's emotional arc.

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

### Per-module design notes (the rest)

A sweep across every code file surfaced a long tail of load-bearing decisions worth recording. Grouped by module:

**`ali/routing/engine.py`** — fallback order is hardcoded `["openai", "anthropic"]`; `route_request_structured()` detects Anthropic clients and routes through `complete_with_tools()` with tool-use enum constraints derived at call-time from `jahnvi.data.dimensions`, preventing hallucinated dimension IDs. Non-Anthropic providers gracefully fall back to plain completion.

**`ali/clients/anthropic_client.py`** — 16k token ceiling on streaming itineraries (Sonnet supports 64k but 16k is safe for 7-14 day trips). `cost_per_1k_tokens` is an abstract property on `BaseLLMClient` but no caller uses it for cost-aware routing yet — it's there for V2.

**`ali/generation/itinerary_generator.py`** — `generate_itinerary_by_day()` streams JSON with a forward-only cursor; yields a parsed `ItineraryDay` the moment `{...}` depth returns to zero. If zero days are detected at stream end, falls back to `parse_itinerary()` on the full buffer to catch markdown fences and key-order quirks. `_patch_day_in_place` + `_patch_activity` backfill cost / duration / category / tags from a known-activities lookup; unknown activities get synthetic UUIDs.

**`ali/generation/output_parser.py`** — **server-side `itinerary_id` is non-negotiable**. LLM-generated IDs risk Firestore collision / overwrites, so every itinerary / destination / activity gets a fresh `uuid.uuid4()` at parse time regardless of what the LLM returned.

**`ali/rag/retriever.py` + `explainer.py`** — Pinecone queries hardcode `filter={"type": "activity_context" | "destination_context"}` against a pre-tagged corpus. `_build_explain_prompt()` repeats the private-framing rule: `emotional_signature` + `emotional_tone` shape cadence, never vocabulary; system prompt explicitly bans self-referential constructions like "as someone who is X".

**`ali/vector/client.py`** — lazy-load + `async.Lock` singleton for the Pinecone index; auto-creates the index if missing. `embed_texts()` coerces empty strings → space to avoid OpenAI 400s on blank inputs.

**`ali/voice/elevenlabs.py` + `mushahid/routes/voice.py`** — cache key is `sha256(text)[:16]` so the same text from the same persona always lands at the same Storage path. `make_public` is idempotent + cheap, called on every cache check. 600-char input cap with truncate-and-ellipsis (friendlier than rejecting a paste). On-disk cost: $0 for cache hits, ~$0.001-0.003 per first play.

**`mushahid/pipeline/orchestrator.py`** — **itinerary is written to Firestore BEFORE validation/matching**, so the UI can save it from the SSE `itinerary_generated` event without waiting for downstream steps. If validation / matching fails, the itinerary is still recoverable. Day-by-day stream + `explain_day()` inline before each `day_ready` event, so the user sees explained days one at a time rather than waiting for the full itinerary + a separate explanation pass.

**`mushahid/refinement/loop.py`** — every refinement attempt calls `build_refined_query(user_profile, feedback)` and re-runs `embed_text()` to update `travel_style_embedding` before re-retrieving. So the LLM gets fresh, feedback-aware context each retry instead of grinding on the original query. Loop is score-maximising: keeps the best itinerary by validator score and breaks early on `ValidationStatus.approved`.

**`mushahid/validation/validator_engine.py`** — repair loop has **oscillation detection**: if a repaired reply equals the input or drops below min length, the loop bails to the fallback rather than looping forever.

**`mushahid/persona/taxonomy.py` + `emotional_signature.py`** — closed-key taxonomy (8 keys), order is stable so the fallback always picks the first key. `EmotionalSignatureResult` carries **dual evidence**: GoEmotions (weak signal) + the user's persona answers (strong signal) + a `confidence: low|medium|high` field. If inference fails and `allow_fallback=True`, returns the first taxonomy key with `low` confidence rather than erroring out.

**`mushahid/realtime/firestore.py`** — Firestore writes use **dotted-path nested merges** for `compatibility_signals` so a single ranker-weight overwrite doesn't replace the whole signals dict. `LOCAL_MODE` swaps Firestore for an in-memory `_store` dict so the entire app can run without Firebase creds (used in tests; not for prod).

**`mushahid/realtime/sse.py`** — `format_event(name, data)` is the only SSE emitter; callers never construct event strings manually. Centralises the `event:\ndata:\n\n` wire format.

**`mushahid/routes/itineraries.py`** — **stale pointer recovery**: if `profile.current_itinerary_id` points to a deleted itinerary, `/current` returns `{itinerary: null}` instead of 404 so the dashboard doesn't break. Save is dedup'd via a `first_save` flag — re-saving the same `id` doesn't duplicate the history.

**`mushahid/routes/cotraveller.py`** — companion intake answers from `TravellerCompatibility` (rhythm / food_priority / recharge / social_energy / mood_handling / budget_style / novelty / documentation) are converted to a natural-language paragraph by `_extra_text_from_prefs()` and **appended to the user's persona text before embedding**, so retrieval skews toward compatible matches without changing the schema.

**`mushahid/auth.py`** — `LOCAL_MODE=true` bypasses Firebase entirely; any token is accepted and the token string itself becomes the uid. `verify_ws_token()` extracts from query params (WebSocket can't set Authorization headers); both paths share the same underlying `_verify()`.

**`mushahid/utils/sanitize.py`** — ~13 lightweight prompt-injection patterns + 2000-char cap enforced before pattern matching (so attempts can't hide in massive pastes). Flagged input is replaced with `"[input removed]"` and logged. Production should layer an LLM classifier on top.

**`shreyas/cotraveller/chat_signal_scanner.py`** — **sarcasm detection** blocks entire-message boosts on high-confidence markers (`/s`, "said no one ever", eye-roll emoji, "love how" clause-openers). **Negation zones** extend 5 words or to the next clause break (whichever first), so "I don't love crowded places" doesn't boost crowded-tag interest. Re-rank is fire-and-forget from the WS handler; user message broadcast is never blocked.

**`shreyas/ranking/salience.py`** — keyword density is **raw count**, not ratio. Longer / more revealing answers get higher weight intentionally. Chip labels (from `PERSONA_LABELS`) count toward density so chip-only users aren't penalised. Uniform `1/N` fallback when every answer is empty (avoids multiplying by zero in the ranker).

**`shreyas/ranking/features.py`** — ordinal alignment is `1.0` exact / `0.5` one-step / `0.0` two-steps-or-more; `None` inputs treated as `0.5` neutral. Pure scoring functions, no policy constants leak in.

**`shreyas/ranking/filters.py`** — filter drops are fire-and-forget logged to `feature_logging` so V2 gradient learning can learn from "what we wouldn't even consider" data, not just from accept/reject events.

**`shreyas/retrieval/search.py`** — Pinecone metadata stores `persona_answers` / `compatibility_signals` as JSON strings; defensive decode falls through to `{}` on parse failure. Flat `voice_id` field is preferred; falls back to nested `voice_profile_json` for backward compatibility with pre-flat seed records. **`search_destinations` is explicitly `NotImplementedError`** — V1 has no corpus discovery flow; the user always types the destination on the form.

**`shreyas/cotraveller/presence.py`** — heartbeat writes ONLY `last_seen`, never rewrites a boolean `online` flag (which would go stale on dropped connections). `is_online` is always derived from `last_seen < TTL`.

**`shared/currency.py`** — live rates from `exchangerate-api.com` with a **3-second timeout**, hardcoded `FALLBACK_RATES` table for 30 currencies used in `LOCAL_MODE` or when the API is unreachable. Format is units-per-1-USD (inverted from the API's USD-per-1-unit) so all conversions are a single multiplication.

**`shared/email.py`** — provider abstraction over `resend | sendgrid | ses`. `LOCAL_MODE` silently logs instead of sending; test endpoints set `force=True` to bypass. Pre-flight raises a concrete `"set EMAIL_API_KEY"` error before reaching the provider rather than surfacing an opaque 401.

**`shared/cities.py`** — on-demand city context via Nominatim + OpenWeather + Wikipedia (all keyless / free). Disk-cached to `.cache/cities.json` so repeats are instant.

**`shared/config.py`** — per-provider model IDs (`ANTHROPIC_SMALL_MODEL` / `OPENAI_SMALL_MODEL` / etc.) with a **3-tier fallback hierarchy**: dedicated env var → legacy single-name var (if provider matches) → hardcoded sensible default. Prevents accidentally sending an Anthropic model ID to OpenAI on provider failover.

**`jahnvi/data/classify_emotions.py`** — GoEmotions classifier embeds each of 27 emotion glosses ONCE per process behind an `async.Lock`. Scores are real cosine values from the embedding space, not LLM confidences — defensible signal even when not calibrated probabilities. The glosses themselves are **tone-anchored, not dictionary-like** ("realization = a quiet click — coming to understand something") to keep the embedding space crisp.

**`jahnvi/data/dimensions.py`** — keywords are substring-matched, not word-tokenised, so "out of comfort zone" counts as ONE signal, not three. `MIN_TOP_PUSH` / `MAX_TOP_PUSH` auto-derive from vocabulary length so adding / removing dimensions never requires script edits.

**`jahnvi/data/voice_catalog.py`** — voice assignment chain: `appearance_descriptor → accent bucket → gender → voice_id`. Japanese / Korean personas map to Southeast Asian voices (nearest substitute) due to ElevenLabs catalog gaps; documented in the file for when the catalog expands.

**`jahnvi/pipeline/module3_persona.py`** — `infer_persona()` only embeds and returns pose / pace. Dimension labels (`top_push`, `top_interests`) and reveal copy come from the LLM in `mushahid/routes/persona.py`; this module returns empty lists for those fields to keep schema shape stable for legacy callers.

**`jahnvi/frontend/src/hooks/useSSE.js`** — manually parses `event:` + `data:` lines because `EventSource` can't set Authorization headers. Tracks `eventName` state across lines and buffers incomplete fragments.

**`jahnvi/frontend/src/lib/destinationPhoto.js`** — Wikipedia REST API with `"City, Country"` → `"City"` fallback for disambiguation. 14-day localStorage TTL with **negative caching** (remembers when an article wasn't found so we don't re-query it). Free, CORS-permissive, no API key.

**`jahnvi/frontend/src/pages/Itinerary.jsx`** — auto-saves generated trips via `autoSavedIdRef` double-persist guard. `PHASE_COPY` map intentionally returns `null` for transient internal events (`persona_inferred`, `retrieval_done`, `ranked`) so the UI label only updates on user-meaningful phases. **Three-way view mode** (`both` / `desktop` / `mobile`) — single `activeActivityIdx` parent state plus `IntersectionObserver` in each view keeps the focused activity synced across view switches. **Wheel router** routes mouse wheel to the phone's internal scroll whenever the cursor is over `phoneSurfaceRef` (not just when the page can't scroll) so the bi-view phone preview stays mouse-scrollable alongside a tall desktop column. **Revise handler** consumes the `/revise` SSE stream via `streamReviseItinerary`, splices revised days into local state on `day_revised`, and narrates progress in a top-of-screen toast (`Rewriting day 3…` → `Day 3 updated` → `Swapped X → Y`).

**`mushahid/refinement/loop.py :: stream_single_revision`** — async generator powering `/revise`. One LLM regen + one validate, no `MAX_REFINEMENT_ATTEMPTS` loop. Routes to `stream_refined_days_by_day` when `target_day_numbers` is set (output 1-2k tokens) and `stream_refined_itinerary_by_day` otherwise (output 3-8k tokens). Always uses the large tier — small tier caps at 512-1024 tokens which silently truncates full-itinerary JSON. Emits SSE events as each day's JSON closes; falls back to a whole-buffer `parse_itinerary` if the brace counter detects nothing.

**`mushahid/refinement/classifier.py`** — small-LLM JSON classifier that scopes user revise feedback. Emits `{scope, summary, target_day_numbers, target_categories, preserve}` so the route can pick the targeted-day prompt path, build a dedupe `DO NOT RE-INTRODUCE` blacklist from prior rejected titles, and feed FOCUS / PRESERVE hints into the regen prompt. Defaults to scope=large on parse failure — better to over-spend on one turn than ship a wrong small-edit. Balanced-brace fallback parser handles markdown-fenced output.

**`mushahid/routes/itineraries.py :: /revise`** — wraps `stream_single_revision` in a `StreamingResponse`. Sniffs the final `revision_done` event off the stream and runs post-stream bookkeeping (revision_history append, per-user ranker weight delta with decay multiplier `max(0.125, 0.5 ** (turn-1))`, monitoring capture, persist with `approval_status="draft"`) **after** the user already has the diff on screen. Emits `revision_persisted` when bookkeeping completes. Failures in bookkeeping are logged but don't break the visible flow — the regenerated itinerary is already saved.

**`jahnvi/frontend/src/pages/PersonaReveal.jsx`** — caches persona in localStorage keyed by a deterministic hash of the trip profile JSON. Changing answers automatically changes the hash and invalidates the cache; no explicit clear needed.

**`jahnvi/frontend/src/components/SonderMark3D.jsx`** — manually transforms SVG viewBox coordinates (200×280, centre 100/140) to Three.js space with scale + flip. Extrude geometry + high-metalness physical material gives the gilded 3D logo feel.

**`jahnvi/frontend/src/components/LuxCursor.jsx`** — dual-layer ring (spring lag) + dot (direct follow). Decoupling visual feedback phases gives the cursor a "trailing" feel without sluggishness.

**`jahnvi/frontend/public/sw.js`** — **Web Push only**, no caching strategies. Deliberately scoped narrow — caching adds invalidation risk we haven't earned yet. Notification clicks prefer focusing an existing tab over opening a new one.

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
4. Add all env vars from `.env.example` (Firebase, OpenAI, Anthropic, Pinecone, VAPID, Sentry, PostHog, per-provider model names, synthetic-agent knobs, `EMAIL_PROVIDER` + `EMAIL_API_KEY` + `EMAIL_FROM` + `FRONTEND_BASE_URL` for transactional emails, `FIRESTORE_DATABASE_ID` if using a named DB)
5. Health check path: `/health`

> **Render env-var gotcha**: long values containing `-` chars (notably VAPID keys) can silently truncate at the first hyphen when pasted into the dashboard UI. After setting, verify via `curl https://<your-service>.onrender.com/api/push/vapid-public-key` returns the full key. If truncated, paste with surrounding quotes or use Render's multi-line value mode.

`ConnectionManager` and the synthetic-agents loop both hold in-memory state. Single-container is fine; multi-container production needs Redis pub/sub for both (the `REDIS_URL` config is already in `shared/config.py`).

### Frontend → Cloudflare Pages
1. Root directory: `jahnvi/frontend`
2. Build command: `npm run build`
3. Build output directory: `dist`
4. Add all `VITE_` env vars (Firebase config, etc.)
5. **API proxy via Pages Function** — `jahnvi/frontend/functions/api/[[path]].js` forwards every `/api/*` request to the Render backend. Edit the `BACKEND` constant at the top to point at your Render URL. (Cloudflare Pages `_redirects` only supports SAME-domain rewrites, so you can't proxy via that file.)
6. **HTTPS required** for Web Push (Cloudflare + Render handle this by default).
7. SPA fallback for client-side routes is automatic when `index.html` exists at the build output root — no rule file needed.

### Synthetic-agents tuning on prod
- Default cadence (15-50s) is built for "feels alive" demo state. For prod with real users, raise `SYNTHETIC_AGENTS_MIN_INTERVAL` / `MAX_INTERVAL` to thin the feed once organic content exists.
- `SYNTHETIC_AGENTS_ENABLED=false` disables the loop entirely.

### Cotraveller avatars
After running `seed_cotravellers.py`, upload `seed_assets/cotraveller_avatars/*.png` to your static host and update the URL prefix in Pinecone metadata or serve `/seed_assets/` from your CDN.

---

See [TASKS.md](./TASKS.md) for the per-person build checklist.
