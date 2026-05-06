# TODO: Ali — prompt templates for itinerary generation.
# ITINERARY_SYSTEM_PROMPT: sets the model's role and output format (JSON schema).
# build_itinerary_prompt(user_profile, destination, activities) → str
#   Inject persona, mood, budget, pace, must-haves, and avoid-list into the user message.
# REFINEMENT_SYSTEM_PROMPT: used during the regeneration loop (Mushahid calls this).
# build_refinement_prompt(itinerary, feedback, validation_result) → str
