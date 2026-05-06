from shared.config import FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL
from shared.schemas import Itinerary

_db = None


def get_db():
    """
    Returns the Firestore client, initialising firebase_admin on first call.

    Expected usage:
        db = get_db()
        db.collection("itineraries").document(itinerary_id).set(data)
    """
    global _db
    if _db is not None:
        return _db
    # TODO: initialise firebase_admin with credentials from config
    # TODO: _db = firestore.client()
    raise NotImplementedError


async def write_itinerary_status(user_id: str, status: str) -> None:
    """
    Write pipeline status to Firestore so the frontend can show live progress.

    Firestore path: itinerary_status/{user_id}
    Expected values: "generating" | "validating" | "ready" | "error"
    """
    # TODO: get_db().collection("itinerary_status").document(user_id).set({"status": status})
    raise NotImplementedError


async def write_itinerary(itinerary: Itinerary) -> None:
    """
    Persist a completed itinerary to Firestore.

    Firestore path: itineraries/{itinerary_id}
    """
    # TODO: get_db().collection("itineraries").document(itinerary.itinerary_id).set(itinerary.model_dump())
    raise NotImplementedError


async def get_itinerary(itinerary_id: str) -> Itinerary | None:
    """
    Read an itinerary from Firestore.

    Expected output: Itinerary object, or None if not found.
    """
    # TODO: doc = get_db().collection("itineraries").document(itinerary_id).get()
    # TODO: return Itinerary(**doc.to_dict()) if doc.exists else None
    raise NotImplementedError
