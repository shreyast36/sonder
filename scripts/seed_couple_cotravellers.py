"""
Seed Pinecone with synthetic COUPLE co-traveller personas. Mirrors
scripts/seed_cotravellers.py exactly — same two-stage blind-writer
architecture, same Pinecone schema (`travel_style: "couple"`), same
gpt-image-1 + ElevenLabs voice + OpenAI 1536-dim embedding pipeline.
The only differences are couple-specific:

  - LLM-A is told to write THE PAIR (display_name "Mira & Theo",
    voice_anchor in "we" voice, partner_name as a separate field,
    quirks describe the dynamic).
  - Diversity matrix is 9 cities × 2 age buckets = 18 male+female
    couples. Primary gender (the chatter — whose voice the chat
    replies read as) alternates per slot so the pool isn't all
    written from one side.
  - Portrait prompt is reframed for a candid couple snapshot
    (two people in the frame, same casual-iPhone register).
  - travel_style is hardcoded to "couple" — couple personas only
    surface for couple users via the cotraveller.py hard style filter.

Pipeline per slot:
    LLM-A blind couple writer
        → real persona-infer LLM (tags + descriptor/paragraph/bullets)
        → emotional_signature inference (parallel)
        → gpt-image-1 portrait (couple snapshot)
        → Firebase Storage upload (avatar)
        → voice_id assignment for the chatting persona
        → embed text via OpenAI 1536-dim
        → upsert to Pinecone `cotravellers` namespace with is_seed: True

CLI:
    python -m scripts.seed_couple_cotravellers
    python -m scripts.seed_couple_cotravellers --dry-run
    python -m scripts.seed_couple_cotravellers --resume
    python -m scripts.seed_couple_cotravellers --purge

Cost estimate (all 18, no --dry-run):
    LLM-A persona      18 × ~$0.005 = ~$0.10
    Real persona-infer 18 × ~$0.005 = ~$0.10
    Emotional sig      18 × ~$0.003 = ~$0.05
    gpt-image-1 medium 18 × $0.042  = ~$0.76
    OpenAI embeds      18 × ~negligible
                                       ───────
                       Total          ~$1
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

from ali.routing.engine import route_request
from ali.vector.embeddings import embed_batch
from jahnvi.data.classify_emotions import classify_emotions
from jahnvi.data.persona_labels import label_for
from jahnvi.data.voice_catalog import voice_for, accent_for_appearance
from jahnvi.schemas.enums import PacePreference, BudgetStyle
from mushahid.persona.emotional_signature import infer_emotional_signature
from mushahid.persona.taxonomy import (
    EMOTIONAL_SIGNATURE_TAXONOMY, PERSONA_QUESTION_CATALOG,
)
from mushahid.realtime.storage import upload_bytes
from shared.config import OPENAI_API_KEY
from shared.schemas import TripConstraints, PersonaQuestionAnswers
from shreyas.ranking.salience import compute_answer_salience
from shreyas.retrieval.client import get_pinecone_index

# Reuse the singles script's helpers verbatim — same blind-writer
# parsing, same persona-infer plumbing, same image template, same
# Pinecone ops. This is the whole point of the "same approach" ask.
from scripts.seed_cotravellers import (
    _parse_json_object,
    persona_infer,
    _PORTRAIT_PROMPT_TEMPLATE,
    purge_namespace,
    existing_profile_ids,
    upsert_batch,
    UPSERT_BATCH_SIZE,
    LLM_A_CONCURRENCY,
    PERSONA_INFER_CONCURRENCY,
    IMAGE_CONCURRENCY,
    PERSONA_OPTION_KEYS,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("seed_couple_cotravellers")


# ── Locked spec constants (couple cohort) ─────────────────────────────────


# 6-city subset of the singles pool, chosen for regional spread. Matrix
# is 6 cities × 3 age buckets = 18 couples — the user-requested 15-20.
CITIES: list[str] = [
    "New York, USA",
    "Mexico City, Mexico",
    "London, United Kingdom",
    "Berlin, Germany",
    "Mumbai, India",
    "Tokyo, Japan",
]

# Same age buckets as the singles seed — 20-50 in 10-year steps. Matches
# the portrait prompt's age rule and keeps the two pools tonally aligned.
AGE_BUCKETS: list[tuple[int, int]] = [
    (20, 30), (30, 40), (40, 50),
]

# All couples are male + female. Primary gender (the chatter) cycles
# per slot so the 18-couple pool isn't all written from one side.
PRIMARY_GENDERS: list[str] = ["female", "male"]


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
    # 'ctcp' prefix = "co-traveller couple" — separate ID-space from
    # singles so a re-run of either script never collides.
    return f"ctcp_{hashlib.sha256('|'.join(parts).encode()).hexdigest()[:20]}"


def build_diversity_matrix() -> list[dict]:
    """9 cities × 2 age buckets = 18 male+female couple slots. Primary
    gender (the chatter, the persona whose voice the chat replies read
    as) alternates across the pool so we don't end up with 18 voices
    written from the same side."""
    slots: list[dict] = []
    i = 0
    for city in CITIES:
        for age_lo, age_hi in AGE_BUCKETS:
            primary_gender = PRIMARY_GENDERS[i % len(PRIMARY_GENDERS)]
            slots.append({
                "profile_id":     _stable_id(city, f"{age_lo}-{age_hi}", "hetero", str(i)),
                "city":           city,
                "age_lo":         age_lo,
                "age_hi":         age_hi,
                "primary_gender": primary_gender,
                # Mirrors the singles slot shape so reused helpers (portrait
                # prompt, voice_for) that read `gender` still work.
                "gender":         primary_gender,
                "rng_seed":       int(hashlib.sha256(f"{city}|{i}".encode()).hexdigest()[:8], 16),
            })
            i += 1
    return slots


# ── Stage 1 — LLM-A (blind couple writer) ─────────────────────────────────


# Same CRITICAL rule as the singles script: never name the matching
# vocabulary. Couple-specific framing layered on top so the model
# writes for the PAIR, not for a solo who happens to have a partner.
# Mirrors scripts/seed_cotravellers.py::_LLM_A_SYSTEM verbatim in
# structure (Rules block, visual_cue examples + ban list, NEVER block,
# JSON output schema) with couple-specific framing layered in. The
# blindness contract is identical — never mention PUSH/PULL, never
# name the emotional_signature taxonomy, never reference matching /
# scoring / dimensions.
_LLM_A_SYSTEM = """
You design a fictional but emotionally specific COUPLE for a travel app.
The goal is a pair who feels real on a profile card — not an archetype,
not a marketing blurb, not a personality test result. Two people, one
man and one woman, who have travelled together enough to have a rhythm.

