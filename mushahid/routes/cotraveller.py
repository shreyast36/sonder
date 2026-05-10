from fastapi import APIRouter, Depends
from pydantic import BaseModel
from shared.schemas import CoTravellerMatch
from mushahid.auth import verify_token

router = APIRouter()


@router.post("/cotraveller", response_model=list[CoTravellerMatch])
async def get_cotraveller_matches(user_id: str, itinerary_id: str, uid: str = Depends(verify_token)):
    try:
        from shreyas.retrieval.search import search_cotravellers
        from shreyas.cotraveller.matching import get_top_matches
        from shared.schemas import UserProfile
        user_profile = UserProfile(user_id=user_id, display_name=uid, constraints=None, persona_answers=None)
        candidates = search_cotravellers(user_profile, itinerary_id)
        return get_top_matches(user_profile, candidates)
    except NotImplementedError:
        return []


class RegenerateMatchesRequest(BaseModel):
    user_id: str
    excluded_profile_ids: list[str]
    feedback: str = ""


@router.post("/cotraveller/regenerate", response_model=list[CoTravellerMatch])
async def regenerate_cotraveller_matches(body: RegenerateMatchesRequest, uid: str = Depends(verify_token)):
    try:
        from shreyas.retrieval.search import search_cotravellers
        from shreyas.cotraveller.matching import get_top_matches
        from ali.vector.embeddings import build_refined_query, embed_text
        from mushahid.utils.sanitize import sanitize_user_input
        from shared.schemas import UserProfile

        feedback = sanitize_user_input(body.feedback)
        user_profile = UserProfile(user_id=body.user_id, display_name=uid, constraints=None, persona_answers=None)

        if feedback:
            user_profile = user_profile.model_copy(update={
                "travel_style_embedding": await embed_text(build_refined_query(user_profile, feedback))
            })

        candidates = search_cotravellers(user_profile)
        all_matches = get_top_matches(user_profile, candidates)
        return [m for m in all_matches if m.profile.profile_id not in body.excluded_profile_ids]
    except NotImplementedError:
        return []
