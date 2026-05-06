# Ali — Lead AI Intelligence & Multi-model Engineer

You own the brain of the product. Every AI decision — which model runs, what it generates, how it explains itself — flows through your code.

---

## What You Own

| Folder | Responsibility |
|---|---|
| `routing/` | Multi-model routing engine — classifies tasks, picks the right model tier |
| `clients/` | LLM provider client wrappers — one file per provider |
| `generation/` | Itinerary generation, output parsing, prompt templates, chat topic generation |
| `rag/` | RAG retrieval + "Why this?" activity explanations |

---

## Your First Decision — Model Selection

**No model names are hard-coded anywhere.** You choose which models to use by setting these in `.env`:

```bash
# Small tier (fast + cheap — chat topics, persona labels, quick edits)
SMALL_MODEL_PROVIDER=           # your choice of provider
SMALL_MODEL_NAME=               # your choice of model

# Large tier (complex — itinerary generation, RAG explanations)
LARGE_MODEL_PROVIDER=           # your choice of provider
LARGE_MODEL_NAME=               # your choice of model

# Validator tier (critic mode — feasibility + quality checks)
VALIDATOR_MODEL_PROVIDER=       # your choice of provider
VALIDATOR_MODEL_NAME=           # your choice of model

# Bedrock model IDs (only needed if you set any provider above to "bedrock")
BEDROCK_SMALL_MODEL_ID=         # your choice
BEDROCK_LARGE_MODEL_ID=         # your choice
BEDROCK_VALIDATOR_MODEL_ID=     # your choice
```

The routing engine (`routing/engine.py`) reads these at runtime and instantiates the right client.

---

## Dependencies

### What I need from others

| From | What exactly | Where I use it | Status needed by |
|---|---|---|---|
| **Jahnvi** | `shared/schemas.py` finalised | All generation and parsing code imports schemas | **Right now — blocks everything** |
| **Jahnvi** | `UserProfile`, `Itinerary`, `ItineraryDay`, `ItineraryActivity`, `Activity`, `Destination` shapes | `generation/itinerary_generator.py`, `rag/explainer.py`, `generation/output_parser.py` | Before I write any generation code |
| **Shreyas** | `retrieval/search.py` — `search_destinations()` and `search_activities()` | `rag/retriever.py` calls these to fetch context chunks | Before I can build the RAG explainer |

### What others need from me

| Who | What exactly | Which file | When they're blocked |
|---|---|---|---|
| **Mushahid** | `route_request()` + `stream_request()` from `routing/engine.py` | `validation/critic.py` + `pipeline/orchestrator.py` | Before validation and orchestrator run |
| **Mushahid** | `generate_itinerary()` streaming generator | `pipeline/orchestrator.py` step 4 | Before the itinerary pipeline runs |
| **Mushahid** | `explain_itinerary()` — populates all `why_this` fields | `pipeline/orchestrator.py` step 5 | Before the explainer step runs |
| **Mushahid** | `generate_itinerary()` again for re-generation | `refinement/loop.py` | Before the refinement loop works |
| **Shreyas** | `generate_topics()` + `generate_icebreaker()` from `generation/topics.py` | `shreyas/cotraveller/chat.py` sends these as AI-generated suggestions | Before chat feature is complete |
| **Everyone** | Decision on `EMBED_MODEL` + `EMBED_DIMENSIONS` | Goes into `shared/config.py`; Shreyas needs this to configure Pinecone | **Announce this early — Shreyas is blocked on it** |

---

## Architecture

```
route_request(task_type, prompt, system)
    │
    ├── classifier.py → classify(task_type) → ModelTier (small | large | validator)
    │
    └── engine.py → get_client(tier)
            │
            └── reads *_MODEL_PROVIDER from env → returns the matching client class
```

---

## Module Contracts

### `routing/` — task type → model tier

```python
# Task types you must handle:
SMALL  → "chat_topics", "icebreaker", "persona_label", "preference_parse",
          "quick_edit", "notification_message", "short_explanation"

LARGE  → "itinerary_generation", "complex_refinement", "conflict_resolution",
          "rag_explanation", "what_if"

VALIDATOR → "validate_itinerary", "critic_check"
```

