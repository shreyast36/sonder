from pydantic import BaseModel, Field
from typing import Optional
from shreyas.schemas.enums import ApprovalStatus
from ali.schemas.trip import Itinerary


class ChatMessage(BaseModel):
    """
    A single message in a chat session.

    Example:
        ChatMessage(
            message_id = "msg_001",
            session_id = "session_abc",
            sender_id  = "user_abc",
            content    = "Hey! Excited to connect! Where are you traveling from?",
            timestamp  = "2025-06-01T09:30:00Z",
            seen       = False
        )
    """
    message_id: str
    session_id: str
    sender_id:  str
    content:    str
    timestamp:  str
    seen:       bool = False


class ChatSession(BaseModel):
    """
    A chat session between a user and a co-traveller profile.

    Example:
        ChatSession(
            session_id      = "session_abc",
            user_id         = "firebase_uid_abc123",
            profile_id      = "maya_001",
            approval_status = ApprovalStatus.pending,
            created_at      = "2025-06-01T09:00:00Z"
        )
    """
    session_id:      str
    user_id:         str
    profile_id:      str
    approval_status: ApprovalStatus = ApprovalStatus.pending
    created_at:      str
    # The trip this chat is anchored to. The synthetic persona's replies
    # are pinned to this trip's destination — without it the persona drifts
    # into talking about their own home city or preferred destination
    # instead of the user's actual planned trip. Optional only for back-
    # compat with sessions created before this field existed.
    itinerary_id:    str | None = None
    # Per-side decisions. The overall approval_status is derived from
    # these (both approved → approved; either denied → denied; else
    # pending). Tracking each side independently is what lets the UI
    # show "you've decided, waiting for them" progress states.
    user_decision:    ApprovalStatus = ApprovalStatus.pending
    profile_decision: ApprovalStatus = ApprovalStatus.pending


class SharedItinerary(BaseModel):
    """
    A collaborative itinerary shared between two users after mutual approval.
    Stored in Firestore and synced in real time.

    version is incremented on every write and used for optimistic locking:
    a write is only accepted if the client's version matches the current Firestore version.
    This prevents the last-write-wins silent overwrite when both users edit simultaneously.

    Example:
        SharedItinerary(
            itinerary_id    = "itin_abc123",
            user_ids        = ["firebase_uid_abc123", "maya_001"],
            itinerary       = Itinerary(...),
            notes           = [
                {"user_id": "maya_001",  "note": "Let's wake up early on Day 2!", "timestamp": "..."},
                {"user_id": "user_abc",  "note": "Great idea!", "timestamp": "..."}
            ],
            last_updated_by = "maya_001",
            version         = 4
        )
    """
    itinerary_id:    str
    user_ids:        list[str]
    itinerary:       Itinerary
    notes:           list[dict] = Field(default_factory=list)
    last_updated_by: Optional[str] = None
    version:         int = 0  # increment on every write; clients must send current version


class ChatStartResponse(BaseModel):
    """
    Response from POST /chat/start — bundles the new session with AI-generated
    conversation starters so the frontend can render them immediately on Screen 5.

    Example:
        ChatStartResponse(
            session    = ChatSession(session_id="session_abc", ...),
            icebreaker = "Hey Maya! Both foodies in Bali — what's top of your must-eat list?",
            topics     = [
                "Must-try local food in Bali",
                "Beach vs adventure balance",
                "Cultural experiences to explore",
                "Budget-friendly activities",
                "Best time to travel & weather"
            ]
        )
    """
    session:    ChatSession
    icebreaker: str
    topics:     list[str]


class ItineraryUpdateEvent(BaseModel):
    """
    A real-time event broadcast when the shared itinerary changes.

    event_type options:
        "activity_added" | "note_added" | "change_proposed" | "co_traveller_joined"

    Example:
        ItineraryUpdateEvent(
            event_type   = "note_added",
            itinerary_id = "itin_abc123",
            user_id      = "maya_001",
            payload      = {"note": "Let's wake up early!", "timestamp": "..."},
            timestamp    = "2025-06-01T10:00:00Z"
        )
    """
    event_type:   str
    itinerary_id: str
    user_id:      str
    payload:      dict
    timestamp:    str
