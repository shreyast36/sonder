import json
import re
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from ali.routing.engine import route_request
from jahnvi.data.classify_emotions import classify_emotions


Confidence = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class EmotionalSignatureResult:
    emotional_signature: str
    emotional_tone: str
    confidence: Confidence
    evidence: list[str]
    goemotions: list[tuple[str, float]] | None = None

    def to_compatibility_signals(self, *, include_debug: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "emotional_signature": self.emotional_signature,
            "emotional_tone": self.emotional_tone,
            "emotional_signature_confidence": self.confidence,
            "emotional_signature_evidence": self.evidence,
        }
        if include_debug and self.goemotions is not None:
            payload["_debug_goemotions"] = [
                {"label": label, "score": score} for label, score in self.goemotions
            ]
        return payload


_SIGNATURE_SYSTEM = """
You infer a user's emotional travel signature from onboarding answers.

This is not mood detection. It is not therapy. It is not personality typing.
Your job is to infer the durable emotional quality this person seems to seek
or bring into travel, based only on the provided answers.

Use GoEmotions labels as weak evidence, not as final labels.
Choose exactly one signature from the allowed taxonomy.
Do not invent signatures outside the taxonomy.

A good emotional signature:
- explains the pattern across multiple answers
- is inferable from behavior, preferences, and free text
- reflects travel desire, not a temporary mood
- can help later prompts sound more personally resonant

Avoid overfitting to one answer unless the free-text answer is unusually strong.
If evidence is thin or contradictory, choose the best-supported allowed signature
and set confidence to low or medium.

Output ONLY valid JSON with this shape:
{
  "emotional_signature": "one allowed signature key",
  "emotional_tone": "short human phrase, 2-6 words",
  "confidence": "low | medium | high",
  "evidence": ["1-3 short answer-derived evidence snippets"]
}
""".strip()


class EmotionalSignatureError(ValueError):
    pass


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _enum_value(value: Any) -> str:
    return _clean_text(getattr(value, "value", value))


def _as_dict(obj: Any) -> dict[str, Any]:
    """Accept pydantic models, dataclasses-ish objects, or plain dicts."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {}


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _strip_code_fences(raw: str) -> str:
    return re.sub(r"```(?:json)?\s*|\s*```", "", raw or "").strip()


def _coerce_answer_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(_enum_value(v) for v in value if _enum_value(v))
    if isinstance(value, dict):
        return "; ".join(
            f"{k}: {_coerce_answer_value(v)}"
            for k, v in value.items()
            if _coerce_answer_value(v)
        )
    return _enum_value(value)


def normalize_answers(answers: Any) -> dict[str, str]:
    """Return non-empty answer_id -> answer text.

    This intentionally does not hardcode question IDs. Whatever the frontend sends
    becomes the source of truth, and question_catalog supplies human labels.
    """
    raw = _as_dict(answers)
    normalized: dict[str, str] = {}
    for key, value in raw.items():
        text = _coerce_answer_value(value)
        if text:
            normalized[str(key)] = text
    return normalized


def build_evidence_rows(
    answers: Mapping[str, str],
    question_catalog: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Join user answers with runtime question metadata."""
    rows: list[dict[str, str]] = []
    for answer_id, answer_text in answers.items():
        meta = question_catalog.get(answer_id, {}) if question_catalog else {}
        if not isinstance(meta, dict):
            meta = {"prompt": str(meta)}
        rows.append(
            {
                "id": answer_id,
                "question": _clean_text(meta.get("prompt") or meta.get("label") or answer_id),
                "answer": answer_text,
            }
        )
    return rows


def build_emotion_classifier_text(evidence_rows: Sequence[Mapping[str, str]]) -> str:
    """Build classifier input from all answer evidence, prioritizing free text naturally.

    No hardcoded question IDs: the entire answer set contributes, while richer
    free-text answers will dominate the embedding because they carry more content.
    """
    parts: list[str] = []
    for row in evidence_rows:
        question = _clean_text(row.get("question"))
        answer = _clean_text(row.get("answer"))
        if answer:
            parts.append(f"{question}: {answer}" if question else answer)
    return "\n".join(parts).strip()


def _allowed_signature_keys(signature_taxonomy: Mapping[str, Any]) -> set[str]:
    return {str(key) for key in signature_taxonomy.keys()}


def build_signature_prompt(
    *,
    evidence_rows: Sequence[Mapping[str, str]],
    signature_taxonomy: Mapping[str, Any],
    goemotions: Sequence[tuple[str, float]],
) -> str:
    emotion_labels = [label for label, _score in goemotions]
    return (
        f"ALLOWED SIGNATURE TAXONOMY:\n{_compact_json(signature_taxonomy)}\n\n"
        f"USER ANSWERS:\n{_compact_json(list(evidence_rows))}\n\n"
        f"GOEMOTIONS CANDIDATES:\n{_compact_json(emotion_labels)}\n\n"
        "Infer exactly one emotional_signature from the allowed taxonomy. "
        "Use the user's answers as primary evidence. Use GoEmotions only as weak tone evidence."
    )


