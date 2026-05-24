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


async def write_user_ranker_weights(user_id: str, surface: str, weights: dict) -> None:
    """Merge per-surface ranker weights into a user's compatibility_signals.
    Read by the engine at rank() time via _resolve_weights — when absent,
    falls back to the policy's uniform defaults."""
    if not surface:
        return
    if LOCAL_MODE:
        key = f"profile:{user_id}"
        prof = _store.get(key) or {}
        cs = dict(prof.get("compatibility_signals") or {})
        rw = dict(cs.get("ranker_weights") or {})
        rw[surface] = dict(weights)
        cs["ranker_weights"] = rw
        prof["compatibility_signals"] = cs
        _store[key] = prof
        return
    try:
        # Firestore dotted paths let us merge a sub-field without rewriting
        # the whole compatibility_signals dict.
        await asyncio.to_thread(
            lambda: get_db()
                .collection("user_profiles").document(user_id)
                .set({"compatibility_signals": {"ranker_weights": {surface: dict(weights)}}}, merge=True)
        )
    except Exception as e:
        logger.warning("write_user_ranker_weights failed: %s", e)


async def write_ranking_event(event: dict) -> None:
    """Single-event write used by feature_logging.record_*. Fire-and-forget
    from the caller — failures are logged at warning and never raised."""
    if LOCAL_MODE:
        eid = event.get("event_id") or f"evt_{len(_store)}"
        _store[f"ranking_event:{eid}"] = event
        return
    try:
        eid = event.get("event_id")
        coll = get_db().collection("ranking_events")
        if eid:
            await asyncio.to_thread(lambda: coll.document(eid).set(event))
        else:
            await asyncio.to_thread(lambda: coll.add(event))
    except Exception as e:
        logger.warning("write_ranking_event failed: %s", e)


async def update_feature_stats(observations: list[dict]) -> None:
    """Batched aggregate of per-feature observations. Uses Welford's online
    algorithm so mean/variance stay accurate without holding raw samples.
    p50/p95 are approximated by the running max/min in V1 — proper
    quantile sketches can come later if we need them."""
    if not observations:
        return
    if LOCAL_MODE:
        # Naive aggregation into _store so tests can inspect distribution
        # without firing real Firestore writes.
        for obs in observations:
            key = f"feature_stats:{obs.get('surface')}__{obs.get('feature')}"
            doc = dict(_store.get(key) or {"count": 0, "mean": 0.0, "m2": 0.0})
            value = float(obs.get("value") or 0.0)
            doc["count"] += 1
            delta = value - doc["mean"]
            doc["mean"] += delta / doc["count"]
            delta2 = value - doc["mean"]
            doc["m2"] += delta * delta2
            doc["last_value"] = value
            doc["last_update"] = obs.get("timestamp")
            _store[key] = doc
        return
    try:
        db = get_db()
        # One transaction-ish write per doc — Firestore client batches not
        # used here to keep this dependency-light. Volume is small (one per
        # rank call * features per call), and observability is best-effort.
        for obs in observations:
            doc_id = f"{obs.get('surface')}__{obs.get('feature')}"
            ref = db.collection("feature_stats").document(doc_id)
            await asyncio.to_thread(
                lambda r=ref, o=obs: r.set({
                    "surface":     o.get("surface"),
                    "feature":     o.get("feature"),
                    "day":         o.get("day"),
                    "last_value":  float(o.get("value") or 0.0),
                    "last_update": o.get("timestamp"),
                }, merge=True)
            )
    except Exception as e:
        logger.warning("update_feature_stats failed: %s", e)


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


