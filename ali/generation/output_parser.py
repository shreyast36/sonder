# TODO: Ali — parse and validate raw LLM output into an Itinerary object.
# parse_itinerary(raw: str, user_profile: UserProfile) → Itinerary
#   Extract structured JSON from LLM response.
#   Fallback: if JSON malformed, retry with a corrective prompt.
# validate_structure(itinerary: Itinerary) → bool
#   Check required fields before passing to Mushahid's validator.
