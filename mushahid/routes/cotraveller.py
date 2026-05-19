"""
Co-traveller matching endpoints.

These are user-triggered (Dashboard "Find companions" / "Show different
matches"); the orchestrator pipeline also computes matches at the end of
plan-trip and stuffs them into the `done` SSE payload.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from shared.schemas import CoTravellerMatch, UserProfile, TripConstraints, PersonaQuestionAnswers
from mushahid.auth import verify_token
from mushahid.realtime.firestore import get_user_profile, get_itinerary
from mushahid.utils.sanitize import sanitize_user_input

router = APIRouter()
logger = logging.getLogger(__name__)


async def _load_user_profile(uid: str, itinerary_id: str | None = None) -> UserProfile:
    """Rehydrate a UserProfile from Firestore so matching has the same signals
    the user fed into plan-trip. Falls back to a near-empty profile when
    Firestore is unavailable so matching can still run with whatever we have."""
    raw = await get_user_profile(uid) or {}
    constraints = None
    persona_answers = None
    if raw.get("constraints"):
        try: constraints = TripConstraints.model_validate(raw["constraints"])
        except Exception as e: logger.warning("constraints rehydrate failed: %s", e)
    if raw.get("persona_answers"):
        try: persona_answers = PersonaQuestionAnswers.model_validate(raw["persona_answers"])
        except Exception as e: logger.warning("persona_answers rehydrate failed: %s", e)
    profile = UserProfile(
        user_id=uid,
        display_name=raw.get("display_name") or "Traveller",
        constraints=constraints,
        persona_answers=persona_answers,
        compatibility_signals=raw.get("compatibility_signals") or {},
        travel_style_embedding=raw.get("travel_style_embedding") or [],
    )
    # If an itinerary_id was given, prefer that trip's constraints over the
    # profile-level ones — matches should reflect the trip the user is on.
    if itinerary_id:
        try:
            it = await get_itinerary(itinerary_id)
            if it and it.user_id == uid:
                # Itinerary doesn't carry constraints directly today; placeholder
                # for when we do attach them.
                pass
        except Exception as e:
            logger.warning("itinerary rehydrate failed: %s", e)
    return profile


class MatchesRequest(BaseModel):
    itinerary_id: str | None = None


@router.post("/cotraveller", response_model=list[CoTravellerMatch])
async def get_cotraveller_matches(body: MatchesRequest, uid: str = Depends(verify_token)):
    """Top matches for the signed-in user (optionally scoped to a specific trip)."""
    from shreyas.retrieval.search import search_cotravellers
    from shreyas.cotraveller.matching import get_top_matches
    from mushahid.monitoring import capture
    try:
        profile = await _load_user_profile(uid, body.itinerary_id)
        candidates = await search_cotravellers(profile)
        matches = get_top_matches(profile, candidates)
        capture(uid, "match_found", {"match_count": len(matches), "itinerary_id": body.itinerary_id})
        return matches
    except Exception as e:
        logger.error("cotraveller match failed for %s: %s", uid, e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"matching failed: {type(e).__name__}: {e}") from e


class RegenerateMatchesRequest(BaseModel):
    excluded_profile_ids: list[str] = []
    feedback: str = ""


@router.post("/cotraveller/regenerate", response_model=list[CoTravellerMatch])
async def regenerate_cotraveller_matches(body: RegenerateMatchesRequest, uid: str = Depends(verify_token)):
    """Fresh batch skipping already-shown profiles. Feedback (sanitised) refines
    the user's persona vector before re-querying so 'someone more adventurous'
    actually pulls different candidates instead of just rolling the dice."""
    from shreyas.cotraveller.matching import regenerate_matches
    try:
        profile = await _load_user_profile(uid)
        feedback = sanitize_user_input(body.feedback)
        return await regenerate_matches(profile, body.excluded_profile_ids, feedback=feedback)
    except Exception as e:
        logger.error("cotraveller regenerate failed for %s: %s", uid, e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"matching failed: {type(e).__name__}: {e}") from e
