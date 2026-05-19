"""
Seed Pinecone with realistic co-traveller personas for matching.

    python -m scripts.seed_cotravellers --count 500

Pipeline:
  1. Pull identity (name, age, photo, city, country) from randomuser.me — one
     batched call, no API key. Mixed nationalities for diversity.
  2. Sample persona dimensions deterministically from each user's stable uuid:
     2 PUSH ids from Jahnvi's Core 12, 3 PULL ids, plus pace + budget + style
     drawn from the schema enums. No hardcoded vocabulary anywhere.
  3. Generate archetype + 2-sentence bio per persona via the small LLM (Haiku
     by default — same routing as the real persona-label task).
  4. Build a keyword-rich persona text from the chosen dimensions + the LLM
     bio so the embedding sits in the same vector space as live users.
  5. Embed via the same `embed_batch` real users hit (OpenAI 1536-dim).
  6. Upsert to Pinecone `cotravellers` namespace with stable IDs derived from
     randomuser's login.uuid → re-running overwrites instead of duplicating.

Honest labelling: every record carries `is_seed: True` in metadata so the
matcher / frontend can disclose "Sonder Curated" when chat would otherwise
imply a real person.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import random
import re
import sys
import time

import httpx

from ali.routing.engine import route_request
from ali.vector.embeddings import embed_batch
from jahnvi.data.dimensions import PUSH_DIMENSIONS, PULL_DIMENSIONS, ALL_DIMENSIONS
from jahnvi.schemas.enums import PacePreference, BudgetStyle, TravelStyle
from shreyas.retrieval.client import get_pinecone_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("seed_cotravellers")

# Mixed nationalities — randomuser.me supports these out of the box.
NATIONALITIES = "us,gb,fr,de,es,ie,au,ca,nz,br,in,nl,no,fi,dk,ch"
RANDOMUSER_URL = "https://randomuser.me/api/"

PUSH_IDS = list(PUSH_DIMENSIONS.keys())
PULL_IDS = list(PULL_DIMENSIONS.keys())

# Concurrency caps. Anthropic returns 529 overloaded under bursty load and
# route_request falls back to OpenAI with the Anthropic model name (404).
# 3 in flight + in-script retry on overload below keeps things on Anthropic.
BIO_CONCURRENCY   = 3
BIO_RETRIES       = 3   # extra retries beyond the SDK's, on overloaded errors
EMBED_BATCH_SIZE  = 100
UPSERT_BATCH_SIZE = 100


# ── randomuser.me ─────────────────────────────────────────────────────────────

async def fetch_users(count: int) -> list[dict]:
    """One call. randomuser.me caps at 5000 per request; we'll never need more."""
    log.info("Fetching %d users from randomuser.me (%s)…", count, NATIONALITIES)
    params = {"results": count, "nat": NATIONALITIES, "exc": "login,registered,id,phone,cell"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        # We need login.uuid for stable IDs — re-add it manually since `exc`
        # excludes it for slimmer payloads otherwise. randomuser supports `inc`
        # but mixing inc/exc is finicky, so just take everything.
        resp = await client.get(RANDOMUSER_URL, params={"results": count, "nat": NATIONALITIES})
        resp.raise_for_status()
        return resp.json()["results"]


# ── Persona sampling — deterministic from uuid ────────────────────────────────

def sample_persona(seed_int: int) -> dict:
    rng = random.Random(seed_int)
    return {
        "top_push":      rng.sample(PUSH_IDS, 2),
        "top_interests": rng.sample(PULL_IDS, 3),
        "pace":          rng.choice(list(PacePreference)).value,
        "budget_style":  rng.choice(list(BudgetStyle)).value,
        "travel_style":  rng.choice(list(TravelStyle)).value,
    }


# ── LLM: archetype + bio ──────────────────────────────────────────────────────

_BIO_SYSTEM = (
    "You write distinctive bios for traveller profile cards on a luxury travel app. "
    "Return ONLY valid JSON with two keys:\n"
    '  {"archetype": "<3-4 word label, title case, no period>", '
    '"bio": "<exactly 2 sentences, ~25 words total, third person, no first-person pronouns>"}\n'
    "Use concrete preferences (long museum afternoons, back-alley dinners, hammock mornings), "
    "not abstract adjectives (passionate, vibrant, amazing). No marketing fluff, no emojis, "
    "no preamble, no code fences."
)


def _bio_prompt(name: str, age: int, location: str, p: dict) -> str:
    return (
        f"Traveller: {name}, {age}, lives in {location}.\n"
        f"Why they travel: {', '.join(p['top_push'])}\n"
        f"Looks for at the destination: {', '.join(p['top_interests'])}\n"
        f"Pace: {p['pace']}. Budget: {p['budget_style']}. Goes with: {p['travel_style']}.\n"
        f"Return archetype + bio JSON."
    )


_JSON_OBJ_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _parse_bio_json(raw: str) -> tuple[str, str]:
    """Strip any preamble / fences and extract the first {...} object."""
    if not isinstance(raw, str):
        raise ValueError("non-string LLM output")
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_OBJ_RE.search(raw)
        if not m:
            raise
        obj = json.loads(m.group(0))
    return str(obj.get("archetype", "")).strip(), str(obj.get("bio", "")).strip()


def _is_overloaded(e: Exception) -> bool:
    s = str(e).lower()
    return "529" in s or "overloaded" in s or "model `claude" in s  # incl. cross-provider 404


async def generate_bio(name: str, age: int, location: str, persona: dict, sem: asyncio.Semaphore) -> tuple[str, str]:
    """Call the small LLM with a bounded concurrency semaphore. Retries
    on Anthropic 529-overloaded (and the cross-provider 404 that follows when
    route_request falls back to OpenAI with the Anthropic model name) before
    accepting a templated fallback so a transient blip doesn't sink the bio."""
    async with sem:
        last_err = None
        for attempt in range(BIO_RETRIES + 1):
            try:
                raw = await route_request("persona_label", _bio_prompt(name, age, location, persona), _BIO_SYSTEM)
                archetype, bio = _parse_bio_json(raw)
                if not archetype or not bio:
                    raise ValueError("empty archetype or bio")
                return archetype, bio
            except Exception as e:
                last_err = e
                if _is_overloaded(e) and attempt < BIO_RETRIES:
                    wait = 2.5 * (attempt + 1) + random.uniform(0, 1.5)
                    await asyncio.sleep(wait)
                    continue
                break
        log.warning("  bio fallback for %s (%s): %s", name, persona.get("top_interests"), last_err)
        interests_pretty = ", ".join(persona["top_interests"][:2]).replace("_", " ")
        return (
            "Quiet Traveller",
            f"Tends toward {interests_pretty}, with a {persona['pace']} pace. "
            f"Travels {persona['travel_style']} and seeks places where the rhythm slows down.",
        )


# ── Persona text for embedding (matches live user text space) ─────────────────

def build_seed_persona_text(persona: dict, bio: str, seed_int: int) -> str:
    """Sample 4 keyword phrases per chosen dimension so the embedding lives in
    the same lexical neighbourhood as a real user's form answers. Add pace +
    travel style + the LLM bio for natural-language texture."""
    rng = random.Random(seed_int + 1)
    keywords: list[str] = []
    for dim_id in persona["top_push"] + persona["top_interests"]:
        kws = ALL_DIMENSIONS.get(dim_id, [])
        if kws:
            keywords.extend(rng.sample(kws, min(4, len(kws))))
    parts = keywords + [persona["pace"], persona["travel_style"], bio]
    return ". ".join(p.strip() for p in parts if p and p.strip())


# ── Pinecone upsert ───────────────────────────────────────────────────────────

async def upsert(records: list[dict]) -> None:
    if not records:
        return
    index = await get_pinecone_index()
    total = len(records)
    for i in range(0, total, UPSERT_BATCH_SIZE):
        chunk = records[i:i + UPSERT_BATCH_SIZE]
        await asyncio.to_thread(lambda c=chunk: index.upsert(namespace="cotravellers", vectors=c))
        log.info("  upserted %d / %d", min(i + UPSERT_BATCH_SIZE, total), total)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(count: int, dry_run: bool) -> None:
    t0 = time.time()
    users = await fetch_users(count)
    log.info("Got %d identity blobs in %.1fs", len(users), time.time() - t0)

    personas = []
    for u in users:
        uuid = u["login"]["uuid"]
        seed_int = int(hashlib.md5(uuid.encode()).hexdigest()[:8], 16)
        personas.append({
            "uuid":     uuid,
            "seed_int": seed_int,
            "name":     f"{u['name']['first']} {u['name']['last']}",
            "age":      u["dob"]["age"],
            "location": f"{u['location']['city']}, {u['location']['country']}",
            "avatar":   u["picture"]["large"],
            "gender":   u.get("gender", ""),
            **sample_persona(seed_int),
        })

    log.info("Generating %d archetype + bio pairs via small LLM (concurrency=%d)…",
             len(personas), BIO_CONCURRENCY)
    t1 = time.time()
    sem = asyncio.Semaphore(BIO_CONCURRENCY)
    bios = await asyncio.gather(*[
        generate_bio(p["name"], p["age"], p["location"], p, sem) for p in personas
    ])
    for p, (archetype, bio) in zip(personas, bios):
        p["archetype"] = archetype
        p["bio"]       = bio
    log.info("Bios done in %.1fs", time.time() - t1)

    log.info("Embedding %d persona texts…", len(personas))
    texts = [build_seed_persona_text(p, p["bio"], p["seed_int"]) for p in personas]
    embeddings: list[list[float]] = []
    t2 = time.time()
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        embeddings.extend(await embed_batch(texts[i:i + EMBED_BATCH_SIZE]))
        log.info("  embedded %d / %d", min(i + EMBED_BATCH_SIZE, len(texts)), len(texts))
    log.info("Embeddings done in %.1fs", time.time() - t2)

    records = []
    for p, text, emb in zip(personas, texts, embeddings):
        pid = f"ct_{p['uuid'].replace('-', '')[:16]}"
        records.append({
            "id":     pid,
            "values": emb,
            "metadata": {
                "profile_id":    pid,
                "display_name":  p["name"],
                "age":           int(p["age"]),
                "location":      p["location"],
                "archetype":     p["archetype"],
                "avatar_url":    p["avatar"],
                "top_push":      p["top_push"],
                "top_interests": p["top_interests"],
                "interests":     p["top_interests"],
                "pace":          p["pace"],
                "budget_style":  p["budget_style"],
                "travel_style":  p["travel_style"],
                "bio":           p["bio"],
                "text":          text[:1000],
                "is_seed":       True,
            },
        })

    if dry_run:
        log.info("--dry-run: showing 3 sample records, not upserting")
        for r in records[:3]:
            md = r["metadata"]
            log.info("  %s | %s, %d, %s | %s | push=%s pull=%s",
                     r["id"], md["display_name"], md["age"], md["location"],
                     md["archetype"], md["top_push"], md["top_interests"])
            log.info("    bio: %s", md["bio"])
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

    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=500, help="how many co-traveller personas to seed")
    p.add_argument("--dry-run", action="store_true", help="generate everything but skip Pinecone upsert")
    args = p.parse_args()
    if args.count < 1 or args.count > 5000:
        log.error("--count must be between 1 and 5000")
        sys.exit(1)
    asyncio.run(main(args.count, args.dry_run))
