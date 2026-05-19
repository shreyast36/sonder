import asyncio
import logging

from shreyas.retrieval.client import get_pinecone_index
from ali.vector.embeddings import embed_text as corpus_embed
from jahnvi.data.convert_to_embeddings import build_persona_text
from shared.schemas import UserProfile, Destination, Activity, CoTravellerProfile

logger = logging.getLogger(__name__)


def search_destinations(user_profile: UserProfile, top_k: int = 10) -> list[dict]:
    """
    Not used in v1. The user types their destination on the form, so the
    orchestrator treats that as the authoritative destination — no need to
    discover/rank candidate destinations from the corpus. Revisit when a
    "Surprise me" flow needs corpus-driven destination suggestions.
    """
    raise NotImplementedError


def _match_to_activity(match, default_kind: str) -> Activity:
    """Convert a Pinecone match record into an Activity. `default_kind` is the
    namespace label (hotel/restaurant/activity) used when Foursquare didn't
    return a more specific subcategory."""
    md = match.metadata or {}
    categories_str = md.get("categories") if isinstance(md.get("categories"), str) else ""
    primary = (categories_str.split(",")[0].strip() if categories_str else "") or default_kind
    tags = [t.strip() for t in (categories_str or "").split(",") if t.strip()]
    # Always prepend the kind tag so the LLM has an obvious signal even when
    # the Foursquare subcategory is generic ("Asian Restaurant").
    if default_kind not in (t.lower() for t in tags):
        tags = [default_kind] + tags
    text = md.get("text") or md.get("description") or md.get("name") or ""
    return Activity(
        activity_id=match.id,
        name=md.get("name", "Unknown"),
        category=primary.lower(),
        cost_usd=0.0,
        duration_hours=2.0,
        tags=tags[:6],
        description=(text or "")[:400],
    )


async def _query_namespace(index, namespace: str, vector: list[float], top_k: int, pinecone_filter: dict, kind: str) -> list[Activity]:
    try:
        result = await asyncio.to_thread(
            lambda: index.query(
                namespace=namespace,
                vector=vector,
                top_k=top_k,
                filter=pinecone_filter,
                include_metadata=True,
            )
        )
    except Exception as e:
        logger.warning("Pinecone query for namespace=%s failed: %s", namespace, e)
        return []
    return [_match_to_activity(m, kind) for m in (getattr(result, "matches", []) or [])]


async def search_activities(
    city: str,
    country: str | None,
    user_profile: UserProfile,
    top_k: int = 20,
) -> list[Activity]:
    """
    Query all three seeded Pinecone namespaces (hotels, restaurants, activities)
    in parallel for the given city, ranked by cosine similarity against the
    user's persona text. Returns a merged list of Activity objects — the
    itinerary LLM uses the category/tags to slot hotels for accommodation,
    restaurants for meals, and activities for sightseeing.

    `top_k` is the total budget split across namespaces (hotels get fewer
    since one trip needs ~1 hotel; restaurants and activities split the rest).
    cost_usd / duration_hours default to 0.0 / 2.0 — the LLM fills in
    realistic values.
    """
    index = await get_pinecone_index()

    persona_text = build_persona_text(
        user_profile.constraints if user_profile else None,
        user_profile.persona_answers if user_profile else None,
    )
    if not persona_text.strip():
        persona_text = f"{city} {country or ''}".strip()
    query_vec = await corpus_embed(persona_text)

    pinecone_filter: dict = {"city": city}
    if country:
        pinecone_filter["country"] = country

    # Split the top_k budget: ~15% hotels, ~40% restaurants, ~45% activities.
    # Hotels need fewer matches (the user picks one); food/things-to-do need more.
    k_hotels = max(3, top_k // 6)
    k_restaurants = max(6, (top_k * 2) // 5)
    k_activities = max(8, top_k - k_hotels - k_restaurants)

    hotels, restaurants, activities = await asyncio.gather(
        _query_namespace(index, "hotels",      query_vec, k_hotels,      pinecone_filter, "hotel"),
        _query_namespace(index, "restaurants", query_vec, k_restaurants, pinecone_filter, "restaurant"),
        _query_namespace(index, "activities",  query_vec, k_activities,  pinecone_filter, "activity"),
    )
    logger.info(
        "Pinecone returned hotels=%d restaurants=%d activities=%d for %s, %s",
        len(hotels), len(restaurants), len(activities), city, country or "—",
    )
    return hotels + restaurants + activities


async def search_cotravellers(user_profile: UserProfile, top_k: int = 50) -> list[CoTravellerProfile]:
    """
    Query the seeded 'cotravellers' Pinecone namespace with the user's persona
    embedding and return up to top_k candidate profiles ranked by cosine.

    The actual fine-grained match scoring (dimension overlap, pace/budget
    alignment, match_reasons) happens in shreyas.cotraveller.matching.get_top_matches —
    this function is purely the coarse retrieval step.
    """
    from shared.schemas import CoTravellerProfile
    from jahnvi.schemas.enums import PacePreference, BudgetStyle, TravelStyle

    # Reuse the user's stored embedding if module3_persona already wrote it;
    # otherwise embed their persona text on the fly. Same path real users hit.
    if user_profile and user_profile.travel_style_embedding:
        query_vec = list(user_profile.travel_style_embedding)
    else:
        persona_text = build_persona_text(
            user_profile.constraints if user_profile else None,
            user_profile.persona_answers if user_profile else None,
        )
        if not persona_text.strip():
            persona_text = (user_profile.display_name if user_profile else "") or "traveller"
        query_vec = await corpus_embed(persona_text)

    index = await get_pinecone_index()
    try:
        result = await asyncio.to_thread(
            lambda: index.query(
                namespace="cotravellers",
                vector=query_vec,
                top_k=top_k,
                include_metadata=True,
            )
        )
    except Exception as e:
        logger.warning("cotraveller Pinecone query failed: %s", e)
        return []

    profiles: list[CoTravellerProfile] = []
    for match in (getattr(result, "matches", []) or []):
        md = match.metadata or {}
        try:
            profiles.append(CoTravellerProfile(
                profile_id   = md.get("profile_id") or match.id,
                display_name = md.get("display_name", "Anonymous"),
                age          = int(md.get("age", 30) or 30),
                location     = md.get("location", ""),
                archetype    = md.get("archetype", "Traveller"),
                interests    = list(md.get("interests") or md.get("top_interests") or []),
                pace         = PacePreference(md.get("pace", "moderate")),
                budget_style = BudgetStyle(md.get("budget_style", "mid_range")),
                travel_style = TravelStyle(md.get("travel_style", "solo")),
                avatar_url   = md.get("avatar_url"),
            ))
        except Exception as e:
            logger.warning("skipping malformed cotraveller %s: %s", match.id, e)
    logger.info("cotraveller search returned %d candidates", len(profiles))
    return profiles


def upsert_destinations(destinations: list[Destination]) -> None:
    """
    Index a list of destinations into Pinecone.
    Each destination must have its .embedding field populated before calling this.
    """
    # TODO: build vector dicts and call index.upsert()
    raise NotImplementedError


def upsert_activities(activities: list[Activity], destination_id: str) -> None:
    """Index activities for a destination. Each activity must have .embedding populated."""
    # TODO: build vector dicts with metadata type="activity", destination_id=destination_id
    raise NotImplementedError


def upsert_cotraveller(profile: CoTravellerProfile) -> None:
    """Index a single co-traveller profile. Profile must have .embedding populated."""
    # TODO: build vector dict with metadata type="cotraveller"
    raise NotImplementedError
