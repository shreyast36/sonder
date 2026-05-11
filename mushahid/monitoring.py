import logging
from shared.config import POSTHOG_API_KEY

logger = logging.getLogger(__name__)
_ph = None


def _get_ph():
    global _ph
    if _ph is not None:
        return _ph
    if not POSTHOG_API_KEY:
        return None
    from posthog import Posthog
    _ph = Posthog(api_key=POSTHOG_API_KEY, host="https://us.i.posthog.com")
    return _ph


def capture(uid: str, event: str, properties: dict | None = None) -> None:
    ph = _get_ph()
    if ph is None:
        return
    try:
        ph.capture(uid, event, properties or {})
    except Exception:
        logger.warning("PostHog capture failed: %s", event)
