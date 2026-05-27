from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

logger = logging.getLogger("travel_app.validators")

# Core State Machine Typings
ValidationStatus = Literal["approved", "revise", "denied"]
IssueSeverity = Literal["low", "medium", "high"]

# -----------------------------------------------------------------------------
# Configuration Layer (Completely externalizes all weights, heuristics, and text prompts)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidatorEngineConfig:
    """Config engine to externalize all dynamic prompts, weights, structures, and criteria."""
    # Semantic Drift & Slop Parameters
    semantic_slop_stems: set[str] = field(default_factory=lambda: {
        "sounds amazing", "sounds incredible", "sounds great", "sounds good",
        "love that", "oh nice", "that is awesome", "so cool", "really cool",
        "hidden gem", "bucket list", "must see", "must try", "fellow traveler"
    })
    genericity_base_weight: float = 0.50
    genericity_multiplier: float = 0.15
    genericity_max_cap: float = 1.0
    genericity_threshold: float = 0.80

    # Conversational Length Rules
    min_acceptable_reply_length: int = 3
    max_proactive_word_count: int = 50

    # History & Memory Engine Patterns
    memory_templates: dict[str, str] = field(default_factory=lambda: {
        "past_destinations": r"\b(?:i've been to|when i was in|visited|traveled to)\s+([a-zA-Z\s]+)",
        "past_negations": r"\b(?:never been to|haven't visited|don't travel to)\s+([a-zA-Z\s]+)"
    })

    # Scoring Rules for Itinerary Evaluation
    itinerary_approval_threshold: float = 0.75

    # --- System Prompts & Rubrics ---
    itinerary_critic_system: str = """
    You are a strict travel itinerary quality reviewer.
    Your job is to evaluate ONLY the itinerary provided against ONLY the user constraints provided. Do not invent missing parameters.
    Evaluate these categories: 1. budget_fit, 2. pacing_realism, 3. must_haves_covered, 4. avoid_list_respected, 5. day_sequence_logic, 6. activity_specificity, 7. feasibility_risk.
    Return ONLY valid JSON matching this shape:
    {
      "score": 0.0,
      "category_scores": {"budget_fit": 0.0, "pacing_realism": 0.0, "must_haves_covered": 0.0, "avoid_list_respected": 0.0, "day_sequence_logic": 0.0, "activity_specificity": 0.0, "feasibility_risk": 0.0},
      "issues": [{"category": "string", "severity": "low|medium|high", "day": "string|null", "evidence": "string", "fix": "string"}],
      "summary": "string"
    }
    """.strip()

    itinerary_critic_user_template: str = """
    USER CONSTRAINTS: {constraints_json}
    ITINERARY: {itinerary_summary_json}
    Validation rules:
    - Penalize generic activities heavily unless they include enough detail to be actionable.
    - Swapability Test: If an activity description applies anywhere else without changing context, it fails specificity.
    Return JSON only.
    """.strip()

    persona_reveal_validator_system: str = """
    You are a strict validator for a persona reveal in a travel app.
    Check ONLY these categories: 1. concrete_observation, 2. evidence_fidelity, 3. no_itinerary_content, 4. specificity, 5. internal_label_leakage.
    Return ONLY valid JSON:
    {"valid": true, "issues": [{"category": "string", "severity": "low|medium|high", "evidence": "string", "fix": "string"}]}
    """.strip()

    persona_reveal_validator_user_template: str = """
    USER SIGNALS: {user_signals}
    PERSONA OUTPUT: {persona_json}
    Return JSON only.
    """.strip()

    cotraveller_match_validator_system: str = """
    You are a strict validator for co-traveller match quality and explanation quality.
    Check these categories: 1. ranking_grounding, 2. evidence_fidelity, 3. specificity, 4. tension_awareness, 5. internal_label_leakage, 6. tone.
    Return ONLY valid JSON:
    {"valid": true, "issues": [{"category": "string", "severity": "low|medium|high", "evidence": "string", "fix": "string"}]}
    """.strip()

    cotraveller_match_validator_user_template: str = """
    VIEWER SIGNALS: {viewer_signals_json}
    CANDIDATE SIGNALS: {candidate_signals_json}
    RANKING FEATURE BREAKDOWN: {feature_breakdown_json}
    GENERATED MATCH REASONS: {match_reasons_json}
    Return JSON only.
    """.strip()

    chat_reply_validator_system: str = """
    You are a strict validator for synthetic co-traveller chat replies.
    The reply should sound like a real person texting. It must NOT sound like an assistant, AI, or generic chatbot.
    Check: assistant_voice, ai_leakage, semantic_drift, token_stutter, empty_token_generation, romantic_vibes, taxonomy_leakage, unsafe_or_weird, bad_conversation_dynamics, contradiction_memory.
    Return ONLY valid JSON:
    {"valid": false, "issues": [{"category": "string", "severity": "low|medium|high", "evidence": "string", "fix": "string"}]}
    """.strip()

    chat_reply_validator_user_template: str = """
    PROFILE CONSTRAINTS: {profile_json}
    CONVERSATION TIMELINE LOGS: {history}
    USER LATEST MESSAGE: {last_message}
    GENERATED CANDIDATE REPLY: {reply}
    Return JSON only.
    """.strip()

    chat_reply_repair_system: str = """
    Rewrite the synthetic co-traveller reply so it passes validation.
    The corrected reply must feel like a natural text, under 50 words, preserve context logic, and omit loops or helper speech.
    Return ONLY the corrected message. No quotes. No preamble.
    """.strip()

    chat_reply_repair_user_template: str = """
    PROFILE: {profile_json}
    CONVERSATION HISTORY: {history}
    USER LATEST MESSAGE: {last_message}
    BAD REPLY: {reply}
    VALIDATION ISSUES: {issues_json}
    Rewrite the reply once.
    """.strip()


