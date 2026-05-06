from shared.schemas import TripConstraints, Destination, Activity


def apply_destination_filters(destinations: list[Destination], constraints: TripConstraints) -> list[Destination]:
    """
    Hard-filter destinations before scoring. Removes obvious mismatches.

    Rules:
        - Drop if avg_daily_cost_usd > (budget_usd / trip_days) * 1.3
        - Drop if any avoid_list tag appears in destination tags

    Expected input:
        destinations = [Destination(city="Bali", avg_daily_cost_usd=120, tags=["beach","culture"]), ...]
        constraints  = TripConstraints(budget_usd=2000, start_date=..., end_date=..., avoid_list=["nightlife"])

    Expected output:
        [Destination(...), ...]  # filtered list, length <= len(destinations)
    """
    # TODO: compute trip_days, daily_budget, apply both filters
    raise NotImplementedError


def apply_activity_filters(activities: list[Activity], constraints: TripConstraints) -> list[Activity]:
    """
    Hard-filter activities. Removes anything in the avoid list.

    Expected input:
        activities  = [Activity(name="Kuta Beach Club", tags=["nightlife","beach"]), ...]
        constraints = TripConstraints(avoid_list=["nightlife"])

    Expected output:
        [...]  # "Kuta Beach Club" dropped because tag "nightlife" is in avoid_list
    """
    # TODO: set intersection of activity tags and avoid_list tags
    raise NotImplementedError
