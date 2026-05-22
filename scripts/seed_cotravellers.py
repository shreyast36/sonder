"""
Seed Pinecone with rich synthetic co-traveller personas.

    python -m scripts.seed_cotravellers --count 50
    python -m scripts.seed_cotravellers --count 50 --dry-run
    python -m scripts.seed_cotravellers --purge          # delete all existing seeds, then seed

Pipeline (everything LLM-driven — no randomuser.me, no stock photos):

  1. Build a diversity matrix from EMOTIONAL_SIGNATURE_TAXONOMY × age brackets
     × locations × travel intent. Each persona's slot in the matrix becomes its
     stable id (sha256-based) so re-runs overwrite the same record.
  2. The LARGE LLM writes the persona JSON end-to-end — name, age, city,
     preferred destination, archetype, interests, pace/budget/style, all four
     persona radio answers (social_role / trip_feeling / friction_response /
     ideal_atmosphere), the gold small_thing free text, a recent-trip memory
     ('voice anchor' for chat grounding), and 1-2 quirks.
  3. gpt-image-1 paints a stylised portrait grounded in the persona's
     preferred destination + archetype + quirks — saved locally under
     seed_assets/cotraveller_avatars/{profile_id}.png. avatar_url is the
     relative path; point your CDN at that directory in deploys.
  4. A stable voice_id is assigned from a deterministic hash of profile_id
     against the OpenAI TTS voice whitelist — same persona always gets the
     same voice so the chat playback feels consistent across sessions.
  5. Each persona is piped through the same emotional-signature inferrer real
     users hit (mushahid.persona.emotional_signature) so synthetic profiles
     land with symmetric compatibility_signals (top_push, top_interests,
     emotional_signature, emotional_tone).
  6. Persona text built from the rich fields (not just dimensions) gets
     embedded via the same `embed_batch` real users use and upserted to the
     'cotravellers' Pinecone namespace.

Every record carries `is_seed: True` so the matcher / frontend can disclose
"Sonder Curated" when needed.
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
from pathlib import Path

from openai import AsyncOpenAI

from ali.routing.engine import route_request
from ali.vector.embeddings import embed_batch
from jahnvi.data.classify_emotions import classify_emotions
from jahnvi.data.dimensions import PUSH_DIMENSIONS, PULL_DIMENSIONS
from jahnvi.schemas.enums import PacePreference, BudgetStyle, TravelStyle
from mushahid.persona.emotional_signature import infer_emotional_signature
from mushahid.persona.taxonomy import (
    EMOTIONAL_SIGNATURE_TAXONOMY, PERSONA_QUESTION_CATALOG,
)
from shared.config import OPENAI_API_KEY
from shreyas.retrieval.client import get_pinecone_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("seed_cotravellers")

PUSH_IDS = list(PUSH_DIMENSIONS.keys())
PULL_IDS = list(PULL_DIMENSIONS.keys())
SIGNATURE_IDS = list(EMOTIONAL_SIGNATURE_TAXONOMY.keys())

# OpenAI's six stock voices — deterministically assigned per persona. Pick
# whichever matches the persona's tone; the seed script just picks by hash.
OPENAI_TTS_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

# Locations the seed covers — wide cultural range so synthetic profiles don't
# all read like one neighborhood. Each is "City, Country" so the LLM can use
# both when writing the portrait prompt and the recent-trip memory.
SEED_LOCATIONS = [
    "Lisbon, Portugal", "Mexico City, Mexico", "Brooklyn, USA",
    "Berlin, Germany", "Bangkok, Thailand", "Buenos Aires, Argentina",
    "Cape Town, South Africa", "Edinburgh, Scotland", "Marrakech, Morocco",
    "Kyoto, Japan", "Reykjavik, Iceland", "Tel Aviv, Israel",
    "Melbourne, Australia", "Montreal, Canada", "Seoul, South Korea",
    "Mumbai, India", "Stockholm, Sweden", "Hanoi, Vietnam",
    "Athens, Greece", "Bogota, Colombia",
]

# Allowed PPM answer-option keys (must match TripPreferences.jsx).
PERSONA_OPTION_KEYS = {
    "social_role":       ["place_finder", "social_bridge", "day_anchor", "pace_reader"],
    "trip_feeling":      ["brain_louder", "disappeared", "story_collector", "exhaled"],
    "friction_response": ["regroup", "pivot", "fix_fast", "mask"],
    "ideal_atmosphere":  ["loud_anonymous", "quiet_attentive", "lively_chaos", "slow_sunlit"],
}

AVATAR_DIR        = Path("seed_assets") / "cotraveller_avatars"
AVATAR_URL_PREFIX = "/seed_assets/cotraveller_avatars"

LLM_CONCURRENCY    = 4
IMAGE_CONCURRENCY  = 4
EMBED_BATCH_SIZE   = 100
UPSERT_BATCH_SIZE  = 100

_openai_client: AsyncOpenAI | None = None


def _openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required for gpt-image-1 portrait generation")
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


# ── Diversity matrix ──────────────────────────────────────────────────────────

def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return f"ct_{digest[:20]}"


def build_diversity_matrix(count: int) -> list[dict]:
    """Generate `count` matrix slots that cover the taxonomy × age × location
    space evenly. The slot itself is the input to the LLM persona prompt and
    the seed for the stable profile_id."""
    rng = random.Random(0xC0FFEE)  # stable across re-runs
    age_brackets = [(22, 28), (29, 36), (37, 45), (46, 60)]

    slots: list[dict] = []
    i = 0
    while len(slots) < count:
        signature = SIGNATURE_IDS[i % len(SIGNATURE_IDS)]
        age_lo, age_hi = age_brackets[(i // len(SIGNATURE_IDS)) % len(age_brackets)]
        location = SEED_LOCATIONS[i % len(SEED_LOCATIONS)]
        pid_seed = f"{signature}|{age_lo}-{age_hi}|{location}|{i}"
        slots.append({
            "profile_id":         _stable_id(pid_seed),
            "target_signature":   signature,
            "age_lo":             age_lo,
            "age_hi":             age_hi,
            "location":           location,
            "rng_seed":           rng.randint(0, 2**32 - 1),
        })
        i += 1
    return slots


# ── LLM persona generation ───────────────────────────────────────────────────

_PERSONA_SYSTEM = """
You design a fictional but emotionally specific traveller for a travel-match
app. The goal is a character who feels real on a profile card — not an
archetype, not a marketing blurb, not a personality test result.

