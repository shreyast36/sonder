from shared.schemas import CoTravellerMatch
from mushahid.realtime.firestore import get_db


async def push_notification(user_id: str, title: str, body: str, data: dict = {}) -> None:
    """
    Write an in-app notification to Firestore. The frontend Firestore listener picks it up.

    Firestore path: notifications/{user_id}/items/{auto_id}
    Expected document:
        {
            "title":     "Your itinerary is ready!",
            "body":      "Your 7-day Bali trip plan is ready to view.",
            "data":      {"itinerary_id": "itin_abc123"},
            "read":      false,
            "timestamp": "2025-06-01T09:05:00Z"
        }
    """
    # TODO: get_db().collection("notifications").document(user_id).collection("items").add(...)
    raise NotImplementedError


async def notify_match_found(user_id: str, match: CoTravellerMatch) -> None:
    """Notify a user that a new co-traveller match is available."""
    # TODO: push_notification(user_id, "New match found!", f"{match.profile.display_name} is {int(match.match_score*100)}% compatible", ...)
    raise NotImplementedError


async def notify_itinerary_ready(user_id: str, itinerary_id: str) -> None:
    """Notify a user that their itinerary has finished generating."""
    # TODO: push_notification(user_id, "Your itinerary is ready!", "Tap to view your personalised trip plan.", ...)
    raise NotImplementedError


async def notify_co_traveller_approved(user_id: str, partner_display_name: str) -> None:
    """Notify both users when mutual approval is reached."""
    # TODO: push_notification(user_id, "You're travel buddies!", f"You and {partner_display_name} are now co-travellers!", ...)
    raise NotImplementedError
