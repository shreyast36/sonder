"""
Per-feature distribution observability.

V1 has no normalization layer — every feature returns raw scores on its
own implicit scale (pinecone cosine ~[0.5, 0.9], ordinal fits {0, 0.5,
1.0}, Jaccard [0, 1], identity {0, 1}). With equal-weight priors this
asymmetry will let one feature silently dominate the combined score.

To make domination visible (instead of guessing): every feature observation
that flows through `rank()` gets fired into a rolling Firestore aggregate
keyed by surface + feature. Aggregates carry p50, p95, mean, variance,
sample count — enough to spot a feature whose distribution is clearly out
of line with the others.

All writes are fire-and-forget via asyncio.create_task to keep the user-
facing flow latency-free.

Firestore layout (illustrative):
    feature_stats/{surface}__{feature_name} = {
      surface:     str,
      feature:     str,
      day:         "YYYY-MM-DD",
      count:       int,
      mean:        float,
      m2:          float,    # Welford's running sum of squared deltas
      p50:         float,    # approximate (TDigest or naive running window)
      p95:         float,
      last_update: ISO8601 UTC,
    }
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Iterable

logger = logging.getLogger(__name__)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _write_observations(observations: list[dict]) -> None:
    """Batched Firestore update for a list of {surface, feature, value}
    observations. Uses naive aggregation (mean + count) since we don't
    want to pull a TDigest dependency in for V1 — p50/p95 come later or
    via offline rollup. Failures swallowed."""
    try:
        from mushahid.realtime.firestore import update_feature_stats
        await update_feature_stats(observations)
    except Exception as e:
        logger.debug("feature_stats write failed: %s", e)


def _fire(observations: list[dict]) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if observations:
        loop.create_task(_write_observations(observations))


def record_rank_call(surface: str, ranked: Iterable[Any]) -> None:
    """Engine fires this once per rank() call. We flatten every candidate's
    feature_scores into an observations list and batch-write them."""
    observations: list[dict] = []
    day = _today()
    ts  = _now_iso()
    for rc in ranked or []:
        for name, (raw, _weighted) in (getattr(rc, "feature_scores", {}) or {}).items():
            observations.append({
                "surface":     surface,
                "feature":     name,
                "value":       float(raw),
                "day":         day,
                "timestamp":   ts,
            })
        # Retrieval score gets its own pseudo-feature key so we can see its
        # distribution alongside the explicit features.
        if hasattr(rc, "retrieval_score"):
            observations.append({
                "surface":     surface,
                "feature":     "_retrieval_score",
                "value":       float(getattr(rc, "retrieval_score", 0.0)),
                "day":         day,
                "timestamp":   ts,
            })
    _fire(observations)


def record_feature_observation(surface: str, feature_name: str, value: float) -> None:
    """Single-shot observation — handy for hand-tracing in tests / scripts."""
    _fire([{
        "surface":   surface,
        "feature":   feature_name,
        "value":     float(value),
        "day":       _today(),
        "timestamp": _now_iso(),
    }])
