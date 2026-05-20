import asyncio
import logging
import uuid
from datetime import datetime, timezone
from shared.config import (
    FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL,
    FIRESTORE_DATABASE_ID, LOCAL_MODE,
)
from shared.schemas import Itinerary

logger = logging.getLogger(__name__)

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
    # If FIRESTORE_DATABASE_ID is set (e.g. "sonder-db1"), point the client at the
    # named database; otherwise the SDK uses the project's "(default)" database.
    _db = firestore.client(database_id=FIRESTORE_DATABASE_ID) if FIRESTORE_DATABASE_ID else firestore.client()
    return _db


async def write_itinerary_status(user_id: str, status: str) -> None:
    if LOCAL_MODE:
        _store[f"status:{user_id}"] = status
        return
    try:
        await asyncio.to_thread(
            lambda: get_db().collection("itinerary_status").document(user_id).set({"status": status})
        )
    except Exception as e:
        logger.warning("write_itinerary_status failed (Firestore unavailable?): %s", e)


async def write_itinerary(itinerary: Itinerary) -> None:
    if LOCAL_MODE:
        _store[f"itinerary:{itinerary.itinerary_id}"] = itinerary.model_dump()
        return
    data = itinerary.model_dump(mode="json")
    try:
        await asyncio.to_thread(
            lambda: get_db().collection("itineraries").document(itinerary.itinerary_id).set(data)
        )
    except Exception as e:
        logger.warning("write_itinerary failed (Firestore unavailable?): %s", e)


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
    try:
        doc = await asyncio.to_thread(
            lambda: get_db().collection("user_profiles").document(user_id).get()
        )
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.warning("get_user_profile failed (Firestore unavailable?): %s", e)
        return None


async def update_user_profile(user_id: str, updates: dict) -> None:
    if LOCAL_MODE:
        existing = _store.get(f"profile:{user_id}", {})
        existing.update(updates)
        _store[f"profile:{user_id}"] = existing
        return
    await asyncio.to_thread(
        lambda: get_db().collection("user_profiles").document(user_id).update(updates)
    )


async def write_journal_entry(entry_id: str, entry: dict) -> None:
    """Upsert one journal entry. Schema: {entry_id, user_id, itinerary_id,
    day_number, text, photos[], is_public, city, country, display_name,
    avatar_url, created_at, updated_at}."""
    if LOCAL_MODE:
        _store[f"journal:{entry_id}"] = entry
        return
    try:
        await asyncio.to_thread(
            lambda: get_db().collection("journal_entries").document(entry_id).set(entry, merge=True)
        )
    except Exception as e:
        logger.warning("write_journal_entry failed: %s", e)


async def get_journal_entry(entry_id: str) -> dict | None:
    if LOCAL_MODE:
        return _store.get(f"journal:{entry_id}")
    try:
        doc = await asyncio.to_thread(
            lambda: get_db().collection("journal_entries").document(entry_id).get()
        )
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.warning("get_journal_entry failed: %s", e)
        return None


async def list_journal_entries_for_trip(itinerary_id: str) -> list[dict]:
    """All entries for a trip, ordered by day_number then created_at."""
    if LOCAL_MODE:
        return sorted(
            (v for k, v in _store.items()
             if k.startswith("journal:") and v.get("itinerary_id") == itinerary_id),
            key=lambda e: (e.get("day_number") or 0, e.get("created_at") or ""),
        )
    try:
        docs = await asyncio.to_thread(
            lambda: list(get_db()
                .collection("journal_entries")
                .where("itinerary_id", "==", itinerary_id)
                .stream())
        )
        return sorted(
            (d.to_dict() for d in docs),
            key=lambda e: (e.get("day_number") or 0, e.get("created_at") or ""),
        )
    except Exception as e:
        logger.warning("list_journal_entries_for_trip failed: %s", e)
        return []


async def list_public_journal_entries_for_city(city: str, country: str | None, limit: int = 40) -> list[dict]:
    """Public entries tagged to a destination. Powers the destination feed."""
    city_l = (city or "").strip().lower()
    if not city_l:
        return []
    if LOCAL_MODE:
        all_public = [
            v for k, v in _store.items()
            if k.startswith("journal:")
            and v.get("is_public")
            and (v.get("city") or "").strip().lower() == city_l
            and (not country or (v.get("country") or "").strip().lower() == country.strip().lower())
        ]
        return sorted(all_public, key=lambda e: e.get("created_at") or "", reverse=True)[:limit]
    try:
        q = (get_db()
             .collection("journal_entries")
             .where("is_public", "==", True)
             .where("city_lower", "==", city_l))
        if country:
            q = q.where("country_lower", "==", country.strip().lower())
        docs = await asyncio.to_thread(lambda: list(q.limit(limit).stream()))
        return sorted(
            (d.to_dict() for d in docs),
            key=lambda e: e.get("created_at") or "",
            reverse=True,
        )
    except Exception as e:
        logger.warning("list_public_journal_entries_for_city failed: %s", e)
        return []


async def write_companion_prefs(itinerary_id: str, prefs: dict) -> None:
    if LOCAL_MODE:
        _store[f"companion_prefs:{itinerary_id}"] = prefs
        return
    try:
        await asyncio.to_thread(
            lambda: get_db().collection("companion_prefs").document(itinerary_id).set(prefs)
        )
    except Exception as e:
        logger.warning("write_companion_prefs failed: %s", e)


