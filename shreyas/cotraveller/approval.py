from shared.schemas import ApprovalStatus
from mushahid.realtime.firestore import get_db
from mushahid.realtime.notifications import notify_co_traveller_approved


async def approve_match(session_id: str, user_id: str) -> ApprovalStatus:
    """
    Record a user's approval in Firestore.
    If both users have now approved → trigger shared itinerary creation.

    Expected Firestore structure:
        chat_sessions/{session_id} → {
            "user_approval": true | false,
            "profile_approval": true | false,
            "status": "pending" | "approved" | "denied"
        }

    Expected output:
        ApprovalStatus.approved  ← if both approved
        ApprovalStatus.pending   ← if waiting on the other user
    """
    # TODO: write approval, check if both approved, create shared itinerary if so
    raise NotImplementedError


async def deny_match(session_id: str, user_id: str) -> ApprovalStatus:
    """
    Record a denial. Close the session and notify the other user.

    Expected output: ApprovalStatus.denied
    """
    # TODO: set status=denied in Firestore, notify other user
    raise NotImplementedError


async def get_approval_status(session_id: str) -> ApprovalStatus:
    """
    Read the current approval status for a session.

    Expected output: ApprovalStatus.pending | .approved | .denied
    """
    # TODO: read from Firestore, return enum value
    raise NotImplementedError