# -----------------------------------------------------------------------------
# Telemetry and Ingestion Tracking Layers
# -----------------------------------------------------------------------------

@dataclass
class TelemetryEvent:
    validator_passed_first_try: bool = True
    repair_triggered: bool = False
    repair_count: int = 0
    regex_precheck_hit: bool = False
    total_latency_ms: float = 0.0
    semantic_genericity_score: float = 0.0
    execution_log: list[str] = field(default_factory=list)
    detected_anomalies: list[str] = field(default_factory=list)

    def serialize_posthog(self) -> dict[str, Any]:
        """Formats the execution tracking payload for product analytics platforms."""
        return {
            "event_name": "validator_stack_execution",
            "properties": {
                "validator_passed_first_try": self.validator_passed_first_try,
                "repair_triggered": self.repair_triggered,
                "repair_count": self.repair_count,
                "regex_precheck_hit": self.regex_precheck_hit,
                "total_latency_ms": round(self.total_latency_ms, 2),
                "semantic_genericity_score": round(self.semantic_genericity_score, 2),
                "execution_log": self.execution_log,
                "detected_anomalies": self.detected_anomalies
            }
        }


@dataclass(frozen=True)
class BackendValidationDecision:
    approved: bool
    status: ValidationStatus
    score: float | None
    issues: list[dict[str, Any]]

# -----------------------------------------------------------------------------
# Defensive String & Text Sanitization Filters
# -----------------------------------------------------------------------------

def clean_model_text(text: Any) -> str:
    """Safely normalizes raw text returns, cleaning terminal wrappers and spacing."""
    if text is None:
        return ""
    return str(text).strip().strip('"').strip("'").strip()


def strip_code_fences(raw: str) -> str:
    """Extracts content inside markdown blocks cleanly using standard multi-line regex."""
    if not raw:
        return ""
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw.strip()


def _extract_json_object(raw: str) -> str:
    """Pull the first balanced {...} block out of a noisy LLM response.

    Some models prefix with "Here is the assessment:" or apologise before
    returning JSON; strip_code_fences only catches markdown-fenced blocks.
    This walks the string with a brace counter so we can recover JSON
    embedded in arbitrary text.
    """
    if not raw:
        return ""
    start = raw.find("{")
    if start < 0:
        return ""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(raw)):
        c = raw[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return raw[start:i + 1]
    return ""


def parse_json_object(raw: str) -> dict[str, Any]:
    """Parse an LLM's validator response into a dict.

    Resilience ladder:
      1. Strip markdown code fences (```json ... ```) if present.
      2. If that's not valid JSON, walk the string for the first
         balanced {...} block — handles "Here's my assessment: {...}"
         and other preamble.
      3. Only raise after both passes fail.

    Empty input is treated as the validator effectively dying — raises
    with a clear message so the caller can fail-open instead of looping
    on revision.
    """
    if not raw or not raw.strip():
        raise ValueError("validator returned an empty response")
    cleaned = strip_code_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        extracted = _extract_json_object(raw)
        if not extracted:
            raise ValueError(
                f"Failed to parse validator JSON: no balanced object found in "
                f"{len(raw)}-char response (preview: {raw[:120]!r})"
            )
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse validator JSON after brace-walk: {e} "
                f"(preview: {raw[:120]!r})"
            ) from e
    if not isinstance(data, dict):
        raise ValueError("validator response must be a JSON object")
    return data

