# TODO: Mushahid — deterministic rule-based constraint checks (fast, no LLM).
# Run these BEFORE the LLM critic to short-circuit obvious failures.
# check_budget(itinerary, constraints) → bool
# check_duration(itinerary, constraints) → bool
# check_pace(itinerary, constraints) → bool
# check_must_haves(itinerary, constraints) → bool
# check_avoid_list(itinerary, constraints) → bool
# run_all_checks(itinerary, constraints) → ConstraintSatisfaction
