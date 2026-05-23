"""
Seed Pinecone with synthetic co-traveller personas. Rewritten per spec.

Spec locked across 6 design questions:

  1. PPM source        — Two-stage. LLM-A (blind to PUSH/PULL/signature
                          vocab) writes the synthetic's "answers". Those
                          answers go through the SAME persona-infer LLM
                          path real users hit. Tags inferred symmetrically.
  2. Diversity matrix  — 16 cities × 7 age buckets × 2 genders = 224 slots.
                          Stable profile_id per slot so re-runs overwrite.
  3. Image params      — gpt-image-1 medium quality, photoreal, 1024×1024.
                          appearance_descriptor + visual_cue from LLM-A
                          drive prompt diversity. Anti-stereotype clause
                          baked in.
  4. Voice             — ElevenLabs from a curated 16-voice catalog
                          (jahnvi/data/voice_catalog.py). Assignment:
                          appearance_descriptor → accent → gender → voice_id.
                          voice_clone=False hardcoded.
  5. Storage           — Firebase Storage. Avatars at
                          cotraveller_avatars/{pid}.png, audio cache
                          at synthetic_audio/{pid}/{hash}.mp3.
  6. CLI               — default = max = 224. --dry-run, --purge
                          (default false), --resume. Concurrency hardcoded.

Pipeline per slot:
    LLM-A blind persona writer
        → real persona-infer LLM (tags + descriptor/paragraph/bullets)
        → emotional_signature inference (parallel)
        → gpt-image-1 portrait (using appearance_descriptor + visual_cue)
        → Firebase Storage upload (avatar)
        → voice_id assignment (accent + gender lookup)
        → embed text via OpenAI 1536-dim
        → upsert to Pinecone `cotravellers` namespace

Every record carries is_seed: True so the frontend can render the
"Sonder Curated" badge.

CLI:
    python -m scripts.seed_cotravellers
    python -m scripts.seed_cotravellers --dry-run
    python -m scripts.seed_cotravellers --resume
    python -m scripts.seed_cotravellers --purge

Cost estimate (all 224, no --dry-run):
    LLM-A persona     224 × ~$0.005 = ~$1.10  (small LLM call per slot)
    Real persona-infer 224 × ~$0.005 = ~$1.10  (same tier)
    Emotional sig      224 × ~$0.003 = ~$0.70
    gpt-image-1 medium 224 × $0.042  = ~$9.40
    OpenAI embeds      224 × ~negligible
                                       ───────
                       Total          ~$12-14
"""

import argparse
import asyncio
import base64
import hashlib
import json
import logging
import random
import re
import sys
import time

from openai import AsyncOpenAI

from ali.routing.engine import route_request, route_request_structured
from ali.vector.embeddings import embed_batch
from jahnvi.data.classify_emotions import classify_emotions
from jahnvi.data.dimensions import PUSH_DIMENSIONS, PULL_DIMENSIONS
from jahnvi.data.persona_labels import label_for
from jahnvi.data.voice_catalog import voice_for, accent_for_appearance
from jahnvi.schemas.enums import PacePreference, BudgetStyle, TravelStyle
from mushahid.persona.emotional_signature import infer_emotional_signature
from mushahid.persona.taxonomy import (
    EMOTIONAL_SIGNATURE_TAXONOMY, PERSONA_QUESTION_CATALOG,
)
from mushahid.realtime.storage import upload_avatar
from mushahid.routes.persona import (
    _redistribute_pools, _structural_validate, _system_prompt,
)
from shared.config import OPENAI_API_KEY
from shared.schemas import TripConstraints, PersonaQuestionAnswers
from shreyas.ranking.salience import compute_answer_salience
from shreyas.retrieval.client import get_pinecone_index


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("seed_cotravellers")


# ── Locked spec constants ─────────────────────────────────────────────────


# 16-city pool — globally balanced. User-confirmed in spec discussion.
CITIES: list[str] = [
    "New York, USA",
    "Mexico City, Mexico",
    "Buenos Aires, Argentina",
    "Bogotá, Colombia",
    "London, United Kingdom",
    "Paris, France",
    "Berlin, Germany",
    "Lisbon, Portugal",
    "Istanbul, Turkey",
    "Lagos, Nigeria",
    "Cape Town, South Africa",
    "Dubai, United Arab Emirates",
    "Mumbai, India",
    "Bangkok, Thailand",
    "Tokyo, Japan",
    "Seoul, South Korea",
]

