"""
Validator orchestrators — wraps `mushahid.validation.validator_engine` so the
existing route + orchestrator callers don't have to change.

This module owns:
  - The LLM client adapters (OpenAI / Anthropic / NVIDIA NIM)
  - Function signatures the rest of the codebase already imports
    (validate_small_output, validate_large_output, validate_persona)

All prompt text, decision logic, severity taxonomy, and orchestration shape
lives in `validator_engine.py`. This file just plumbs LLM calls through it.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import openai
import anthropic

from shared.schemas import Itinerary, UserProfile, ValidationResult, ValidationStatus
from shared.config import (
    SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME,
    LARGE_VALIDATOR_PROVIDER, LARGE_VALIDATOR_MODEL_NAME,
    OPENAI_API_KEY, ANTHROPIC_API_KEY, NVIDIA_API_KEY,
)
from mushahid.validation.validator_engine import (
    ValidatorEngineConfig,
    BackendValidationDecision,
    CHAT_HARD_FAIL_CATEGORIES, CHAT_DENIED_CATEGORIES,
    MATCH_HARD_FAIL_CATEGORIES, PERSONA_HARD_FAIL_CATEGORIES,
    enforce_itinerary_decision,
    enforce_boolean_validator_decision,
    parse_json_object,
    validate_and_repair_chat_reply,
)

logger = logging.getLogger(__name__)

_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

_small_client = None
_large_client = None

# Single shared config — every validator call reads prompts + thresholds
# from here. Replace at import time if you want to plug in a custom
# semantic_slop_stems list or override the approval threshold.
ENGINE_CONFIG = ValidatorEngineConfig()


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


async def _call_llm(client, provider: str, model: str, prompt: str, system: str, *, max_tokens: int = 2048) -> str:
    """Single LLM call returning raw text. max_tokens defaults higher
    than the original 1024 because reasoning-style validator models
    (gpt-5-mini, nvidia-nemotron) burn part of the budget on internal
    reasoning before emitting visible output — at 1024 the visible
    JSON was getting truncated to "" and the caller failed JSON parse.
    """
    if provider == "anthropic":
        response = await client.messages.create(
            model=model,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.content[0].text

    # NVIDIA NIM's OpenAI-compatible endpoint rejects max_completion_tokens
    # as an unknown field — it only accepts max_tokens. OpenAI proper
    # supports both, but max_completion_tokens is the post-o1 spelling.
    token_kwargs = {"max_tokens": max_tokens} if provider == "nvidia" else {"max_completion_tokens": max_tokens}
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        **token_kwargs,
    )
    return response.choices[0].message.content


# ── Summaries ──────────────────────────────────────────────────────────────


def _itinerary_summary(itinerary: Itinerary) -> dict[str, Any]:
    """Structured (not human-string) summary so the validator's JSON prompt
    has unambiguous fields to inspect."""
    return {
        "destination": f"{itinerary.destination.city}, {itinerary.destination.country}",
        "total_budget_usd": round(itinerary.total_budget_usd, 2),
        "days": [
            {
                "day_number": day.day_number,
                "theme": day.theme,
                "daily_cost_usd": round(day.daily_cost_usd or 0.0, 2),
                "activities": [
                    {
                        "name": ia.activity.name,
                        "category": ia.activity.category,
                        "cost_usd": ia.activity.cost_usd,
                        "duration_hours": ia.activity.duration_hours,
                        "tags": list(ia.activity.tags or []),
                    }
                    for ia in day.activities
                ],
            }
            for day in itinerary.days
        ],
    }


def _constraints_summary(user_profile: UserProfile) -> dict[str, Any]:
    c = user_profile.constraints
    if not c:
        return {}
    pace = c.pace.value if c.pace else None
    duration = (c.end_date - c.start_date).days if (c.start_date and c.end_date) else None
    return {
        "budget_usd": c.budget_usd,
        "duration_days": duration,
        "pace": pace,
        "must_haves": list(c.must_haves or []),
        "avoid_list": list(c.avoid_list or []),
        "who_travelling_with": getattr(c.who_travelling_with, "value", None),
    }


# ── Itinerary critic ──────────────────────────────────────────────────────


def _decision_to_validation_result(
    itinerary_id: str,
    decision: BackendValidationDecision,
    summary: str | None = None,
) -> ValidationResult:
    """Bridge the engine's BackendValidationDecision into the
    ValidationResult shape downstream consumers (refinement loop,
    orchestrator) already speak."""
    status = ValidationStatus.approved if decision.approved else ValidationStatus.revise
    feedback = summary or " | ".join(
        f"{i.get('category')}: {i.get('evidence', '')}" for i in decision.issues[:3]
    ) or "No issues."
    improvement_suggestions = [
        f"{i.get('category')}: {i.get('fix', '')}".strip()
        for i in decision.issues
        if i.get("fix")
    ]
    return ValidationResult(
        itinerary_id=itinerary_id,
        status=status,
        score=float(decision.score if decision.score is not None else 0.0),
        feedback=feedback,
        improvement_suggestions=improvement_suggestions,
    )


def _itinerary_user_prompt(itinerary: Itinerary, user_profile: UserProfile) -> str:
    return ENGINE_CONFIG.itinerary_critic_user_template.format(
        constraints_json=json.dumps(_constraints_summary(user_profile), ensure_ascii=False),
        itinerary_summary_json=json.dumps(_itinerary_summary(itinerary), ensure_ascii=False),
    )


async def _run_itinerary_validator(
    client, provider: str, model: str,
    itinerary: Itinerary, user_profile: UserProfile,
    tier: str = "large",
) -> ValidationResult:
    raw = ""
    last_error: Exception | None = None
    # Two attempts — first at the default budget, second at a much
    # bigger token ceiling. Reasoning models occasionally burn the
    # whole 2048 on internal scratch and emit nothing; doubling the
    # ceiling almost always recovers the visible JSON.
    for attempt, tokens in enumerate((2048, 4096), start=1):
        try:
            raw = await _call_llm(
                client, provider, model,
                _itinerary_user_prompt(itinerary, user_profile),
                ENGINE_CONFIG.itinerary_critic_system,
                max_tokens=tokens,
            )
            parsed = parse_json_object(raw)
            decision = enforce_itinerary_decision(parsed, ENGINE_CONFIG)
            result = _decision_to_validation_result(
                itinerary.itinerary_id, decision, summary=parsed.get("summary"),
            )
            try:
                from mushahid.monitoring import capture, EVENT_TRIP_VALIDATION
                issue_categories = [str(i.get("category") or "") for i in decision.issues]
                capture(user_profile.user_id, EVENT_TRIP_VALIDATION, {
                    "itinerary_id":     itinerary.itinerary_id,
                    "tier":             tier,
                    "approved":         decision.approved,
                    "score":            decision.score,
                    "issue_count":      len(decision.issues),
                    "issue_categories": issue_categories,
                    "category_scores":  parsed.get("category_scores") or {},
                    "attempt":          attempt,
                })
            except Exception:
                pass
            return result
        except Exception as e:
            last_error = e
            logger.warning(
                "itinerary validator attempt %d failed (%s): raw=%r",
                attempt, e, (raw or "")[:200],
            )
            continue

    # Both attempts failed. The validator is broken (empty response,
    # unparseable JSON, provider down). Flagging for revision here puts
    # the generator into a revision loop that costs LLM credits and
    # delays the user without improving the itinerary. Fail OPEN — trust
    # the generator's output, log loudly so we notice in Sentry. The
    # itinerary the user lands on is whatever Claude/GPT produced; the
    # validator just isn't blocking it.
    logger.error(
        "itinerary validator failed both attempts (last=%s) — failing open, "
        "approving the itinerary without validator feedback",
        last_error,
    )
    try:
        from mushahid.monitoring import capture, EVENT_TRIP_VALIDATION
        capture(user_profile.user_id, EVENT_TRIP_VALIDATION, {
            "itinerary_id": itinerary.itinerary_id,
            "tier":         tier,
            "approved":     True,   # fail-open
            "error":        type(last_error).__name__ if last_error else "unknown",
            "fail_open":    True,
        })
    except Exception:
        pass
    return ValidationResult(
            itinerary_id=itinerary.itinerary_id,
            status=ValidationStatus.approve,
            score=0.5,
            feedback="Validator unavailable — itinerary approved without LLM review.",
            improvement_suggestions=[],
        )


async def validate_small_output(itinerary: Itinerary, user_profile: UserProfile) -> ValidationResult:
    """Quick LLM sanity check using the small validator model. Same prompt
    + decision logic as the large path — the difference is just model tier."""
    if not SMALL_VALIDATOR_PROVIDER or not SMALL_VALIDATOR_MODEL_NAME:
        raise RuntimeError("SMALL_VALIDATOR_PROVIDER and SMALL_VALIDATOR_MODEL_NAME must be set")
    return await _run_itinerary_validator(
        _get_small_client(), SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME,
        itinerary, user_profile, tier="small",
    )


async def validate_large_output(itinerary: Itinerary, user_profile: UserProfile) -> ValidationResult:
    """Thorough LLM review using the large validator model. Use for final
    approval before returning the itinerary to the user."""
    if not LARGE_VALIDATOR_PROVIDER or not LARGE_VALIDATOR_MODEL_NAME:
        raise RuntimeError("LARGE_VALIDATOR_PROVIDER and LARGE_VALIDATOR_MODEL_NAME must be set")
    return await _run_itinerary_validator(
        _get_large_client(), LARGE_VALIDATOR_PROVIDER, LARGE_VALIDATOR_MODEL_NAME,
        itinerary, user_profile, tier="large",
    )


# ── Persona reveal validator ──────────────────────────────────────────────


async def validate_persona(user_signals: str, persona_output: dict) -> tuple[bool, list[str]]:
    """
    Cross-provider semantic check on the persona reveal output. Now uses the
    structured concrete_observation / evidence_fidelity / no_itinerary_content
    / specificity / internal_label_leakage rubric from validator_engine.

    Fails OPEN on any error — the validator is a quality gate, not a
    correctness gate, so a downed validator never breaks the user flow.
    Returns (valid, issues_as_strings) so existing callers stay drop-in.
    """
    try:
        if not SMALL_VALIDATOR_PROVIDER or not SMALL_VALIDATOR_MODEL_NAME:
            raise RuntimeError("SMALL_VALIDATOR_PROVIDER / SMALL_VALIDATOR_MODEL_NAME not configured")
        prompt = ENGINE_CONFIG.persona_reveal_validator_user_template.format(
            user_signals=user_signals,
            persona_json=json.dumps(persona_output, ensure_ascii=False),
        )
        raw = await _call_llm(
            _get_small_client(), SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME,
            prompt, ENGINE_CONFIG.persona_reveal_validator_system,
        )
        parsed = parse_json_object(raw)
        decision = enforce_boolean_validator_decision(
            parsed,
            hard_fail_categories=PERSONA_HARD_FAIL_CATEGORIES,
            critical_denied_set=PERSONA_HARD_FAIL_CATEGORIES,
        )
        issues = [
            f"{i.get('category')}: {i.get('evidence', '')}".strip(": ")
            for i in decision.issues
        ]
        return decision.approved, issues
    except Exception as e:
        logger.warning("persona validator failed open: %s", e)
        return True, []


# ── Cotraveller match validator ───────────────────────────────────────────


async def validate_match(
    viewer_signals: dict,
    candidate_signals: dict,
    feature_breakdown: dict,
    match_reasons: list[str],
) -> tuple[bool, list[str]]:
    """Quality check on a generated match (reasons + grounding). Available
    for the cotraveller route to call before returning matches to the user;
    not yet wired into the default code path."""
    try:
        if not SMALL_VALIDATOR_PROVIDER or not SMALL_VALIDATOR_MODEL_NAME:
            raise RuntimeError("SMALL_VALIDATOR_PROVIDER / SMALL_VALIDATOR_MODEL_NAME not configured")
        prompt = ENGINE_CONFIG.cotraveller_match_validator_user_template.format(
            viewer_signals_json=json.dumps(viewer_signals, ensure_ascii=False),
            candidate_signals_json=json.dumps(candidate_signals, ensure_ascii=False),
            feature_breakdown_json=json.dumps(feature_breakdown, ensure_ascii=False),
            match_reasons_json=json.dumps(match_reasons, ensure_ascii=False),
        )
        raw = await _call_llm(
            _get_small_client(), SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME,
            prompt, ENGINE_CONFIG.cotraveller_match_validator_system,
        )
        parsed = parse_json_object(raw)
        decision = enforce_boolean_validator_decision(
            parsed,
            hard_fail_categories=MATCH_HARD_FAIL_CATEGORIES,
            critical_denied_set=MATCH_HARD_FAIL_CATEGORIES,
        )
        issues = [
            f"{i.get('category')}: {i.get('evidence', '')}".strip(": ")
            for i in decision.issues
        ]
        return decision.approved, issues
    except Exception as e:
        logger.warning("match validator failed open: %s", e)
        return True, []


# ── Chat reply validator + repair (available; wire when ready) ────────────


async def _call_validator_adapter(system: str, user: str) -> dict:
    """Adapter the chat-reply orchestrator can use to issue validator LLM
    calls through the configured small-validator provider."""
    if not SMALL_VALIDATOR_PROVIDER or not SMALL_VALIDATOR_MODEL_NAME:
        raise RuntimeError("SMALL_VALIDATOR_PROVIDER / SMALL_VALIDATOR_MODEL_NAME not configured")
    raw = await _call_llm(
        _get_small_client(), SMALL_VALIDATOR_PROVIDER, SMALL_VALIDATOR_MODEL_NAME,
        user, system,
    )
    return parse_json_object(raw)


async def _call_repair_adapter(system: str, user: str) -> str:
    """Adapter for the chat-reply repair LLM. Uses the LARGE tier via
    ali/routing/engine.route_request since the repair task wants the same
    fidelity the original reply generator had."""
    from ali.routing.engine import route_request
    return await route_request("complex_refinement", user, system)


async def validate_and_repair_chat_reply_wired(
    *,
    profile_json: str,
    history: str,
    last_message: str,
    reply: str,
    city: str | None = None,
) -> tuple[str, dict]:
    """Production-ready entry point — wires the engine's orchestrator to
    the small validator for validation and the large LLM for repair.
    Returns (final_reply, telemetry_event_payload)."""
    return await validate_and_repair_chat_reply(
        profile_json=profile_json,
        history=history,
        last_message=last_message,
        reply=reply,
        call_validator=_call_validator_adapter,
        call_repair=_call_repair_adapter,
        city=city,
        config=ENGINE_CONFIG,
    )


# Re-export the engine's category sets so any future caller can import
# from this module without reaching into validator_engine directly.
__all__ = [
    "ENGINE_CONFIG",
    "validate_small_output",
    "validate_large_output",
    "validate_persona",
    "validate_match",
    "validate_and_repair_chat_reply_wired",
    "CHAT_HARD_FAIL_CATEGORIES",
    "CHAT_DENIED_CATEGORIES",
    "MATCH_HARD_FAIL_CATEGORIES",
    "PERSONA_HARD_FAIL_CATEGORIES",
]
