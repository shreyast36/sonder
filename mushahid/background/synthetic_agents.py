"""
Background loop that drives synthetic personas to act on the social
surfaces so /discover and /feed feel alive even with no other real
users online.

Every SYNTHETIC_AGENTS_MIN_INTERVAL..MAX_INTERVAL seconds the loop:
  1. Picks a random seeded CoTravellerProfile from Pinecone.
  2. Picks an action (post on /feed, or open a trip on /discover).
  3. Generates the content via an LLM call in the persona's voice.
  4. Persists + broadcasts so connected users see it pop in real time.

Broadcasts reuse the existing fan-out path (`broadcast_global` on the
notification socket), so the frontend listens with the same handlers
it already uses for real activity — there's no synthetic-specific
event type.

The loop is started in mushahid/main.py's lifespan and cancelled on
shutdown. SYNTHETIC_AGENTS_ENABLED=false skips it entirely.
"""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import date, datetime, timedelta, timezone

from shared.config import (
    SYNTHETIC_AGENTS_ENABLED,
    SYNTHETIC_AGENTS_MIN_INTERVAL,
    SYNTHETIC_AGENTS_MAX_INTERVAL,
    SYNTHETIC_AGENTS_SEED_COUNT,
    SMALL_MODEL_PROVIDER,
)
from shared.schemas import Destination, Itinerary, ItineraryDay

logger = logging.getLogger(__name__)


# Small curated destination pool. We deliberately don't pull from
# Pinecone for the opener — the destination metadata needs city +
# country fields formatted for the trip card, and we want stability
# rather than whatever happens to be top-k for a generic vector.
_DESTINATIONS: list[dict] = [
    {"city": "Lisbon",     "country": "Portugal",     "tags": ["food", "coast", "slow"]},
    {"city": "Oaxaca",     "country": "Mexico",       "tags": ["food", "art", "culture"]},
    {"city": "Kyoto",      "country": "Japan",        "tags": ["culture", "temples", "slow"]},
    {"city": "Taipei",     "country": "Taiwan",       "tags": ["food", "night", "rain"]},
    {"city": "Tbilisi",    "country": "Georgia",      "tags": ["wine", "mountains", "offbeat"]},
    {"city": "Mexico City","country": "Mexico",       "tags": ["food", "neighborhoods", "art"]},
    {"city": "Hanoi",      "country": "Vietnam",      "tags": ["food", "street", "humid"]},
    {"city": "Marrakesh",  "country": "Morocco",      "tags": ["souks", "desert", "color"]},
    {"city": "Reykjavik",  "country": "Iceland",      "tags": ["roadtrip", "nature", "cold"]},
    {"city": "Buenos Aires","country": "Argentina",   "tags": ["nightlife", "tango", "steak"]},
    {"city": "Ljubljana",  "country": "Slovenia",     "tags": ["alps", "quiet", "lakes"]},
    {"city": "Cape Town",  "country": "South Africa", "tags": ["coast", "hiking", "wine"]},
]


async def _pick_personas(n: int = 8) -> list:
    """Fetch a handful of seeded personas from Pinecone. We over-fetch
    so a single LLM call can choose from variety; the caller picks one
    at random. Returns [] if Pinecone is unreachable — the loop logs
    and skips the cycle."""
    from shreyas.retrieval.search import search_cotravellers
    from shared.schemas import UserProfile
    try:
        # A neutral query — we just want anyone seeded. The cotraveller
        # pool is small enough that top_k gives us decent variety.
        viewer = UserProfile(user_id="__synthetic_agent__", display_name="traveller")
        profiles = await search_cotravellers(viewer, top_k=40)
        seeded = [p for p in profiles if getattr(p, "is_seed", False)]
        if not seeded:
            return profiles[:n]
        random.shuffle(seeded)
        return seeded[:n]
    except Exception as e:
        logger.warning("synthetic_agents: persona fetch failed: %s", e)
        return []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _emit_post(persona) -> None:
    """Generate a persona-voiced post, persist it, broadcast it."""
    from ali.generation.synthetic_social import generate_synthetic_post
    from mushahid.realtime.firestore import write_social_post
    from shreyas.cotraveller.chat import manager as ws_manager

    text = await generate_synthetic_post(persona)
    if not text:
        return

    post = {
        "post_id":        _new_id("post"),
        "author_id":      getattr(persona, "profile_id", "") or _new_id("ct"),
        "author_name":    getattr(persona, "display_name", None) or "Traveller",
        "author_avatar":  getattr(persona, "avatar_url", None),
        "text":           text,
        "linked_trip_id": None,
        "image_url":      None,
        "comment_count":  0,
        "created_at":     _now_iso(),
        "is_synthetic":   True,
    }
    await write_social_post(post)
    try:
        await ws_manager.broadcast_global({"type": "discover_post_new", "post": post})
    except Exception as e:
        logger.debug("synthetic_agents: broadcast post failed: %s", e)
    logger.info("synthetic_agents: posted as %s (%s chars)",
                post["author_name"], len(text))