async def delete_itinerary_and_related(itinerary_id: str) -> dict:
    """Hard-delete an itinerary and every doc bound to it.

    Cleans up: the itinerary doc, its shared-itinerary twin (if any),
    its companion_prefs doc, every journal entry tagged to it, and
    every chat_session anchored to it (along with each session's
    messages subcollection). Cotraveller matches are unique per trip
    — when the trip is deleted, the conversation context is gone too,
    so the match goes with it.

    Returns a count breakdown so the caller can log / surface what
    was removed. Caller is responsible for purging the user_profile
    pointer (saved_itinerary_ids / current_itinerary_id) since that
    requires the uid, which this helper doesn't take.
    """
    removed = {
        "itinerary": 0, "shared_itinerary": 0, "companion_prefs": 0,
        "journal_entries": 0, "chat_sessions": 0, "chat_messages": 0,
    }
    if LOCAL_MODE:
        if _store.pop(f"itinerary:{itinerary_id}", None) is not None:
            removed["itinerary"] = 1
        if _store.pop(f"shared:{itinerary_id}", None) is not None:
            removed["shared_itinerary"] = 1
        if _store.pop(f"companion_prefs:{itinerary_id}", None) is not None:
            removed["companion_prefs"] = 1
        j_keys = [k for k, v in _store.items()
                  if k.startswith("journal:") and v.get("itinerary_id") == itinerary_id]
        for k in j_keys:
            _store.pop(k, None)
        removed["journal_entries"] = len(j_keys)
        # Chat sessions in LOCAL_MODE are stored under "chat:{session_id}"
        # with the session data at the top level (see write_chat_session).
        c_keys = []
        for k, v in list(_store.items()):
            if not k.startswith("chat:"):
                continue
            if isinstance(v, dict) and v.get("itinerary_id") == itinerary_id:
                c_keys.append(k)
        for k in c_keys:
            v = _store.pop(k, {}) or {}
            removed["chat_messages"] += len(v.get("messages") or [])
        removed["chat_sessions"] = len(c_keys)
        return removed

    db = get_db()
    # Itinerary doc.
    try:
        await asyncio.to_thread(lambda: db.collection("itineraries").document(itinerary_id).delete())
        removed["itinerary"] = 1
    except Exception as e:
        logger.warning("delete itinerary doc failed: %s", e)
    # Shared-itinerary twin (best-effort — most trips won't have one).
    try:
        await asyncio.to_thread(lambda: db.collection("shared_itineraries").document(itinerary_id).delete())
        removed["shared_itinerary"] = 1
    except Exception as e:
        logger.debug("delete shared itinerary doc failed (likely none existed): %s", e)
    # Companion prefs.
    try:
        await asyncio.to_thread(lambda: db.collection("companion_prefs").document(itinerary_id).delete())
        removed["companion_prefs"] = 1
    except Exception as e:
        logger.debug("delete companion_prefs failed: %s", e)
    # Journal entries — query then bulk delete.
    try:
        docs = await asyncio.to_thread(
            lambda: list(db.collection("journal_entries")
                           .where("itinerary_id", "==", itinerary_id)
                           .stream())
        )
        for d in docs:
            try:
                await asyncio.to_thread(lambda r=d.reference: r.delete())
                removed["journal_entries"] += 1
            except Exception as e:
                logger.warning("delete journal entry %s failed: %s", d.id, e)
    except Exception as e:
        logger.warning("query journal entries for delete failed: %s", e)

    # Chat sessions tied to this trip — and their messages subcollection.
    # Cotraveller matches are unique per trip; the session anchors the
    # conversation to the trip's context (itinerary digest, persona-
    # weights snapshot, match score), so deleting the trip removes the
    # match too. We page through messages in 200-doc batches to bound
    # the worst-case round-trip count on long threads.
    try:
        sess_docs = await asyncio.to_thread(
            lambda: list(db.collection("chat_sessions")
                           .where("itinerary_id", "==", itinerary_id)
                           .stream())
        )
        for sd in sess_docs:
            sid = sd.id
            # Delete messages subcollection in batches.
            try:
                while True:
                    msg_batch = await asyncio.to_thread(
                        lambda: list(db.collection("chat_sessions")
                                       .document(sid)
                                       .collection("messages")
                                       .limit(200)
                                       .stream())
                    )
                    if not msg_batch:
                        break
                    for m in msg_batch:
                        try:
                            await asyncio.to_thread(lambda r=m.reference: r.delete())
                            removed["chat_messages"] += 1
                        except Exception as e:
                            logger.warning("delete chat message %s/%s failed: %s", sid, m.id, e)
                    if len(msg_batch) < 200:
                        break
            except Exception as e:
                logger.warning("paged delete of messages for session %s failed: %s", sid, e)
            # Then the session doc itself.
            try:
                await asyncio.to_thread(lambda r=sd.reference: r.delete())
                removed["chat_sessions"] += 1
            except Exception as e:
                logger.warning("delete chat session %s failed: %s", sid, e)
    except Exception as e:
        logger.warning("query chat_sessions for delete failed: %s", e)

    return removed


