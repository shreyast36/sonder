import json
import logging
import openai
import anthropic
from ali.generation.output_parser import _strip_fences
from shared.schemas import Itinerary, UserProfile, ValidationResult, ValidationStatus
from shared.config import (
    SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME,
    LARGE_VALIDATOR_PROVIDER, LARGE_VALIDATOR_MODEL_NAME,
    OPENAI_API_KEY, ANTHROPIC_API_KEY, NVIDIA_API_KEY,
)

logger = logging.getLogger(__name__)

_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

_small_client = None
_large_client = None


def _make_client(provider: str):
    if provider == "nvidia":
        return openai.AsyncOpenAI(api_key=NVIDIA_API_KEY, base_url=_NVIDIA_BASE_URL)
    if provider == "openai":
        return openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    if provider == "anthropic":
        return anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    raise ValueError(f"Unsupported validator provider: '{provider}'")


def _get_small_client():
    global _small_client
    if _small_client is None:
        if not SMALL_VALIDATOR_PROVIDER:
            raise RuntimeError("SMALL_VALIDATOR_PROVIDER is not set (nvidia | openai | anthropic)")
        _small_client = _make_client(SMALL_VALIDATOR_PROVIDER)
    return _small_client


def _get_large_client():
    global _large_client
    if _large_client is None:
        if not LARGE_VALIDATOR_PROVIDER:
            raise RuntimeError("LARGE_VALIDATOR_PROVIDER is not set (nvidia | openai | anthropic)")
        _large_client = _make_client(LARGE_VALIDATOR_PROVIDER)
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

    # NVIDIA NIM's OpenAI-compatible endpoint rejects max_completion_tokens
    # as an unknown field — it only accepts max_tokens. OpenAI proper
    # supports both, but max_completion_tokens is the post-o1 spelling.
    token_kwargs = {"max_tokens": 512} if provider == "nvidia" else {"max_completion_tokens": 512}
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        **token_kwargs,
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
    pace = c.pace.value if c.pace else "moderate"
    duration = (c.end_date - c.start_date).days if (c.start_date and c.end_date) else "?"
    parts = [
        f"Budget: ${c.budget_usd:.0f}",
        f"Duration: {duration} days",
        f"Pace: {pace}",
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
    if not SMALL_VALIDATOR_PROVIDER or not SMALL_VALIDATOR_MODEL_NAME:
        raise RuntimeError("SMALL_VALIDATOR_PROVIDER and SMALL_VALIDATOR_MODEL_NAME must be set")
    raw = await _call_llm(
        _get_small_client(), SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME,
        _critic_prompt(itinerary, user_profile), _CRITIC_SYSTEM,
    )
    return _parse_validation_result(itinerary.itinerary_id, raw)


async def validate_large_output(itinerary: Itinerary, user_profile: UserProfile) -> ValidationResult:
    """
    Thorough LLM review using the large validator model.
    Use for final approval before returning the itinerary to the user.
    """
    if not LARGE_VALIDATOR_PROVIDER or not LARGE_VALIDATOR_MODEL_NAME:
        raise RuntimeError("LARGE_VALIDATOR_PROVIDER and LARGE_VALIDATOR_MODEL_NAME must be set")
    raw = await _call_llm(
        _get_large_client(), LARGE_VALIDATOR_PROVIDER, LARGE_VALIDATOR_MODEL_NAME,
        _critic_prompt(itinerary, user_profile), _CRITIC_SYSTEM,
    )
    return _parse_validation_result(itinerary.itinerary_id, raw)


# ── Persona reveal validator (small tier, cross-provider) ─────────────────────

_PERSONA_VALIDATOR_SYSTEM = (
    "You are a strict quality reviewer for an app's persona-reveal output. "
    "You receive the original user signals and the LLM-generated persona reveal. "
    "Your job is to check three things and ONLY these three things:\n"
    "  1. Tone — the descriptor/paragraph/bullets must NOT sound like a horoscope, "
    "MBTI label, or psychometric report. They must read as concrete observation.\n"
    "  2. Echo — the bullets must paraphrase the user's actual selections, not "
    "invent details the user never said.\n"
    "  3. No itinerary — the output must contain zero trip/itinerary suggestions "
    "(no destinations, days, activities, restaurants, hotels).\n\n"
    "Respond with valid JSON ONLY:\n"
    '{"valid": true | false, "issues": ["short reason", ...]}\n'
    "issues is empty when valid is true. No preamble, no markdown."
)


def _persona_validator_prompt(user_signals: str, persona_output: dict) -> str:
    return (
        f"USER SIGNALS:\n{user_signals}\n\n"
        f"PERSONA OUTPUT:\n{json.dumps(persona_output, ensure_ascii=False)}\n\n"
        "Apply the three checks. Return JSON."
    )


async def validate_persona(user_signals: str, persona_output: dict) -> tuple[bool, list[str]]:
    """
    Cross-provider semantic check on the persona reveal output.
    Runs the small validator (NVIDIA Nemotron Nano by default). Returns
    (valid, issues). Structural checks (dim IDs, counts) live in
    mushahid/routes/persona.py — this only catches tone + echo + scope drift.

    Fails OPEN: on any validator error, returns (True, []) — the validator
    is a quality gate, not a correctness gate, so we don't want to break the
    user flow if it's unavailable.
    """
    try:
        if not SMALL_VALIDATOR_PROVIDER or not SMALL_VALIDATOR_MODEL_NAME:
            raise RuntimeError("SMALL_VALIDATOR_PROVIDER / SMALL_VALIDATOR_MODEL_NAME not configured")
        raw = await _call_llm(
            _get_small_client(), SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME,
            _persona_validator_prompt(user_signals, persona_output),
            _PERSONA_VALIDATOR_SYSTEM,
        )
        data = json.loads(_strip_fences(raw))
        return bool(data.get("valid", True)), [str(x) for x in data.get("issues", [])]
    except Exception as e:
        logger.warning("persona validator failed open: %s", e)
        return True, []
