from mushahid.realtime.firestore import get_db
from shared.config import PRESENCE_TTL_SECONDS

# Presence data lives in Firestore: presence/{user_id}
# { "online": true, "last_seen": "2025-06-01T09:30:00Z" }
#
# [Gap 5] Heartbeat-based presence:
# The client sends a WebSocket "ping" message every ~30 seconds.
# Shreyas's ConnectionManager routes pings to heartbeat() which refreshes last_seen.
# is_online() uses last_seen + PRESENCE_TTL_SECONDS for stale detection instead of
# trusting the "online" flag, which can get stuck true if a connection drops silently.


async def set_online(user_id: str) -> None:
    """
    Mark a user as online in Firestore.

    Expected Firestore write:
        presence/{user_id} → { "online": true, "last_seen": <now> }
    """
    # TODO: get_db().collection("presence").document(user_id).set({"online": True, "last_seen": datetime.utcnow().isoformat()})
    raise NotImplementedError


async def set_offline(user_id: str) -> None:
    """
    Mark a user as offline.

    Expected Firestore write:
        presence/{user_id} → { "online": false, "last_seen": <now> }
    """
    # TODO: get_db().collection("presence").document(user_id).update({"online": False, "last_seen": ...})
    raise NotImplementedError


async def heartbeat(user_id: str) -> None:
    """
    [Gap 5] Refresh last_seen for a connected user. Called every time the client
    sends a WebSocket "ping" message (every ~30 seconds).

    This is the TTL reset — if a connection drops silently, last_seen will go stale
    and is_online() will return False after PRESENCE_TTL_SECONDS without a heartbeat.

    Expected Firestore write:
        presence/{user_id} → { "last_seen": <now> }  (partial update, keeps online=true)
    """
    # TODO: get_db().collection("presence").document(user_id).update({"last_seen": datetime.utcnow().isoformat()})
    raise NotImplementedError


async def is_online(user_id: str) -> bool:
    """
    [Gap 5] Check if a user is currently online using last_seen TTL rather than
    the boolean flag alone. Returns False if last_seen is older than PRESENCE_TTL_SECONDS
    even if online=true, handling silent disconnects.

    Expected output: True | False

    Expected logic:
        doc = presence/{user_id}
        if not doc.exists or not doc["online"]: return False
        age = now - parse(doc["last_seen"])
        return age.total_seconds() < PRESENCE_TTL_SECONDS
    """
    # TODO: get presence doc, check last_seen age against PRESENCE_TTL_SECONDS
    # TODO: if stale, also call set_offline(user_id) to clean up the flag
    raise NotImplementedError


async def cleanup_stale_presence() -> int:
    """
    [Gap 5] Scan all presence documents and mark stale ones offline.
    Call this from a FastAPI background task on a regular interval (e.g. every 60s).

    Expected output: number of users marked offline

    Expected logic:
        for doc in presence collection where online == true:
            if age(doc["last_seen"]) > PRESENCE_TTL_SECONDS:
                set_offline(doc.user_id)
    """
    # TODO: query presence collection where online == true
    # TODO: for each doc, check last_seen age and call set_offline if stale
    raise NotImplementedError
