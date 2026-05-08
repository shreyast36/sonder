# Ali — Lead AI Intelligence & Multi-model Engineer

You own the database and everything that runs through an LLM.

**Database:** You set up and seed the Pinecone index. You decide the embedding model, the vector dimensions, and where the destination/activity data comes from. Shreyas queries your index but does not manage it.

**LLM layer:** Every AI call in the product routes through your engine — itinerary generation, validation, explanations, chat topics, icebreakers.

**RAG:** Once Shreyas's search has already selected and ranked the best activities, your RAG pipeline fetches factual context about those chosen activities from Pinecone and passes it to the LLM to write the "Why this?" explanations shown on Screen 3.

**You do not select candidates.** Deciding which destinations or activities to show the user is Shreyas's job (his search + ranking). You explain the already-chosen ones.

---

## What You Own

| Folder | Responsibility |
|---|---|
| `vector/client.py` | Pinecone index setup — `get_pinecone_index()` used by Shreyas's `search.py` |
| `clients/` | One LLM provider wrapper per file — the only place API calls are made |
| `routing/` | Classify tasks by model tier (SMALL / LARGE / VALIDATOR), route to correct client |
| `generation/` | Itinerary generation (streaming), prompt templates, output parsing, chat topics |
| `rag/retriever.py` | Fetch text context about an already-chosen activity from Pinecone (calls Shreyas's search) |
| `rag/explainer.py` | Pass that context to the LLM and write the "Why this?" explanation |

---

## The Selection vs. RAG Distinction

Both you and Shreyas query Pinecone, but for completely different things:

| | Shreyas (`retrieval/search.py`) | Ali (`rag/retriever.py`) |
|---|---|---|
| **When** | Pipeline steps 2, 3, 7 — before the itinerary exists | After the itinerary is generated — one activity at a time |
| **Input** | Full user profile + constraints | A single already-chosen activity or destination |
| **Output** | Top-N candidate list for ranking | Text chunks (facts) to feed into the LLM prompt |
| **Purpose** | Decide WHAT to show the user | Explain WHY something was chosen |

Your `retriever.py` calls Shreyas's `search.py` under the hood — you reuse his search interface to pull context chunks, then hand them to `explainer.py` which calls the LLM.

---

## Your Decisions

### Embedding model + dimensions
You decide `EMBED_MODEL_PROVIDER`, `EMBED_MODEL`, and `EMBED_DIMENSIONS`. Write them into `shared/config.py`. Shreyas reads them in `embeddings.py` — he is blocked until these are set.

### Destination & activity data source
You own the seed script (`scripts/seed_pinecone.py`) and decide where the data comes from. Coordinate with Shreyas on the metadata field names — his `search.py` filters on specific fields.

| Option | Notes |
|---|---|
| **Amadeus Travel API** | Large coverage, free tier, destinations + activities + POIs. Best starting point. |
| **Foursquare Places API** | Strong POI/activity data, free tier up to 1k calls/day. |
| **Tripadvisor Content API** | Rich reviews and photos — useful for RAG context snippets. Paid. |
| **Curated CSV** | Fastest to ship — 20–30 destinations, 5–10 activities each. Use for demo. |

### LLM model selection
No model names are hardcoded. Every provider file implements three client classes — Small, Large, and Validator. Set which provider + model to use for each tier in `.env`:

```bash
SMALL_MODEL_PROVIDER=       # openai | anthropic | google | groq | mistral | bedrock
SMALL_MODEL_NAME=           # e.g. gpt-4o-mini, claude-haiku-4-5, gemini-flash

LARGE_MODEL_PROVIDER=       # openai | anthropic | google | groq | mistral | bedrock
LARGE_MODEL_NAME=           # e.g. gpt-4o, claude-opus-4-7, gemini-pro

VALIDATOR_MODEL_PROVIDER=   # openai | anthropic | google | groq | mistral | bedrock
VALIDATOR_MODEL_NAME=       # e.g. gpt-4o, claude-sonnet-4-6 — needs structured output support

# Only needed if any provider above is set to "bedrock":
BEDROCK_SMALL_MODEL_ID=
BEDROCK_LARGE_MODEL_ID=
BEDROCK_VALIDATOR_MODEL_ID=
```

The routing engine reads these at runtime and instantiates `{Provider}{Tier}Client` accordingly — e.g. `SMALL_MODEL_PROVIDER=anthropic` → `AnthropicSmallClient`. You can mix providers across tiers (e.g. Groq for Small, Anthropic for Large, OpenAI for Validator).

---

## Dependencies

### What I need from others

| From | What exactly | Where I use it | Needed by |
|---|---|---|---|
| **Jahnvi** | `shared/schemas.py` finalised | All generation and parsing imports schemas | Right now — blocks everything |
| **Jahnvi** | `UserProfile`, `Itinerary`, `ItineraryDay`, `ItineraryActivity` shapes | `itinerary_generator.py`, `explainer.py`, `output_parser.py` | Before any generation code |
| **Shreyas** | `search_destinations()`, `search_activities()` from `retrieval/search.py` | `rag/retriever.py` calls these to get context chunks | Before I build the explainer |

### What others need from me

| Who | What exactly | Which file | When they're blocked |
|---|---|---|---|
| **Shreyas** | `get_pinecone_index()` from `ali/vector/client.py` | `shreyas/retrieval/search.py` | Before Shreyas can build search |
| **Shreyas** | `EMBED_DIMENSIONS` in `shared/config.py` | `shreyas/retrieval/embeddings.py` | Before Shreyas can write embeddings |
| **Mushahid** | `route_request()` + `stream_request()` from `routing/engine.py` | `validation/critic.py` + `orchestrator.py` | Before validation + orchestrator |
| **Mushahid** | `generate_itinerary()` streaming generator | `orchestrator.py` step 4 | Before itinerary pipeline |
| **Mushahid** | `explain_itinerary()` | `orchestrator.py` step 5 | Before explainer step |
| **Mushahid** | `generate_topics()` + `generate_icebreaker()` | `routes/chat.py` `start_chat` via `asyncio.gather` | Before chat feature |

---

## Module Contracts

### `routing/engine.py`

```python
route_request(
    task_type = "itinerary_generation",
    prompt    = "Generate a 7-day beach trip for Bali...",
    system    = "You are an expert travel planner. Output valid JSON.",
    context   = {"token_estimate": 3200}
)
# → '{"days": [{"day_number": 1, "theme": "Culture & Coastal Views", ...}]}'
```

### `generation/itinerary_generator.py`

```python
generate_itinerary(user_profile, destination, activities)
# Streams token chunks → assembled into Itinerary after streaming completes
# Note: why_this fields are None here — explainer.py fills them in next
```

### `rag/retriever.py`

```python
# Given an already-chosen activity, fetch text facts about it from Pinecone
retrieve_activity_context(
    activity     = Activity(name="Uluwatu Temple", category="culture"),
    user_profile = UserProfile(...)
)
# → ["Uluwatu sits on a 70m cliff...", "Perfect for slow travellers...", ...]
# These strings go directly into the LLM prompt in explainer.py
```

### `rag/explainer.py`

```python
explain_activity(
    activity     = Activity(name="Uluwatu Temple", ...),
    context      = ["Uluwatu sits on a 70m cliff...", ...],  # from retriever.py
    user_profile = UserProfile(persona_answers=PersonaQuestionAnswers(culture_interest=5))
)
# → "This matches your relaxed pace and love for culture. Uluwatu Temple offers a
#    serene 2-hour experience on dramatic ocean cliffs — the sunset Kecak dance here
#    is one of Bali's most memorable cultural moments."
# This string is written into ItineraryActivity.why_this and shown on Screen 3.
```

### `generation/topics.py`

```python
# Both called by Mushahid's POST /chat/start via asyncio.gather
generate_topics(user_profile, match, itinerary)
# → ["Must-try local food in Bali", "Beach vs adventure balance", ...]  # 5 chips on Screen 5

generate_icebreaker(user_profile, match)
# → "Hey Maya! I noticed you're also a foodie — what dish are you most excited to try?"
```

---

## How Your Code Connects to Others

| You call | From | Purpose |
|---|---|---|
| `shreyas/retrieval/search.py` | `rag/retriever.py` | Fetch RAG context chunks from Pinecone |
| `shared/config.py` | All clients | Read API keys + model names |
| `shared/schemas.py` | Everywhere | Data models |

| Others call you | From | Purpose |
|---|---|---|
| `mushahid/pipeline/orchestrator.py` | `itinerary_generator.py`, `explainer.py` | Pipeline steps 4 + 5 |
| `mushahid/validation/critic.py` | `routing/engine.py` | Validator LLM calls |
| `mushahid/refinement/loop.py` | `itinerary_generator.py` | Regeneration |
| `mushahid/routes/chat.py` | `generation/topics.py` | Chat topics + icebreaker |

---

## Build Order

1. `vector/client.py` — Pinecone init first; Shreyas is blocked until `get_pinecone_index()` exists
2. Write `EMBED_MODEL` + `EMBED_DIMENSIONS` into `shared/config.py` — unblocks Shreyas's embeddings
3. Seed Pinecone: `python -m scripts.seed_pinecone --namespace all`
4. `clients/base.py` → all provider clients in `clients/`
5. `routing/classifier.py` → `routing/engine.py`
6. `generation/prompts.py` → `generation/output_parser.py` → `generation/itinerary_generator.py`
7. `rag/retriever.py` → `rag/explainer.py` (needs Shreyas's `search.py` to be working)
8. `generation/topics.py`
