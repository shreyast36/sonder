"""
Hard pre-ranking filters.

Budget is feasibility, not chemistry — candidates that literally can't fit
the user's stated budget get dropped here so the ranker doesn't waste
positive contributions on them. No multipliers, no fudge factors: a
destination's `avg_daily_cost_usd` must be <= the user's `budget_usd /
trip_days`, period. An activity's `cost_usd` must be <= that same daily
budget (we don't track running daily spend in V1).

`avoid_list` removes any candidate carrying a tag the user explicitly
asked to skip.

Every drop is recorded via `feature_logging.record_filter_drop` so we can
see post-launch whether the filters are too strict and revisit.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from shared.schemas import TripConstraints, Destination, Activity

logger = logging.getLogger(__name__)


def _trip_days(constraints: TripConstraints) -> int:
    """Days between start_date and end_date, inclusive. Falls back to 1 if
    dates are missing — caller's filter math will then make the budget
    look generous, which is intentional (we shouldn't drop candidates on
    missing-data we caused)."""
    s = getattr(constraints, "start_date", None)
    e = getattr(constraints, "end_date", None)
    if not isinstance(s, date) or not isinstance(e, date):
        return 1
    days = (e - s).days + 1
    return max(1, days)


def _daily_budget(constraints: TripConstraints) -> float:
    """User's stated total budget divided by trip duration. Zero when no
    budget is set; the filters short-circuit on zero to avoid filtering
    everything out for users who skipped budget entry."""
    budget = float(getattr(constraints, "budget_usd", 0) or 0)
    if budget <= 0:
        return 0.0
    return budget / _trip_days(constraints)


def _record_drop(surface: str, reason: str, candidate: Any, constraints: Any) -> None:
    """Fire-and-forget log of a filter drop. Wrapped in try so observability
    failures never affect the user flow."""
    try:
        from shreyas.ranking.feature_logging import record_filter_drop
        record_filter_drop(surface, reason, candidate, constraints)
    except Exception as e:
        logger.debug("filter drop log failed (%s) for surface=%s: %s", reason, surface, e)


def apply_destination_filters(
    destinations: list[Destination],
    constraints: TripConstraints,
) -> list[Destination]:
    """
    Drop destinations the user can't afford and any carrying an avoid_list tag.

    Rules (no multipliers):
        - Drop if avg_daily_cost_usd > budget_usd / trip_days
        - Drop if any avoid_list tag appears in destination tags
    """
    if not destinations:
        return []
    daily = _daily_budget(constraints)
    avoid = set((getattr(constraints, "avoid_list", []) or []))

    kept: list[Destination] = []
    for d in destinations:
        cost = float(getattr(d, "avg_daily_cost_usd", 0) or 0)
        tags = set((getattr(d, "tags", []) or []))

        if daily > 0 and cost > daily:
            _record_drop("destination", "over_daily_budget", d, constraints)
            continue
        if avoid and avoid & tags:
            _record_drop("destination", "avoid_list_tag", d, constraints)
            continue
        kept.append(d)
    return kept


def apply_activity_filters(
    activities: list[Activity],
    constraints: TripConstraints,
) -> list[Activity]:
    """
    Drop activities the user can't afford for a single day and any carrying
    an avoid_list tag.

    Rules (no multipliers):
        - Drop if cost_usd > budget_usd / trip_days
        - Drop if any avoid_list tag appears in activity tags
    """
    if not activities:
        return []
    daily = _daily_budget(constraints)
    avoid = set((getattr(constraints, "avoid_list", []) or []))

    kept: list[Activity] = []
    for a in activities:
        cost = float(getattr(a, "cost_usd", 0) or 0)
        tags = set((getattr(a, "tags", []) or []))

        if daily > 0 and cost > daily:
            _record_drop("activity", "over_daily_budget", a, constraints)
            continue
        if avoid and avoid & tags:
            _record_drop("activity", "avoid_list_tag", a, constraints)
            continue
        kept.append(a)
    return kept