# -----------------------------------------------------------------------------
# Dynamic Heuristics & Local Checking Passages
# -----------------------------------------------------------------------------

def isolate_linguistic_bigrams(text: str) -> list[tuple[str, str]]:
    """Generates continuous token arrays to scan for repeating sampler outputs."""
    normalized = re.sub(r"[^\w\s]", "", text.lower()).split()
    if len(normalized) < 2:
        return []
    return list(zip(normalized, normalized[1:]))


def has_repetition(text: str) -> bool:
    """Verifies sliding bigram uniqueness profiles to protect context stability."""
    bigrams = isolate_linguistic_bigrams(text)
    return bool(bigrams and len(bigrams) != len(set(bigrams)))


def evaluate_semantic_genericity(text: str, config: ValidatorEngineConfig) -> float:
    """Calculates a localized similarity score using configurable weights passed at runtime."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    matches = 0
    for stem in config.semantic_slop_stems:
        if stem in cleaned:
            matches += 1

    if not matches:
        return 0.0

    calculated_score = config.genericity_base_weight + (matches * config.genericity_multiplier)
    return min(config.genericity_max_cap, calculated_score)


def extract_timeline_entities(conversation_history: str, config: ValidatorEngineConfig) -> dict[str, set[str]]:
    """Scans chat records to extract claimed locations using external templates."""
    entities: dict[str, set[str]] = {"visited": set(), "unvisited": set()}
    if not conversation_history:
        return entities

    lines = conversation_history.lower().split("\n")
    for line in lines:
        for loc in re.findall(config.memory_templates["past_destinations"], line):
            entities["visited"].add(clean_model_text(loc))
        for loc in re.findall(config.memory_templates["past_negations"], line):
            entities["unvisited"].add(clean_model_text(loc))

    return entities


def evaluate_memory_contradictions(reply: str, history: str, config: ValidatorEngineConfig) -> list[dict[str, Any]]:
    """Identifies logical fallacies or context flips against previous chat logs."""
    issues = []
    reply_lowered = reply.lower()
    memory = extract_timeline_entities(history, config)

    for unvisited_place in memory["unvisited"]:
        if f"when i was in {unvisited_place}" in reply_lowered or f"visited {unvisited_place}" in reply_lowered:
            issues.append({
                "category": "contradiction_memory",
                "severity": "high",
                "evidence": f"Reply claims previous travel experience in '{unvisited_place}', which explicitly contradicts past log statements.",
                "fix": "Reconcile chronological travel history assertions."
            })

    for visited_place in memory["visited"]:
        if f"never been to {visited_place}" in reply_lowered or f"haven't visited {visited_place}" in reply_lowered:
            issues.append({
                "category": "contradiction_memory",
                "severity": "high",
                "evidence": f"Reply states user has never been to '{visited_place}', directly contradicting prior messages.",
                "fix": "Maintain cohesive contextual timeline identity parameters."
            })

    return issues


def chat_reply_local_precheck(reply: str, history: str, config: ValidatorEngineConfig) -> list[dict[str, Any]]:
    """Runs fast local evaluation checks using dynamically configurable metrics."""
    issues: list[dict[str, Any]] = []
    cleaned = clean_model_text(reply)

    if len(cleaned) < config.min_acceptable_reply_length:
        issues.append({
            "category": "empty_token_generation",
            "severity": "high",
            "evidence": f"Raw content length: {len(cleaned)} chars.",
            "fix": "Generate a full conversational reply that addresses the chat history context directly."
        })
        return issues

    if has_repetition(cleaned):
        issues.append({
            "category": "token_stutter",
            "severity": "high",
            "evidence": "Repetitive language structures or consecutive token loops observed.",
            "fix": "Remove repetitive text or loops and provide a clean, direct sentence structure."
        })

    genericity = evaluate_semantic_genericity(cleaned, config)
    if genericity > config.genericity_threshold:
        issues.append({
            "category": "semantic_drift",
            "severity": "high",
            "evidence": f"Calculated score: {genericity}. Response contains excessive boilerplate or generic filler text.",
            "fix": "Rewrite the reply to include unique details specific to this conversation instead of generic filler."
        })

    issues.extend(evaluate_memory_contradictions(cleaned, history, config))
    return issues

# -----------------------------------------------------------------------------
# Taxonomy State Mapping Layer
# -----------------------------------------------------------------------------

CHAT_REVISE_CATEGORIES = {
    "assistant_voice",
    "ai_leakage",
    "taxonomy_leakage",
    "semantic_drift",
    "token_stutter",
    "contradiction_memory",
    "bad_conversation_dynamics",
}

CHAT_DENIED_CATEGORIES = {
    "unsafe_or_weird",
    "romantic_vibes",
    "empty_token_generation",
}

CHAT_HARD_FAIL_CATEGORIES = CHAT_REVISE_CATEGORIES | CHAT_DENIED_CATEGORIES

MATCH_HARD_FAIL_CATEGORIES = {"ranking_grounding", "evidence_fidelity", "internal_label_leakage"}
PERSONA_HARD_FAIL_CATEGORIES = {"evidence_fidelity", "no_itinerary_content", "internal_label_leakage"}
ITINERARY_HARD_FAIL_CATEGORIES = {"budget_fit", "must_haves_covered", "avoid_list_respected", "feasibility_risk"}


def issue_severity(issue: Mapping[str, Any]) -> str:
    sev = str(issue.get("severity") or "").strip().lower()
    return sev if sev in {"low", "medium", "high"} else "medium"


def has_high_severity_issue(issues: Sequence[Mapping[str, Any]]) -> bool:
    return any(issue_severity(issue) == "high" for issue in issues or [])


def has_hard_fail_category(issues: Sequence[Mapping[str, Any]], hard_fail_categories: set[str]) -> bool:
    for issue in issues or []:
        category = str(issue.get("category") or "").strip()
        if category in hard_fail_categories and issue_severity(issue) in {"medium", "high"}:
            return True
    return False


def determine_validation_status(approved: bool, issues: list[dict[str, Any]], critical_denied_set: set[str]) -> ValidationStatus:
    if approved:
        return "approved"

    for issue in issues:
        category = str(issue.get("category") or "").strip()
        if category in critical_denied_set and issue_severity(issue) in {"medium", "high"}:
            return "denied"

    return "revise"


def get_issues(parsed: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues = parsed.get("issues")
    if issues is None:
        return []

    if not isinstance(issues, list):
        return [{
            "category": "empty_token_generation",
            "severity": "high",
            "evidence": str(issues),
            "fix": "The 'issues' key must be a structured JSON list array.",
        }]

    validated_issues: list[dict[str, Any]] = []
    for issue in issues:
        if isinstance(issue, dict) and "category" in issue and "severity" in issue:
            validated_issues.append(issue)
        else:
            validated_issues.append({
                "category": "empty_token_generation",
                "severity": "high",
                "evidence": str(issue),
                "fix": "Ensure individual issue objects match required string attributes.",
            })
    return validated_issues


def enforce_itinerary_decision(parsed: Mapping[str, Any], config: ValidatorEngineConfig) -> BackendValidationDecision:
    raw_score = parsed.get("score", 0.0)
    try:
        score = max(0.0, min(1.0, float(raw_score)))
    except (TypeError, ValueError):
        score = 0.0

    issues = get_issues(parsed)
    approved = (
        score >= config.itinerary_approval_threshold
        and not has_high_severity_issue(issues)
        and not has_hard_fail_category(issues, ITINERARY_HARD_FAIL_CATEGORIES)
    )
    status = "approved" if approved else ("denied" if has_high_severity_issue(issues) else "revise")

    return BackendValidationDecision(approved=approved, status=status, score=score, issues=issues)


def enforce_boolean_validator_decision(
    parsed: Mapping[str, Any],
    *,
    hard_fail_categories: set[str],
    critical_denied_set: set[str]
) -> BackendValidationDecision:
    issues = get_issues(parsed)
    model_valid = bool(parsed.get("valid") is True)
    approved = (
        model_valid
        and not has_high_severity_issue(issues)
        and not has_hard_fail_category(issues, hard_fail_categories)
    )
    status = determine_validation_status(approved, issues, critical_denied_set)

    return BackendValidationDecision(approved=approved, status=status, score=None, issues=issues)

# -----------------------------------------------------------------------------
# Constrained Generator Payload Construction
# -----------------------------------------------------------------------------

def build_constrained_generator_context(profile_json: str, history: str, config: ValidatorEngineConfig) -> dict[str, Any]:
    """Assembles a proactive generation schema using current dynamic configuration bounds."""
    memory_profile = extract_timeline_entities(history, config)
    return {
        "outbound_formatting_rules": {
            "max_word_count": config.max_proactive_word_count,
            "banned_phrases": list(config.semantic_slop_stems),
            "required_identity_claims": json.loads(profile_json) if profile_json else {}
        },
        "proactive_timeline_boundaries": {
            "asserted_visited_locations": list(memory_profile["visited"]),
            "banned_unvisited_locations": list(memory_profile["unvisited"]),
            "execution_policy": "Maintain facts from previous messages. Enforce behavioral specificity rules."
        }
    }

# -----------------------------------------------------------------------------
# Core Orchestration Hook
# -----------------------------------------------------------------------------

def chat_reply_fallback(city: str | None = None) -> str:
    if city:
        return f"fair. i'd probably need one good coffee in {city} first, then i'd be in."
    return "fair. i'd probably need one good coffee first, then i'd be in."


async def validate_and_repair_chat_reply(
    *,
    profile_json: str,
    history: str,
    last_message: str,
    reply: str,
    call_validator,
    call_repair,
    city: str | None = None,
    config: ValidatorEngineConfig | None = None,
) -> tuple[str, dict[str, Any]]:
    """Orchestrates validation cycles entirely driven by variables supplied from config."""
    start_time = time.perf_counter()
    telemetry = TelemetryEvent()

    # Establish dynamic rule map configuration parameters
    engine_config = config or ValidatorEngineConfig()

    current_reply = clean_model_text(reply)
    telemetry.semantic_genericity_score = evaluate_semantic_genericity(current_reply, engine_config)

    # Step 1: Run local triage parameters completely decoupled from script strings
    local_issues = chat_reply_local_precheck(current_reply, history, engine_config)
    if local_issues:
        telemetry.regex_precheck_hit = True
        telemetry.validator_passed_first_try = False

        for issue in local_issues:
            telemetry.detected_anomalies.append(issue["category"])

        local_status = determine_validation_status(approved=False, issues=local_issues, critical_denied_set=CHAT_DENIED_CATEGORIES)
        if local_status == "denied":
            telemetry.total_latency_ms = (time.perf_counter() - start_time) * 1000
            telemetry.execution_log.append("hard_denied_at_local_precheck")
            return chat_reply_fallback(city), telemetry.serialize_posthog()

        telemetry.repair_triggered = True
        telemetry.execution_log.append("failed_local_triage_precheck")

        repaired = await call_repair(
            engine_config.chat_reply_repair_system,
            engine_config.chat_reply_repair_user_template.format(
                profile_json=profile_json,
                history=history,
                last_message=last_message,
                reply=current_reply,
                issues_json=json.dumps(local_issues, ensure_ascii=False),
            ),
        )
        current_reply = clean_model_text(repaired)
        telemetry.repair_count += 1

    if len(current_reply) < engine_config.min_acceptable_reply_length:
        telemetry.total_latency_ms = (time.perf_counter() - start_time) * 1000
        telemetry.execution_log.append("circuit_breaker_intercept")
        return chat_reply_fallback(city), telemetry.serialize_posthog()

    # Step 2: Primary LLM Validation Flight driven via dynamic parameters
    # Track infrastructure failures separately from real deny verdicts —
    # NVIDIA Nemotron 504s shouldn't make every user see the same
    # hardcoded "coffee first" fallback line. If the validator itself
    # can't speak, trust the small-tier generator's already-generated
    # reply; only fall back to the boilerplate when the validator
    # genuinely returned a deny verdict.
    infra_failed = False
    try:
        raw_validation = await call_validator(
            engine_config.chat_reply_validator_system,
            engine_config.chat_reply_validator_user_template.format(
                profile_json=profile_json,
                history=history,
                last_message=last_message,
                reply=current_reply,
            ),
        )
        parsed = raw_validation if isinstance(raw_validation, dict) else parse_json_object(str(raw_validation))
        decision = enforce_boolean_validator_decision(
            parsed,
            hard_fail_categories=CHAT_HARD_FAIL_CATEGORIES,
            critical_denied_set=CHAT_DENIED_CATEGORIES
        )
    except Exception as e:
        infra_failed = True
        logger.error(f"Infrastructural validation loop breakdown: {e}")
        # Fail-open: approve the reply when the validator infrastructure
        # itself is broken. The reply was already generated by the
        # small-tier model and survived the deterministic local
        # precheck — that's a strictly better signal than a hardcoded
        # boilerplate fallback. The error is still logged to Sentry
        # so the underlying provider issue is visible.
        decision = BackendValidationDecision(approved=True, status="approved", score=None, issues=[])

    if decision.status == "denied" and not infra_failed:
        telemetry.total_latency_ms = (time.perf_counter() - start_time) * 1000
        telemetry.execution_log.append("hard_denied_on_first_validation_flight")
        return chat_reply_fallback(city), telemetry.serialize_posthog()

    if infra_failed:
        telemetry.total_latency_ms = (time.perf_counter() - start_time) * 1000
        telemetry.execution_log.append("validator_infra_failed_fail_open")
        return current_reply, telemetry.serialize_posthog()

    if decision.approved:
        telemetry.total_latency_ms = (time.perf_counter() - start_time) * 1000
        telemetry.execution_log.append("approved_primary_flight")
        return current_reply, telemetry.serialize_posthog()

    # Step 3: Run target revision repair using template loaded via configuration layer
    telemetry.repair_triggered = True
    telemetry.validator_passed_first_try = False
    for issue in decision.issues:
        telemetry.detected_anomalies.append(issue.get("category", "untyped_model_fault"))
    telemetry.execution_log.append("triggered_model_repair_loop")

    repaired_second = await call_repair(
        engine_config.chat_reply_repair_system,
        engine_config.chat_reply_repair_user_template.format(
            profile_json=profile_json,
            history=history,
            last_message=last_message,
            reply=current_reply,
            issues_json=json.dumps(decision.issues, ensure_ascii=False),
        ),
    )
    repaired_reply = clean_model_text(repaired_second)
    telemetry.repair_count += 1

    if repaired_reply == current_reply or len(repaired_reply) < engine_config.min_acceptable_reply_length or has_repetition(repaired_reply):
        telemetry.total_latency_ms = (time.perf_counter() - start_time) * 1000
        telemetry.execution_log.append("aborted_generation_due_to_oscillation_degradation")
        return chat_reply_fallback(city), telemetry.serialize_posthog()

    # Step 4: Final Validation Verification Flight
    second_infra_failed = False
    try:
        raw_second = await call_validator(
            engine_config.chat_reply_validator_system,
            engine_config.chat_reply_validator_user_template.format(
                profile_json=profile_json,
                history=history,
                last_message=last_message,
                reply=repaired_reply,
            ),
        )
        parsed_second = raw_second if isinstance(raw_second, dict) else parse_json_object(str(raw_second))
        second_decision = enforce_boolean_validator_decision(
            parsed_second,
            hard_fail_categories=CHAT_HARD_FAIL_CATEGORIES,
            critical_denied_set=CHAT_DENIED_CATEGORIES
        )
    except Exception as e:
        # Same fail-open rule on the repair re-validate. We already
        # have a repaired reply; without a validator we ship it.
        second_infra_failed = True
        logger.error(f"Infrastructural validation loop breakdown (repair pass): {e}")
        second_decision = BackendValidationDecision(approved=True, status="approved", score=None, issues=[])

    telemetry.total_latency_ms = (time.perf_counter() - start_time) * 1000

    if second_decision.status == "denied" and not second_infra_failed:
        telemetry.execution_log.append("hard_denied_on_final_validation_flight")
        return chat_reply_fallback(city), telemetry.serialize_posthog()

    if second_infra_failed:
        telemetry.execution_log.append("validator_infra_failed_repair_pass_fail_open")
        return repaired_reply, telemetry.serialize_posthog()

    if second_decision.approved:
        telemetry.execution_log.append("approved_post_repair_evaluation")
        return repaired_reply, telemetry.serialize_posthog()

    # Step 5: Fallback deployment
    telemetry.execution_log.append("hard_fallback_deployed")
    return chat_reply_fallback(city), telemetry.serialize_posthog()
