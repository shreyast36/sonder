# Shreyas — Lead AI Systems & Real-time Engineer

You find the right things and keep everything in sync.

**Selection:** Your code answers "which destinations, activities, and people should we show this user?" — embeddings turn the user profile into a query vector, search queries Pinecone for candidates, and ranking scores and orders them.

**Real-time:** Once two users match, you own everything that keeps them in sync — WebSocket chat, presence, shared itinerary, approval flow.

**You do not explain things.** The "Why this?" text on Screen 3 is Ali's RAG pipeline. Your search hands off candidates; Ali's explainer writes the reasoning.

---

## What You Own

| Folder | Responsibility |
|---|---|
| `retrieval/embeddings.py` | Convert user profile into a Pinecone query vector |
| `retrieval/search.py` | Query Pinecone and return top-N candidate destinations, activities, co-travellers |
| `ranking/` | Filter hard constraints, then score and rank candidates |
| `cotraveller/matching.py` | Score compatibility between two user profiles |
| `cotraveller/chat.py` | WebSocket engine for real-time chat |
| `cotraveller/presence.py` | Online/offline tracking via Firestore |
| `cotraveller/shared_itinerary.py` | Collaborative itinerary sync with optimistic locking |
| `cotraveller/approval.py` | Approve/deny co-traveller matches |

---

## The Selection vs. RAG Distinction

Both you and Ali query Pinecone, but for completely different things:

| | Shreyas (`retrieval/search.py`) | Ali (`rag/retriever.py`) |
|---|---|---|
| **When** | Pipeline steps 2, 3, 7 — before the itinerary exists | After the itinerary is generated — one activity at a time |
| **Input** | Full user profile + constraints | A single already-chosen activity or destination |
| **Output** | Top-N candidate list for ranking | Text chunks (facts) to feed into the LLM prompt |
| **Purpose** | Decide WHAT to show the user | Explain WHY something was chosen |

Ali's `retriever.py` calls your `search.py` under the hood. You provide the interface; he uses it for a different purpose.

---

## Dependencies

### What I need from others

| From | What exactly | Where I use it | Needed by |
|---|---|---|---|
| **Jahnvi** | `shared/schemas.py` finalised | Every module imports schemas | Right now — blocks everything |
| **Jahnvi** | `UserProfile` with `compatibility_signals` + `travel_style_embedding` | `matching.py` + `search.py` | Before co-traveller search |
| **Jahnvi** | `CoTravellerProfile`, `CoTravellerMatch` shapes | `matching.py` | Before matching |
| **Ali** | `get_pinecone_index()` from `ali/vector/client.py` | `search.py` — all Pinecone queries go through this | Before I can build search |
| **Ali** | `EMBED_DIMENSIONS` written into `shared/config.py` | `embeddings.py` — vector length must match index | Before I can write embeddings |
| **Mushahid** | `get_db()` in `realtime/firestore.py` | `presence.py`, `shared_itinerary.py`, `approval.py` | Before real-time features |
| **Mushahid** | `notify_co_traveller_approved()` in `realtime/notifications.py` | `approval.py` on mutual approval | Before approval flow |

### What others need from me

| Who | What exactly | Which file | When they're blocked |
|---|---|---|---|
| **Jahnvi** | `embed_text(text) → list[float]` | `module3_persona.py` — `build_travel_style_embedding()` | Before Module 3 |
| **Ali** | `search_destinations()`, `search_activities()` | `ali/rag/retriever.py` calls these for RAG context chunks | Before Ali builds the explainer |
| **Mushahid** | `search_destinations()` + `search_activities()` | `orchestrator.py` steps 2–3 | Before orchestrator runs |
| **Mushahid** | `rank_destinations()` + `rank_activities()` | `orchestrator.py` step 3 | Before orchestrator runs |
| **Mushahid** | `search_cotravellers()` + `get_top_matches()` | `orchestrator.py` step 7 + `/cotraveller` route | Before co-traveller feature |
| **Mushahid** | `ConnectionManager` from `cotraveller/chat.py` | `routes/chat.py` WebSocket proxy | Before `/ws/chat/{id}` |
| **Mushahid** | `approve_match()` + `deny_match()` | `routes/chat.py` | Before Screen 6 |

