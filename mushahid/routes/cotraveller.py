from fastapi import APIRouter, Depends
from pydantic import BaseModel
from shared.schemas import CoTravellerMatch
from mushahid.auth import verify_token

router = APIRouter()


@router.post("/cotraveller", response_model=list[CoTravellerMatch])
async def get_cotraveller_matches(user_id: str, itinerary_id: str, uid: str = Depends(verify_token)):
    """
    Return the top 3 co-traveller matches for a user.

    Expected output:
        [
            CoTravellerMatch(
                profile         = CoTravellerProfile(display_name="Maya Sharma", match_score=0.92, ...),
                match_reasons   = ["Similar interests in food and culture", "Same travel pace"],
                compatibility_breakdown = {"interests": 0.95, "pace": 1.0, "budget": 0.85}
            ),
            CoTravellerMatch(...),  # 87% match
            CoTravellerMatch(...),  # 81% match
        ]
    """
    # TODO: verify auth
    # TODO: load user_profile from Firestore
    # TODO: search_cotravellers(user_profile) → candidates
    # TODO: get_top_matches(user_profile, candidates) → list[CoTravellerMatch]
    raise NotImplementedError


class RegenerateMatchesRequest(BaseModel):
    user_id:              str
    excluded_profile_ids: list[str]        # profiles already shown to the user
    feedback:             str = ""         # optional — "I want someone more adventurous"


@router.post("/cotraveller/regenerate", response_model=list[CoTravellerMatch])
async def regenerate_cotraveller_matches(body: RegenerateMatchesRequest, uid: str = Depends(verify_token)):
    """
    Find a fresh batch of co-traveller matches, skipping already-shown profiles.
    Called when a user denies all current matches or requests new ones.

    If feedback is provided, compatibility signals are updated before re-querying
    Pinecone so the new batch reflects updated preferences — not just a random slice.

    Expected input:
        {
            "user_id":              "firebase_uid_abc123",
            "excluded_profile_ids": ["maya_001", "raj_002", "sarah_003"],
            "feedback":             "I want someone more adventurous"
        }

    Expected output:  3 new CoTravellerMatch objects, none in excluded_profile_ids
    """
    # TODO: verify auth
    # TODO: load user_profile from Firestore
    # TODO: regenerate_matches(user_profile, body.excluded_profile_ids, body.feedback)
    raise NotImplementedError
