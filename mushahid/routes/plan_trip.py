from fastapi import APIRouter, Depends, Request
from shared.schemas import PlanTripRequest, UserProfile
from shared.config import PLAN_TRIP_RATE_LIMIT
from mushahid.main import limiter
from mushahid.auth import verify_token
from mushahid.realtime.sse import stream_pipeline_events
from mushahid.realtime.firestore import get_user_profile
from mushahid.pipeline import orchestrator

router = APIRouter()


def _uid_rate_key(request: Request) -> str:
    # Rate-limit per authenticated user via their Bearer token, not by IP.
    # Users behind the same NAT/proxy would otherwise share a single limit.
    auth = request.headers.get("Authorization", "").strip()
    return auth if auth else (request.client.host if request.client else "anonymous")


@router.post("/plan-trip")
@limiter.limit(PLAN_TRIP_RATE_LIMIT, key_func=_uid_rate_key)
async def plan_trip(request: Request, body: PlanTripRequest, uid: str = Depends(verify_token)):
    profile_doc = await get_user_profile(uid)
    display_name = profile_doc.get("display_name", "") if profile_doc else ""

    user_profile = UserProfile(
        user_id=uid,
        display_name=display_name,
        constraints=body.constraints,
        persona_answers=body.persona_answers,
    )
    return stream_pipeline_events(orchestrator.run_plan_trip_pipeline(user_profile))
