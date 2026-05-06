from shreyas.retrieval.client import get_pinecone_index
from shreyas.retrieval.embeddings import embed_text, build_user_query
from shared.schemas import UserProfile, Destination, Activity, CoTravellerProfile


def search_destinations(user_profile: UserProfile, top_k: int = 10) -> list[dict]:
    """
    Find the most relevant destinations for a user via vector similarity.

    Expected input:
        user_profile = UserProfile(constraints=..., persona_answers=..., emotion_intent="excited")
        top_k = 10

    Expected output:
        [
            {"id": "dest_bali", "score": 0.91, "metadata": {"city": "Bali", "country": "Indonesia", ...}},
            {"id": "dest_lisbon", "score": 0.87, "metadata": {"city": "Lisbon", ...}},
            ...
        ]
    """
    # TODO: embed build_user_query(user_profile), query Pinecone with filter={"type": "destination"}
    raise NotImplementedError


def search_activities(destination_id: str, user_profile: UserProfile, top_k: int = 20) -> list[dict]:
    """
    Find the best activities for a destination given the user's profile.

    Expected input:  destination_id="bali_001", user_profile=..., top_k=20
    Expected output:
        [
            {"id": "act_uluwatu", "score": 0.88, "metadata": {"name": "Uluwatu Temple", "category": "culture", ...}},
            ...
        ]
    """
    # TODO: query Pinecone with filter={"type": "activity", "destination_id": destination_id}
    raise NotImplementedError


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
