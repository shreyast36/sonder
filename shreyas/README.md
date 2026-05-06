# Shreyas — Lead AI Systems & Real-time Engineer

You own the intelligence layer that finds the right destinations, activities, and people — and keeps everything in sync once users connect.

---

## What You Own

| Folder | Responsibility |
|---|---|
| `retrieval/` | Pinecone vector search — embed queries, search destinations, activities, co-travellers |
| `ranking/` | Score and rank retrieval results using multi-signal scoring |
| `cotraveller/` | Compatibility matching, WebSocket chat engine, presence, shared itinerary sync, approval |

---

## Module Contracts

### `retrieval/` — inputs & outputs

**`embeddings.py`**
```python
# Input
embed_text("beach trip, relaxed pace, budget $2000, food lover, excited mood")

# Output
[0.023, -0.187, 0.094, ...]  # list of floats, length == EMBED_DIMENSIONS (from .env)
```

**`search.py`**
```python
# search_destinations — input
user_profile = UserProfile(
    constraints=TripConstraints(destination_type="beach", budget_usd=2000, pace_preference="relaxed"),
    persona_answers=PersonaQuestionAnswers(food_interest=5, culture_interest=4),
    emotion_intent=EmotionIntent.excited
)

# search_destinations — output
[
    {"id": "dest_bali",   "score": 0.91, "metadata": {"city": "Bali",   "country": "Indonesia"}},
    {"id": "dest_lisbon", "score": 0.87, "metadata": {"city": "Lisbon", "country": "Portugal"}},
    ...  # top_k results
]

# search_cotravellers — output
[
    {"id": "ct_maya_001", "score": 0.94, "metadata": {"profile_id": "maya_001", "archetype": "Cultural Explorer"}},
    ...
]
```

---

### `ranking/` — inputs & outputs

**`destination_ranker.py`**
```python
# rank_destinations — input
candidates = [
    (Destination(city="Bali",   avg_daily_cost_usd=120, tags=["beach","culture","food"]), 0.91),
    (Destination(city="Lisbon", avg_daily_cost_usd=160, tags=["culture","food","history"]), 0.87),
]

# rank_destinations — output (top 5, sorted by final score)
[
    Destination(city="Bali", ...),    # score 0.83 after weighting
    Destination(city="Lisbon", ...),  # score 0.79
]
```

**Scoring weights (your decision — suggested starting point):**
- 60% vector similarity (Pinecone score)
- 20% budget fit
- 20% tag-interest bonus (persona alignment)

---

### `cotraveller/` — inputs & outputs

**`matching.py`**
```python
# get_top_matches — input
user_profile = UserProfile(persona_answers=PersonaQuestionAnswers(food_interest=5, pace_preference="relaxed"))
candidates   = [CoTravellerProfile(...), ...]  # 20 profiles from Pinecone

# get_top_matches — output (top 3)
[
    CoTravellerMatch(
        profile         = CoTravellerProfile(display_name="Maya Sharma", location="Delhi, India"),
        match_score     = 0.92,
        match_reasons   = ["Similar interests in food and culture", "Same travel pace", "Similar budget range"],
        compatibility_breakdown = {"interests": 0.95, "pace": 1.0, "budget": 0.85}
    ),
    CoTravellerMatch(...),  # 0.88
    CoTravellerMatch(...),  # 0.81
]
```

**`chat.py` — WebSocket message shapes**
```python
# Client → Server
{"type": "message", "content": "Hey! Excited to connect!"}
{"type": "typing"}
{"type": "seen", "message_id": "msg_001"}

# Server → Client (broadcast)
{"type": "message",  "sender_id": "user_abc", "content": "Hey!",   "timestamp": "2025-06-01T09:30:00Z"}
{"type": "typing",   "user_id":   "user_abc"}
{"type": "seen",     "message_id": "msg_001", "user_id": "user_abc"}
```

**`approval.py`**
```python
# approve_match — output
ApprovalStatus.approved  # if both users have now approved
ApprovalStatus.pending   # if waiting on the other user

# deny_match — output
ApprovalStatus.denied
```

**`shared_itinerary.py`**
```python
# create_shared_itinerary — output
SharedItinerary(
    itinerary_id    = "itin_abc123",
    user_ids        = ["firebase_uid_abc", "maya_001"],
    itinerary       = Itinerary(...),
    notes           = [],
    last_updated_by = None
)
```

---

## How Your Code Connects to Others

| You call | From | Purpose |
|---|---|---|
| `mushahid/realtime/firestore.py` | `presence.py`, `shared_itinerary.py`, `approval.py` | Read/write Firestore |
| `mushahid/realtime/notifications.py` | `approval.py` | Push notifications on approval/denial |
| `shared/schemas.py` | Everywhere | All data models |
| `shared/config.py` | `retrieval/client.py`, `retrieval/embeddings.py` | API keys |

| Others call you | From | Purpose |
|---|---|---|
| `mushahid/pipeline/orchestrator.py` | `search.py`, `ranking/`, `cotraveller/matching.py` | Pipeline steps 2, 3, 7 |
| `mushahid/routes/chat.py` | `cotraveller/chat.py` | WebSocket proxy |
| `mushahid/routes/cotraveller.py` | `cotraveller/matching.py` | HTTP co-traveller endpoint |
| `ali/rag/retriever.py` | `retrieval/search.py` | RAG context retrieval |

---

## Build Order

1. `retrieval/client.py` first — everything else needs a working Pinecone connection
2. `retrieval/embeddings.py` + `retrieval/search.py`
3. Seed Pinecone with destination, activity, and co-traveller data
4. `ranking/filters.py` → `ranking/destination_ranker.py` → `ranking/activity_ranker.py`
5. `cotraveller/matching.py`
6. `cotraveller/chat.py` → `cotraveller/presence.py` → `cotraveller/approval.py` → `cotraveller/shared_itinerary.py`
