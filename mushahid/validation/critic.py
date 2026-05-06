from shared.schemas import Itinerary, UserProfile, ValidationResult, ValidationStatus
from ali.routing.engine import route_request


async def validate_with_llm(itinerary: Itinerary, user_profile: UserProfile) -> ValidationResult:
    """
    LLM-based quality validation via the VALIDATOR model tier.
    Run this after run_all_checks() passes — the LLM catches qualitative issues
    that rules can't (e.g. unrealistic travel times, poor activity sequencing).

    Expected input:
        itinerary    = Itinerary(days=[...], total_budget_usd=1950)
        user_profile = UserProfile(constraints=TripConstraints(budget_usd=2000, pace="relaxed"))

    Expected output (approved):
        ValidationResult(
            itinerary_id           = "itin_abc123",
            status                 = ValidationStatus.approved,
            constraint_satisfaction = ConstraintSatisfaction(budget_ok=True, ...),
            score                  = 0.94,
            feedback               = "Well-paced itinerary with great cultural balance.",
            improvement_suggestions = []
        )

    Expected output (revise):
        ValidationResult(
            itinerary_id           = "itin_abc123",
            status                 = ValidationStatus.revise,
            score                  = 0.61,
            feedback               = "Day 3 has 6 activities which is too many for a relaxed pace.",
            improvement_suggestions = ["Reduce Day 3 to 3 activities", "Move Tanah Lot to Day 4"]
        )
    """
    # TODO: build critic prompt (include itinerary JSON + user constraints + persona)
    # TODO: route_request("validate_itinerary", prompt, system) → raw response
    # TODO: parse response into ValidationResult
    raise NotImplementedError
