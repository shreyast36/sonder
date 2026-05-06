# Ali — Multi-model Routing, Itinerary Generation & RAG

Read `ali/README.md` for the full picture. This file is a quick-reference for Claude Code.

---

## What lives here

| File / Folder | Purpose |
|---|---|
| `routing/classifier.py` | Maps task type string → `ModelTier` (small / large / validator) |
| `routing/engine.py` | `route_request()` + `stream_request()` — reads env to pick the right client |
| `clients/base.py` | Abstract base class all provider clients must implement |
| `clients/anthropic_client.py` | Anthropic client stubs |
| `clients/openai_client.py` | OpenAI client stubs |
| `clients/google_client.py` | Google client stubs |
| `clients/groq_client.py` | Groq client stubs |
| `clients/bedrock_client.py` | AWS Bedrock client stubs |
| `generation/prompts.py` | Prompt templates — itinerary generation, refinement, validator critic |
| `generation/output_parser.py` | Parse LLM JSON output; handle markdown-wrapped responses |
| `generation/itinerary_generator.py` | `generate_itinerary()` — streaming generator, token-by-token |
| `generation/topics.py` | `generate_topics()` + `generate_icebreaker()` for chat screen |
| `rag/retriever.py` | Calls `shreyas/retrieval/search.py` to fetch Pinecone context |
| `rag/explainer.py` | `explain_itinerary()` — populates `why_this` on every activity using asyncio.gather |

---

## Model selection — your decision, set in .env

Never hard-code a model name or provider anywhere in this folder. All model config comes from `shared/config.py`:

```python
from shared.config import SMALL_MODEL_PROVIDER, SMALL_MODEL_NAME, LARGE_MODEL_PROVIDER, ...
```

`routing/engine.py` reads these at runtime and returns the right client instance.

---

## Task type → model tier mapping

```
SMALL     → chat_topics, icebreaker, persona_label, preference_parse, quick_edit,
             notification_message, short_explanation
LARGE     → itinerary_generation, complex_refinement, conflict_resolution,
             rag_explanation, what_if
VALIDATOR → validate_itinerary, critic_check
```

---

## Streaming contract

`generate_itinerary()` must be an async generator that yields raw token strings one at a time. The orchestrator forwards each chunk immediately as a `generating` SSE event — it does not buffer.

`generate_itinerary_by_day()` yields one `ItineraryDay` at a time as it finishes parsing, so the orchestrator can fire `day_ready` events and start explaining days in parallel before the full itinerary is complete.

---

## RAG explainer — asyncio.gather

`explain_itinerary()` calls `explain_day()` for all days concurrently:

```python
explained_days = await asyncio.gather(*[explain_day(day, user_profile) for day in itinerary.days])
```

Do not explain days sequentially — it would be too slow.

---

## output_parser.py — LLMs return messy JSON

LLMs often wrap JSON in markdown code fences or add preamble text. The parser must strip this before passing to Pydantic:

```python
# Input from LLM:
'```json\n{"days": [...]}\n```'

# After parsing:
Itinerary(days=[...])
```

---

## Announce your embedding decision early

`EMBED_DIMENSIONS` in `shared/config.py` determines the Pinecone index dimension. Shreyas cannot finalise the Pinecone index until you set this. Announce `EMBED_MODEL_PROVIDER`, `EMBED_MODEL`, and `EMBED_DIMENSIONS` in `.env.example` before Shreyas starts retrieval work.

---

## What not to do

- Do not call any provider SDK directly from outside `ali/` — always go through `routing/engine.py`
- Do not hard-code model names, API keys, or provider strings anywhere
- Do not buffer token chunks before forwarding — yield immediately
- Do not call `os.getenv()` — use `shared/config.py`
- Do not define or modify data schemas — those are Jahnvi's (import from `shared/schemas.py`)
