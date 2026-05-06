# TODO: Mushahid — closed-loop regeneration / refinement.
# run_refinement_loop(itinerary, user_profile, feedback, validation_result) → UpdateTripResponse
#   Loop up to MAX_REFINEMENT_ATTEMPTS times:
#     1. Re-rank & re-filter (Shreyas's ranking)
#     2. Re-query Ali's itinerary_generator with updated prompt (includes feedback + validation feedback)
#     3. Validator re-checks (rules.py then critic.py)
#     4. If APPROVED → break
#   Push final itinerary to Firestore in real time after each attempt.
#   Return UpdateTripResponse with final itinerary + attempt count.
