# TODO: Shreyas — co-traveller compatibility scoring.
# - score_compatibility(user_profile, candidate: CoTravellerProfile) → CoTravellerMatch
#   Multi-signal scoring: shared interests, pace match, budget range overlap,
#   travel style fit, itinerary overlap (if itinerary already generated).
# - get_top_matches(user_profile, candidates, top_n=3) → list[CoTravellerMatch]
#   Return top_n sorted by match_score descending with match_reasons populated.
