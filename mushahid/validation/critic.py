import json
import openai
import anthropic
from ali.generation.output_parser import _strip_fences
from shared.schemas import Itinerary, UserProfile, ValidationResult, ValidationStatus
from shared.config import (
    SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME,
    LARGE_VALIDATOR_PROVIDER, LARGE_VALIDATOR_MODEL_NAME,
    OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY,
)

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"

_small_client = None
_large_client = None


def _make_client(provider: str):
    if provider == "deepseek":
        return openai.AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=_DEEPSEEK_BASE_URL)
    if provider == "openai":
        return openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    if provider == "anthropic":
        return anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    raise ValueError(f"Unsupported validator provider: '{provider}'")


def _get_small_client():
    global _small_client
    if _small_client is None:
        _small_client = _make_client(SMALL_VALIDATOR_PROVIDER or "deepseek")
    return _small_client


def _get_large_client():
    global _large_client
    if _large_client is None:
        _large_client = _make_client(LARGE_VALIDATOR_PROVIDER or "deepseek")
    return _large_client


async def _call_llm(client, provider: str, model: str, prompt: str, system: str) -> str:
    if provider == "anthropic":
        response = await client.messages.create(
            model=model,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        return response.content[0].text
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=512,
    )
    return response.choices[0].message.content


def _parse_validation_result(itinerary_id: str, raw: str) -> ValidationResult:
    try:
        data = json.loads(_strip_fences(raw))
        return ValidationResult(
            itinerary_id=itinerary_id,
            status=ValidationStatus(data["status"]),
            score=float(data["score"]),
            feedback=data.get("feedback", ""),
            improvement_suggestions=data.get("improvement_suggestions", []),
        )
    except Exception:
        return ValidationResult(
            itinerary_id=itinerary_id,
            status=ValidationStatus.revise,
            score=0.0,
            feedback="Validation parse error — flagging for revision.",
            improvement_suggestions=[],
        )


def _itinerary_summary(itinerary: Itinerary) -> str:
    lines = [
        f"Destination: {itinerary.destination.city}, {itinerary.destination.country}",
        f"Total budget: ${itinerary.total_budget_usd:.0f}",
        f"Days: {len(itinerary.days)}",
    ]
    for day in itinerary.days:
        acts = ", ".join(ia.activity.name for ia in day.activities)
        lines.append(f"  Day {day.day_number} ({day.theme or 'no theme'}, ${day.daily_cost_usd:.0f}): {acts}")
    return "\n".join(lines)


def _constraints_summary(user_profile: UserProfile) -> str:
    c = user_profile.constraints
    if not c:
        return "No constraints provided."
    parts = [
        f"Budget: ${c.budget_usd:.0f}",
        f"Duration: {(c.end_date - c.start_date).days} days",
        f"Pace: {c.pace_preference.value}",
    ]
    if c.must_haves:
        parts.append(f"Must-haves: {', '.join(c.must_haves)}")
    if c.avoid_list:
        parts.append(f"Avoid: {', '.join(c.avoid_list)}")
    return " | ".join(parts)


_CRITIC_SYSTEM = (
    "You are a travel itinerary quality reviewer. "
    "Evaluate the itinerary against the user's constraints and preferences. "
    "Respond ONLY with valid JSON matching this schema exactly:\n"
    '{"status": "approved" | "revise", "score": 0.0-1.0, '
    '"feedback": "one sentence", "improvement_suggestions": ["..."]}'
)


def _critic_prompt(itinerary: Itinerary, user_profile: UserProfile) -> str:
    return (
        f"User constraints: {_constraints_summary(user_profile)}\n\n"
        f"Itinerary:\n{_itinerary_summary(itinerary)}\n\n"
        "Review for: realistic pacing, budget fit, must-haves included, avoid-list respected, "
        "logical day sequencing. Score 0-1. If score >= 0.75 use status=approved, else revise."
    )


async def validate_small_output(itinerary: Itinerary, user_profile: UserProfile) -> ValidationResult:
    """
    Quick LLM sanity check using the small validator model.
    Use for mid-refinement checks where speed matters more than depth.
    """
    provider = SMALL_VALIDATOR_PROVIDER or "deepseek"
    model = SMALL_VALIDATOR_MODEL_NAME or "deepseek-chat"
    raw = await _call_llm(_get_small_client(), provider, model, _critic_prompt(itinerary, user_profile), _CRITIC_SYSTEM)
    return _parse_validation_result(itinerary.itinerary_id, raw)


async def validate_large_output(itinerary: Itinerary, user_profile: UserProfile) -> ValidationResult:
    """
    Thorough LLM review using the large validator model.
    Use for final approval before returning the itinerary to the user.
    """
    provider = LARGE_VALIDATOR_PROVIDER or "deepseek"
    model = LARGE_VALIDATOR_MODEL_NAME or "deepseek-chat"
    raw = await _call_llm(_get_large_client(), provider, model, _critic_prompt(itinerary, user_profile), _CRITIC_SYSTEM)
    return _parse_validation_result(itinerary.itinerary_id, raw)
