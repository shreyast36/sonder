from datetime import datetime, timezone
from shared.schemas import CoTravellerMatch
from shared.config import LOCAL_MODE

_local_notifications: dict[str, list] = {}


async def push_notification(user_id: str, title: str, body: str, data: dict = {}) -> None:
    doc = {
        "title": title,
        "body": body,
        "data": data,
        "read": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if LOCAL_MODE:
        _local_notifications.setdefault(user_id, []).append(doc)
        return
    from mushahid.realtime.firestore import get_db
    get_db().collection("notifications").document(user_id).collection("items").add(doc)


async def notify_match_found(user_id: str, match: CoTravellerMatch) -> None:
    await push_notification(
        user_id,
        title="New match found!",
        body=f"{match.profile.display_name} is {int(match.match_score * 100)}% compatible with you.",
        data={"profile_id": match.profile.profile_id},
    )


async def notify_itinerary_ready(user_id: str, itinerary_id: str) -> None:
    await push_notification(
        user_id,
        title="Your itinerary is ready!",
        body="Tap to view your personalised trip plan.",
        data={"itinerary_id": itinerary_id},
    )


async def notify_co_traveller_approved(user_id: str, partner_display_name: str) -> None:
    await push_notification(
        user_id,
        title="You're travel buddies!",
        body=f"You and {partner_display_name} are now co-travellers!",
        data={"type": "approval"},
    )
