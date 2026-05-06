from shared.schemas import Itinerary, TripConstraints, ConstraintSatisfaction


def check_budget(itinerary: Itinerary, constraints: TripConstraints) -> bool:
    """
    Pass if itinerary.total_budget_usd <= constraints.budget_usd.

    Expected:
        itinerary.total_budget_usd = 1950, constraints.budget_usd = 2000 → True
        itinerary.total_budget_usd = 2150, constraints.budget_usd = 2000 → False
    """
    # TODO: return itinerary.total_budget_usd <= constraints.budget_usd
    raise NotImplementedError


def check_duration(itinerary: Itinerary, constraints: TripConstraints) -> bool:
    """
    Pass if number of itinerary days == trip duration from constraints.

    Expected:
        len(itinerary.days) = 7, trip_days = 7 → True
    """
    # TODO: trip_days = (constraints.end_date - constraints.start_date).days
    raise NotImplementedError


def check_pace(itinerary: Itinerary, constraints: TripConstraints) -> bool:
    """
    Pass if average activities per day matches pace preference.
    Suggested thresholds (your decision):
        relaxed  → avg <= 3 activities/day
        moderate → avg <= 5 activities/day
        packed   → any number is fine

    Expected:
        pace=relaxed, avg=4.2 activities/day → False
    """
    # TODO: compute avg activities per day, compare to pace threshold
    raise NotImplementedError


def check_must_haves(itinerary: Itinerary, constraints: TripConstraints) -> bool:
    """
    Pass if all must_haves appear in activity tags across the itinerary.

    Expected:
        must_haves=["snorkeling"], activity tags include "snorkeling" somewhere → True
        must_haves=["snorkeling"], no activity has tag "snorkeling" → False
    """
    # TODO: flatten all activity tags, check each must_have is present
    raise NotImplementedError


def check_avoid_list(itinerary: Itinerary, constraints: TripConstraints) -> bool:
    """
    Pass if no activity tag appears in the avoid_list.

    Expected:
        avoid_list=["nightlife"], activity "Kuta Beach Club" has tag "nightlife" → False
    """
    # TODO: check no activity tag intersects with avoid_list
    raise NotImplementedError


def run_all_checks(itinerary: Itinerary, constraints: TripConstraints) -> ConstraintSatisfaction:
    """
    Run all 5 checks and return a ConstraintSatisfaction summary.

    Expected output:
        ConstraintSatisfaction(
            budget_ok    = True,
            duration_ok  = True,
            pace_ok      = False,  ← too many activities for relaxed pace
            must_haves_ok = True,
            avoid_list_ok = True
        )
    """
    # TODO: call all checks, return ConstraintSatisfaction(...)
    raise NotImplementedError
