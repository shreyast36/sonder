from shared.schemas import Itinerary, SharedItinerary, Activity, ItineraryUpdateEvent
from mushahid.realtime.firestore import get_db


async def create_shared_itinerary(itinerary: Itinerary, user_ids: list[str]) -> SharedItinerary:
    """
    Create a shared itinerary in Firestore when both users approve.

    Expected input:
        itinerary = Itinerary(itinerary_id="itin_001", destination=..., days=[...])
        user_ids  = ["user_abc", "maya_001"]

    Expected Firestore write:
        shared_itineraries/{itinerary_id} → SharedItinerary as dict

    Expected output:
        SharedItinerary(itinerary_id="itin_001", user_ids=["user_abc", "maya_001"], notes=[])
    """
    # TODO: write to Firestore, return SharedItinerary
    raise NotImplementedError


async def add_note(itinerary_id: str, user_id: str, note: str) -> None:
    """
    Append a note to the shared itinerary. Triggers a live update for both users.

    Expected Firestore update:
        shared_itineraries/{itinerary_id}.notes → arrayUnion({ "user_id": user_id, "note": note, "timestamp": ... })
    """
    # TODO: Firestore arrayUnion on notes field
    raise NotImplementedError


async def add_activity(itinerary_id: str, user_id: str, activity: Activity, day_number: int) -> None:
    """
    Add an activity to a specific day of the shared itinerary.

    Expected Firestore update: update the matching day in SharedItinerary.itinerary.days
    Emit ItineraryUpdateEvent(event_type="activity_added", ...) to both users via WebSocket.
    """
    # TODO: update Firestore, emit WebSocket event
    raise NotImplementedError


async def sync_changes(itinerary_id: str) -> SharedItinerary:
    """
    Read the latest shared itinerary state from Firestore.

    Expected output: SharedItinerary with all latest notes and activities
    """
    # TODO: get_db().collection("shared_itineraries").document(itinerary_id).get()
    raise NotImplementedError