async def _emit_open_trip(persona) -> None:
    """Mint a minimal Itinerary doc owned by the synthetic persona,
    flag it open, broadcast a discover_trip_open card so the feed
    surfaces it instantly."""
    from ali.generation.synthetic_social import generate_synthetic_open_trip_note
    from mushahid.realtime.firestore import write_itinerary, set_itinerary_open
    from mushahid.routes.discover import _trip_card
    from shreyas.cotraveller.chat import manager as ws_manager

    dest_meta = random.choice(_DESTINATIONS)
    note = await generate_synthetic_open_trip_note(
        persona, dest_meta["city"], dest_meta["country"],
    )

    # Start the trip 2-8 weeks out — gives the feed a realistic window
    # spread. One-day stub itinerary so the card has a date range; the
    # trip is symbolic, the user won't actually plan against it.
    start = date.today() + timedelta(days=random.randint(14, 56))
    end   = start + timedelta(days=random.randint(3, 9))

    destination = Destination(
        destination_id = f"synth_{dest_meta['city'].lower().replace(' ', '_')}",
        city           = dest_meta["city"],
        country        = dest_meta["country"],
        avg_daily_cost_usd = 0.0,
        tags           = dest_meta["tags"],
        description    = "",
    )
    days = [
        ItineraryDay(day_number=1, trip_date=start, activities=[], daily_cost_usd=0.0),
        ItineraryDay(day_number=(end - start).days + 1, trip_date=end,
                     activities=[], daily_cost_usd=0.0),
    ]
    itinerary_id = _new_id("itin_synth")
    itinerary = Itinerary(
        itinerary_id     = itinerary_id,
        user_id          = getattr(persona, "profile_id", "") or _new_id("ct"),
        destination      = destination,
        days             = days,
        total_budget_usd = 0.0,
        is_open_to_join  = True,
        join_capacity    = random.choice([1, 2]),
    )
    await write_itinerary(itinerary)
    await set_itinerary_open(itinerary_id, is_open=True, join_capacity=itinerary.join_capacity)

    # Persist the note via the same raw merge path the real /open route
    # uses, so the trip card carries the same `open_join_note` field.
    if note:
        try:
            from mushahid.realtime.firestore import get_db, LOCAL_MODE, _store
            if LOCAL_MODE:
                key = f"itinerary:{itinerary_id}"
                if key in _store:
                    _store[key] = {**_store[key], "open_join_note": note, "is_synthetic": True}
            else:
                await asyncio.to_thread(
                    lambda: get_db().collection("itineraries").document(itinerary_id)
                                    .set({"open_join_note": note, "is_synthetic": True}, merge=True)
                )
        except Exception as e:
            logger.debug("synthetic_agents: note persist failed: %s", e)

    # Shape the broadcast card. Recipients render is_yours themselves.
    raw_dict = itinerary.model_dump(mode="json")
    if note:
        raw_dict["open_join_note"] = note
    card = await _trip_card(raw_dict, viewer_uid="")
    card.pop("is_yours", None)
    card["owner_uid"] = itinerary.user_id
    try:
        await ws_manager.broadcast_global({"type": "discover_trip_open", "trip": card})
    except Exception as e:
        logger.debug("synthetic_agents: broadcast trip failed: %s", e)
    logger.info("synthetic_agents: opened trip %s -> %s, %s",
                itinerary_id, dest_meta["city"], dest_meta["country"])


async def _run_action(persona) -> None:
    """One agent action: 65% posts, 35% open trips. Swallows errors."""
    try:
        if random.random() < 0.65:
            await _emit_post(persona)
        else:
            await _emit_open_trip(persona)
    except Exception as e:
        logger.warning("synthetic_agents: action failed: %s", e)


async def _seed_burst(personas: list, count: int) -> None:
    """Fire `count` actions in parallel on cold-start so the surface
    isn't empty when the first user lands. Uses asyncio.gather so the
    LLM calls overlap instead of serialising. Failures are swallowed
    per-action."""
    if not personas or count <= 0:
        return
    chosen = [random.choice(personas) for _ in range(count)]
    logger.info("synthetic_agents: seed burst (%d actions)", len(chosen))
    await asyncio.gather(*(_run_action(p) for p in chosen), return_exceptions=True)


async def synthetic_agents_loop() -> None:
    """The forever-loop. Sleeps a randomised interval, then fires one
    action. Catches every exception per-cycle so a single failure
    never kills the loop."""
    if not SYNTHETIC_AGENTS_ENABLED:
        logger.info("synthetic_agents: disabled via SYNTHETIC_AGENTS_ENABLED=false")
        return
    if not SMALL_MODEL_PROVIDER:
        logger.warning("synthetic_agents: SMALL_MODEL_PROVIDER unset — loop won't run")
        return

    lo = max(8, SYNTHETIC_AGENTS_MIN_INTERVAL)
    hi = max(lo + 10, SYNTHETIC_AGENTS_MAX_INTERVAL)
    logger.info("synthetic_agents: loop starting (interval %d-%ds, seed=%d)",
                lo, hi, SYNTHETIC_AGENTS_SEED_COUNT)

    # Tiny stagger so the seed burst doesn't fight cold-start work,
    # then prime the feed immediately so users don't land on empty.
    await asyncio.sleep(random.uniform(2.0, 5.0))
    try:
        personas = await _pick_personas(n=12)
        await _seed_burst(personas, SYNTHETIC_AGENTS_SEED_COUNT)
    except Exception as e:
        logger.warning("synthetic_agents: seed burst failed: %s", e)

    # Steady-state loop.
    while True:
        try:
            personas = await _pick_personas(n=8)
            if not personas:
                logger.info("synthetic_agents: no personas available, skipping cycle")
            else:
                await _run_action(random.choice(personas))
        except Exception as e:
            logger.warning("synthetic_agents: cycle failed: %s", e)

        await asyncio.sleep(random.uniform(lo, hi))
