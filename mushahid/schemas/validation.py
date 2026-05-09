from pydantic import BaseModel
from mushahid.schemas.enums import ValidationStatus


class ConstraintSatisfaction(BaseModel):
    """
    Output of validation/rules.py run_all_checks().
    One boolean per deterministic rule — all must be True before LLM critic runs.

    Example:
        ConstraintSatisfaction(
            budget_ok     = True,
            duration_ok   = True,
            pace_ok       = False,  # 4.2 avg activities/day exceeds relaxed threshold of 3
            must_haves_ok = True,
            avoid_list_ok = True
        )
    """
    budget_ok:     bool
    duration_ok:   bool
    pace_ok:       bool
    must_haves_ok: bool
    avoid_list_ok: bool

    @property
    def all_passed(self) -> bool:
        return all([self.budget_ok, self.duration_ok, self.pace_ok, self.must_haves_ok, self.avoid_list_ok])


class ValidationResult(BaseModel):
    """
    Output of validation/critic.py validate_large_output().
    Returned in UpdateTripResponse and emitted in the "validated" SSE event.

    Example (approved):
        ValidationResult(
            itinerary_id            = "itin_abc123",
            status                  = ValidationStatus.approved,
            score                   = 0.94,
            feedback                = "Well-paced itinerary with great cultural balance.",
            improvement_suggestions = []
        )

    Example (revise):
        ValidationResult(
            itinerary_id            = "itin_abc123",
            status                  = ValidationStatus.revise,
            score                   = 0.61,
            feedback                = "Day 3 has 6 activities — too many for a relaxed pace.",
            improvement_suggestions = ["Reduce Day 3 to 3 activities", "Move Tanah Lot to Day 4"]
        )
    """
    itinerary_id:            str
    status:                  ValidationStatus
    score:                   float           # 0.0 to 1.0
    feedback:                str
    improvement_suggestions: list[str] = []
