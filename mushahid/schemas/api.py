from pydantic import BaseModel
from typing import Literal, Optional
from jahnvi.schemas.user import TripConstraints, PersonaQuestionAnswers, UserProfile
from ali.schemas.trip import Itinerary
from shreyas.schemas.cotraveller import CoTravellerMatch
from mushahid.schemas.validation import ValidationResult
from mushahid.schemas.enums import VisaRequirement


# ── Visa ──────────────────────────────────────────────────────────────────────

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


# ── Plan Trip ─────────────────────────────────────────────────────────────────

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


# ── Update Trip ───────────────────────────────────────────────────────────────

class ActivityFeedback(BaseModel):
    """
    Per-activity feedback submitted when the user taps "swap" or thumbs-down on an
    activity card. Passed alongside free-text feedback in UpdateTripRequest so the
    refinement loop can apply targeted changes instead of rewriting the whole itinerary.

    action values:
        "swap"        — replace this activity with something different
        "remove"      — drop this activity entirely, free up the time slot
        "adjust_time" — keep the activity but move it (reason should specify when)

    Example:
        ActivityFeedback(
            activity_id = "uluwatu_001",
            action      = "swap",
            reason      = "Not into temples — prefer something more active"
        )
    """
    activity_id: str
    action:      Literal["swap", "remove", "adjust_time"]
    reason:      Optional[str] = None


class UpdateTripRequest(BaseModel):
    """
    Request body for POST /update-trip.

    Send either free-text feedback, per-activity feedback, or both.
    The refinement loop converts activity_feedback to structured signal updates
    before re-embedding — so targeted swaps don't pollute the whole profile.

    Example (free-text only):
        UpdateTripRequest(
            itinerary_id      = "itin_abc123",
            feedback          = "I want more free time each day, fewer activities.",
            current_itinerary = Itinerary(...)
        )

    Example (per-activity):
        UpdateTripRequest(
            itinerary_id      = "itin_abc123",
            feedback          = "",
            activity_feedback = [
                ActivityFeedback(activity_id="uluwatu_001", action="swap", reason="prefer active over temples"),
                ActivityFeedback(activity_id="seminyak_001", action="remove")
            ],
            current_itinerary = Itinerary(...)
        )
    """
    itinerary_id:      str
    feedback:          str = ""
    activity_feedback: list[ActivityFeedback] = []
    current_itinerary: Itinerary


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


# ── Export ────────────────────────────────────────────────────────────────────

class EmailItineraryRequest(BaseModel):
    """
    Request body for POST /export/email.

    Example:
        EmailItineraryRequest(
            itinerary_id  = "itin_abc123",
            recipients    = ["user@example.com", "cotraveller@example.com"],
            include_notes = True
        )
    """
    itinerary_id:  str
    recipients:    list[str]
    include_notes: bool = True
