from shared.schemas import Itinerary, UserProfile, ValidationResult, UpdateTripResponse
from shared.config import MAX_REFINEMENT_ATTEMPTS


async def run_refinement_loop(
    itinerary: Itinerary,
    user_profile: UserProfile,
    feedback: str,
    validation_result: ValidationResult,
) -> UpdateTripResponse:
    """
    Closed-loop regeneration. Iterates up to MAX_REFINEMENT_ATTEMPTS times until
    the validator approves or max attempts is reached.

    Loop:
        1. Re-rank & re-filter (Shreyas's ranking with adjusted constraints)
        2. Re-query Ali's generator with updated prompt (includes feedback + validation issues)
        3. Validator re-checks (rules → LLM critic)
        4. Push updated itinerary to Firestore after each attempt (live update for user)
        5. If approved → break
        6. If max attempts reached → return best result so far

    Expected input:
        itinerary        = Itinerary(...)           ← current failing itinerary
        user_profile     = UserProfile(...)
        feedback         = "I want more free time each day"
        validation_result = ValidationResult(status=REVISE, feedback="Too many activities on Day 3")

    Expected output:
        UpdateTripResponse(
            itinerary           = Itinerary(...),  # approved revised itinerary
            validation          = ValidationResult(status=approved, score=0.96),
            refinement_attempts = 2
        )
    """
    # TODO: implement loop up to MAX_REFINEMENT_ATTEMPTS
    # TODO: write to Firestore after each attempt so UI updates live
    raise NotImplementedError