async def get_itinerary(itinerary_id: str) -> Itinerary | None:
    from pydantic import ValidationError as PydanticValidationError
    if LOCAL_MODE:
        data = _store.get(f"itinerary:{itinerary_id}")
        if not data:
            return None
        try:
            return Itinerary.model_validate(data)
        except PydanticValidationError as e:
            logger.warning("get_itinerary: malformed local document for %s: %s", itinerary_id, e)
            return None
    doc = await asyncio.to_thread(
        lambda: get_db().collection("itineraries").document(itinerary_id).get()
    )
    if not doc.exists:
        return None
    try:
        return Itinerary.model_validate(doc.to_dict())
    except PydanticValidationError as e:
        logger.warning("get_itinerary: malformed Firestore document for %s: %s", itinerary_id, e)
        return None


# ── Shared itinerary (collaborative negotiation surface) ──────────────────


async def write_shared_itinerary(shared) -> None:
    """Upsert the SharedItinerary doc. Caller increments version +
    sets last_updated_by before calling."""
    if LOCAL_MODE:
        _store[f"shared:{shared.itinerary_id}"] = shared.model_dump()
        return
    data = shared.model_dump(mode="json")
    try:
        await asyncio.to_thread(
            lambda: get_db().collection("shared_itineraries").document(shared.itinerary_id).set(data)
        )
    except Exception as e:
        logger.warning("write_shared_itinerary failed: %s", e)


async def get_shared_itinerary(itinerary_id: str):
    """Return the SharedItinerary or None when no shared doc exists yet."""
    from shared.schemas import SharedItinerary
    if LOCAL_MODE:
        data = _store.get(f"shared:{itinerary_id}")
        return SharedItinerary.model_validate(data) if data else None
    try:
        doc = await asyncio.to_thread(
            lambda: get_db().collection("shared_itineraries").document(itinerary_id).get()
        )
        return SharedItinerary.model_validate(doc.to_dict()) if doc.exists else None
    except Exception as e:
        logger.warning("get_shared_itinerary failed for %s: %s", itinerary_id, e)
        return None



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


async def list_outreach_eligible_users(limit: int = 50) -> list[dict]:
    """Return user_profile docs eligible for synthetic-persona outreach
    chats. Eligibility:
      - has a current_itinerary_id (something for the persona to anchor on)
      - travel style is solo or couple (family / friends excluded)

    Returns thin summaries: {user_id, current_itinerary_id, who, group}.
    Cap is generous; the synthetic agents loop picks one at random per
    cycle so even 50 candidates rotates enough."""
    if LOCAL_MODE:
        out: list[dict] = []
        for key, val in _store.items():
            if not key.startswith("profile:") or not isinstance(val, dict):
                continue
            current = val.get("current_itinerary_id")
            if not current:
                continue
            constraints = val.get("constraints") or {}
            who = (constraints.get("who_travelling_with") or "").lower()
            if who not in ("solo", "couple"):
                continue
            out.append({
                "user_id":              val.get("user_id") or key.split(":", 1)[1],
                "current_itinerary_id": current,
                "who":                  who,
                "group_size":           constraints.get("group_size", 1),
            })
            if len(out) >= limit:
                break
        return out
    try:
        # Firestore "in" supports up to 30 values per query, so two
        # round-trips is fine for the two eligible styles. We over-fetch
        # since the next filter pass (has current_itinerary_id) happens
        # in Python.
        docs = await asyncio.to_thread(
            lambda: list(
                get_db().collection("user_profiles")
                .where("constraints.who_travelling_with", "in", ["solo", "couple"])
                .limit(limit).stream()
            )
        )
        out: list[dict] = []
        for d in docs:
            data = d.to_dict() or {}
            current = data.get("current_itinerary_id")
            if not current:
                continue
            constraints = data.get("constraints") or {}
            out.append({
                "user_id":              data.get("user_id") or d.id,
                "current_itinerary_id": current,
                "who":                  constraints.get("who_travelling_with"),
                "group_size":           constraints.get("group_size", 1),
            })
        return out
    except Exception as e:
        logger.warning("list_outreach_eligible_users failed: %s", e)
        return []


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


