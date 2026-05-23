"""
Feature-breakdown event log.

Every shown candidate, every accept/reject, and every filter drop gets
recorded to Firestore so V2 can later compute replacement gradients:

    gradient = accepted.feature_scores - rejected.feature_scores

and nudge per-user weights toward features that better explain accepted
items.

All writes are fire-and-forget via asyncio.create_task to avoid adding
latency to the user-facing flow. Failures are logged at debug level and
swallowed — observability never blocks ranking.

Firestore layout (illustrative):
    ranking_events/{event_id} = {
      uid:        str,
      surface:    "cotraveller" | "destination" | "activity",
      kind:       "shown" | "accept" | "reject" | "filter_drop",
      candidate_id: str | None,
      feature_breakdown: { name: {raw, weighted}, ... } | None,
      retrieval_score: float | None,
      reason:     str | None,
      timestamp:  ISO8601 UTC,
    }
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

logger = logging.getLogger(__name__)


def _candidate_id(candidate: Any) -> str | None:
    for attr in ("profile_id", "destination_id", "activity_id", "id"):
        val = getattr(candidate, attr, None)
        if val:
            return str(val)
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _write_event(doc: dict) -> None:
    """Single Firestore write. Failures logged at debug, never raised."""
    try:
        from mushahid.realtime.firestore import write_ranking_event
        await write_ranking_event(doc)
    except Exception as e:
        logger.debug("ranking event write failed: %s", e)


def _fire(doc: dict) -> None:
    """Schedule the write without awaiting. If no event loop is running
    (e.g. called from a sync context), silently drop — V1 callers are all
    async."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_write_event(doc))


def record_rank_call(surface: str, ranked: Iterable[Any]) -> None:
    """Called by the engine right after rank() completes. Logs a 'shown'
    event per candidate with the full feature_breakdown so V2 can compute
    accept-vs-shown deltas later."""
    for rc in ranked or []:
        feature_breakdown = {
            name: {"raw": raw, "weighted": weighted}
            for name, (raw, weighted) in (getattr(rc, "feature_scores", {}) or {}).items()
        }
        _fire({
            "event_id":          str(uuid.uuid4()),
            "surface":           surface,
            "kind":              "shown",
            "candidate_id":      _candidate_id(getattr(rc, "candidate", None)),
            "feature_breakdown": feature_breakdown,
            "retrieval_score":   getattr(rc, "retrieval_score", None),
            "final_score":       getattr(rc, "final_score", None),
            "timestamp":         _now_iso(),
        })


def record_accept(uid: str, surface: str, candidate: Any, feature_breakdown: dict | None = None) -> None:
    """User picked this candidate (clicked into the match, kept the
    activity through refinement, etc)."""
    _fire({
        "event_id":          str(uuid.uuid4()),
        "uid":               uid,
        "surface":           surface,
        "kind":              "accept",
        "candidate_id":      _candidate_id(candidate),
        "feature_breakdown": feature_breakdown,
        "timestamp":         _now_iso(),
    })


def record_reject(uid: str, surface: str, candidate: Any, feature_breakdown: dict | None = None, reason: str | None = None) -> None:
    """User rejected (swap/remove from itinerary, denied a match)."""
    _fire({
        "event_id":          str(uuid.uuid4()),
        "uid":               uid,
        "surface":           surface,
        "kind":              "reject",
        "candidate_id":      _candidate_id(candidate),
        "feature_breakdown": feature_breakdown,
        "reason":            reason,
        "timestamp":         _now_iso(),
    })


def record_filter_drop(surface: str, reason: str, candidate: Any, constraints: Any | None = None) -> None:
    """Pre-ranking filter dropped a candidate — logged so we can spot
    overly-strict filters from data instead of guessing."""
    _fire({
        "event_id":      str(uuid.uuid4()),
        "surface":       surface,
        "kind":          "filter_drop",
        "candidate_id":  _candidate_id(candidate),
        "reason":        reason,
        "timestamp":     _now_iso(),
    })


def record_event(uid: str, surface: str, kind: str, candidate: Any, **extra: Any) -> None:
    """Generic catch-all for the update_trip route: 'swap' / 'remove' /
    'adjust_time' edits land here without the route having to pick the
    right accept/reject helper."""
    doc = {
        "event_id":     str(uuid.uuid4()),
        "uid":          uid,
        "surface":      surface,
        "kind":         kind,
        "candidate_id": _candidate_id(candidate),
        "timestamp":    _now_iso(),
    }
    doc.update({k: v for k, v in extra.items() if v is not None})
    _fire(doc)
