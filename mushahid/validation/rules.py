from shared.schemas import Itinerary, TripConstraints, ConstraintSatisfaction, PacePreference

_PACE_MAX = {
    PacePreference.relaxed: 3,
    PacePreference.moderate: 5,
    PacePreference.packed: 999,
}


def check_budget(itinerary: Itinerary, constraints: TripConstraints) -> bool:
    return itinerary.total_budget_usd <= constraints.budget_usd


def check_duration(itinerary: Itinerary, constraints: TripConstraints) -> bool:
    trip_days = (constraints.end_date - constraints.start_date).days
    return len(itinerary.days) == trip_days


def check_pace(itinerary: Itinerary, constraints: TripConstraints) -> bool:
    if not itinerary.days:
        return True
    avg = sum(len(d.activities) for d in itinerary.days) / len(itinerary.days)
    return avg <= _PACE_MAX.get(constraints.pace, 999)


def check_must_haves(itinerary: Itinerary, constraints: TripConstraints) -> bool:
    if not constraints.must_haves:
        return True
    all_tags = {
        tag
        for day in itinerary.days
        for ia in day.activities
        for tag in (ia.activity.tags or [])
    }
    return all(mh.lower() in {t.lower() for t in all_tags} for mh in constraints.must_haves)


def check_avoid_list(itinerary: Itinerary, constraints: TripConstraints) -> bool:
    if not constraints.avoid_list:
        return True
    avoid = {a.lower() for a in constraints.avoid_list}
    for day in itinerary.days:
        for ia in day.activities:
            for tag in (ia.activity.tags or []):
                if tag.lower() in avoid:
                    return False
    return True


def run_all_checks(itinerary: Itinerary, constraints: TripConstraints) -> ConstraintSatisfaction:
    return ConstraintSatisfaction(
        budget_ok=check_budget(itinerary, constraints),
        duration_ok=check_duration(itinerary, constraints),
        pace_ok=check_pace(itinerary, constraints),
        must_haves_ok=check_must_haves(itinerary, constraints),
        avoid_list_ok=check_avoid_list(itinerary, constraints),
    )