The user gives you a target emotional signature, age range, and home city.
You return ONE JSON object matching the schema below — nothing else.

Rules:
- Specific over abstract. "Eats cold dumplings for breakfast" beats "loves food".
- Contradictions are good. Real people have them.
- Pick exactly one option key for each of social_role / trip_feeling /
  friction_response / ideal_atmosphere from the ALLOWED OPTIONS provided.
  Pick the option that best fits the target_signature, but vary your
  picks across the four fields so the persona isn't on-the-nose.
- small_thing is gold — one sentence, first-person, oddly specific, the
  kind of detail nobody invents for a survey ("the way the espresso
  machine at my corner cafe sighs when it warms up").
- voice_anchor is a 1-2 sentence first-person recent-trip memory the
  chat LLM will use to ground replies. Anchor it in a real place + a
  sensory detail.
- quirks: 1-2 short third-person quirks ("can't function without
  morning coffee", "always ends up in markets", "allergic to crowded
  beaches").
- Names should match the persona's home city plausibly (mix nationalities).

Output ONLY this JSON object — no preface, no markdown fences:

{
  "display_name": "...",
  "age": 27,
  "location": "City, Country",
  "preferred_destination": "City, Country — somewhere they'd actually go",
  "archetype": "3-4 word evocative label, title case, no period",
  "interests": ["3-5 specific lowercase tags"],
  "pace": "relaxed | moderate | packed",
  "budget_style": "budget | mid_range | luxury",
  "travel_style": "solo | couple | family | friends",
  "persona_answers": {
    "social_role":       "one of the allowed keys",
    "trip_feeling":      "one of the allowed keys",
    "friction_response": "one of the allowed keys",
    "ideal_atmosphere":  "one of the allowed keys",
    "small_thing":       "one sentence, oddly specific, first-person"
  },
  "voice_anchor": "1-2 sentence first-person recent-trip memory",
  "quirks": ["short third-person quirk", "another short quirk"]
}
""".strip()


def _persona_prompt(slot: dict) -> str:
    return (
        f"TARGET EMOTIONAL SIGNATURE: {slot['target_signature']} — "
        f"{EMOTIONAL_SIGNATURE_TAXONOMY[slot['target_signature']]}\n"
        f"AGE RANGE: {slot['age_lo']}-{slot['age_hi']}\n"
        f"HOME CITY: {slot['location']}\n"
        "\n"
        f"ALLOWED OPTIONS for persona_answers:\n"
        f"  social_role:       {PERSONA_OPTION_KEYS['social_role']}\n"
        f"  trip_feeling:      {PERSONA_OPTION_KEYS['trip_feeling']}\n"
        f"  friction_response: {PERSONA_OPTION_KEYS['friction_response']}\n"
        f"  ideal_atmosphere:  {PERSONA_OPTION_KEYS['ideal_atmosphere']}\n"
        "\n"
        "Return the JSON persona object."
    )


_JSON_OBJ_RE = re.compile(r"\{[\s\S]+\}", re.DOTALL)


def _parse_persona_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_OBJ_RE.search(raw)
        if not m:
            raise
        return json.loads(m.group(0))


def _coerce_persona(obj: dict, slot: dict) -> dict:
    """Validate enums + clamp to allowed PPM keys. LLM occasionally drifts —
    fall back to the slot defaults rather than crashing the seed."""
    age = int(obj.get("age") or random.Random(slot["rng_seed"]).randint(slot["age_lo"], slot["age_hi"]))
    age = max(slot["age_lo"], min(slot["age_hi"], age))

    def _enum(value: str, choices: list[str], default: str) -> str:
        v = (value or "").strip().lower()
        return v if v in choices else default

    pace   = _enum(obj.get("pace"),         [p.value for p in PacePreference],  "moderate")
    budget = _enum(obj.get("budget_style"), [b.value for b in BudgetStyle],     "mid_range")
    style  = _enum(obj.get("travel_style"), [t.value for t in TravelStyle],     "solo")

    pa = obj.get("persona_answers") or {}
    persona_answers = {
        "social_role":       _enum(pa.get("social_role"),       PERSONA_OPTION_KEYS["social_role"],       "place_finder"),
        "trip_feeling":      _enum(pa.get("trip_feeling"),      PERSONA_OPTION_KEYS["trip_feeling"],      "story_collector"),
        "friction_response": _enum(pa.get("friction_response"), PERSONA_OPTION_KEYS["friction_response"], "pivot"),
        "ideal_atmosphere":  _enum(pa.get("ideal_atmosphere"),  PERSONA_OPTION_KEYS["ideal_atmosphere"],  "lively_chaos"),
        "small_thing":       str(pa.get("small_thing") or "").strip(),
    }

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
        "location":              str(obj.get("location") or slot["location"]).strip(),
        "preferred_destination": str(obj.get("preferred_destination") or "").strip(),
        "archetype":             str(obj.get("archetype") or "").strip() or "Traveller",
        "interests":             interests,
        "pace":                  pace,
        "budget_style":          budget,
        "travel_style":          style,
        "persona_answers":       persona_answers,
        "voice_anchor":          str(obj.get("voice_anchor") or "").strip(),
        "quirks":                quirks,
    }


async def generate_persona(slot: dict, sem: asyncio.Semaphore) -> dict | None:
    """Hit the LARGE tier with the diversity slot, parse + coerce, return the
    persona dict. None on parse failure after retries."""
    async with sem:
        for attempt in range(3):
            try:
                raw = await route_request("complex_refinement", _persona_prompt(slot), _PERSONA_SYSTEM)
                return _coerce_persona(_parse_persona_json(raw), slot)
            except Exception as e:
                log.warning("  persona LLM attempt %d failed (%s): %s", attempt + 1, slot["target_signature"], e)
                if attempt < 2:
                    await asyncio.sleep(2.0 + random.uniform(0, 1.5))
    return None


# ── gpt-image-1 portrait ─────────────────────────────────────────────────────

def _portrait_prompt(persona: dict) -> str:
    dest = persona.get("preferred_destination") or persona["location"]
    archetype = persona["archetype"].lower()
    quirks = "; ".join(persona["quirks"][:1]) or ""
    return (
        f"Stylised cinematic portrait of a {persona['age']}-year-old traveller "
        f"in {dest}. They are a {archetype}. {quirks}. "
        "Soft natural light, painterly texture, slightly cinematic, candid "
        "framing — not photoreal, not a stock photo, not a magazine cover. "
        "The image should clearly read as illustrated/rendered rather than "
        "photographed. Focus on atmosphere of the destination behind them — "
        "architecture, light quality, weather of the place — not on the face "
        "as a portrait subject. Warm tones, mid-distance composition."
    )


async def generate_portrait(persona: dict, profile_id: str, sem: asyncio.Semaphore) -> str | None:
    """Call gpt-image-1, save the PNG under seed_assets/, return the relative
    URL. Returns None on failure — caller falls back to initials chip."""
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    out_path = AVATAR_DIR / f"{profile_id}.png"
    if out_path.exists():
        return f"{AVATAR_URL_PREFIX}/{profile_id}.png"
    async with sem:
        for attempt in range(2):
            try:
                resp = await _openai().images.generate(
                    model="gpt-image-1",
                    prompt=_portrait_prompt(persona),
                    size="1024x1024",
                    quality="medium",
                    n=1,
                )
                b64 = resp.data[0].b64_json
                if not b64:
                    raise ValueError("empty b64_json in image response")
                out_path.write_bytes(base64.b64decode(b64))
                return f"{AVATAR_URL_PREFIX}/{profile_id}.png"
            except Exception as e:
                log.warning("  portrait attempt %d failed for %s: %s", attempt + 1, profile_id, e)
                if attempt < 1:
                    await asyncio.sleep(3.0)
    return None


# ── Voice id assignment ──────────────────────────────────────────────────────

def assign_voice_id(profile_id: str) -> str:
    """Stable deterministic pick from the OpenAI TTS whitelist — same persona
    always gets the same voice so chat playback feels consistent."""
    h = int(hashlib.sha256(profile_id.encode()).hexdigest()[:8], 16)
    return OPENAI_TTS_VOICES[h % len(OPENAI_TTS_VOICES)]


# ── Embedding text — rich + uses the same field set real users carry ─────────

def build_seed_persona_text(persona: dict, signature: str, tone: str) -> str:
    pa = persona["persona_answers"]
    parts = [
        persona["archetype"],
        ", ".join(persona["interests"]),
        f"pace: {persona['pace']}, budget: {persona['budget_style']}, style: {persona['travel_style']}",
        f"social role: {pa['social_role']}",
        f"trip feeling: {pa['trip_feeling']}",
        f"friction response: {pa['friction_response']}",
        f"ideal atmosphere: {pa['ideal_atmosphere']}",
        pa["small_thing"],
        persona["voice_anchor"],
        ". ".join(persona["quirks"]),
        f"emotional signature: {signature}",
        f"tone: {tone}",
    ]
    return ". ".join(p.strip() for p in parts if p and p.strip())


# ── Purge ───────────────────────────────────────────────────────────────────

async def purge_seeds() -> None:
    """Delete every vector in the cotravellers namespace. One-shot. Use when
    the schema changes or you want to regenerate the whole pool."""
    log.info("Purging Pinecone 'cotravellers' namespace…")
    index = await get_pinecone_index()
    try:
        await asyncio.to_thread(lambda: index.delete(delete_all=True, namespace="cotravellers"))
        log.info("  purge complete")
    except Exception as e:
        log.warning("  purge failed (namespace may not exist yet): %s", e)


# ── Upsert ──────────────────────────────────────────────────────────────────

async def upsert(records: list[dict]) -> None:
    if not records:
        return
    index = await get_pinecone_index()
    total = len(records)
    for i in range(0, total, UPSERT_BATCH_SIZE):
        chunk = records[i:i + UPSERT_BATCH_SIZE]
        await asyncio.to_thread(lambda c=chunk: index.upsert(namespace="cotravellers", vectors=c))
        log.info("  upserted %d / %d", min(i + UPSERT_BATCH_SIZE, total), total)


# ── Main ────────────────────────────────────────────────────────────────────

async def main(count: int, dry_run: bool, purge: bool) -> None:
    t0 = time.time()
    if purge and not dry_run:
        await purge_seeds()

    slots = build_diversity_matrix(count)
    log.info("Built diversity matrix: %d slots across %d signatures × %d locations",
             len(slots), len(SIGNATURE_IDS), len(SEED_LOCATIONS))

    # 1. Persona JSON via LARGE LLM, in parallel with bounded concurrency.
    log.info("Generating %d personas via LARGE LLM (concurrency=%d)…", len(slots), LLM_CONCURRENCY)
    t1 = time.time()
    llm_sem = asyncio.Semaphore(LLM_CONCURRENCY)
    personas_raw = await asyncio.gather(*[generate_persona(s, llm_sem) for s in slots])
    personas: list[tuple[dict, dict]] = [
        (slot, p) for slot, p in zip(slots, personas_raw) if p is not None
    ]
    log.info("  personas done in %.1fs (%d/%d ok)", time.time() - t1, len(personas), len(slots))

    # 2. Portraits via gpt-image-1, in parallel.
    log.info("Painting %d portraits via gpt-image-1 (concurrency=%d)…",
             len(personas), IMAGE_CONCURRENCY)
    t2 = time.time()
    img_sem = asyncio.Semaphore(IMAGE_CONCURRENCY)
    portraits = await asyncio.gather(*[
        generate_portrait(p, slot["profile_id"], img_sem) for slot, p in personas
    ])
    log.info("  portraits done in %.1fs (%d painted)",
             time.time() - t2, sum(1 for u in portraits if u))

    # 3. Emotional-signature inference per persona — reuses the user-side
    #    classifier + LLM inferrer so synthetic profiles end up with the same
    #    compatibility_signals shape real users have.
    log.info("Inferring emotional signatures via persona inferrer…")
    t3 = time.time()

    async def _infer(persona: dict) -> dict:
        pa = persona["persona_answers"]
        signature_inputs = {
            "social_role":       pa["social_role"],
            "trip_feeling":      pa["trip_feeling"],
            "friction_response": pa["friction_response"],
            "ideal_atmosphere":  pa["ideal_atmosphere"],
            "small_thing":       pa["small_thing"],
            "voice_anchor":      persona["voice_anchor"],
            "quirks":            ", ".join(persona["quirks"]),
        }
        # Classify emotions once, reuse for the signature inferrer.
        classifier_text = ". ".join(filter(None, [
            pa["small_thing"], persona["voice_anchor"], " ".join(persona["quirks"]),
        ]))
        goemotions = await classify_emotions(classifier_text, top_k=5) if classifier_text else []
        signature = await infer_emotional_signature(
            signature_inputs,
            question_catalog=PERSONA_QUESTION_CATALOG,
            signature_taxonomy=EMOTIONAL_SIGNATURE_TAXONOMY,
            precomputed_goemotions=goemotions,
        )
        # Deterministic-ish PPM picks from the LLM persona's interests +
        # the inferred signature. The matcher needs top_push / top_interests
        # in compat signals; the LLM persona didn't pick those directly, so
        # use the signature taxonomy + an RNG seeded on profile_id.
        rng = random.Random(int(hashlib.sha256(persona["display_name"].encode()).hexdigest()[:8], 16))
        return {
            **signature.to_compatibility_signals(),
            "top_push":      rng.sample(PUSH_IDS, 2),
            "top_interests": rng.sample(PULL_IDS, 3),
            "goemotions":    [label for label, _ in goemotions],
        }

    compat_results = await asyncio.gather(*[_infer(p) for _, p in personas])
    log.info("  signatures done in %.1fs", time.time() - t3)

    # 4. Embedding text + embed.
    enriched: list[dict] = []
    texts: list[str] = []
    for (slot, persona), avatar_url, compat in zip(personas, portraits, compat_results):
        signature = compat.get("emotional_signature", "")
        tone      = compat.get("emotional_tone", "")
        text = build_seed_persona_text(persona, signature, tone)
        enriched.append({
            "slot":       slot,
            "persona":    persona,
            "avatar_url": avatar_url,
            "compat":     compat,
            "text":       text,
            "voice_id":   assign_voice_id(slot["profile_id"]),
        })
        texts.append(text)

    log.info("Embedding %d persona texts…", len(texts))
    t4 = time.time()
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        embeddings.extend(await embed_batch(texts[i:i + EMBED_BATCH_SIZE]))
        log.info("  embedded %d / %d", min(i + EMBED_BATCH_SIZE, len(texts)), len(texts))
    log.info("  embeds done in %.1fs", time.time() - t4)

    # 5. Pinecone records. Nested dicts (persona_answers, compatibility_signals)
    #    are JSON-encoded because Pinecone metadata only accepts primitives +
    #    string lists; search.py decodes them on read.
    records = []
    for rec, emb in zip(enriched, embeddings):
        slot      = rec["slot"]
        persona   = rec["persona"]
        compat    = rec["compat"]
        records.append({
            "id":     slot["profile_id"],
            "values": emb,
            "metadata": {
                "profile_id":            slot["profile_id"],
                "display_name":          persona["display_name"],
                "age":                   persona["age"],
                "location":              persona["location"],
                "preferred_destination": persona["preferred_destination"],
                "archetype":             persona["archetype"],
                "interests":             persona["interests"],
                "pace":                  persona["pace"],
                "budget_style":          persona["budget_style"],
                "travel_style":          persona["travel_style"],
                "avatar_url":            rec["avatar_url"] or "",
                "voice_id":              rec["voice_id"],
                "voice_anchor":          persona["voice_anchor"],
                "quirks":                persona["quirks"],
                "persona_answers_json":  json.dumps(persona["persona_answers"], ensure_ascii=False),
                "top_push":              compat.get("top_push", []),
                "top_interests":         compat.get("top_interests", []),
                "compatibility_signals_json": json.dumps(compat, ensure_ascii=False),
                "text":                  rec["text"][:1500],
                "is_seed":               True,
            },
        })

    if dry_run:
        log.info("--dry-run: showing 3 sample records, not upserting")
        for r in records[:3]:
            md = r["metadata"]
            log.info("  %s | %s, %d, %s | %s",
                     r["id"], md["display_name"], md["age"], md["location"], md["archetype"])
            log.info("    sig: %s | tone: %s | voice: %s | avatar: %s",
                     json.loads(md["compatibility_signals_json"]).get("emotional_signature"),
                     json.loads(md["compatibility_signals_json"]).get("emotional_tone"),
                     md["voice_id"], md["avatar_url"])
            log.info("    voice_anchor: %s", md["voice_anchor"][:120])
        log.info("Total: %d records ready (not upserted)", len(records))
        return

    log.info("Upserting %d records to Pinecone 'cotravellers'…", len(records))
    await upsert(records)
    log.info("=== Done in %.1fs total ===", time.time() - t0)


if __name__ == "__main__":
    # Windows' default ProactorEventLoop spams "Event loop is closed" tracebacks
    # when httpx/openai clients are GC'd after asyncio.run returns. The selector
    # loop is friendlier to HTTP libraries and we don't use subprocesses here.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50,
                        help="how many co-traveller personas to seed (default 50)")
    parser.add_argument("--dry-run", action="store_true",
                        help="generate everything but skip Pinecone upsert")
    parser.add_argument("--purge", action="store_true",
                        help="delete the entire cotravellers namespace before seeding")
    args = parser.parse_args()
    if args.count < 1 or args.count > 500:
        log.error("--count must be between 1 and 500 (gpt-image-1 cost guard)")
        sys.exit(1)
    asyncio.run(main(args.count, args.dry_run, args.purge))