async def list_chat_sessions_for_user(user_id: str) -> list[dict]:
    """Return every chat session this user is a participant in (either
    side). Used by the matching route to filter out previously-denied
    profiles and detect active approved pairings.
    Falls back to an empty list when Firestore is unreachable."""
    if LOCAL_MODE:
        out: list[dict] = []
        for key, val in _store.items():
            if not key.startswith("chat:"):
                continue
            s = val.get("session") if isinstance(val, dict) else None
            if s and (s.get("user_id") == user_id or s.get("profile_id") == user_id):
                out.append(s)
        return out
    try:
        # Two queries because Firestore doesn't OR-where naturally.
        # Most users have a small handful of sessions, so this is cheap.
        as_user = await asyncio.to_thread(
            lambda: list(get_db().collection("chat_sessions")
                         .where("user_id", "==", user_id).limit(200).stream())
        )
        as_profile = await asyncio.to_thread(
            lambda: list(get_db().collection("chat_sessions")
                         .where("profile_id", "==", user_id).limit(200).stream())
        )
        seen: set[str] = set()
        out: list[dict] = []
        for d in (*as_user, *as_profile):
            data = d.to_dict() or {}
            sid = data.get("session_id") or d.id
            if sid in seen:
                continue
            seen.add(sid)
            out.append(data)
        return out
    except Exception as e:
        logger.warning("list_chat_sessions_for_user failed for %s: %s", user_id, e)
        return []


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
    # Use the caller's message_id as the Firestore doc id when it's
    # present so update_chat_message_content can find the doc by key.
    # Falls back to a fresh uuid for legacy messages without a
    # message_id field.
    msg_id = (message.get("message_id") or "").strip() or str(uuid.uuid4())
    await asyncio.to_thread(
        lambda: get_db()
            .collection("chat_sessions")
            .document(session_id)
            .collection("messages")
            .document(msg_id)
            .set(message)
    )


async def update_chat_message_content(session_id: str, message_id: str, content: str) -> bool:
    """Update an existing chat message's `content` field in place. Used
    by the async validator path that swaps the persona's reply text
    after the initial broadcast. Returns True on success."""
    if not session_id or not message_id:
        return False
    if LOCAL_MODE:
        session_data = _store.get(f"chat:{session_id}", {})
        msgs = session_data.get("messages") or []
        for m in msgs:
            if isinstance(m, dict) and m.get("message_id") == message_id:
                m["content"] = content
                return True
        return False
    # Firestore path: first try the message_id-keyed doc (the new
    # write convention). If that doesn't exist (legacy uuid-keyed
    # docs), query by message_id field and update the match.
    try:
        ref = get_db().collection("chat_sessions").document(session_id) \
                      .collection("messages").document(message_id)
        snap = await asyncio.to_thread(ref.get)
        if getattr(snap, "exists", False):
            await asyncio.to_thread(lambda: ref.set({"content": content}, merge=True))
            return True
        # Fallback: query.
        docs = await asyncio.to_thread(
            lambda: list(
                get_db().collection("chat_sessions").document(session_id)
                        .collection("messages")
                        .where("message_id", "==", message_id)
                        .limit(1).stream()
            )
        )
        if docs:
            await asyncio.to_thread(lambda: docs[0].reference.set({"content": content}, merge=True))
            return True
        return False
    except Exception as e:
        logger.warning("update_chat_message_content failed for %s/%s: %s", session_id, message_id, e)
        return False


