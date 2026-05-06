# TODO: Mushahid — POST /plan-trip → Server-Sent Events stream.
# Accept: PlanTripRequest (UserProfile)
# Verify Firebase Auth token from Authorization header.
# Call pipeline/orchestrator.py → stream SSE events:
#   persona_inferring → persona_inferred → retrieving → retrieval_done
#   → ranking → ranked → generating → itinerary_generated
#   → explaining → validating → (revision if needed) → matched → done
# Final event payload: PlanTripResponse
