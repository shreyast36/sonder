from shared.schemas import Activity, UserProfile
from shreyas.ranking.filters import apply_activity_filters


def score_activity(activity: Activity, user_profile: UserProfile, pinecone_score: float) -> float:
    """
    Score an activity for a specific user.

    Factors to consider:
        - Vector similarity (pinecone_score)
        - Category interest alignment with persona answers
        - Cost vs. remaining daily budget
        - Pace compatibility (relaxed pace = prefer shorter, fewer activities)

    Expected input:
        activity       = Activity(name="Uluwatu Temple", category="culture", cost_usd=15, duration_hours=2)
        user_profile   = UserProfile(persona_answers=PersonaQuestionAnswers(culture_interest=5))
        pinecone_score = 0.88

    Expected output:
        0.91  # float between 0.0 and 1.0
    """
    # TODO: implement weighted scoring, factor in pace
    raise NotImplementedError


def rank_activities(
    candidates: list[tuple[Activity, float]],
    user_profile: UserProfile,
    top_n: int = 15,
) -> list[Activity]:
    """
    Filter, score, and sort activities. Respects pace preference in top_n:
        relaxed → fewer activities per day, longer durations preferred
        packed  → more activities, shorter durations acceptable

    Expected input:
        candidates = [(Activity(name="Uluwatu Temple"), 0.88), ...]
        top_n      = 15

    Expected output:
        [Activity(name="Uluwatu Temple"), ...]  # top_n sorted by score
    """
    # TODO: filter, score, sort, return top_n
    raise NotImplementedError
