# TODO: Shreyas — real-time shared itinerary collaboration.
# - create_shared_itinerary(itinerary, user_ids) → SharedItinerary
#   Write to Firestore, notify both users via WebSocket.
# - add_note(itinerary_id, user_id, note: str) → None
# - add_activity(itinerary_id, user_id, activity: Activity) → None
# - sync_changes(itinerary_id) → SharedItinerary
#   Read latest state from Firestore and broadcast ItineraryUpdateEvent to all participants.
