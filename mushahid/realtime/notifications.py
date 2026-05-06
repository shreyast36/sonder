# TODO: Mushahid — instant notifications via Firestore.
# push_notification(user_id: str, title: str, body: str, data: dict) → None
#   Write to Firestore notifications/{user_id}/items collection.
#   Frontend Firestore listener picks this up and shows in-app notification.
# notify_match_found(user_id, match: CoTravellerMatch) → None
# notify_itinerary_ready(user_id, itinerary_id) → None
# notify_co_traveller_approved(user_id, partner_id) → None
