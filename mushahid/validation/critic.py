from shared.schemas import Itinerary, UserProfile, ValidationResult, ValidationStatus
from shared.config import SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME, \
                          LARGE_VALIDATOR_PROVIDER, LARGE_VALIDATOR_MODEL_NAME


def _get_validator_client(provider: str, model_name: str):
    """Instantiate the correct LLM client for the given provider."""
    # TODO: import and return the matching client from ali/clients/
    # e.g. provider="anthropic" → AnthropicClient(model_name=model_name)
    raise NotImplementedError


async def validate_small_output(output: str, context: dict) -> ValidationResult:
    """
    Validates outputs from the Small LLM (persona labels, chat topics, icebreakers).
    Uses the Small Validator configured via SMALL_VALIDATOR_PROVIDER in .env.

    Expected output (approved):
        ValidationResult(status=ValidationStatus.approved, score=0.95, feedback="...")

    Expected output (revise):
        ValidationResult(status=ValidationStatus.revise, score=0.55,
                         feedback="Persona label doesn't match answers.",
                         improvement_suggestions=["Try 'Relaxed Wanderer' instead"])
    """
    # TODO: instantiate _get_validator_client(SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME)
    # TODO: build prompt from output + context
    # TODO: call client.complete(prompt, system) → raw response
    # TODO: parse response into ValidationResult
    raise NotImplementedError


async def validate_large_output(itinerary: Itinerary, user_profile: UserProfile) -> ValidationResult:
    """
    Validates outputs from the Large LLM (full itineraries).
    Uses the Large Validator configured via LARGE_VALIDATOR_PROVIDER in .env.
    Run after run_all_checks() passes — catches qualitative issues rules can't
    (e.g. unrealistic travel times, poor activity sequencing).

    Expected output (approved):
        ValidationResult(
            itinerary_id            = "itin_abc123",
            status                  = ValidationStatus.approved,
            score                   = 0.94,
            feedback                = "Well-paced itinerary with great cultural balance.",
            improvement_suggestions = []
        )

    Expected output (revise):
        ValidationResult(
            itinerary_id            = "itin_abc123",
            status                  = ValidationStatus.revise,
            score                   = 0.61,
            feedback                = "Day 3 has 6 activities which is too many for a relaxed pace.",
            improvement_suggestions = ["Reduce Day 3 to 3 activities", "Move Tanah Lot to Day 4"]
        )
    """
    # TODO: instantiate _get_validator_client(LARGE_VALIDATOR_PROVIDER, LARGE_VALIDATOR_MODEL_NAME)
    # TODO: build critic prompt (itinerary JSON + user constraints + persona)
    # TODO: call client.complete(prompt, system) → raw response
    # TODO: parse response into ValidationResult
    raise NotImplementedError
