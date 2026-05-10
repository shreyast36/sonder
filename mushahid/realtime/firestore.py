import asyncio
from datetime import datetime, timezone
from shared.config import (
    FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL, LOCAL_MODE,
)
from shared.schemas import Itinerary

# In-memory store used when LOCAL_MODE=true (no Firestore connection needed)
_store: dict = {}
_db = None


def get_db():
    global _db
    if LOCAL_MODE:
        return None
    if _db is not None:
        return _db
    import firebase_admin
    from firebase_admin import credentials, firestore
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": FIREBASE_PROJECT_ID,
            "private_key": FIREBASE_PRIVATE_KEY,
            "client_email": FIREBASE_CLIENT_EMAIL,
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        firebase_admin.initialize_app(cred)
    _db = firestore.client()
    return _db


async def write_itinerary_status(user_id: str, status: str) -> None:
    if LOCAL_MODE:
        _store[f"status:{user_id}"] = status
        return
    await asyncio.to_thread(
        lambda: get_db().collection("itinerary_status").document(user_id).set({"status": status})
    )


async def write_itinerary(itinerary: Itinerary) -> None:
    if LOCAL_MODE:
        _store[f"itinerary:{itinerary.itinerary_id}"] = itinerary.model_dump()
        return
    data = itinerary.model_dump(mode="json")
    await asyncio.to_thread(
        lambda: get_db().collection("itineraries").document(itinerary.itinerary_id).set(data)
    )


async def get_itinerary(itinerary_id: str) -> Itinerary | None:
    if LOCAL_MODE:
        data = _store.get(f"itinerary:{itinerary_id}")
        return Itinerary.model_validate(data) if data else None
    doc = await asyncio.to_thread(
        lambda: get_db().collection("itineraries").document(itinerary_id).get()
    )
    return Itinerary.model_validate(doc.to_dict()) if doc.exists else None


async def create_user_profile(user_id: str, display_name: str) -> None:
    doc = {
        "user_id": user_id,
        "display_name": display_name,
        "constraints": None,
        "persona_answers": None,
        "compatibility_signals": {},
        "travel_style_embedding": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if LOCAL_MODE:
        _store[f"profile:{user_id}"] = doc
        return
    await asyncio.to_thread(
        lambda: get_db().collection("user_profiles").document(user_id).set(doc)
    )


async def get_user_profile(user_id: str) -> dict | None:
    if LOCAL_MODE:
        return _store.get(f"profile:{user_id}")
    doc = await asyncio.to_thread(
        lambda: get_db().collection("user_profiles").document(user_id).get()
    )
    return doc.to_dict() if doc.exists else None


async def update_user_profile(user_id: str, updates: dict) -> None:
    if LOCAL_MODE:
        existing = _store.get(f"profile:{user_id}", {})
        existing.update(updates)
        _store[f"profile:{user_id}"] = existing
        return
    await asyncio.to_thread(
        lambda: get_db().collection("user_profiles").document(user_id).update(updates)
    )


async def write_chat_session(session) -> None:
    data = session.model_dump(mode="json")
    if LOCAL_MODE:
        _store[f"chat:{session.session_id}"] = {**data, "messages": []}
        return
    await asyncio.to_thread(
        lambda: get_db().collection("chat_sessions").document(session.session_id).set(data)
    )


async def append_chat_message(session_id: str, message: dict) -> None:
    if LOCAL_MODE:
        session_data = _store.get(f"chat:{session_id}", {})
        session_data.setdefault("messages", []).append(message)
        _store[f"chat:{session_id}"] = session_data
        return
    import uuid
    msg_id = message.get("id") or str(uuid.uuid4())
    await asyncio.to_thread(
        lambda: get_db()
            .collection("chat_sessions")
            .document(session_id)
            .collection("messages")
            .document(msg_id)
            .set(message)
    )