```python
# route_request — input
route_request(
    task_type = "itinerary_generation",
    prompt    = "Generate a 7-day beach trip for Bali...",
    system    = "You are an expert travel planner. Output valid JSON.",
    context   = {"token_estimate": 3200}
)

# route_request — output
'{"days": [{"day_number": 1, "theme": "Culture & Coastal Views", "activities": [...]}]}'
```

### `generation/itinerary_generator.py` — streaming output

```python
# Input
generate_itinerary(user_profile, destination, activities)

# Streaming output (token chunks, assembled into full Itinerary after streaming)
'{"days"' → ': [{"day' → '_number": 1' → ', "theme": ...' → ...

# Final assembled Itinerary structure:
Itinerary(
    itinerary_id     = "itin_abc123",
    destination      = Destination(city="Bali", country="Indonesia"),
    days             = [
        ItineraryDay(
            day_number     = 1,
            theme          = "Culture & Coastal Views",
            daily_cost_usd = 140.0,
            activities     = [
                ItineraryActivity(time="9:00 AM",  activity=Activity(name="Uluwatu Temple"),    why_this=None),
                ItineraryActivity(time="1:00 PM",  activity=Activity(name="Padang Padang Beach"), why_this=None),
                ItineraryActivity(time="6:00 PM",  activity=Activity(name="Jimbaran Bay Dinner"), why_this=None),
            ]
        ),
        # ... days 2–7
    ],
    total_budget_usd = 840.0
)
# Note: why_this fields are None here — explainer.py fills them in next.
```

### `rag/explainer.py` — "Why this?" explanations

```python
# explain_activity — input
activity     = Activity(name="Uluwatu Temple", category="culture", duration_hours=2.0)
context      = ["Uluwatu sits on a 70m cliff...", "Perfect for slow travellers..."]
user_profile = UserProfile(persona_answers=PersonaQuestionAnswers(culture_interest=5, pace="relaxed"))

# explain_activity — output (this text is shown on Screen 3 under the activity)
"This matches your relaxed pace and love for culture.
 Uluwatu Temple offers a serene 2-hour experience on dramatic ocean cliffs —
 the sunset Kecak dance here is one of Bali's most memorable cultural moments."
```

### `generation/topics.py` — chat topics

```python
# generate_topics — output (shown on Screen 4 and Screen 5)
[
    "Must-try local food in Bali",
    "Beach vs adventure balance",
    "Cultural experiences to explore",
    "Budget-friendly activities",
    "Best time to travel & weather"
]

# generate_icebreaker — output (suggested first message on Screen 5)
"Hey Maya! I noticed you're also a foodie — what's the one dish you're most excited to try in Bali?"
```

### `generation/output_parser.py` — JSON parsing

```python
# Input: raw LLM response (may have markdown, extra text, etc.)
raw = '```json\n{"days": [...]}\n```'

# Output: clean Itinerary object, or retried if malformed
Itinerary(days=[...], total_budget_usd=840.0, ...)
```

---

## How Your Code Connects to Others

| You call | From | Purpose |
|---|---|---|
| `shreyas/retrieval/search.py` | `rag/retriever.py` | Fetch RAG context from Pinecone |
| `shared/config.py` | All clients | Read API keys + model names |
| `shared/schemas.py` | Everywhere | Data models |

| Others call you | From | Purpose |
|---|---|---|
| `mushahid/pipeline/orchestrator.py` | `generation/itinerary_generator.py`, `rag/explainer.py` | Pipeline steps 4 + 5 |
| `mushahid/validation/critic.py` | `routing/engine.py` | Validator LLM calls |
| `mushahid/refinement/loop.py` | `generation/itinerary_generator.py` | Regeneration |
| `shreyas/cotraveller/chat.py` | `generation/topics.py` | AI chat topics |

---

## Build Order

1. `clients/base.py` — define the interface first
2. All provider clients in `clients/` — implement whichever providers you choose to support
3. `routing/classifier.py` → `routing/engine.py`
4. `generation/prompts.py` → `generation/output_parser.py` → `generation/itinerary_generator.py`
5. `rag/retriever.py` → `rag/explainer.py`
6. `generation/topics.py`
