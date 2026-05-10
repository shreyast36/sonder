import json
from fastapi import APIRouter, Depends, HTTPException, Request
from shared.schemas import UpdateTripRequest, UpdateTripResponse, ValidationStatus, UserProfile, Itinerary, ValidationResult as VR
from shared.config import UPDATE_TRIP_RATE_LIMIT
from mushahid.auth import verify_token
from mushahid.main import limiter
from mushahid.realtime.firestore import get_itinerary, write_itinerary, get_user_profile
from mushahid.validation.critic import validate_large_output
from mushahid.refinement.loop import run_refinement_loop
from mushahid.utils.sanitize import sanitize_user_input

router = APIRouter()


@router.post("/update-trip", response_model=UpdateTripResponse)
@limiter.limit(UPDATE_TRIP_RATE_LIMIT)
async def update_trip(request: Request, body: UpdateTripRequest, uid: str = Depends(verify_token)):
    itinerary = body.current_itinerary
    if itinerary is None:
        itinerary = await get_itinerary(body.itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised to update this itinerary")

    profile_doc = await get_user_profile(uid)
    display_name = profile_doc.get("display_name", "") if profile_doc else ""

    user_profile = UserProfile(
        user_id=uid,
        display_name=display_name,
        constraints=None,
        persona_answers=None,
    )

    feedback = sanitize_user_input(body.feedback or "")
    activity_feedback = [
        af.model_copy(update={"reason": sanitize_user_input(af.reason) if af.reason else None})
        for af in body.activity_feedback
    ]
    validation = await validate_large_output(itinerary, user_profile)

    if validation.status == ValidationStatus.revise or feedback:
        best_itinerary = itinerary
        best_validation = validation
        attempt = 0
        data: dict = {}
        async for event in run_refinement_loop(
            itinerary, user_profile,
            feedback=feedback,
            validation_result=validation,
            activity_feedback=activity_feedback,
        ):
            data = json.loads(event.split("data: ", 1)[-1])
            if "itinerary" in data:
                best_itinerary = Itinerary.model_validate(data["itinerary"])
                best_validation = VR.model_validate(data["validation"])
                attempt = data["refinement_attempts"]

        await write_itinerary(best_itinerary)
        return UpdateTripResponse(
            itinerary=best_itinerary,
            validation=best_validation,
            refinement_attempts=attempt,
            reached_max_attempts=data.get("reached_max_attempts", False),
        )

    await write_itinerary(itinerary)
    return UpdateTripResponse(
        itinerary=itinerary,
        validation=validation,
        refinement_attempts=0,
    )