async def get_companion_prefs(itinerary_id: str) -> dict | None:
    if LOCAL_MODE:
        return _store.get(f"companion_prefs:{itinerary_id}")
    try:
        doc = await asyncio.to_thread(
            lambda: get_db().collection("companion_prefs").document(itinerary_id).get()
        )
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.warning("get_companion_prefs failed: %s", e)
        return None


async def write_chat_session(session) -> None:
    data = session.model_dump(mode="json")
    if LOCAL_MODE:
        _store[f"chat:{session.session_id}"] = {**data, "messages": []}
        return
    await asyncio.to_thread(
        lambda: get_db().collection("chat_sessions").document(session.session_id).set(data)
    )


async def get_chat_session(session_id: str) -> dict | None:
    if LOCAL_MODE:
        return _store.get(f"chat:{session_id}")
    doc = await asyncio.to_thread(
        lambda: get_db().collection("chat_sessions").document(session_id).get()
    )
    return doc.to_dict() if doc.exists else None


async def list_chat_messages(session_id: str) -> list[dict]:
    """Return all messages for a session in time order. Falls back to an
    empty list when the session has no messages yet."""
    if LOCAL_MODE:
        session_data = _store.get(f"chat:{session_id}", {})
        return list(session_data.get("messages", []))
    try:
        docs = await asyncio.to_thread(
            lambda: list(get_db()
                .collection("chat_sessions")
                .document(session_id)
                .collection("messages")
                .stream())
        )
        return sorted(
            (d.to_dict() for d in docs),
            key=lambda m: m.get("timestamp") or "",
        )
    except Exception as e:
        logger.warning("list_chat_messages failed: %s", e)
        return []


async def write_push_subscription(user_id: str, sub: dict) -> None:
    """Upsert a Web Push subscription for a user, keyed by endpoint so the
    same browser doesn't accumulate duplicates after re-permission."""
    endpoint = sub.get("endpoint") or ""
    if not endpoint:
        return
    sub_id = _hash_endpoint(endpoint)
    record = {**sub, "user_id": user_id, "endpoint": endpoint, "sub_id": sub_id}
    if LOCAL_MODE:
        _store.setdefault(f"push_subs:{user_id}", {})[sub_id] = record
        return
    try:
        await asyncio.to_thread(
            lambda: get_db()
                .collection("users").document(user_id)
                .collection("push_subscriptions").document(sub_id)
                .set(record, merge=True)
        )
    except Exception as e:
        logger.warning("write_push_subscription failed: %s", e)


async def list_push_subscriptions(user_id: str) -> list[dict]:
    """Every subscription for this user (one per browser/device)."""
    if LOCAL_MODE:
        return list((_store.get(f"push_subs:{user_id}") or {}).values())
    try:
        docs = await asyncio.to_thread(
            lambda: list(get_db()
                .collection("users").document(user_id)
                .collection("push_subscriptions").stream())
        )
        return [d.to_dict() for d in docs]
    except Exception as e:
        logger.warning("list_push_subscriptions failed: %s", e)
        return []


async def delete_push_subscription(user_id: str, endpoint: str) -> None:
    """Remove a single subscription. Called when the push service tells us
    the endpoint is gone (HTTP 404/410) or on explicit unsubscribe."""
    if not endpoint:
        return
    sub_id = _hash_endpoint(endpoint)
    if LOCAL_MODE:
        bucket = _store.get(f"push_subs:{user_id}") or {}
        bucket.pop(sub_id, None)
        return
    try:
        await asyncio.to_thread(
            lambda: get_db()
                .collection("users").document(user_id)
                .collection("push_subscriptions").document(sub_id)
                .delete()
        )
    except Exception as e:
        logger.warning("delete_push_subscription failed: %s", e)


def _hash_endpoint(endpoint: str) -> str:
    """Stable, filesystem-safe doc id derived from the endpoint URL."""
    import hashlib
    return hashlib.sha256(endpoint.encode()).hexdigest()[:32]


async def write_presence(user_id: str, doc: dict) -> None:
    """Upsert a presence document. Schema: {online: bool, last_seen: ISO8601}."""
    if LOCAL_MODE:
        _store[f"presence:{user_id}"] = doc
        return
    try:
        await asyncio.to_thread(
            lambda: get_db().collection("presence").document(user_id).set(doc, merge=True)
        )
    except Exception as e:
        logger.warning("write_presence failed: %s", e)


async def get_presence(user_id: str) -> dict | None:
    if LOCAL_MODE:
        return _store.get(f"presence:{user_id}")
    try:
        doc = await asyncio.to_thread(
            lambda: get_db().collection("presence").document(user_id).get()
        )
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.warning("get_presence failed: %s", e)
        return None


async def append_chat_message(session_id: str, message: dict) -> None:
    if LOCAL_MODE:
        session_data = _store.get(f"chat:{session_id}", {})
        session_data.setdefault("messages", []).append(message)
        _store[f"chat:{session_id}"] = session_data
        return
    msg_id = str(uuid.uuid4())
    await asyncio.to_thread(
        lambda: get_db()
            .collection("chat_sessions")
            .document(session_id)
            .collection("messages")
            .document(msg_id)
            .set(message)
    )
