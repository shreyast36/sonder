"""
Heartbeat-based presence.

The client sends `{"type": "ping"}` on its WebSocket every ~30s; the route
calls heartbeat() which writes last_seen. is_online() never trusts the
boolean flag alone — a silent disconnect leaves online=true forever, so
we always check last_seen against PRESENCE_TTL_SECONDS.

Persisted shape (Firestore `presence/{user_id}` doc):
    {"online": bool, "last_seen": ISO8601 UTC}
"""

from datetime import datetime, timezone
from mushahid.realtime.firestore import write_presence, get_presence
from shared.config import PRESENCE_TTL_SECONDS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def set_online(user_id: str) -> None:
    await write_presence(user_id, {"online": True, "last_seen": _now_iso()})


async def set_offline(user_id: str) -> None:
    await write_presence(user_id, {"online": False, "last_seen": _now_iso()})


async def heartbeat(user_id: str) -> None:
    # Partial update keeps online=true; only refresh last_seen.
    await write_presence(user_id, {"online": True, "last_seen": _now_iso()})


async def is_online(user_id: str) -> bool:
    doc = await get_presence(user_id)
    if not doc or not doc.get("online"):
        return False
    last_seen = doc.get("last_seen")
    if not last_seen:
        return False
    try:
        ts = datetime.fromisoformat(last_seen)
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    if age >= PRESENCE_TTL_SECONDS:
        # Lazily mark offline so list views don't show ghosts.
        await set_offline(user_id)
        return False
    return True