# 7 buckets, 20–90 in 10-year steps. User-defined.
AGE_BUCKETS: list[tuple[int, int]] = [
    (20, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 90),
]

# 50/50 split, hard-locked. User-defined.
GENDERS: list[str] = ["male", "female"]


# Allowed option keys per chip — must match jahnvi/data/persona_labels.py.
PERSONA_OPTION_KEYS: dict[str, list[str]] = {
    "social_role":       ["place_finder", "social_bridge", "day_anchor", "pace_reader"],
    "trip_feeling":      ["brain_louder", "disappeared", "story_collector", "exhaled"],
    "friction_response": ["regroup", "pivot", "fix_fast", "mask"],
    "ideal_atmosphere":  ["loud_anonymous", "quiet_attentive", "lively_chaos", "slow_sunlit"],
}


# Concurrency caps (hardcoded per spec).
LLM_A_CONCURRENCY        = 4
PERSONA_INFER_CONCURRENCY = 4
IMAGE_CONCURRENCY        = 4
UPSERT_BATCH_SIZE        = 100


_openai_client: AsyncOpenAI | None = None


def _openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required for gpt-image-1 portrait generation")
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


# ── Diversity matrix ──────────────────────────────────────────────────────


def _stable_id(*parts: str) -> str:
    return f"ct_{hashlib.sha256('|'.join(parts).encode()).hexdigest()[:20]}"


def build_diversity_matrix() -> list[dict]:
    """Full Cartesian product: every (city, age_bucket, gender) triple.
    Slot index `i` becomes part of the profile_id so re-runs overwrite the
    same Pinecone record."""
    slots: list[dict] = []
    i = 0
    for city in CITIES:
        for age_lo, age_hi in AGE_BUCKETS:
            for gender in GENDERS:
                slots.append({
                    "profile_id": _stable_id(city, f"{age_lo}-{age_hi}", gender, str(i)),
                    "city":       city,
                    "age_lo":     age_lo,
                    "age_hi":     age_hi,
                    "gender":     gender,
                    "rng_seed":   int(hashlib.sha256(f"{city}|{i}".encode()).hexdigest()[:8], 16),
                })
                i += 1
    return slots


# ── Stage 1 — LLM-A (blind persona writer) ────────────────────────────────


# CRITICAL: This system prompt MUST NOT mention:
#   - PUSH / PULL / MOTIVATION labels
#   - emotional_signature taxonomy (reset_seeker, story_collector, etc.)
#   - top_push / top_interests vocabulary
#   - matching feature names
# The blindness is the whole point of the two-stage design — it prevents the
# writer from "knowing the answer key" while constructing the character.
_LLM_A_SYSTEM = """
You design a fictional but emotionally specific traveller for a travel app.
The goal is a character who feels real on a profile card — not an archetype,
not a marketing blurb, not a personality test result.

The user gives you a home city, age range, and gender. You return ONE JSON
object matching the schema below.

Rules:
- Specific over abstract. "Eats cold dumplings for breakfast" beats "loves food".
- Contradictions are good. Real people have them.
- Pick exactly one option key for each of social_role / trip_feeling /
  friction_response / ideal_atmosphere from the ALLOWED OPTIONS provided.
  Vary your picks across the four fields so the persona doesn't read as
  on-the-nose.
- small_thing is gold — one sentence, first-person, oddly specific
  ("the way the espresso machine at my corner cafe sighs when it warms up").
- voice_anchor is a 1-2 sentence first-person recent-trip memory the chat
  LLM will use to ground replies. Anchor it in a real place + a sensory
  detail.
- quirks: 1-2 short third-person quirks ("can't function without morning
  coffee", "always ends up in markets", "allergic to crowded beaches").
- visual_cue: a short phrase the image generator will use for the
  portrait setting, e.g. "leaning against a market stall, late afternoon
  light" or "at a tiny cafe table near the harbour, overcast".
- appearance_descriptor: 1-3 words for visual reference only (e.g.
  "Indian", "Nigerian", "Brazilian of Italian descent"). Treat this as
  appearance information for image generation, not demographic
  classification.
- Name should match the home city plausibly (mix of ethnicities is fine
  — most cosmopolitan cities have residents of many backgrounds).

NEVER mention or refer to:
- "push" or "pull" motivations
- emotional signatures / archetypes by name
- travel matching, tags, scoring, dimensions
The character is just a character. Nothing else.

Output ONLY this JSON object — no preface, no markdown fences:

{
  "display_name": "...",
  "age": 27,
  "appearance_descriptor": "...",
  "preferred_destination": "City, Country — somewhere they'd actually go",
  "archetype": "3-4 word evocative label, title case, no period",
  "interests": ["3-5 specific lowercase tags"],
  "pace": "relaxed | moderate | packed",
  "budget_style": "budget | mid_range | luxury",
  "travel_style": "solo | couple | family | friends",
  "social_role":       "one of the allowed keys",
  "trip_feeling":      "one of the allowed keys",
  "friction_response": "one of the allowed keys",
  "ideal_atmosphere":  "one of the allowed keys",
  "small_thing":       "one sentence, oddly specific, first-person",
  "voice_anchor":      "1-2 sentence first-person recent-trip memory",
  "quirks":            ["short quirk", "another short quirk"],
  "visual_cue":        "short phrase describing portrait setting"
}
""".strip()


