from pydantic import BaseModel
from jahnvi.schemas.user import TripConstraints, PersonaQuestionAnswers, UserProfile
from jahnvi.schemas.trip import Itinerary
from jahnvi.schemas.cotraveller import CoTravellerMatch
from jahnvi.schemas.validation import ValidationResult
from jahnvi.schemas.enums import VisaRequirement


# ── Visa ─────────────────────────────────────────────────────────────────────────

class VisaInfo(BaseModel):
    """
    Response from GET /visa-check.

    Example:
        VisaInfo(
            destination_country = "Portugal",
            nationality         = "US",
            requirement         = VisaRequirement.visa_free,
            notes               = "US citizens can stay up to 90 days without a visa."
        )
    """
    destination_country: str
    nationality:         str
    requirement:         VisaRequirement
    notes:               str


# ── Plan Trip ─────────────────────────────────────────────────────────────────────

class PlanTripRequest(BaseModel):
    """
    Request body for POST /plan-trip.
    user_id is also extracted from the auth token — include in body for convenience.

    Example:
        PlanTripRequest(
            user_id         = "firebase_uid_abc123",
            constraints     = TripConstraints(destination_type="beach", budget_usd=2000, ...),
            persona_answers = PersonaQuestionAnswers(food_interest=5, culture_interest=4, ...)
        )
    """
    user_id:         str
    constraints:     TripConstraints
    persona_answers: PersonaQuestionAnswers


class PlanTripResponse(BaseModel):
    """
    Payload of the final "done" SSE event from POST /plan-trip.

    Example:
        PlanTripResponse(
            itinerary  = Itinerary(itinerary_id="itin_abc123", destination=..., days=[...]),
            matches    = [CoTravellerMatch(...), CoTravellerMatch(...), CoTravellerMatch(...)],
            validation = ValidationResult(status=approved, score=0.94, ...)
        )
    """
    itinerary:  Itinerary
    matches:    list[CoTravellerMatch]
    validation: ValidationResult


# ── Update Trip ───────────────────────────────────────────────────────────────────

class UpdateTripRequest(BaseModel):
    """
    Request body for POST /update-trip.

    Example:
        UpdateTripRequest(
            itinerary_id      = "itin_abc123",
            feedback          = "I want more free time each day, fewer activities.",
            current_itinerary = Itinerary(...)
        )
    """
    itinerary_id:       str
    feedback:           str
    current_itinerary:  Itinerary


class UpdateTripResponse(BaseModel):
    """
    Response from POST /update-trip.

    reached_max_attempts=True means the refinement loop gave up after
    MAX_REFINEMENT_ATTEMPTS tries. The itinerary is the best result found —
    not validator-approved. The frontend should show a soft warning:
    "We couldn't fully optimise this — here's the best version we found."

    Example (approved after 2 tries):
        UpdateTripResponse(
            itinerary            = Itinerary(...),
            validation           = ValidationResult(status=approved, score=0.96),
            refinement_attempts  = 2,
            reached_max_attempts = False
        )
    """
    itinerary:            Itinerary
    validation:           ValidationResult
    refinement_attempts:  int
    reached_max_attempts: bool = False
