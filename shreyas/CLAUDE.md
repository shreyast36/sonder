# Shreyas — Pinecone Retrieval, Ranking, Co-traveller & Real-time

Read `shreyas/README.md` for the full picture. This file is a quick-reference for Claude Code.

---

## What lives here

| File / Folder | Purpose |
|---|---|
| `retrieval/client.py` | `get_pinecone_index()` — initialise Pinecone, return index handle |
| `retrieval/embeddings.py` | `embed_text(text)` → `list[float]`; `build_refined_query(profile, feedback)` |
| `retrieval/search.py` | `search_destinations()`, `search_activities()`, `search_cotravellers()` |
| `ranking/filters.py` | Hard filters before scoring (budget cap, date availability) |
| `ranking/destination_ranker.py` | `rank_destinations(candidates, user_profile)` — multi-signal scoring |
| `ranking/activity_ranker.py` | `rank_activities(candidates, user_profile)` |
| `cotraveller/matching.py` | `get_top_matches()`, `score_match()`, `regenerate_matches()` |
| `cotraveller/chat.py` | `ConnectionManager` — WebSocket session management |
| `cotraveller/presence.py` | `heartbeat()`, `is_online()`, `cleanup_stale_presence()` |
| `cotraveller/approval.py` | `approve_match()`, `deny_match()` — mutual approval logic |
| `cotraveller/shared_itinerary.py` | `create_shared_itinerary()`, `add_activity()`, `add_note()`, `sync_changes()` |

---

## Pinecone — 3 namespaces

```
destinations   — destination vectors (city-level)
activities     — activity/POI vectors (activity-level)
cotravellers   — user travel-style embeddings (updated on each refinement)
```

Index dimension = `EMBED_DIMENSIONS` from `shared/config.py`. Wait for Ali to finalise this before creating the index.

Seed the index:
```bash
python -m scripts.seed_pinecone --namespace all
```

---

## Embedding provider — your choice

Set `EMBED_MODEL_PROVIDER`, `EMBED_MODEL`, and `EMBED_DIMENSIONS` in `.env`. Vectors always go to Pinecone regardless of which provider generates them. If using Bedrock, also set `BEDROCK_EMBED_MODEL_ID`.

`embed_text()` is the only place that touches the embedding provider. Everything else calls `embed_text()`.

---

## Presence — TTL-based, not boolean

```python
PRESENCE_TTL_SECONDS = 90   # from shared/config.py

async def is_online(user_id: str) -> bool:
    last_seen = await get_last_seen(user_id)   # from Firestore
    return (datetime.utcnow() - last_seen).seconds < PRESENCE_TTL_SECONDS
```

The frontend sends `{"type": "ping"}` via WebSocket every 30 seconds. `handle_ping()` in `chat.py` calls `heartbeat(user_id)` which writes `last_seen` to Firestore. Do not use a boolean `online` flag — it goes stale when connections drop unexpectedly.

---

## ConnectionManager — Redis required in production

The `ConnectionManager` holds WebSocket sessions in a Python dict. Fine locally. On ECS with multiple containers, messages sent to one container won't reach sessions on another.

Production fix:
- Replace the dict with Redis pub/sub (`aioredis`)
- Each container subscribes to `session:{session_id}`
- `broadcast_to_session()` publishes to Redis
- `REDIS_URL` is already in `shared/config.py` — read it there
- `LOCAL_MODE=true` → in-memory fallback is fine

---

## Optimistic locking on shared itinerary

`add_activity()` and `add_note()` use a `version` field to prevent silent overwrites:

```python
# Firestore transaction:
if current_doc["version"] != client_version:
    raise HTTPException(409, "Conflict — re-fetch and retry")
# else: apply change, increment version
```

Frontend re-fetches on 409 via `sync_changes()` and lets the user retry.

---

## Refinement loop — re-embed before re-querying

When `refinement/loop.py` calls `build_refined_query(user_profile, feedback)`, it must then call `embed_text()` on the result and update `user_profile.travel_style_embedding` before re-running `search_destinations()` and `search_activities()`. This ensures the refinement is driven by the updated signal, not the original query.

---

## What others need from you first

- **Jahnvi** needs `embed_text()` before she can finish `build_travel_style_embedding()` in Module 3
- **Ali** needs `search_destinations()` + `search_activities()` before the RAG retriever works
- **Mushahid** needs `search_*`, `rank_*`, `ConnectionManager`, `approve_match`, `deny_match` before the orchestrator and routes work

---

## What not to do

- Do not call `os.getenv()` — use `shared/config.py`
- Do not import schemas from `jahnvi/schemas/` — use `shared/schemas.py`
- Do not call `get_db()` directly — import it from `mushahid/realtime/firestore.py`
- Do not call push notification functions — import `notify_co_traveller_approved()` from `mushahid/realtime/notifications.py`
- Do not use a boolean `online` field for presence — use the TTL check in `is_online()`
