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

    # Online weight updates from this edit, fire-and-forget so they don't
    # block the user's refinement response. Free-text feedback nudges the
    # cotraveller + destination + activity weights via keyword map; the
    # structured per-activity edits go to feature_logging for V2 gradient
    # learning once we accumulate replacement deltas.
    if feedback or activity_feedback:
        try:
            import asyncio as _asyncio
            _asyncio.create_task(_apply_ranker_feedback(uid, feedback, activity_feedback))
        except Exception:
            pass

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


async def _apply_ranker_feedback(uid: str, feedback_text: str, activity_feedback: list) -> None:
    """Online weight updates from a /update-trip edit.

    Free-text feedback runs the keyword→feature map for each ranking
    surface; the result is merged into the user's compatibility_signals.
    Structured per-activity edits (swap/remove/adjust_time) get logged via
    feature_logging so V2 can later compute replacement-gradient updates
    once enough delta data accumulates.

    All work happens off the request path — failures are logged at debug
    and never raised.
    """
    import logging
    log = logging.getLogger(__name__)
    try:
        from mushahid.realtime.firestore import get_user_profile, write_user_ranker_weights
        from shreyas.ranking.feedback import apply_text_feedback
        from shreyas.ranking.policies import load_policy

        profile = await get_user_profile(uid) or {}
        cs = dict(profile.get("compatibility_signals") or {})
        existing = dict(cs.get("ranker_weights") or {})

        if feedback_text:
            for surface in ("cotraveller", "destination", "activity"):
                try:
                    policy = load_policy(surface)
                    current = dict(existing.get(surface) or {})
                    new_weights, boosted = apply_text_feedback(current, feedback_text, policy)
                    if boosted:
                        await write_user_ranker_weights(uid, surface, new_weights)
                        log.info("ranker weights updated for uid=%s surface=%s boosted=%s",
                                 uid, surface, boosted)
                except Exception as e:
                    log.debug("apply_text_feedback failed for surface=%s: %s", surface, e)

        if activity_feedback:
            from shreyas.ranking.feature_logging import record_event
            for af in activity_feedback:
                # ActivityFeedback shape: {activity_id, action, reason?}
                try:
                    record_event(
                        uid=uid,
                        surface="activity",
                        kind=getattr(af, "action", "edit"),
                        candidate=type("_Lite", (), {
                            "activity_id": getattr(af, "activity_id", None)
                        })(),
                        reason=getattr(af, "reason", None),
                    )
                except Exception as e:
                    log.debug("record_event failed: %s", e)
    except Exception as e:
        log.debug("ranker feedback task failed: %s", e)
