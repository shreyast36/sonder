# TODO: Ali — generate "Why this?" explanations for each itinerary activity.
# explain_activity(activity: Activity, context: list[str], user_profile: UserProfile) → str
#   Route to LARGE model. Ground the explanation in retrieved context + user persona.
#   Output is the "Why this?" text shown on the Itinerary screen (Screen 3).
# explain_itinerary(itinerary: Itinerary, user_profile: UserProfile) → Itinerary
#   Run explain_activity for each activity, return itinerary with why_this fields populated.