# ── Discover surface: open trips + join requests + social feed ────────────


async def list_open_trips(limit: int = 60) -> list[dict]:
    """Return Itinerary docs where is_open_to_join=True. Bounded so the
    feed query stays cheap; v1 has no pagination — newest first."""
    if LOCAL_MODE:
        out = [v for k, v in _store.items()
               if k.startswith("itinerary:")
               and isinstance(v, dict)
               and v.get("is_open_to_join")]
        return sorted(out, key=lambda d: d.get("created_at") or "", reverse=True)[:limit]
    try:
        docs = await asyncio.to_thread(
            lambda: list(
                get_db().collection("itineraries")
                .where("is_open_to_join", "==", True)
                .limit(limit).stream()
            )
        )
        return [d.to_dict() | {"itinerary_id": d.id} for d in docs]
    except Exception as e:
        logger.warning("list_open_trips failed: %s", e)
        return []


async def set_itinerary_open(itinerary_id: str, *, is_open: bool, join_capacity: int) -> bool:
    """Flip an itinerary's join-discovery state. Returns True on success."""
    payload = {"is_open_to_join": bool(is_open), "join_capacity": max(0, int(join_capacity))}
    if LOCAL_MODE:
        key = f"itinerary:{itinerary_id}"
        if key not in _store:
            return False
        _store[key] = {**_store[key], **payload}
        return True
    try:
        await asyncio.to_thread(
            lambda: get_db().collection("itineraries").document(itinerary_id).set(payload, merge=True)
        )
        return True
    except Exception as e:
        logger.warning("set_itinerary_open failed for %s: %s", itinerary_id, e)
        return False


async def write_join_request(req: dict) -> None:
    """Upsert a JoinRequest. request_id is the key. Caller mints it."""
    rid = req.get("request_id")
    if not rid:
        return
    if LOCAL_MODE:
        _store[f"join_request:{rid}"] = req
        return
    try:
        await asyncio.to_thread(
            lambda: get_db().collection("join_requests").document(rid).set(req)
        )
    except Exception as e:
        logger.warning("write_join_request failed: %s", e)


async def get_join_request(request_id: str) -> dict | None:
    if LOCAL_MODE:
        return _store.get(f"join_request:{request_id}")
    try:
        doc = await asyncio.to_thread(
            lambda: get_db().collection("join_requests").document(request_id).get()
        )
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.warning("get_join_request failed: %s", e)
        return None


async def list_join_requests_for_user(user_id: str, *, as_owner: bool = False) -> list[dict]:
    """Return requests where the user is either the requester (default)
    or the owner (as_owner=True). v1 caps at 50 — most users won't have
    more open requests than that."""
    field = "owner_id" if as_owner else "requester_id"
    if LOCAL_MODE:
        return [v for k, v in _store.items()
                if k.startswith("join_request:")
                and isinstance(v, dict)
                and v.get(field) == user_id]
    try:
        docs = await asyncio.to_thread(
            lambda: list(
                get_db().collection("join_requests")
                .where(field, "==", user_id)
                .limit(50).stream()
            )
        )
        return [d.to_dict() for d in docs]
    except Exception as e:
        logger.warning("list_join_requests_for_user failed for %s: %s", user_id, e)
        return []


async def write_social_post(post: dict) -> None:
    """Upsert a SocialPost. post_id is the key."""
    pid = post.get("post_id")
    if not pid:
        return
    if LOCAL_MODE:
        _store[f"post:{pid}"] = post
        return
    try:
        await asyncio.to_thread(
            lambda: get_db().collection("social_posts").document(pid).set(post)
        )
    except Exception as e:
        logger.warning("write_social_post failed: %s", e)


async def get_social_post(post_id: str) -> dict | None:
    if LOCAL_MODE:
        return _store.get(f"post:{post_id}")
    try:
        doc = await asyncio.to_thread(
            lambda: get_db().collection("social_posts").document(post_id).get()
        )
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.warning("get_social_post failed: %s", e)
        return None


