from fastapi import APIRouter, Depends, HTTPException
from shared.schemas import UpdateTripRequest, UpdateTripResponse, ValidationStatus
from mushahid.auth import verify_token
from mushahid.realtime.firestore import get_itinerary, write_itinerary
from mushahid.validation.critic import validate_large_output
from mushahid.utils.sanitize import sanitize_user_input

router = APIRouter()


@router.post("/update-trip", response_model=UpdateTripResponse)
async def update_trip(body: UpdateTripRequest, uid: str = Depends(verify_token)):
    itinerary = body.current_itinerary
    if itinerary is None:
        itinerary = await get_itinerary(body.itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    from shared.schemas import UserProfile
    user_profile = UserProfile(
        user_id=uid,
        display_name=uid,
        constraints=None,
        persona_answers=None,
    )

    feedback = sanitize_user_input(body.feedback or "")

    validation = await validate_large_output(itinerary, user_profile)

    if validation.status == ValidationStatus.revise or feedback:
        from mushahid.refinement.loop import run_refinement_loop
        best_itinerary = itinerary
        best_validation = validation
        attempt = 0
        async for event in run_refinement_loop(
            itinerary, user_profile,
            feedback=feedback,
            validation_result=validation,
            activity_feedback=body.activity_feedback,
        ):
            import json
            data = json.loads(event.split("data: ", 1)[-1])
            if "itinerary" in data:
                from shared.schemas import Itinerary, ValidationResult as VR
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
