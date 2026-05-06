from fastapi import APIRouter
from shared.schemas import UpdateTripRequest, UpdateTripResponse

router = APIRouter()


@router.post("/update-trip", response_model=UpdateTripResponse)
async def update_trip(request: UpdateTripRequest):
    """
    Refine an existing itinerary based on user feedback.
    Triggers the refinement loop, pushes result to Firestore.

    Expected input:
        UpdateTripRequest(
            itinerary_id      = "itin_abc123",
            user_id           = "firebase_uid_abc",
            feedback          = "I want more time at each place, fewer activities per day.",
            current_itinerary = Itinerary(...)
        )

    Expected output:
        UpdateTripResponse(
            itinerary           = Itinerary(...),  # revised itinerary
            validation          = ValidationResult(status="approved", score=0.96, ...),
            refinement_attempts = 1
        )
    """
    # TODO: verify auth, call refinement/loop.py, push result to Firestore
    raise NotImplementedError