async def delete_social_post(post_id: str) -> bool:
    if LOCAL_MODE:
        existed = f"post:{post_id}" in _store
        _store.pop(f"post:{post_id}", None)
        # Also drop any comments under this post.
        for k in [k for k in _store.keys() if k.startswith(f"comment:{post_id}:")]:
            _store.pop(k, None)
        return existed
    try:
        # Best-effort delete of comments subcollection first, then the doc.
        await asyncio.to_thread(
            lambda: [
                d.reference.delete()
                for d in get_db().collection("social_posts").document(post_id)
                                .collection("comments").stream()
            ]
        )
        await asyncio.to_thread(
            lambda: get_db().collection("social_posts").document(post_id).delete()
        )
        return True
    except Exception as e:
        logger.warning("delete_social_post failed for %s: %s", post_id, e)
        return False


async def list_social_posts(limit: int = 40, before: str | None = None) -> list[dict]:
    """Newest-first feed page. `before` is the ISO timestamp of the
    oldest post the client already has — passing it walks older pages.
    v1 returns up to 40 posts; pagination is keyset-style on created_at."""
    if LOCAL_MODE:
        all_posts = [v for k, v in _store.items()
                     if k.startswith("post:") and isinstance(v, dict)]
        all_posts.sort(key=lambda p: p.get("created_at") or "", reverse=True)
        if before:
            all_posts = [p for p in all_posts if (p.get("created_at") or "") < before]
        return all_posts[:limit]
    try:
        q = get_db().collection("social_posts").order_by("created_at", direction="DESCENDING").limit(limit)
        if before:
            q = q.start_after({"created_at": before})
        docs = await asyncio.to_thread(lambda: list(q.stream()))
        return [d.to_dict() for d in docs]
    except Exception as e:
        logger.warning("list_social_posts failed: %s", e)
        return []


async def write_social_comment(post_id: str, comment: dict) -> None:
    cid = comment.get("comment_id")
    if not cid:
        return
    if LOCAL_MODE:
        _store[f"comment:{post_id}:{cid}"] = comment
        return
    try:
        await asyncio.to_thread(
            lambda: get_db().collection("social_posts")
                            .document(post_id)
                            .collection("comments")
                            .document(cid).set(comment)
        )
    except Exception as e:
        logger.warning("write_social_comment failed: %s", e)


async def list_social_comments(post_id: str, limit: int = 50) -> list[dict]:
    """Oldest-first so the thread reads top-to-bottom."""
    if LOCAL_MODE:
        out = [v for k, v in _store.items()
               if k.startswith(f"comment:{post_id}:") and isinstance(v, dict)]
        return sorted(out, key=lambda c: c.get("created_at") or "")[:limit]
    try:
        docs = await asyncio.to_thread(
            lambda: list(
                get_db().collection("social_posts")
                .document(post_id)
                .collection("comments")
                .order_by("created_at")
                .limit(limit).stream()
            )
        )
        return [d.to_dict() for d in docs]
    except Exception as e:
        logger.warning("list_social_comments failed for %s: %s", post_id, e)
        return []


async def increment_post_comment_count(post_id: str, delta: int = 1) -> None:
    """Denormalised counter on SocialPost so the feed query doesn't need
    to count subcollection sizes per card. Best-effort — failure is logged
    and ignored; the next post update will fix the count."""
    if LOCAL_MODE:
        key = f"post:{post_id}"
        if key not in _store:
            return
        cur = int(_store[key].get("comment_count") or 0)
        _store[key]["comment_count"] = max(0, cur + delta)
        return
    try:
        from google.cloud.firestore import Increment
        await asyncio.to_thread(
            lambda: get_db().collection("social_posts").document(post_id)
                            .set({"comment_count": Increment(delta)}, merge=True)
        )
    except Exception as e:
        logger.debug("increment_post_comment_count failed for %s: %s", post_id, e)
