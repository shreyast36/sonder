from fastapi import HTTPException
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


async def add_activity(
    itinerary_id: str,
    user_id: str,
    activity: Activity,
    day_number: int,
    client_version: int,
) -> SharedItinerary:
    """
    Add an activity to a specific day of the shared itinerary.
    Uses optimistic locking via `version` to prevent silent overwrites when both
    users edit simultaneously.

    Expected input:
        client_version = 4  ← the version the client last read from Firestore

    Conflict behaviour:
        If Firestore version != client_version → raise HTTP 409 Conflict.
        The frontend must re-fetch, show the latest state, and let the user retry.

    On success:
        - Increment version in Firestore
        - Update the matching day
        - Emit ItineraryUpdateEvent(event_type="activity_added", ...) via WebSocket
        - Return updated SharedItinerary
    """
    # TODO: use Firestore transaction:
    #   current = get_db().collection("shared_itineraries").document(itinerary_id).get()
    #   if current["version"] != client_version: raise HTTPException(409, "Conflict — re-fetch and retry")
    #   update day, increment version, write back in same transaction
    # TODO: emit WebSocket event to both users
    raise NotImplementedError


async def add_note(itinerary_id: str, user_id: str, note: str, client_version: int) -> SharedItinerary:
    """
    Append a note to the shared itinerary with optimistic locking.
    Same conflict behaviour as add_activity — raise 409 if versions don't match.

    Expected Firestore update:
        notes → arrayUnion({ "user_id": user_id, "note": note, "timestamp": ... })
        version → increment
    """
    # TODO: Firestore transaction with version check, then arrayUnion on notes
    raise NotImplementedError


async def sync_changes(itinerary_id: str) -> SharedItinerary:
    """
    Read the latest shared itinerary state from Firestore.
    The frontend calls this after receiving a 409 to get the current version before retrying.

    Expected output: SharedItinerary with current version and all latest changes
    """
    # TODO: get_db().collection("shared_itineraries").document(itinerary_id).get()
    raise NotImplementedError