The user gives you a home city, age range, and which of the two is the
"protagonist" (the one whose voice the chat replies will read as). You
return ONE JSON object matching the schema below.

Rules:
- Specific over abstract. "She always orders the spicy thing and
  regrets it; he finishes whatever she leaves" beats "they love food".
- Contradictions are good. Real couples have them.
- Pick exactly one option key for each of social_role / trip_feeling /
  friction_response / ideal_atmosphere from the ALLOWED OPTIONS — these
  reflect the couple's SHARED answer (the one they'd give together). If
  they genuinely diverge, pick the protagonist's and note the partner's
  lean in a quirk. Vary your picks across the four fields so the persona
  doesn't read as on-the-nose.
- display_name MUST be "X & Y" — the two first names, ampersand
  ("Mira & Theo"). protagonist_name is the first name of the chatter;
  partner_name is the first name of the other.
- small_thing is gold — the PROTAGONIST'S first-person ("I" not "we"),
  one sentence, oddly specific ("the way our cat headbutts the front
  door when we get home from a trip").
- voice_anchor is in WE voice — a 1-2 sentence shared recent-trip
  memory the chat LLM will use to ground replies. Anchor it in a real
  place + a sensory detail ("we got lost trying to find this tiny
  dumpling place in Shanghai and ended up at a karaoke bar at midnight").
- quirks: 1-2 short third-person quirks about the COUPLE'S DYNAMIC, not
  one person ("she plans, he wings it", "they always order one of
  everything to share", "he reads at breakfast while she over-
  caffeinates and talks too much").
- visual_cue: a short phrase the image generator will use for the
  candid-snapshot setting. The image is a casual smartphone photo of
  TWO PEOPLE, NOT a posed couples-shoot, NOT an engagement photo.
  Cue must be a mundane everyday moment where the pair happens to be
  near a camera.
  EXAMPLES OF THE RIGHT REGISTER (do NOT pick these verbatim — invent
  a different mundane shared moment tailored to THIS specific couple's
  city, age, and quirks):
        "waiting on a bench at a bus stop, one looking at phone",
        "leaning against a kitchen counter mid-conversation",
        "standing in line at a bakery, slightly apart",
        "side by side on a couch, half-watching the same screen",
        "walking down an ordinary residential street, mid-step",
        "sitting on apartment steps, one tying a shoelace",
        "in a crowded transit station, slightly out of sync".
  Treat the examples as showing the *register* (mundane, candid,
  unposed, no props), not the content. Each couple should get its own
  freshly-invented ordinary moment — bus stops, laundromats, pharmacy
  queues, apartment stairwells, parking lots, supermarket aisles,
  sidewalk corners, etc. Vary the setting, the body positions, what
  they're each looking at, and whether they're interacting with each
  other or doing parallel things.
  BAD (avoid all of these — they break the candid feel):
        "golden hour", "serene morning light", "dappled sunlight",
        "under a cherry blossom tree", "on a temple step", "reading a
        worn paperback together", "rooftop bar", "scenic overlook",
        "looking off into the distance", "holding hands on the beach",
        "kissing in front of the eiffel tower", "contemplative",
        any cafe, any holding of a book/map/journal/camera/postcard,
        any iconic landmark, any engagement / wedding / anniversary
        framing.
  No props in their hands except possibly an ordinary phone. The cue
  should sound like something a friend would say describing a candid
  photo of the two of them, not a travel ad.
- appearance_descriptor: 1-3 words EACH for the two of them, separated
  by ' + ' in PROTAGONIST + PARTNER order. Example: "Indian + Brazilian",
  "Korean + Korean", "Black + East Asian". Treat this as appearance
  information for image generation, not demographic classification.
- Names should match the home city plausibly (mix of ethnicities is
  fine — most cosmopolitan cities have residents of many backgrounds).

NEVER mention or refer to:
- "push" or "pull" motivations
- emotional signatures / archetypes by name
- travel matching, tags, scoring, dimensions
The couple is just a couple. Nothing else.

Output ONLY this JSON object — no preface, no markdown fences:

{
  "display_name": "Name & Name",
  "protagonist_name": "...",
  "partner_name": "...",
  "age": 28,
  "partner_age": 30,
  "appearance_descriptor": "X + Y",
  "preferred_destination": "City, Country — somewhere they'd actually go together",
  "archetype": "3-4 word evocative label for the COUPLE, title case, no period",
  "interests": ["3-5 specific lowercase tags they both enjoy"],
  "pace": "relaxed | moderate | packed",
  "budget_style": "budget | mid_range | luxury",
  "social_role":       "one of the allowed keys",
  "trip_feeling":      "one of the allowed keys",
  "friction_response": "one of the allowed keys",
  "ideal_atmosphere":  "one of the allowed keys",
  "small_thing":       "one sentence, oddly specific, FIRST-PERSON (protagonist)",
  "voice_anchor":      "1-2 sentence WE-voice recent shared-trip memory",
  "quirks":            ["short couple-dynamic quirk", "another couple-dynamic quirk"],
  "visual_cue":        "short phrase describing the candid couple snapshot setting"
}
""".strip()


def _llm_a_prompt(slot: dict) -> str:
    partner_gender = "male" if slot["primary_gender"] == "female" else "female"
    return (
        f"HOME CITY: {slot['city']}\n"
        f"AGE RANGE: {slot['age_lo']}-{slot['age_hi']} (both partners roughly within)\n"
        f"PROTAGONIST GENDER (the chatter): {slot['primary_gender']}\n"
        f"PARTNER GENDER: {partner_gender}\n"
        "\n"
        f"ALLOWED OPTIONS for chip selections:\n"
        f"  social_role:       {PERSONA_OPTION_KEYS['social_role']}\n"
        f"  trip_feeling:      {PERSONA_OPTION_KEYS['trip_feeling']}\n"
        f"  friction_response: {PERSONA_OPTION_KEYS['friction_response']}\n"
        f"  ideal_atmosphere:  {PERSONA_OPTION_KEYS['ideal_atmosphere']}\n"
        "\n"
        "Return the JSON couple object."
    )


def _coerce_llm_a(obj: dict, slot: dict) -> dict:
    """Couple-aware validation. Hard-locks travel_style to 'couple' so
    the cotraveller route's hard style filter surfaces these only for
    couple viewers."""
    rng = random.Random(slot["rng_seed"])
    age = int(obj.get("age") or rng.randint(slot["age_lo"], slot["age_hi"]))
    age = max(slot["age_lo"], min(slot["age_hi"], age))
    partner_age = int(obj.get("partner_age") or rng.randint(slot["age_lo"], slot["age_hi"]))
    partner_age = max(slot["age_lo"], min(slot["age_hi"], partner_age))

    def _enum(value, choices, default):
        v = (value or "").strip().lower() if isinstance(value, str) else ""
        return v if v in choices else default

    pace   = _enum(obj.get("pace"),         [p.value for p in PacePreference], "moderate")
    budget = _enum(obj.get("budget_style"), [b.value for b in BudgetStyle],    "mid_range")

    interests = obj.get("interests") or []
    if not isinstance(interests, list):
        interests = [str(interests)]
    interests = [str(i).strip().lower() for i in interests if str(i).strip()][:5]

    quirks = obj.get("quirks") or []
    if not isinstance(quirks, list):
        quirks = [str(quirks)]
    quirks = [str(q).strip() for q in quirks if str(q).strip()][:2]

    display_name = str(obj.get("display_name") or "").strip() or "Anonymous & Anonymous"
    # Defensive: ensure '&' / 'and' shape so the frontend / chat layer
    # can render the pair consistently.
    if "&" not in display_name and " and " not in display_name.lower():
        protagonist = str(obj.get("protagonist_name") or display_name).strip().split()[0]
        partner = str(obj.get("partner_name") or "Partner").strip().split()[0]
        display_name = f"{protagonist} & {partner}"

    return {
        "display_name":          display_name,
        "protagonist_name":      str(obj.get("protagonist_name") or display_name.split("&")[0]).strip(),
        "partner_name":          str(obj.get("partner_name") or display_name.split("&")[-1]).strip(),
        "age":                   age,
        "partner_age":           partner_age,
        "appearance_descriptor": str(obj.get("appearance_descriptor") or "").strip(),
        "preferred_destination": str(obj.get("preferred_destination") or "").strip(),
        "archetype":             str(obj.get("archetype") or "").strip() or "Travel Pair",
        "interests":             interests,
        "pace":                  pace,
        "budget_style":          budget,
        "travel_style":          "couple",   # HARD-LOCKED for this script
        "social_role":           _enum(obj.get("social_role"),       PERSONA_OPTION_KEYS["social_role"],       "place_finder"),
        "trip_feeling":          _enum(obj.get("trip_feeling"),      PERSONA_OPTION_KEYS["trip_feeling"],      "story_collector"),
        "friction_response":     _enum(obj.get("friction_response"), PERSONA_OPTION_KEYS["friction_response"], "pivot"),
        "ideal_atmosphere":      _enum(obj.get("ideal_atmosphere"),  PERSONA_OPTION_KEYS["ideal_atmosphere"],  "slow_sunlit"),
        "small_thing":           str(obj.get("small_thing") or "").strip(),
        "voice_anchor":          str(obj.get("voice_anchor") or "").strip(),
        "quirks":                quirks,
        "visual_cue":            str(obj.get("visual_cue") or "").strip(),
        # Slot-derived fields the downstream stages need:
    }


async def llm_a_generate(slot: dict, sem: asyncio.Semaphore) -> dict | None:
    """Run LLM-A blind to the tag vocabulary. Same retry shape as the
    singles seeder."""
    async with sem:
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                raw = await route_request("complex_refinement", _llm_a_prompt(slot), _LLM_A_SYSTEM)
                return _coerce_llm_a(_parse_json_object(raw), slot)
            except Exception as e:
                last_err = e
                if attempt < 2:
                    log.debug("  LLM-A attempt %d retrying for slot %s: %s",
                              attempt + 1, slot["profile_id"][-6:], e)
                    await asyncio.sleep(2.0 + random.uniform(0, 1.5))
        log.warning("  LLM-A failed for slot %s after 3 attempts: %s",
                    slot["profile_id"][-6:], last_err)
    return None


# ── Stage 3 — Couple portrait (extends the singles template) ─────────────


_COUPLE_PORTRAIT_HEADER = """\
You are generating a casual smartphone-style profile photo for a
COUPLE — two people in the frame — on a modern social travel app.

The image MUST contain two distinct people — one man and one woman —
both visibly within the {age_lo}-{age_hi} age range, in the SAME
candid moment. Appearance reference (for both subjects):
{appearance_descriptor}.

The photo should NOT look like:
- an engagement / wedding photo
- a couples-shoot
- a posed pair portrait
- a stock-photo "happy couple"
- an Instagram travel-couple aesthetic
- two people forced to face the camera together

It SHOULD look like:
- a friend snapping a quick photo of them mid-life
- two people doing something ordinary in the same frame
- one of those photos people keep on their phone home screen
- candid, slightly imperfect, real

"""


def _portrait_prompt(persona: dict, slot: dict) -> str:
    """Stitch the couple-specific header onto the singles photo
    template. The singles template already enforces casual / candid /
    no-tourism-ad / age-rule constraints; we just lead with the
    two-people-in-the-frame instruction so the model doesn't render
    a solo by default."""
    header = _COUPLE_PORTRAIT_HEADER.format(
        age_lo=slot["age_lo"],
        age_hi=slot["age_hi"],
        appearance_descriptor=persona.get("appearance_descriptor") or "two adults",
    )
    body = _PORTRAIT_PROMPT_TEMPLATE.format(
        age=persona.get("age", 30),
        gender=slot["gender"],
        city=slot["city"],
        appearance_descriptor=persona.get("appearance_descriptor") or "two adults",
        visual_cue=persona.get("visual_cue") or "the two of them doing something ordinary",
    )
    return header + body


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
                log.warning("  portrait attempt %d failed (%s): %s",
                            attempt + 1, slot["profile_id"][-6:], e)
                if attempt < 1:
                    await asyncio.sleep(3.0)
    return None


# ── Stage 4 — Embedding text + Pinecone metadata builder ─────────────────


def build_embedding_text(persona: dict, tags: dict, signature: dict) -> str:
    """Same shape as the singles embedding text — chip labels + small_thing
    + voice_anchor + quirks + tags + signature — with the couple-voice
    additions (partner_name, archetype framed as 'travel pair')."""
    parts: list[str] = [
        f"couple: {persona['archetype']}",
        f"partners: {persona.get('protagonist_name', '')} and {persona.get('partner_name', '')}",
        ", ".join(persona["interests"]),
        f"pace: {persona['pace']}, budget: {persona['budget_style']}, style: couple",
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
    slot: dict, persona: dict, tags: dict, signature: dict, salience: dict,
    voice_profile: dict, avatar_url: str | None, embedding_text: str,
) -> dict:
    """Same Pinecone metadata shape as the singles seed so the same
    get_cotraveller_by_id decoder reads both. Couple-specific fields
    (partner_name, partner_age) ride along as additional metadata."""
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
        "travel_style":          "couple",
        "avatar_url":            avatar_url or "",
        "voice_anchor":          persona.get("voice_anchor", ""),
        "quirks":                persona.get("quirks", []),
        "voice_id":              voice_profile.get("voice_id") or "",
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
        # Couple-specific extras (won't be read by existing decoder but
        # available for future couple-aware UI):
        "couple_protagonist":    persona.get("protagonist_name", ""),
        "couple_partner":        persona.get("partner_name", ""),
        "couple_partner_age":    persona.get("partner_age", persona["age"]),
    }


# ── Main pipeline (mirrors process_slot in seed_cotravellers.py) ──────────


async def process_slot(
    slot: dict, *,
    dry_run: bool,
    llm_a_sem: asyncio.Semaphore,
    persona_sem: asyncio.Semaphore,
    image_sem: asyncio.Semaphore,
    local_out_dir: str | None = None,
) -> dict | None:
    pid = slot["profile_id"]

    # Stage 1: blind couple writer
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
    tags = tags_obj

    if isinstance(signature_result, Exception):
        log.warning("  slot %s — signature inference failed: %s", pid[-6:], signature_result)
        signature = {}
    else:
        signature = signature_result.to_compatibility_signals()
        signature["goemotions_top"] = [label for label, _score in goemotions]

    # Salience — same pure-function the real persona route persists.
    constraints_shell = TripConstraints(
        social_role=persona["social_role"],
        trip_feeling=persona["trip_feeling"],
        friction_response=persona["friction_response"],
        ideal_atmosphere=persona["ideal_atmosphere"],
    )
    answers_shell = PersonaQuestionAnswers(small_thing=persona.get("small_thing", ""))
    salience = compute_answer_salience(answers_shell, constraints_shell)

    # Stage 3: voice assignment — protagonist's voice only (they're the chatter).
    voice_profile = voice_for(persona.get("appearance_descriptor"), slot["primary_gender"])

    # Stage 4: gpt-image-1 couple portrait + Firebase / local destination.
    # local_out_dir takes priority over Firebase — used by the
    # --out-dir test path so we can preview portraits without
    # touching Storage or Pinecone.
    avatar_url: str | None = None
    if local_out_dir:
        png_bytes = await generate_portrait(persona, slot, image_sem)
        if png_bytes is not None:
            import os
            os.makedirs(local_out_dir, exist_ok=True)
            out_path = os.path.join(local_out_dir, f"{pid}.png")
            try:
                with open(out_path, "wb") as f:
                    f.write(png_bytes)
                avatar_url = f"file://{os.path.abspath(out_path)}"
                log.info("  slot %s — portrait saved → %s", pid[-6:], out_path)
            except Exception as e:
                log.warning("  slot %s — local save failed: %s", pid[-6:], e)
    elif not dry_run:
        png_bytes = await generate_portrait(persona, slot, image_sem)
        if png_bytes is not None:
            try:
                # New 'couples/' Firebase Storage folder, separate from
                # the singles 'cotraveller_avatars/' namespace so the
                # two pools don't share path conventions.
                avatar_url = await upload_bytes(
                    f"couples/{pid}.png",
                    png_bytes,
                    content_type="image/png",
                    make_public=True,
                )
            except Exception as e:
                log.warning("  slot %s — Firebase Storage upload failed: %s", pid[-6:], e)
                avatar_url = None
    else:
        log.info("  slot %s — DRY RUN, skipping portrait + upload", pid[-6:])

    embedding_text = build_embedding_text(persona, tags, signature)
    metadata = build_metadata(slot, persona, tags, signature, salience, voice_profile, avatar_url, embedding_text)

    return {
        "id":           pid,
        "values":       None,
        "metadata":     metadata,
        "embed_text":   embedding_text,
        "log_preview": {
            "name":         persona["display_name"],
            "city":         slot["city"],
            "ages":         f"{persona['age']} + {persona.get('partner_age', persona['age'])}",
            "archetype":    persona["archetype"],
            "signature":    signature.get("emotional_signature"),
            "voice":        voice_profile["voice_id"],
            "avatar":       bool(avatar_url),
        },
    }


async def main(
    dry_run: bool, do_purge: bool, do_resume: bool,
    limit: int | None = None, local_out_dir: str | None = None,
) -> None:
    t0 = time.time()

    if do_purge and do_resume:
        raise SystemExit("--purge and --resume are mutually exclusive")

    # Purging here would nuke the shared 'cotravellers' namespace
    # including the singles. Force --purge to be explicit about it.
    if do_purge and not dry_run:
        log.warning("--purge will delete the entire cotravellers namespace "
                    "(singles + couples). Continuing in 3s — Ctrl+C to abort.")
        await asyncio.sleep(3.0)
        await purge_namespace()

    slots = build_diversity_matrix()
    log.info("Couple diversity matrix: %d slots (%d cities × %d age buckets)",
             len(slots), len(CITIES), len(AGE_BUCKETS))

    if limit and limit > 0:
        before = len(slots)
        slots = slots[:limit]
        log.info("--limit %d: processing %d of %d slots", limit, len(slots), before)

    skip_ids: set[str] = set()
    if do_resume:
        log.info("Querying existing Pinecone slots for --resume…")
        skip_ids = await existing_profile_ids()
        before = len(slots)
        slots = [s for s in slots if s["profile_id"] not in skip_ids]
        log.info("  %d already-completed couple slots skipped → %d remaining",
                 before - len(slots), len(slots))

    if not slots:
        log.info("Nothing to do — exiting.")
        return

    llm_a_sem   = asyncio.Semaphore(LLM_A_CONCURRENCY)
    persona_sem = asyncio.Semaphore(PERSONA_INFER_CONCURRENCY)
    image_sem   = asyncio.Semaphore(IMAGE_CONCURRENCY)

    log.info("Processing %d couple slots…", len(slots))
    t1 = time.time()
    raw_records = await asyncio.gather(*[
        process_slot(s, dry_run=dry_run, llm_a_sem=llm_a_sem,
                     persona_sem=persona_sem, image_sem=image_sem,
                     local_out_dir=local_out_dir)
        for s in slots
    ])
    records = [r for r in raw_records if r is not None]
    log.info("Slot processing done in %.1fs (%d/%d ok)",
             time.time() - t1, len(records), len(slots))

    if not records:
        log.warning("Zero usable couple records produced — bailing.")
        return

    # --out-dir means "preview only": never embed, never upsert.
    if local_out_dir:
        log.info("--out-dir set → skipping embeddings + Pinecone upsert. "
                 "Portraits saved to %s", local_out_dir)
        for r in records:
            log.info("  %s", json.dumps(r["log_preview"], ensure_ascii=False))
            md = r["metadata"]
            log.info("    archetype=%s  appearance=%s  voice_anchor=%s",
                     md["archetype"], md["appearance_descriptor"],
                     (r["embed_text"][:200] + "…") if len(r["embed_text"]) > 200 else r["embed_text"])
        return

    log.info("Embedding %d couple persona texts…", len(records))
    t2 = time.time()
    texts = [r["embed_text"] for r in records]
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), 100):
        embeddings.extend(await embed_batch(texts[i:i + 100]))
        log.info("  embedded %d / %d", min(i + 100, len(texts)), len(texts))
    for rec, vec in zip(records, embeddings):
        rec["values"] = vec
    log.info("Embeds done in %.1fs", time.time() - t2)

    pinecone_records = [
        {"id": r["id"], "values": r["values"], "metadata": r["metadata"]}
        for r in records
    ]

    if dry_run:
        log.info("--dry-run — printing 3 sample couple records, NOT upserting")
        for r in records[:3]:
            log.info("  %s", json.dumps(r["log_preview"], ensure_ascii=False))
            md = r["metadata"]
            log.info("    appearance=%s  accent=%s  small_thing=%s",
                     md["appearance_descriptor"], md["accent_bucket"], md["text"][:120])
        log.info("Total: %d couple records ready (not upserted)", len(records))
        return

    log.info("Upserting %d couple records to Pinecone 'cotravellers'…", len(records))
    await upsert_batch(pinecone_records)
    log.info("=== Done in %.1fs total ===", time.time() - t0)


# ── CLI ───────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = argparse.ArgumentParser(
        description="Seed Pinecone with 18 synthetic COUPLE co-traveller "
                    "personas. Matrix is 9 cities × 2 age buckets. "
                    "Same two-stage blind-writer pipeline as the singles "
                    "seeder; travel_style hard-locked to 'couple'."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="generate the couple personas + log them, but "
                             "skip gpt-image-1, Firebase upload, and Pinecone "
                             "upsert. Useful for iterating on LLM-A.")
    parser.add_argument("--purge", action="store_true",
                        help="DANGER: deletes the ENTIRE cotravellers "
                             "namespace (singles included) before seeding. "
                             "Mutually exclusive with --resume.")
    parser.add_argument("--resume", action="store_true",
                        help="skip slots whose profile_id is already present "
                             "in Pinecone.")
    parser.add_argument("--limit", type=int, default=None,
                        help="process at most N slots (from the start of the "
                             "matrix). Useful for test runs and image previews.")
    parser.add_argument("--out-dir", type=str, default=None,
                        help="generate portraits and save PNGs to this local "
                             "directory instead of uploading to Firebase Storage. "
                             "Also skips Pinecone upsert entirely — pure local "
                             "preview mode. Use with --limit for cheap test runs.")
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, do_purge=args.purge,
                     do_resume=args.resume, limit=args.limit,
                     local_out_dir=args.out_dir))
