"""
Per-question salience computation.

Salience answers: "how informative is this user's answer to question X for
ranking?" — based on push/pull/motivation keyword density in the answer
text plus the chip→dimension mapping that already exists in
jahnvi/data/persona_labels.py + the PUSH/PULL keyword lists in
jahnvi/data/dimensions.py.

Output: dict[question_id, weight] normalized to sum to 1.0 across the
five persona questions. Read by the salience_weighted_question_overlap
feature in features.py at scoring time.

Pure function, no LLM calls, no I/O. Cheap enough to run on every
/persona-infer.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from jahnvi.data.dimensions import PUSH_DIMENSIONS, PULL_DIMENSIONS
from jahnvi.data.persona_labels import PERSONA_LABELS


# Five persona-questions that contribute to salience. Field names must match
# TripConstraints (radio answers) + PersonaQuestionAnswers (free text).
PERSONA_QUESTION_FIELDS = (
    "social_role",
    "trip_feeling",
    "friction_response",
    "ideal_atmosphere",
    "small_thing",
)


def _all_ppm_keywords() -> set[str]:
    """Flat set of every push + pull dimension keyword, lowercased."""
    keywords: set[str] = set()
    for kws in PUSH_DIMENSIONS.values():
        keywords.update(k.lower() for k in kws)
    for kws in PULL_DIMENSIONS.values():
        keywords.update(k.lower() for k in kws)
    return keywords


_PPM_KEYWORDS_CACHED: set[str] | None = None


def _ppm_keywords() -> set[str]:
    global _PPM_KEYWORDS_CACHED
    if _PPM_KEYWORDS_CACHED is None:
        _PPM_KEYWORDS_CACHED = _all_ppm_keywords()
    return _PPM_KEYWORDS_CACHED


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z']+", (text or "").lower())


def _keyword_density(text: str) -> float:
    """Count PPM-keyword hits in `text`. Returns a non-negative float — the
    raw count, not a ratio. Pure additive signal so longer text with more
    PPM presence gets more weight (intentional)."""
    if not text:
        return 0.0
    keywords = _ppm_keywords()
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    return float(sum(1 for tok in tokens if tok in keywords))


def _chip_to_text(field: str, option_key: str | None) -> str:
    """Resolve a radio chip selection to its natural-language label, so the
    chip's text contributes to keyword density. Without this, chip-only
    users would have near-zero salience compared to free-text-heavy users."""
    if not option_key:
        return ""
    return PERSONA_LABELS.get(field, {}).get(option_key, "") or ""


def _answer_text(field: str, persona_answers: Any, constraints: Any) -> str:
    """Combine the chip label (if any) and the free text (if any) into one
    string per question, ready for keyword density."""
    if field == "small_thing":
        return (getattr(persona_answers, "small_thing", "") or "").strip() if persona_answers else ""
    # Radio chip — read from constraints
    if constraints is None:
        return ""
    option_key = getattr(constraints, field, None)
    return _chip_to_text(field, option_key)


def compute_answer_salience(
    persona_answers: Any,
    constraints: Any,
    fields: tuple[str, ...] = PERSONA_QUESTION_FIELDS,
) -> dict[str, float]:
    """
    Compute per-question salience as a distribution summing to 1.0.

    The signal is PPM-keyword density per question:
      - Chip answers contribute via their label text (so a "story_collector"
        chip earns the dimension's keywords).
      - small_thing contributes via the user's free text.

    When every answer is empty (no signal), returns a uniform 1/N
    distribution so the ranker doesn't multiply by zeros.

    Args:
        persona_answers: PersonaQuestionAnswers or dict-shaped object with
            a .small_thing free text field.
        constraints: TripConstraints or dict-shaped object holding the four
            radio answer keys.
        fields: which question fields to consider (default = all five).

    Returns:
        dict mapping question_field -> weight in [0,1], summing to 1.0.
    """
    raw_densities: dict[str, float] = {}
    for field in fields:
        text = _answer_text(field, persona_answers, constraints)
        raw_densities[field] = _keyword_density(text)

    total = sum(raw_densities.values())
    if total <= 0.0:
        # No signal at all — fall back to uniform so the ranker stays sane.
        uniform = 1.0 / max(1, len(fields))
        return {f: uniform for f in fields}

    return {f: raw_densities[f] / total for f in fields}


def overlap_score(
    viewer_answers: Mapping[str, Any],
    candidate_answers: Mapping[str, Any],
    fields: tuple[str, ...] = PERSONA_QUESTION_FIELDS,
) -> dict[str, float]:
    """
    For each question, score answer alignment between viewer and candidate
    on [0,1]. Used by the salience_weighted_question_overlap feature.

    Rules:
      - For radio chips: 1.0 on exact match, 0.0 otherwise. (V1 — V2 could
        introduce option-level similarity if we observe close-but-not-same
        chips behaving similarly.)
      - For small_thing: token-overlap Jaccard on the lowercased token sets.

    Returns per-field score in [0,1]. The caller multiplies by viewer's
    salience to produce the final weighted overlap.
    """
    out: dict[str, float] = {}
    for field in fields:
        v = viewer_answers.get(field)
        c = candidate_answers.get(field)
        if field == "small_thing":
            v_tokens = set(_tokenize(str(v or "")))
            c_tokens = set(_tokenize(str(c or "")))
            if not v_tokens or not c_tokens:
                out[field] = 0.0
            else:
                shared = v_tokens & c_tokens
                union  = v_tokens | c_tokens
                out[field] = len(shared) / max(1, len(union))
        else:
            out[field] = 1.0 if v and c and v == c else 0.0
    return out


def viewer_persona_answers(viewer: Any) -> dict[str, Any]:
    """Build the viewer's answer dict in the same shape candidates use, so
    overlap_score can compare like-for-like."""
    constraints = getattr(viewer, "constraints", None)
    persona = getattr(viewer, "persona_answers", None)
    out: dict[str, Any] = {}
    for field in PERSONA_QUESTION_FIELDS:
        if field == "small_thing":
            out[field] = getattr(persona, "small_thing", "") if persona else ""
        else:
            out[field] = getattr(constraints, field, None) if constraints else None
    return out


def candidate_persona_answers(candidate: Any) -> dict[str, Any]:
    """Same shape as viewer_persona_answers but read from a synthetic
    CoTravellerProfile. Synthetic profiles store the chip answers under
    `persona_answers` (a dict written by seed_cotravellers.py)."""
    pa = getattr(candidate, "persona_answers", None) or {}
    if not isinstance(pa, dict):
        # Pydantic model on UserProfile path
        return viewer_persona_answers(candidate)
    out: dict[str, Any] = {}
    for field in PERSONA_QUESTION_FIELDS:
        out[field] = pa.get(field)
    return out
