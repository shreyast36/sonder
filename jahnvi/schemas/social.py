"""
Social-layer models — posts, comments, and join-requests for the
Discover surface.

Owned by Jahnvi (schemas live under jahnvi/schemas). Re-exported from
shared/schemas.py. Mushahid owns the routes that read/write these;
Firestore is the persistence layer (no Pinecone — these are
ephemeral social objects, not retrieval targets).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SocialPost(BaseModel):
    """A short user-authored post that shows up in the /discover feed.

    `linked_trip_id` optionally anchors the post to a planned trip (so
    "going to Tokyo in March, anyone in?" can deep-link to the
    itinerary). `image_url` is reserved for v2 — no upload UI in v1.
    `comment_count` is denormalised so the feed list doesn't need to
    walk a subcollection per card.

    Example:
        SocialPost(
            post_id        = "post_abc123",
            author_id      = "firebase_uid_abc",
            author_name    = "Sarah",
            author_avatar  = "https://...",
            text           = "anyone done Lisbon's tile museum lately?",
            linked_trip_id = "itin_xyz",
            comment_count  = 3,
            created_at     = "2026-05-23T18:00:00Z",
        )
    """
    post_id:        str
    author_id:      str
    author_name:    str = "Traveller"
    author_avatar:  Optional[str] = None
    text:           str
    linked_trip_id: Optional[str] = None
    image_url:      Optional[str] = None
    comment_count:  int = 0
    created_at:     str


class SocialComment(BaseModel):
    """A reply on a SocialPost. Stored under
    posts/{post_id}/comments/{comment_id} for cheap per-post reads."""
    comment_id:    str
    post_id:       str
    author_id:     str
    author_name:   str = "Traveller"
    author_avatar: Optional[str] = None
    text:          str
    created_at:    str


class JoinRequest(BaseModel):
    """A user's request to join someone else's open trip. Owner of the
    target itinerary accepts → the requester is added to
    `Itinerary.co_traveller_ids` and a shared session is bootstrapped.
    Owner denies → the request is closed and the requester sees a
    polite "not this one" state in the UI.

    status flows:
        proposed → approved → (downstream: shared itinerary bootstrap)
        proposed → denied   → terminal
        proposed → withdrawn (requester pulled it back, optional v2)
    """
    request_id:    str
    itinerary_id:  str
    owner_id:      str
    requester_id:  str
    requester_name:   str = "Traveller"
    requester_avatar: Optional[str] = None
    message:       str = ""           # 1-2 sentence "why I'd be a good companion"
    status:        str = "proposed"    # "proposed" | "approved" | "denied" | "withdrawn"
    created_at:    str = ""


class OpenTripCard(BaseModel):
    """Compact projection of a joinable trip for the discovery feed.

    Built by the backend on the GET /api/discover/trips route — wraps
    just enough of the Itinerary for a card render without shipping
    the full days/activities tree. The frontend pulls full detail via
    /api/itineraries/{id} when the user taps a card."""
    itinerary_id:    str
    owner_id:        str
    owner_name:      str = "Traveller"
    owner_avatar:    Optional[str] = None
    destination_city:    str = ""
    destination_country: str = ""
    start_date:      Optional[str] = None  # ISO date
    end_date:        Optional[str] = None
    join_capacity:   int = 1
    confirmed_companions: int = 0          # len(co_traveller_ids)
    note:            str = ""              # optional 1-line owner pitch
    your_request_status: Optional[str] = None  # "proposed"/"approved"/"denied"/None
