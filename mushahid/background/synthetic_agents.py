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


_FALLBACK_PERSONAS_CACHE: list = []


def _fallback_personas() -> list:
    """Inline persona pool used when Pinecone returns nothing. These are
    plain SimpleNamespace instances quacking like CoTravellerProfile —
    enough for the LLM prompts and the open-trip schema to render. The
    loop should always have *someone* to act as, even with no Pinecone."""
    from types import SimpleNamespace
    global _FALLBACK_PERSONAS_CACHE
    if _FALLBACK_PERSONAS_CACHE:
        return _FALLBACK_PERSONAS_CACHE
    seed = [
        ("Mira",    "Berlin",     "Quiet wanderer",   ["food", "vintage shops", "walking"],     "moderate",  "mid_range",  "solo",     ["lingers in cafes", "skips museums she's seen photos of"]),
        ("Theo",    "Lisbon",     "Slow opportunist", ["coast", "music", "wine"],               "slow",      "mid_range",  "couple",   ["always asks the bartender", "naps at 4pm"]),
        ("Aiko",    "Kyoto",      "Patterned drifter",["temples", "stationery", "tea"],         "slow",      "mid_range",  "solo",     ["writes postcards she never sends"]),
        ("Luca",    "Milan",      "Romantic planner", ["design", "aperitivo", "tailoring"],     "moderate",  "luxury",     "couple",   ["over-orders at every meal"]),
        ("Noor",    "Marrakesh",  "Curious haggler",  ["souks", "spice", "rooftops"],           "fast",      "budget",     "friends",  ["talks to every shopkeeper"]),
        ("Sasha",   "Tbilisi",    "Mountain person",  ["wine", "hiking", "ruins"],              "moderate",  "budget",     "solo",     ["always has a jacket in the bag"]),
        ("Ren",     "Taipei",     "Late-night eater", ["night markets", "scooters", "rain"],    "fast",      "budget",     "friends",  ["maps every dessert shop"]),
        ("Esme",    "Mexico City","Neighbourhood crawler", ["mezcal", "murals", "tacos"],        "moderate",  "mid_range",  "couple",   ["takes the wrong bus on purpose"]),
        ("Kai",     "Reykjavik",  "Roadtrip type",    ["geysers", "long drives", "cold air"],   "moderate",  "mid_range",  "solo",     ["plays the same album the whole trip"]),
        ("Priya",   "Hanoi",      "Street-food first", ["food", "coffee", "alleys", "humidity"], "fast",      "budget",     "friends",  ["orders the same dish twice"]),
    ]
    out = []
    for i, (name, location, archetype, interests, pace, budget, style, quirks) in enumerate(seed):
        out.append(SimpleNamespace(
            profile_id   = f"ct_synth_{i:02d}_{name.lower()}",
            display_name = name,
            location     = location,
            archetype    = archetype,
            interests    = interests if isinstance(interests, list) else [interests],
            pace         = pace,
            budget_style = budget,
            travel_style = style,
            quirks       = quirks if isinstance(quirks, list) else [quirks],
            avatar_url   = None,
            is_seed      = True,
        ))
    _FALLBACK_PERSONAS_CACHE = out
    return out


