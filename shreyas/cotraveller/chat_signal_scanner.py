"""
Live chat-message signal scanner for cotraveller matching.

Each user message in a Sonder chat is scanned for keywords that imply
the user cares about specific compatibility dimensions. When a keyword
fires, the corresponding cotraveller-policy feature's weight is boosted
on the session. The candidate is then re-ranked with the updated weights
to produce a fresh match_score — that score is what the persona's
reciprocal approval threshold ultimately reads.

Why scan chat content instead of just trusting the retrieval-time score:
- The retrieval-time score is built from structured signals (constraints,
  PPM tags, embeddings) captured BEFORE the chat happened.
- The chat itself reveals fresh signal — user mentions of nightlife,
  burnout, splurging, etc. — that wasn't in those structured fields.
- This module routes that fresh signal back into the same feature space
  the matching engine already understands.

Keyword vocabularies are imported directly from
jahnvi/data/dimensions.py so the scanner stays in lockstep with the
PPM dimension definitions used at matching time. Pace/budget/style/
emotional cues are added on top because cotraveller policy has dedicated
features for those that PPM keywords alone don't cover.

Threading model: scan is pure-Python regex (cheap, ~ms even with the
full PPM vocab). The re-rank step is the expensive part — fire-and-
forget from the WS handler, never block the user's message broadcast.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from jahnvi.data.dimensions import PUSH_DIMENSIONS, PULL_DIMENSIONS

logger = logging.getLogger(__name__)


# ── Keyword → feature mapping (built once at import) ──────────────────────


def _alternation(keywords: list[str]) -> str:
    """Compile a list of literal keywords into one alternation regex,
    word-bounded for multi-word keywords with spaces and case-insensitive
    via the caller's re.IGNORECASE flag."""
    # Sort longest-first so multi-word phrases match before their substrings.
    ordered = sorted({k.strip() for k in keywords if k and k.strip()}, key=len, reverse=True)
    return r"(?:" + "|".join(re.escape(k) for k in ordered) + r")"


def _build_keyword_map() -> dict[re.Pattern, list[str]]:
    """Compile pattern → cotraveller feature names.

    All PPM (push) + PULL keywords feed
    salience_weighted_question_overlap, since that's the feature that
    compares PPM tag agreement at matching time. Pace/budget/style/
    emotional cues feed their dedicated cotraveller features."""
    mapping: dict[re.Pattern, list[str]] = {}

    # All PPM + PULL keywords → salience_weighted_question_overlap.
    # One big alternation per dimension keeps the compiled regex small.
    ppm_pull = {**PUSH_DIMENSIONS, **PULL_DIMENSIONS}
    for dim_name, keywords in ppm_pull.items():
        if not keywords:
            continue
        pattern = re.compile(_alternation(keywords), re.IGNORECASE)
        mapping[pattern] = ["salience_weighted_question_overlap"]

    # Pace cues — packed/rushed/chill/relaxed style.
    pace_kws = [
        "packed", "rushed", "busy", "hectic", "crammed",
        "chill", "relaxed", "laid back", "slow", "slower", "easygoing",
        "back to back", "non stop", "non-stop", "go go go",
        "take it easy", "lazy day", "lazy mornings",
    ]
    mapping[re.compile(r"\b" + _alternation(pace_kws) + r"\b", re.IGNORECASE)] = ["pace_ordinal_fit"]

    # Budget cues.
    budget_kws = [
        "cheap", "cheaper", "expensive", "pricey", "costly",
        "afford", "affordable", "budget", "shoestring",
        "splurge", "treat myself", "spend", "spend big",
        "luxury", "five star", "5 star", "high end",
        "mid range", "mid-range", "value", "worth it",
        "save money", "tight budget",
    ]
    mapping[re.compile(r"\b" + _alternation(budget_kws) + r"\b", re.IGNORECASE)] = ["budget_ordinal_fit"]

    # Style cues — who they're travelling with / how.
    style_kws = [
        "solo", "by myself", "on my own",
        "couple", "with my partner", "my boyfriend", "my girlfriend",
        "my husband", "my wife", "anniversary",
        "family", "with my kids", "the whole family",
        "friends", "with friends", "group trip", "group of",
    ]
    mapping[re.compile(r"\b" + _alternation(style_kws) + r"\b", re.IGNORECASE)] = ["style_match"]

    # Emotional-tone cues that signal which signature the user resonates with.
    # Not exhaustive — high-signal words only, since signature_proximity is
    # already informed by structured PPM at matching time.
    emotion_kws = [
        "burnt out", "burned out", "drained", "exhausted", "depleted",
        "energised", "energized", "alive", "buzzing",
        "anxious", "stressed", "overwhelmed",
        "calm", "centered", "centred", "grounded",
        "homesick", "missing", "lonely",
        "joyful", "elated", "ecstatic",
        "curious", "fascinated",
        "nostalgic", "wistful",
    ]
    mapping[re.compile(r"\b" + _alternation(emotion_kws) + r"\b", re.IGNORECASE)] = ["signature_proximity"]

    return mapping


_KEYWORD_MAP: dict[re.Pattern, list[str]] = _build_keyword_map()


# ── Public API ────────────────────────────────────────────────────────────


def fired_features(text: str, allowed: set[str]) -> list[str]:
    """Return the unique cotraveller-policy features the text implies
    should gain weight, restricted to features the policy actually uses."""
    if not text:
        return []
    out: list[str] = []
    for pattern, features in _KEYWORD_MAP.items():
        if pattern.search(text):
            for f in features:
                if f in allowed and f not in out:
                    out.append(f)
    return out


def scan_and_apply(
    text: str,
    current_weights: dict[str, float] | None,
    policy: Any,
) -> tuple[dict[str, float], list[str]]:
    """Scan `text` for compatibility signals and return updated weights.

    Mirrors the boost/clamp/renormalize math from
    shreyas/ranking/feedback.py:apply_text_feedback so the chat signal
    path uses the same tuning hyperparameters policy designers already
    set. Defined separately because the keyword map here is calibrated
    for chat content (PPM + emotional cues), not the post-trip free-text
    feedback that feedback.py handles.

    Returns (new_weights, fired) — new_weights is a normalised feature →
    weight dict suitable for stamping onto ChatSession.live_weights,
    fired is the list of feature names that fired (for logging).
    """
    features = set(getattr(policy, "features", []) or [])
    if not features:
        return dict(current_weights or {}), []

    cfg = getattr(policy, "feedback_policy", {}) or {}
    boost_amount = float(cfg.get("boost_amount", 0.10))
    min_weight   = float(cfg.get("min_weight",   0.05))
    strategy     =       cfg.get("renormalization", "sum_to_one")

    defaults = dict(getattr(policy, "weights", {}) or {})
    weights: dict[str, float] = {
        name: float((current_weights or {}).get(name, defaults.get(name, 0.0)))
        for name in features
    }

    fired = fired_features(text, features)
    for name in fired:
        weights[name] = weights[name] + boost_amount

    # Clamp + renormalize.
    weights = {k: max(min_weight, v) for k, v in weights.items()}
    if strategy == "sum_to_one":
        total = sum(weights.values()) or 1.0
        weights = {k: v / total for k, v in weights.items()}

    return weights, fired
