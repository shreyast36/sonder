from mushahid.realtime.firestore import get_db

# Presence data lives in Firestore: presence/{user_id}
# { "online": true, "last_seen": "2025-06-01T09:30:00Z" }


async def set_online(user_id: str) -> None:
    """
    Mark a user as online in Firestore.

    Expected Firestore write:
        presence/{user_id} → { "online": true, "last_seen": <now> }
    """
    # TODO: get_db().collection("presence").document(user_id).set({"online": True, "last_seen": ...})
    raise NotImplementedError


async def set_offline(user_id: str) -> None:
    """
    Mark a user as offline.

    Expected Firestore write:
        presence/{user_id} → { "online": false, "last_seen": <now> }
    """
    # TODO: update presence doc
    raise NotImplementedError


async def is_online(user_id: str) -> bool:
    """
    Check if a user is currently online.

    Expected output: True | False
    """
    # TODO: get presence doc, return doc["online"]
    raise NotImplementedError
