"""
PostHog product analytics.

All event names live as module-level constants so the dashboard side stays
consistent — no `"trip_planned"` typos floating around. `capture()` is for
user-attributed events (uid required); `capture_system()` is for events
where there's no user yet (cron jobs, seed scripts, system-wide error
counters). Both no-op when POSTHOG_API_KEY isn't configured, so dev envs
without the key never break.

Five top-level metrics this powers:
  - User satisfaction        → match_approved/denied, refinement attempts
  - Retrieval quality         → retrieval_done with destination/activity counts
  - Response quality          → validator_stack_execution per surface
  - Hallucination rate        → itinerary_validation + persona_validation
                                approval rates + issue category counts
  - Itinerary completion rate → trip_plan_started → trip_done → trip_saved
                                → trip_viewed funnel
"""

import logging
from typing import Any

from shared.config import POSTHOG_API_KEY, POSTHOG_HOST

logger = logging.getLogger(__name__)
_ph = None


# ── Event names (single source of truth) ──────────────────────────────────


# Auth / onboarding
EVENT_USER_SIGNED_UP        = "user_signed_up"
EVENT_PERSONA_FORM_STARTED  = "persona_form_started"

# Persona inference
EVENT_PERSONA_INFERRED         = "persona_inferred"
EVENT_PERSONA_VALIDATION       = "persona_validation"

# Trip planning funnel
EVENT_TRIP_PLAN_STARTED        = "trip_plan_started"
EVENT_RETRIEVAL_DONE           = "retrieval_done"
EVENT_TRIP_GENERATED           = "trip_generated"
EVENT_TRIP_VALIDATION          = "itinerary_validation"
EVENT_TRIP_REFINEMENT_ATTEMPTED = "trip_refinement_attempted"
EVENT_TRIP_DONE                = "trip_planned"      # legacy event name kept
EVENT_TRIP_SAVED               = "trip_saved"
EVENT_TRIP_SET_CURRENT         = "trip_set_current"
EVENT_TRIP_VIEWED              = "trip_viewed"

# Cotraveller matching
EVENT_MATCH_FOUND              = "match_found"       # legacy event name kept
EVENT_MATCH_REGENERATED        = "match_regenerated"
EVENT_MATCH_APPROVED           = "match_approved"
EVENT_MATCH_DENIED             = "match_denied"
EVENT_MATCH_PROFILE_VIEWED     = "match_profile_viewed"

# Chat
EVENT_CHAT_STARTED             = "chat_started"      # legacy event name kept
EVENT_CHAT_MESSAGE_SENT        = "chat_message_sent"
EVENT_CHAT_REPLY_SENT          = "chat_reply_sent"
EVENT_CHAT_VALIDATOR_EXECUTION = "validator_stack_execution"

# Journal / discovery
EVENT_JOURNAL_ENTRY_CREATED    = "journal_entry_created"
EVENT_DESTINATION_FEED_VIEWED  = "destination_feed_viewed"

# Errors / system
EVENT_PIPELINE_ERROR           = "pipeline_error"


# ── Client init ────────────────────────────────────────────────────────────


def _get_ph():
    global _ph
    if _ph is not None:
        return _ph
    if not POSTHOG_API_KEY:
        return None
    from posthog import Posthog
    _ph = Posthog(api_key=POSTHOG_API_KEY, host=POSTHOG_HOST)
    return _ph


# ── Public API ─────────────────────────────────────────────────────────────


def capture(uid: str, event: str, properties: dict | None = None) -> None:
    """User-attributed event. `uid` becomes the PostHog distinct_id so events
    aggregate per-user in dashboards. Properties dict is shallow — nested
    objects get flattened by PostHog's UI."""
    ph = _get_ph()
    if ph is None:
        return
    try:
        ph.capture(uid or "anonymous", event, _clean_props(properties))
    except Exception:
        logger.warning("PostHog capture failed: %s", event)


def capture_system(event: str, properties: dict | None = None) -> None:
    """Non-user-attributed event (cron, system error, batch job). Uses a
    fixed `_system_` distinct_id so these are easy to filter out of user
    cohort dashboards but still queryable on their own."""
    capture("_system_", event, properties)


def _clean_props(props: dict | None) -> dict[str, Any]:
    """Shallow-coerce non-JSON-serializable values into strings so PostHog
    accepts the payload. Lists / dicts pass through; everything else
    becomes a str representation."""
    if not props:
        return {}
    out: dict[str, Any] = {}
    for k, v in props.items():
        if v is None or isinstance(v, (bool, int, float, str, list, dict)):
            out[k] = v
        else:
            out[k] = str(v)
    return out
