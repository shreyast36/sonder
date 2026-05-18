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


async def search_activities(
    city: str,
    country: str | None,
    user_profile: UserProfile,
    top_k: int = 20,
) -> list[Activity]:
    """
    Query the seeded Pinecone 'activities' namespace, filtered to the given
    city (and country when present), ranked by cosine similarity against the
    user's persona text. Returns Activity objects with metadata drawn from
    the Foursquare records seeded into the corpus. cost_usd and
    duration_hours are not in the corpus and default to 0.0 / 2.0 — the
    itinerary LLM fills in realistic values.
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

    result = await asyncio.to_thread(
        lambda: index.query(
            namespace="activities",
            vector=query_vec,
            top_k=top_k,
            filter=pinecone_filter,
            include_metadata=True,
        )
    )

    activities: list[Activity] = []
    for match in getattr(result, "matches", []) or []:
        md = match.metadata or {}
        categories_str = md.get("categories") if isinstance(md.get("categories"), str) else ""
        primary = (categories_str.split(",")[0].strip() if categories_str else "") or "activity"
        tags = [t.strip() for t in (categories_str or "").split(",") if t.strip()]
        text = md.get("text") or md.get("description") or md.get("name") or ""
        activities.append(Activity(
            activity_id=match.id,
            name=md.get("name", "Unknown"),
            category=primary.lower(),
            cost_usd=0.0,
            duration_hours=2.0,
            tags=tags,
            description=(text or "")[:400],
        ))
    return activities


def search_cotravellers(user_profile: UserProfile, top_k: int = 20) -> list[dict]:
    """
    Find the most compatible co-traveller profiles via vector similarity.

    Expected input:  user_profile with travel_style_embedding populated (from Jahnvi's module3)
    Expected output:
        [
            {"id": "ct_maya_001", "score": 0.94, "metadata": {"profile_id": "maya_001", "archetype": "Cultural Explorer"}},
            ...
        ]
    """
    # TODO: use user_profile.travel_style_embedding if set, else embed build_user_query(user_profile)
    # TODO: query Pinecone with filter={"type": "cotraveller"}
    raise NotImplementedError


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