async def _pick_personas(n: int = 8) -> list:
    """Fetch a handful of seeded personas from Pinecone, falling back to
    a hardcoded persona pool when Pinecone is unreachable or empty so
    the loop always has someone to act as."""
    from shreyas.retrieval.search import search_cotravellers
    from shared.schemas import UserProfile
    try:
        viewer = UserProfile(user_id="__synthetic_agent__", display_name="traveller")
        profiles = await search_cotravellers(viewer, top_k=40)
        seeded = [p for p in profiles if getattr(p, "is_seed", False)]
        pool = seeded or profiles
        if pool:
            random.shuffle(pool)
            return pool[:n]
    except Exception as e:
        logger.warning("synthetic_agents: persona fetch failed (using fallback): %s", e)

    # Pinecone returned nothing or errored — use the hardcoded pool so
    # the feed/discover still feels alive.
    fb = list(_fallback_personas())
    random.shuffle(fb)
    return fb[:n]


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

    # Auto-illustrate from Pixabay so synthetic posts read as scrollable
    # social cards, not text walls. Best-effort — no key / no hits just
    # returns None and the post renders text-only.
    image_url = None
    try:
        from shared.pixabay import fetch_image_url_for_post_text
        image_url = await fetch_image_url_for_post_text(text)
    except Exception as e:
        logger.debug("synthetic_agents: pixabay lookup failed: %s", e)

    post = {
        "post_id":        _new_id("post"),
        "author_id":      getattr(persona, "profile_id", "") or _new_id("ct"),
        "author_name":    getattr(persona, "display_name", None) or "Traveller",
        "author_avatar":  getattr(persona, "avatar_url", None),
        "text":           text,
        "linked_trip_id": None,
        "image_url":      image_url,
        "comment_count":  0,
        "created_at":     _now_iso(),
        "is_synthetic":   True,
    }
    await write_social_post(post)
    try:
        await ws_manager.broadcast_global({"type": "discover_post_new", "post": post})
    except Exception as e:
        logger.debug("synthetic_agents: broadcast post failed: %s", e)
    logger.warning("[synthetic_agents] posted as %s (%s chars)",
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
    try:
        await write_itinerary(itinerary)
    except Exception as e:
        logger.warning("[synthetic_agents] write_itinerary failed for %s, aborting trip creation: %s", itinerary_id, e)
        return
    await set_itinerary_open(itinerary_id, is_open=True, join_capacity=itinerary.join_capacity)

    # Persist note + synthetic-owner snapshot. The latter lets the join-
    # request route reconstruct the persona for instant match scoring
    # without re-hitting Pinecone (the fallback personas don't live there
    # anyway).
    owner_snapshot = {
        "profile_id":   getattr(persona, "profile_id", "") or "",
        "display_name": getattr(persona, "display_name", "") or "",
        "location":     getattr(persona, "location", "") or "",
        "archetype":    getattr(persona, "archetype", "") or "",
        "interests":    list(getattr(persona, "interests", []) or [])[:10],
        "pace":         str(getattr(getattr(persona, "pace", ""), "value", "") or getattr(persona, "pace", "") or "moderate"),
        "budget_style": str(getattr(getattr(persona, "budget_style", ""), "value", "") or getattr(persona, "budget_style", "") or "mid_range"),
        "travel_style": str(getattr(getattr(persona, "travel_style", ""), "value", "") or getattr(persona, "travel_style", "") or "solo"),
        "quirks":       list(getattr(persona, "quirks", []) or [])[:5],
        "avatar_url":   getattr(persona, "avatar_url", None),
        "is_seed":      bool(getattr(persona, "is_seed", True)),
    }
    merge_payload: dict = {
        "is_synthetic":    True,
        "synthetic_owner": owner_snapshot,
    }
    if note:
        merge_payload["open_join_note"] = note
    try:
        from mushahid.realtime.firestore import get_db, LOCAL_MODE, _store
        if LOCAL_MODE:
            key = f"itinerary:{itinerary_id}"
            if key in _store:
                _store[key] = {**_store[key], **merge_payload}
        else:
            await asyncio.to_thread(
                lambda: get_db().collection("itineraries").document(itinerary_id)
                                .set(merge_payload, merge=True)
            )
    except Exception as e:
        logger.debug("synthetic_agents: merge persist failed: %s", e)

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
    logger.warning("[synthetic_agents] opened trip %s -> %s, %s",
                   itinerary_id, dest_meta["city"], dest_meta["country"])


async def _emit_outreach_chat(persona) -> bool:
    """Pick a real eligible user (solo / couple with a current trip),
    start a chat session as `persona`, and drop an LLM-generated opener
    anchored on the user's trip. Returns True if a chat was actually
    created, False if no eligible user was available.

    Skips users who already have an active chat session with this
    persona — repeated cold-opens from the same profile would feel
    spammy."""
    from ali.generation.synthetic_social import generate_outreach_opener
    from mushahid.realtime.firestore import (
        list_outreach_eligible_users, get_itinerary,
        list_chat_sessions_for_user, write_chat_session, append_chat_message,
    )
    from shreyas.cotraveller.chat import manager as ws_manager
    from shared.schemas import ChatSession, ApprovalStatus

    users = await list_outreach_eligible_users(limit=30)
    if not users:
        return False
    random.shuffle(users)

    persona_id = getattr(persona, "profile_id", "") or ""
    persona_name = getattr(persona, "display_name", None) or "Traveller"

    for target in users[:5]:
        uid = target.get("user_id")
        itinerary_id = target.get("current_itinerary_id")
        if not uid or not itinerary_id:
            continue
        # Skip if a session already exists between this user and this persona.
        try:
            sessions = await list_chat_sessions_for_user(uid)
        except Exception:
            sessions = []
        if any(s.get("profile_id") == persona_id for s in sessions):
            continue

        # Anchor the opener on the user's trip.
        try:
            itin = await get_itinerary(itinerary_id)
        except Exception:
            itin = None
        if itin is None:
            continue
        dest = getattr(itin, "destination", None)
        city    = (getattr(dest, "city", "") or "").strip() if dest else ""
        country = (getattr(dest, "country", "") or "").strip() if dest else ""
        if not city:
            continue
        days = getattr(itin, "days", None) or []
        window = ""
        if days and getattr(days[0], "trip_date", None) and getattr(days[-1], "trip_date", None):
            window = f"{days[0].trip_date} → {days[-1].trip_date}"

        target_name = (target.get("display_name") or "").strip()
        opener = await generate_outreach_opener(
            persona, city, country, window,
            target_display_name=target_name,
        )
        if not opener:
            continue

        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            user_id=uid,
            profile_id=persona_id,
            itinerary_id=itinerary_id,
            approval_status=ApprovalStatus.pending,
            created_at=_now_iso(),
            match_score=None,
        )
        try:
            await write_chat_session(session)
        except Exception as e:
            logger.warning("outreach: write_chat_session failed: %s", e)
            return False

        msg_id = _new_id("msg")
        message = {
            "message_id": msg_id,
            "session_id": session_id,
            "sender_id":  persona_id,
            "content":    opener,
            "timestamp":  _now_iso(),
        }
        try:
            await append_chat_message(session_id, message)
        except Exception as e:
            logger.warning("outreach: append_chat_message failed: %s", e)

        # Notify the target via WS + web push so the inbox + dashboard
        # banner light up instantly.
        try:
            await ws_manager.notify_user(uid, {
                "type":           "chat_notification",
                "session_id":     session_id,
                "sender_id":      persona_id,
                "sender_name":    persona_name,
                "sender_is_seed": bool(getattr(persona, "is_seed", True)),
                "preview":        opener[:140],
                "timestamp":      message["timestamp"],
            })
        except Exception as e:
            logger.debug("outreach: notify_user failed: %s", e)

        try:
            from mushahid.realtime.web_push import send_web_push
            asyncio.create_task(send_web_push(uid, {
                "title": persona_name,
                "body":  opener[:140],
                "url":   f"/chat/{session_id}",
                "tag":   f"sonder-chat-{session_id}",
            }))
        except Exception as e:
            logger.debug("outreach: web push failed: %s", e)

        logger.warning("[synthetic_agents] outreach %s -> %s about %s",
                       persona_name, uid, city)
        return True

    return False


async def _run_action(persona) -> None:
    """One agent action: 55% outreach (chat → push/email notif), 25%
    posts, 20% open trips. Outreach is the only action that generates
    a chat_notification for the user, so it dominates the mix when we
    want 'more notifications'. Outreach returns False when no eligible
    user exists OR every persona has already messaged the user; in
    that case we fall back to a post so the cycle isn't wasted."""
    try:
        roll = random.random()
        if roll < 0.55:
            sent = await _emit_outreach_chat(persona)
            if not sent:
                # No eligible target → don't waste the cycle on silence,
                # post something so /feed stays alive instead.
                await _emit_post(persona)
        elif roll < 0.80:
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
    logger.warning(
        "[synthetic_agents] LOOP STARTED — interval %d-%ds, seed=%d. "
        "Watch for '[synthetic_agents] posted ...' / 'opened trip ...' lines.",
        lo, hi, SYNTHETIC_AGENTS_SEED_COUNT,
    )

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