---

## Module Contracts

### `retrieval/embeddings.py`

```python
embed_text("beach trip, relaxed pace, budget $2000, food lover, excited mood")
# → [0.023, -0.187, 0.094, ...]  length == EMBED_DIMENSIONS (from shared/config.py)
```

### `retrieval/search.py`

```python
# search_destinations — input: user profile, output: top-N Pinecone hits
search_destinations(user_profile)
# → [{"id": "dest_bali", "score": 0.91, "metadata": {...}}, ...]

# search_cotravellers — output: top co-traveller profile hits
search_cotravellers(user_profile)
# → [{"id": "ct_maya_001", "score": 0.94, "metadata": {"profile_id": "maya_001"}}, ...]
```

### `ranking/destination_ranker.py`

```python
# rank_destinations — scoring weights (your decision):
# 60% vector similarity · 20% budget fit · 20% persona tag match
rank_destinations(candidates=[(Destination(...), 0.91), ...])
# → [Destination(city="Bali", ...), ...]  sorted by final score
```

### `cotraveller/matching.py`

```python
get_top_matches(user_profile, candidates=[CoTravellerProfile(...), ...])
# → [
#     CoTravellerMatch(profile=..., match_score=0.92,
#                      match_reasons=["Similar food interest", "Same pace"],
#                      compatibility_breakdown={"interests": 0.95, "pace": 1.0, "budget": 0.85}),
#     ...  # top 3
# ]
```

### `cotraveller/chat.py` — WebSocket message shapes

```python
# Client → Server
{"type": "message", "content": "Hey!"}
{"type": "typing"}
{"type": "seen",    "message_id": "msg_001"}
{"type": "ping"}    # heartbeat every 30s — resets 90s TTL in Firestore presence

# Server → Client
{"type": "message", "sender_id": "uid_abc", "content": "Hey!", "timestamp": "..."}
{"type": "typing",  "user_id": "uid_abc"}
{"type": "seen",    "message_id": "msg_001", "user_id": "uid_abc"}
```

### `cotraveller/shared_itinerary.py`

```python
# Optimistic locking — every write checks client_version == current Firestore version.
# Mismatch → return HTTP 409. Client must re-fetch and re-apply change.
create_shared_itinerary(itinerary_id, user_ids)
# → SharedItinerary(version=0, notes=[], ...)
```

### `cotraveller/approval.py`

```python
approve_match(session_id, approver_uid)
# → ApprovalStatus.approved   (both users approved)
# → ApprovalStatus.pending    (waiting on the other user)

deny_match(session_id, denier_uid)
# → ApprovalStatus.denied
```

---

## Production Notes

### ConnectionManager — Redis required in production
`ConnectionManager` in `chat.py` holds WebSocket sessions in a Python dict. Fine locally, **breaks on ECS** — multiple containers each have their own memory.

Fix before production:
- Replace in-memory dict with Redis pub/sub using `aioredis`
- Each container subscribes to `session:{session_id}` channel
- `broadcast_to_session()` publishes to Redis; all containers receive + forward
- `REDIS_URL` is in `shared/config.py` — read from there
- When `LOCAL_MODE=true` in-memory fallback is fine

### Embeddings — model chosen by Ali
Ali sets `EMBED_MODEL_PROVIDER`, `EMBED_MODEL`, and `EMBED_DIMENSIONS` in `shared/config.py`. Read them from there — do not hardcode any values.

---

## Build Order

1. Wait for Ali: `ali/vector/client.py` live + `EMBED_DIMENSIONS` in `shared/config.py`
2. `retrieval/embeddings.py` (reads config, does not need Pinecone)
3. `retrieval/search.py` (imports `get_pinecone_index` from Ali)
4. `ranking/filters.py` → `ranking/destination_ranker.py` → `ranking/activity_ranker.py`
5. `cotraveller/matching.py`
6. `cotraveller/chat.py` → `cotraveller/presence.py` → `cotraveller/approval.py` → `cotraveller/shared_itinerary.py`
