from shared.schemas import Destination, UserProfile
from shreyas.ranking.filters import apply_destination_filters


def score_destination(dest: Destination, user_profile: UserProfile, pinecone_score: float) -> float:
    """
    Compute a final score for a destination combining multiple signals.

    Suggested weighting (adjust as you see fit):
        60% — Pinecone vector similarity score
        20% — Budget fit (how well daily cost fits the user's budget)
        20% — Tag-interest bonus (persona interests aligned with destination tags)

    Expected input:
        dest           = Destination(city="Bali", avg_daily_cost_usd=120, tags=["beach","culture","food"])
        user_profile   = UserProfile(persona_answers=PersonaQuestionAnswers(food_interest=5, culture_interest=4))
        pinecone_score = 0.87  # raw cosine similarity from Pinecone

    Expected output:
        0.83  # float between 0.0 and 1.0
    """
    # TODO: implement weighted scoring
    raise NotImplementedError


def rank_destinations(
    candidates: list[tuple[Destination, float]],
    user_profile: UserProfile,
    top_n: int = 5,
) -> list[Destination]:
    """
    Filter then score then sort destinations, returning the top_n.

    Expected input:
        candidates = [(Destination(city="Bali"), 0.87), (Destination(city="Lisbon"), 0.81), ...]
        top_n      = 5

    Expected output:
        [Destination(city="Bali"), Destination(city="Lisbon"), ...]  # top 5, sorted by final score
    """
    # TODO: apply_destination_filters, score each, sort descending, return top_n
    raise NotImplementedError
