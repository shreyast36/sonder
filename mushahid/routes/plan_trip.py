from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from shared.schemas import PlanTripRequest

router = APIRouter()


@router.post("/plan-trip")
async def plan_trip(request: PlanTripRequest):
    """
    Generate a personalised itinerary. Returns a Server-Sent Events stream.
    Each event signals a pipeline stage completion so the frontend can update live.

    Expected SSE event sequence:
        event: persona_inferring
        data: {}

        event: persona_inferred
        data: {"archetype": "Cultural Explorer", "emotion": "excited"}

        event: retrieving
        data: {}

        event: retrieval_done
        data: {"destination_count": 8, "activity_count": 45}

        event: ranking
        data: {}

        event: ranked
        data: {"top_destination": "Bali, Indonesia"}

        event: generating
        data: {}

        event: itinerary_generated
        data: {}

        event: explaining
        data: {}

        event: validating
        data: {}

        event: revision          ← only emitted if validator returns REVISE
        data: {"attempt": 1, "reason": "Budget exceeded by $120"}

        event: validated
        data: {"score": 0.94}

        event: matching_cotravellers
        data: {}

        event: matched
        data: {"match_count": 3}

        event: done
        data: { ...PlanTripResponse as JSON... }

    Auth: verify Firebase ID token from Authorization header before processing.
    """
    # TODO: verify auth token
    # TODO: return StreamingResponse(orchestrator.run_plan_trip_pipeline(request.user_profile), media_type="text/event-stream")
    raise NotImplementedError
