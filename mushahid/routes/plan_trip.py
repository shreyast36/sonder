from fastapi import APIRouter, Depends, Request
from shared.schemas import PlanTripRequest, UserProfile
from mushahid.main import limiter
from mushahid.auth import verify_token
from mushahid.realtime.sse import stream_pipeline_events
from mushahid.pipeline import orchestrator

router = APIRouter()


@router.post("/plan-trip")
@limiter.limit("5/hour")
async def plan_trip(request: Request, body: PlanTripRequest, uid: str = Depends(verify_token)):
    user_profile = UserProfile(
        user_id=body.user_id,
        display_name=uid,
        constraints=body.constraints,
        persona_answers=body.persona_answers,
    )
    return stream_pipeline_events(orchestrator.run_plan_trip_pipeline(user_profile))