def _llm_a_prompt(slot: dict) -> str:
    return (
        f"HOME CITY: {slot['city']}\n"
        f"AGE RANGE: {slot['age_lo']}-{slot['age_hi']}\n"
        f"GENDER: {slot['gender']}\n"
        "\n"
        f"ALLOWED OPTIONS for chip selections:\n"
        f"  social_role:       {PERSONA_OPTION_KEYS['social_role']}\n"
        f"  trip_feeling:      {PERSONA_OPTION_KEYS['trip_feeling']}\n"
        f"  friction_response: {PERSONA_OPTION_KEYS['friction_response']}\n"
        f"  ideal_atmosphere:  {PERSONA_OPTION_KEYS['ideal_atmosphere']}\n"
        "\n"
        "Return the JSON persona object."
    )


def _parse_json_object(raw: str) -> dict:
    """Lenient JSON parser — LLMs are creative with trailing commas, stray
    fences, and post-object commentary. The strict json.loads path tries
    first; balanced-brace extraction + trailing-comma stripping picks up
    the long tail of "almost valid" responses that the previous regex
    couldn't handle."""
    raw = (raw or "").strip()
    # Strip wrapping code fences anywhere (start, end, both).
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```\s*$", "", raw).strip()

    # Happy path — strict JSON.
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Find the outermost {...} via balanced-brace counting. Tolerates
    # LLM preamble ("Here is the JSON:\n{...}") and post-object text
    # ("...}\n\nDone!") that broke the greedy regex.
    start = raw.find("{")
    if start == -1:
        raise ValueError("no JSON object found in LLM output")

    depth = 0
    in_string = False
    escape = False
    end = -1
    for i in range(start, len(raw)):
        c = raw[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        raise ValueError("unclosed JSON object in LLM output")

    candidate = raw[start:end + 1]
    # Strip trailing commas before } or ] — Python's json.loads rejects
    # them but LLMs love producing them.
    candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
    return json.loads(candidate)


def _coerce_llm_a(obj: dict, slot: dict) -> dict:
    """Validate enums + clamp PPM-answer keys against the allowed set. LLM
    occasionally drifts — fall back to slot defaults rather than crashing."""
    rng = random.Random(slot["rng_seed"])
    age = int(obj.get("age") or rng.randint(slot["age_lo"], slot["age_hi"]))
    age = max(slot["age_lo"], min(slot["age_hi"], age))

    def _enum(value, choices, default):
        v = (value or "").strip().lower() if isinstance(value, str) else ""
        return v if v in choices else default

    pace   = _enum(obj.get("pace"),         [p.value for p in PacePreference], "moderate")
    budget = _enum(obj.get("budget_style"), [b.value for b in BudgetStyle],    "mid_range")
    style  = _enum(obj.get("travel_style"), [t.value for t in TravelStyle],    "solo")

    interests = obj.get("interests") or []
    if not isinstance(interests, list):
        interests = [str(interests)]
    interests = [str(i).strip().lower() for i in interests if str(i).strip()][:5]

    quirks = obj.get("quirks") or []
    if not isinstance(quirks, list):
        quirks = [str(quirks)]
    quirks = [str(q).strip() for q in quirks if str(q).strip()][:2]

    return {
        "display_name":          str(obj.get("display_name") or "").strip() or "Anonymous",
        "age":                   age,
        "appearance_descriptor": str(obj.get("appearance_descriptor") or "").strip(),
        "preferred_destination": str(obj.get("preferred_destination") or "").strip(),
        "archetype":             str(obj.get("archetype") or "").strip() or "Traveller",
        "interests":             interests,
        "pace":                  pace,
        "budget_style":          budget,
        "travel_style":          style,
        "social_role":           _enum(obj.get("social_role"),       PERSONA_OPTION_KEYS["social_role"],       "place_finder"),
        "trip_feeling":          _enum(obj.get("trip_feeling"),      PERSONA_OPTION_KEYS["trip_feeling"],      "story_collector"),
        "friction_response":     _enum(obj.get("friction_response"), PERSONA_OPTION_KEYS["friction_response"], "pivot"),
        "ideal_atmosphere":      _enum(obj.get("ideal_atmosphere"),  PERSONA_OPTION_KEYS["ideal_atmosphere"],  "lively_chaos"),
        "small_thing":           str(obj.get("small_thing") or "").strip(),
        "voice_anchor":          str(obj.get("voice_anchor") or "").strip(),
        "quirks":                quirks,
        "visual_cue":            str(obj.get("visual_cue") or "").strip(),
    }


async def llm_a_generate(slot: dict, sem: asyncio.Semaphore) -> dict | None:
    """Run LLM-A blind to the tag vocabulary. Retries twice on parse / API
    failure before giving up on this slot. Mid-attempt failures log at
    DEBUG (transient and recoverable); only the final-attempt failure
    logs at WARNING."""
    async with sem:
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                raw = await route_request("complex_refinement", _llm_a_prompt(slot), _LLM_A_SYSTEM)
                return _coerce_llm_a(_parse_json_object(raw), slot)
            except Exception as e:
                last_err = e
                if attempt < 2:
                    log.debug("  LLM-A attempt %d retrying for slot %s: %s", attempt + 1, slot["profile_id"][-6:], e)
                    await asyncio.sleep(2.0 + random.uniform(0, 1.5))
        log.warning("  LLM-A failed for slot %s after 3 attempts: %s", slot["profile_id"][-6:], last_err)
    return None


# ── Stage 2 — Real persona inference (same path as real users) ────────────


_ALLOWED_PUSH = list(PUSH_DIMENSIONS.keys())
_ALLOWED_PULL = list(PULL_DIMENSIONS.keys())


def _build_persona_inference_prompt(persona: dict) -> str:
    """Construct the user prompt that the persona-infer LLM sees, in the
    same shape real users produce. The system prompt comes from
    mushahid.routes.persona._system_prompt() — same code path."""
    styles = ", ".join(filter(None, [persona["pace"], persona["budget_style"], persona["travel_style"]]))
    who    = persona["travel_style"]
    pace   = persona["pace"]
    friends     = label_for("social_role",       persona["social_role"])      or "—"
    restaurant  = label_for("trip_feeling",      persona["trip_feeling"])     or "—"
    notice      = label_for("friction_response", persona["friction_response"]) or "—"
    atmosphere  = label_for("ideal_atmosphere",  persona["ideal_atmosphere"]) or "—"
    small       = (persona.get("small_thing") or "").strip() or "—"

    return (
        f"User's persona signals:\n\n"
        f"Travel style chips: {styles}\n"
        f"Pace: {pace}\n"
        f"Travelling with: {who}\n\n"
        f"Their persona answers:\n"
        f"- Friends say they're the one who: {friends}\n"
        f"- At a new restaurant they: {restaurant}\n"
        f"- First thing they notice in a new place: {notice}\n"
        f"- Most at home in: {atmosphere}\n"
        f"- A small thing that made them happy lately: \"{small}\"\n\n"
        "Return the JSON."
    )


async def persona_infer(persona: dict, sem: asyncio.Semaphore) -> dict | None:
    """Run the synthetic's "answers" through the same persona-infer LLM
    call real users hit. Returns the structured persona dict with
    top_push / top_interests / descriptor / paragraph / bullets.

    Mid-attempt failures log at DEBUG; only final-attempt failure logs at
    WARNING (most retries succeed)."""
    async with sem:
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                user_prompt = _build_persona_inference_prompt(persona)
                raw = await route_request_structured(
                    "persona_label", user_prompt, _system_prompt(),
                    push_ids=_ALLOWED_PUSH, pull_ids=_ALLOWED_PULL,
                )
                obj = _parse_json_object(raw)
                obj = _redistribute_pools(obj)
                issues = _structural_validate(obj)
                if issues:
                    raise ValueError(f"structural issues: {issues}")
                return obj
            except Exception as e:
                last_err = e
                if attempt < 2:
                    log.debug("  persona-infer attempt %d retrying (%s): %s", attempt + 1, persona.get("display_name", "?"), e)
                    await asyncio.sleep(2.0 + random.uniform(0, 1.5))
        log.warning("  persona-infer failed for %s after 3 attempts: %s", persona.get("display_name", "?"), last_err)
    return None


# ── Stage 3 — gpt-image-1 portrait ────────────────────────────────────────


# Anti-stereotype + diversity-aware prompt clause (constraint set
# locked with the user during spec).
_IMAGE_PROMPT_GUARDRAILS = (
    "Photoreal portrait, candid, medium-distance composition, natural light. "
    "Important constraints: do not stereotype clothing, props, skin tone, or setting "
    "based on the appearance descriptor. Do not infer religion, caste, tribe, or "
    "political identity. Use natural, ordinary portrait context — what a real "
    "person looks like on a normal day in this city. Ground the image in the "
    "persona's city and lifestyle, not tourist clichés (no famous landmarks "
    "behind them, no postcard backdrops, no costume-of-the-region props). "
    "Mid-distance composition with the face visible but the setting also "
    "present. Warm honest tones, mid-quality realism, not magazine-cover."
)


def _portrait_prompt(persona: dict, slot: dict) -> str:
    appearance = persona.get("appearance_descriptor") or "person"
    visual_cue = persona.get("visual_cue") or "in a quiet ordinary corner of the city"
    age = persona.get("age", 30)
    gender = slot["gender"]
    city = slot["city"]
    return (
        f"Portrait of a {age}-year-old {gender}, {appearance}, in {city}. "
        f"{visual_cue}. {_IMAGE_PROMPT_GUARDRAILS}"
    )


async def generate_portrait(persona: dict, slot: dict, sem: asyncio.Semaphore) -> bytes | None:
    async with sem:
        for attempt in range(2):
            try:
                resp = await _openai().images.generate(
                    model="gpt-image-1",
                    prompt=_portrait_prompt(persona, slot),
                    size="1024x1024",
                    quality="medium",
                    n=1,
                )
                b64 = resp.data[0].b64_json
                if not b64:
                    raise ValueError("empty b64_json")
                return base64.b64decode(b64)
            except Exception as e:
                log.warning("  portrait attempt %d failed (%s): %s", attempt + 1, slot["profile_id"][-6:], e)
                if attempt < 1:
                    await asyncio.sleep(3.0)
    return None


# ── Stage 4 — Embedding text + Pinecone metadata builder ─────────────────


def build_embedding_text(persona: dict, tags: dict, signature: dict) -> str:
    """Rich, naturally-phrased text the cotraveller-namespace embedding
    lives on. Mixes the chip labels + small_thing + voice_anchor + quirks
    + tags + signature so cosine retrieval lands close to real users with
    similar texture."""
    parts: list[str] = [
        persona["archetype"],
        ", ".join(persona["interests"]),
        f"pace: {persona['pace']}, budget: {persona['budget_style']}, style: {persona['travel_style']}",
        label_for("social_role",       persona["social_role"]),
        label_for("trip_feeling",      persona["trip_feeling"]),
        label_for("friction_response", persona["friction_response"]),
        label_for("ideal_atmosphere",  persona["ideal_atmosphere"]),
        persona.get("small_thing", ""),
        persona.get("voice_anchor", ""),
        ". ".join(persona.get("quirks", [])),
        f"draws toward: {', '.join(tags.get('top_interests', []))}",
        f"travels because of: {', '.join(tags.get('top_push', []))}",
        f"emotional tone: {signature.get('emotional_tone', '')}",
    ]
    return ". ".join(p.strip() for p in parts if p and str(p).strip())


def build_metadata(
    slot: dict,
    persona: dict,
    tags: dict,
    signature: dict,
    salience: dict,
    voice_profile: dict,
    avatar_url: str | None,
    embedding_text: str,
) -> dict:
    """Pinecone metadata can only carry primitives + list[str]. Nested
    dicts get JSON-encoded so search.py's get_cotraveller_by_id can
    decode them on read."""
    compat: dict = {
        "top_push":            tags.get("top_push", []),
        "top_interests":       tags.get("top_interests", []),
        "answer_salience":     salience,
    }
    compat.update(signature)

    return {
        "profile_id":            slot["profile_id"],
        "display_name":          persona["display_name"],
        "age":                   persona["age"],
        "location":              slot["city"],
        "preferred_destination": persona["preferred_destination"],
        "archetype":             persona["archetype"],
        "interests":             persona["interests"],
        "pace":                  persona["pace"],
        "budget_style":          persona["budget_style"],
        "travel_style":          persona["travel_style"],
        "avatar_url":            avatar_url or "",
        "voice_anchor":          persona.get("voice_anchor", ""),
        "quirks":                persona.get("quirks", []),
        "voice_profile_json":    json.dumps(voice_profile, ensure_ascii=False),
        "appearance_descriptor": persona.get("appearance_descriptor", ""),
        "accent_bucket":         accent_for_appearance(persona.get("appearance_descriptor")),
        "persona_answers_json":  json.dumps({
            "social_role":       persona["social_role"],
            "trip_feeling":      persona["trip_feeling"],
            "friction_response": persona["friction_response"],
            "ideal_atmosphere":  persona["ideal_atmosphere"],
            "small_thing":       persona.get("small_thing", ""),
        }, ensure_ascii=False),
        "top_push":              tags.get("top_push", []),
        "top_interests":         tags.get("top_interests", []),
        "compatibility_signals_json": json.dumps(compat, ensure_ascii=False),
        "text":                  embedding_text[:1500],
        "is_seed":               True,
    }


# ── Pinecone ops ──────────────────────────────────────────────────────────


async def purge_namespace() -> None:
    log.info("Purging Pinecone 'cotravellers' namespace…")
    index = await get_pinecone_index()
    try:
        await asyncio.to_thread(lambda: index.delete(delete_all=True, namespace="cotravellers"))
        log.info("  purge complete")
    except Exception as e:
        log.warning("  purge failed (namespace may not exist): %s", e)


async def existing_profile_ids() -> set[str]:
    """For --resume: list current cotravellers profile_ids so we can skip
    them. Pinecone doesn't expose a list-all-vectors API per spec — we use
    list_paginated for namespaces that support it. Returns empty set on
    error (resume falls back to overwriting)."""
    index = await get_pinecone_index()
    try:
        ids: set[str] = set()
        result = await asyncio.to_thread(lambda: index.list(namespace="cotravellers"))
        for batch in result:
            ids.update(batch)
        return ids
    except Exception as e:
        log.warning("Pinecone list() failed (%s) — --resume will overwrite", e)
        return set()


async def upsert_batch(records: list[dict]) -> None:
    if not records:
        return
    index = await get_pinecone_index()
    for i in range(0, len(records), UPSERT_BATCH_SIZE):
        chunk = records[i:i + UPSERT_BATCH_SIZE]
        await asyncio.to_thread(lambda c=chunk: index.upsert(namespace="cotravellers", vectors=c))
        log.info("  upserted %d / %d", min(i + UPSERT_BATCH_SIZE, len(records)), len(records))


# ── Main pipeline ─────────────────────────────────────────────────────────


async def process_slot(
    slot: dict,
    *,
    dry_run: bool,
    llm_a_sem: asyncio.Semaphore,
    persona_sem: asyncio.Semaphore,
    image_sem: asyncio.Semaphore,
) -> dict | None:
    """End-to-end one slot. Returns the Pinecone record (id + values + metadata),
    or None when any stage fails fatally."""
    pid = slot["profile_id"]

    # Stage 1: blind persona writer
    persona = await llm_a_generate(slot, llm_a_sem)
    if persona is None:
        log.warning("  slot %s skipped — LLM-A failed", pid[-6:])
        return None

    # Stage 2: real persona-infer (parallel with emotional-signature inference)
    tags_task = persona_infer(persona, persona_sem)

    signature_inputs = {
        "social_role":       persona["social_role"],
        "trip_feeling":      persona["trip_feeling"],
        "friction_response": persona["friction_response"],
        "ideal_atmosphere":  persona["ideal_atmosphere"],
        "small_thing":       persona.get("small_thing", ""),
        "voice_anchor":      persona.get("voice_anchor", ""),
    }
    # Classifier text — used by both classify_emotions and as
    # precomputed_goemotions input to the signature inferrer.
    classifier_text = ". ".join(filter(None, [
        persona.get("small_thing", ""), persona.get("voice_anchor", ""),
        ". ".join(persona.get("quirks", [])),
    ]))
    goemotions = await classify_emotions(classifier_text, top_k=5) if classifier_text else []

    signature_task = infer_emotional_signature(
        signature_inputs,
        question_catalog=PERSONA_QUESTION_CATALOG,
        signature_taxonomy=EMOTIONAL_SIGNATURE_TAXONOMY,
        precomputed_goemotions=goemotions,
    )

    tags_obj, signature_result = await asyncio.gather(tags_task, signature_task, return_exceptions=True)

    if isinstance(tags_obj, Exception) or tags_obj is None:
        log.warning("  slot %s — persona-infer failed: %s", pid[-6:], tags_obj)
        return None
    tags = tags_obj  # already a dict with top_push / top_interests / descriptor / etc.

    if isinstance(signature_result, Exception):
        log.warning("  slot %s — signature inference failed: %s", pid[-6:], signature_result)
        signature = {}
    else:
        signature = signature_result.to_compatibility_signals()
        signature["goemotions_top"] = [label for label, _score in goemotions]

    # Salience — same pure-function the real persona route persists.
    # Build a TripConstraints + PersonaQuestionAnswers shell so salience can
    # read the chip selections + small_thing through its normal accessors.
    constraints_shell = TripConstraints(
        social_role=persona["social_role"],
        trip_feeling=persona["trip_feeling"],
        friction_response=persona["friction_response"],
        ideal_atmosphere=persona["ideal_atmosphere"],
    )
    answers_shell = PersonaQuestionAnswers(small_thing=persona.get("small_thing", ""))
    salience = compute_answer_salience(answers_shell, constraints_shell)

    # Stage 3: voice assignment (no LLM call — just catalog lookup).
    voice_profile = voice_for(persona.get("appearance_descriptor"), slot["gender"])

    # Stage 4: gpt-image-1 portrait + Firebase Storage upload.
    avatar_url: str | None = None
    if not dry_run:
        png_bytes = await generate_portrait(persona, slot, image_sem)
        if png_bytes is not None:
            try:
                avatar_url = await upload_avatar(pid, png_bytes)
            except Exception as e:
                log.warning("  slot %s — Firebase Storage upload failed: %s", pid[-6:], e)
                avatar_url = None
    else:
        log.info("  slot %s — DRY RUN, skipping portrait + upload", pid[-6:])

    # Stage 5: build the Pinecone record. Embedding text + values via
    # the same OpenAI 1536-dim embedder real users hit.
    embedding_text = build_embedding_text(persona, tags, signature)
    metadata = build_metadata(slot, persona, tags, signature, salience, voice_profile, avatar_url, embedding_text)

    return {
        "id":           pid,
        "values":       None,  # filled in by the batched embed call
        "metadata":     metadata,
        "embed_text":   embedding_text,
        "log_preview": {
            "name":      persona["display_name"],
            "city":      slot["city"],
            "age":       persona["age"],
            "gender":    slot["gender"],
            "archetype": persona["archetype"],
            "signature": signature.get("emotional_signature"),
            "voice":     voice_profile["voice_id"],
            "avatar":    bool(avatar_url),
        },
    }


async def main(dry_run: bool, do_purge: bool, do_resume: bool) -> None:
    t0 = time.time()

    if do_purge and do_resume:
        raise SystemExit("--purge and --resume are mutually exclusive")

    if do_purge and not dry_run:
        await purge_namespace()

    slots = build_diversity_matrix()
    log.info("Diversity matrix: %d slots (%d cities × %d age buckets × %d genders)",
             len(slots), len(CITIES), len(AGE_BUCKETS), len(GENDERS))

    skip_ids: set[str] = set()
    if do_resume:
        log.info("Querying existing Pinecone slots for --resume…")
        skip_ids = await existing_profile_ids()
        before = len(slots)
        slots = [s for s in slots if s["profile_id"] not in skip_ids]
        log.info("  %d already-completed slots skipped → %d remaining", before - len(slots), len(slots))

    if not slots:
        log.info("Nothing to do — exiting.")
        return

    # Bounded concurrency per stage.
    llm_a_sem   = asyncio.Semaphore(LLM_A_CONCURRENCY)
    persona_sem = asyncio.Semaphore(PERSONA_INFER_CONCURRENCY)
    image_sem   = asyncio.Semaphore(IMAGE_CONCURRENCY)

    log.info("Processing %d slots…", len(slots))
    t1 = time.time()
    raw_records = await asyncio.gather(*[
        process_slot(s, dry_run=dry_run, llm_a_sem=llm_a_sem, persona_sem=persona_sem, image_sem=image_sem)
        for s in slots
    ])
    records = [r for r in raw_records if r is not None]
    log.info("Slot processing done in %.1fs (%d/%d ok)", time.time() - t1, len(records), len(slots))

    if not records:
        log.warning("Zero usable records produced — bailing.")
        return

    # Embed the texts in batches (same OpenAI 1536-dim path as live users).
    log.info("Embedding %d persona texts…", len(records))
    t2 = time.time()
    texts = [r["embed_text"] for r in records]
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), 100):
        embeddings.extend(await embed_batch(texts[i:i + 100]))
        log.info("  embedded %d / %d", min(i + 100, len(texts)), len(texts))
    for rec, vec in zip(records, embeddings):
        rec["values"] = vec
    log.info("Embeds done in %.1fs", time.time() - t2)

    # Strip the helper fields the seed used internally (embed_text, log_preview)
    # before upserting — Pinecone only takes id + values + metadata.
    pinecone_records = [
        {"id": r["id"], "values": r["values"], "metadata": r["metadata"]}
        for r in records
    ]

    if dry_run:
        log.info("--dry-run — printing 3 sample records, NOT upserting")
        for r in records[:3]:
            log.info("  %s", json.dumps(r["log_preview"], ensure_ascii=False))
            md = r["metadata"]
            log.info("    appearance=%s  accent=%s  small_thing=%s",
                     md["appearance_descriptor"], md["accent_bucket"], md["text"][:120])
        log.info("Total: %d records ready (not upserted)", len(records))
        return

    log.info("Upserting %d records to Pinecone 'cotravellers'…", len(records))
    await upsert_batch(pinecone_records)
    log.info("=== Done in %.1fs total ===", time.time() - t0)


# ── CLI ───────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # Windows' default ProactorEventLoop spams "Event loop is closed" tracebacks
    # when httpx/openai clients are GC'd after asyncio.run returns. The selector
    # loop is friendlier to HTTP libraries and we don't use subprocesses here.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = argparse.ArgumentParser(
        description="Seed Pinecone with 224 synthetic co-traveller personas. "
                    "Matrix is 16 cities × 7 age buckets × 2 genders, fixed."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="generate the personas + log them, but skip "
                             "gpt-image-1, Firebase Storage upload, and "
                             "Pinecone upsert. Useful for iterating on LLM-A.")
    parser.add_argument("--purge", action="store_true",
                        help="delete the entire cotravellers namespace before "
                             "seeding. Mutually exclusive with --resume.")
    parser.add_argument("--resume", action="store_true",
                        help="skip slots whose profile_id is already present "
                             "in Pinecone (useful after a crashed run).")
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, do_purge=args.purge, do_resume=args.resume))
