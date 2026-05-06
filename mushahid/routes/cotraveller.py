from fastapi import APIRouter
from shared.schemas import CoTravellerMatch

router = APIRouter()


@router.post("/cotraveller", response_model=list[CoTravellerMatch])
async def get_cotraveller_matches(user_id: str, itinerary_id: str):
    """
    Return the top 3 co-traveller matches for a user.

    Expected output:
        [
            CoTravellerMatch(
                profile         = CoTravellerProfile(display_name="Maya Sharma", match_score=0.92, ...),
                match_reasons   = ["Similar interests in food and culture", "Same travel pace"],
                compatibility_breakdown = {"interests": 0.95, "pace": 1.0, "budget": 0.85}
            ),
            CoTravellerMatch(...),  # 92% match
            CoTravellerMatch(...),  # 87% match
        ]
    """
    # TODO: verify auth
    # TODO: load user_profile from Firestore
    # TODO: search_cotravellers(user_profile) → candidates
    # TODO: get_top_matches(user_profile, candidates) → list[CoTravellerMatch]
    raise NotImplementedError