def parse_signature_response(raw: str, allowed_signatures: set[str]) -> dict[str, Any]:
    cleaned = _strip_code_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise EmotionalSignatureError(f"Invalid emotional signature JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise EmotionalSignatureError("Emotional signature response must be a JSON object")

    signature = _clean_text(data.get("emotional_signature"))
    if signature not in allowed_signatures:
        raise EmotionalSignatureError(f"Invalid emotional_signature: {signature!r}")

    tone = _clean_text(data.get("emotional_tone"))
    if not tone:
        raise EmotionalSignatureError("Missing emotional_tone")

    confidence = _clean_text(data.get("confidence")).lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"

    evidence_raw = data.get("evidence") or []
    if not isinstance(evidence_raw, list):
        evidence_raw = [str(evidence_raw)]
    evidence = [_clean_text(item) for item in evidence_raw if _clean_text(item)][:3]

    return {
        "emotional_signature": signature,
        "emotional_tone": tone[:80],
        "confidence": confidence,
        "evidence": evidence,
    }


def deterministic_signature_fallback(
    *,
    answers: Mapping[str, str],
    signature_taxonomy: Mapping[str, Any],
    goemotions: Sequence[tuple[str, float]],
) -> dict[str, Any]:
    """Last-resort fallback without hardcoded mappings.

    Chooses the first taxonomy key, because taxonomy ordering is config-owned.
    This should almost never be used; it exists to keep writes well-formed.
    """
    allowed = list(signature_taxonomy.keys())
    if not allowed:
        raise EmotionalSignatureError("signature_taxonomy cannot be empty")

    first_answer = next((text for text in answers.values() if text), "insufficient answer evidence")
    top_emotion = goemotions[0][0] if goemotions else "unclear"
    return {
        "emotional_signature": str(allowed[0]),
        "emotional_tone": f"{top_emotion} undertone",
        "confidence": "low",
        "evidence": [first_answer[:120]],
    }


async def infer_emotional_signature(
    answers: Any,
    *,
    question_catalog: Mapping[str, Any],
    signature_taxonomy: Mapping[str, Any],
    top_k: int = 5,
    include_debug: bool = False,
    allow_fallback: bool = True,
    precomputed_goemotions: Sequence[tuple[str, float]] | None = None,
) -> EmotionalSignatureResult:
    """Infer one configurable emotional signature from onboarding answers.

    Nothing in this function hardcodes your product taxonomy or frontend question
    labels. Pass both in at runtime.

    Args:
        answers: dict/model of onboarding answers from the frontend.
        question_catalog: runtime metadata keyed by answer id.
        signature_taxonomy: allowed signature keys and descriptions.
        top_k: number of GoEmotions candidates to use as weak evidence.
        include_debug: whether result.to_compatibility_signals includes GoEmotions.
        allow_fallback: if true, returns a low-confidence configured fallback if
            the LLM response is malformed.
        precomputed_goemotions: pass already-classified emotions to skip the
            internal classify_emotions call (avoids redundant work when the
            caller has already run the classifier in parallel).
    """
    if not signature_taxonomy:
        raise EmotionalSignatureError("signature_taxonomy cannot be empty")

    normalized_answers = normalize_answers(answers)
    evidence_rows = build_evidence_rows(normalized_answers, question_catalog)

    if precomputed_goemotions is not None:
        goemotions = list(precomputed_goemotions)
    else:
        classifier_text = build_emotion_classifier_text(evidence_rows)
        goemotions = await classify_emotions(classifier_text, top_k=top_k) if classifier_text else []

    prompt = build_signature_prompt(
        evidence_rows=evidence_rows,
        signature_taxonomy=signature_taxonomy,
        goemotions=goemotions,
    )
    raw = await route_request("persona_emotional_signature", prompt, _SIGNATURE_SYSTEM)

    allowed = _allowed_signature_keys(signature_taxonomy)
    try:
        parsed = parse_signature_response(raw, allowed)
    except EmotionalSignatureError:
        if not allow_fallback:
            raise
        parsed = deterministic_signature_fallback(
            answers=normalized_answers,
            signature_taxonomy=signature_taxonomy,
            goemotions=goemotions,
        )

    return EmotionalSignatureResult(
        emotional_signature=parsed["emotional_signature"],
        emotional_tone=parsed["emotional_tone"],
        confidence=parsed["confidence"],  # type: ignore[arg-type]
        evidence=parsed["evidence"],
        goemotions=goemotions if include_debug else None,
    )
