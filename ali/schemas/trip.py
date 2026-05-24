from pydantic import BaseModel
from typing import Optional
from datetime import date


class Destination(BaseModel):
    """
    Example:
        Destination(
            destination_id      = "bali_001",
            city                = "Bali",
            country             = "Indonesia",
            avg_daily_cost_usd  = 120.0,
            tags                = ["beach", "culture", "food", "nature"],
            description         = "Tropical island known for temples, rice terraces, and surf.",
            image_url           = "https://...",
            embedding           = [0.023, ...]  # set by Shreyas before upserting to Pinecone
        )
    """
    destination_id:     str
    city:               str
    country:            str
    avg_daily_cost_usd: float
    tags:               list[str]
    description:        str
    image_url:          Optional[str] = None
    embedding:          Optional[list[float]] = None


class Activity(BaseModel):
    """
    Example:
        Activity(
            activity_id    = "uluwatu_001",
            name           = "Uluwatu Temple",
            category       = "culture",
            cost_usd       = 15.0,
            duration_hours = 2.0,
            tags           = ["culture", "scenic", "spiritual"],
            description    = "Clifftop sea temple with sweeping Indian Ocean views.",
            image_url      = "https://...",
            embedding      = [0.041, ...]
        )
    """
    activity_id:    str
    name:           str
    category:       str
    cost_usd:       float
    duration_hours: float
    tags:           list[str]
    description:    str
    image_url:      Optional[str] = None
    embedding:      Optional[list[float]] = None


class ItineraryActivity(BaseModel):
    """
    An activity placed at a specific time in the itinerary.

    Example:
        ItineraryActivity(
            activity = Activity(name="Uluwatu Temple", ...),
            time     = "9:00 AM",
            why_this = "This matches your relaxed pace and love for culture and scenic views."
        )
    """
    activity: Activity
    time:     str
    why_this: Optional[str] = None


class ItineraryDay(BaseModel):
    """
    Example:
        ItineraryDay(
            day_number       = 1,
            trip_date        = date(2025, 6, 1),
            activities       = [ItineraryActivity(...), ItineraryActivity(...)],
            daily_cost_usd   = 145.0,
            theme            = "Culture & Coastal Views"
        )
    """
    day_number:     int
    trip_date:      Optional[date] = None   # field name shadowed datetime.date in Pydantic v2 — use trip_date
    activities:     list[ItineraryActivity]
    daily_cost_usd: float
    theme:          Optional[str] = None


class Itinerary(BaseModel):
    """
    Full trip plan. Output of Ali's itinerary generator.

    Example:
        Itinerary(
            itinerary_id     = "itin_abc123",
            user_id          = "firebase_uid_abc123",
            destination      = Destination(city="Bali", ...),
            days             = [ItineraryDay(day_number=1, ...), ...],
            total_budget_usd = 840.0,
            notes            = [],
            co_traveller_ids = []
        )
    """
    itinerary_id:     str
    user_id:          str
    destination:      Destination
    days:             list[ItineraryDay]
    total_budget_usd: float
    notes:            list[str] = []
    co_traveller_ids: list[str] = []
    # Trip-discovery fields. When `is_open_to_join` is True, the trip
    # surfaces in /discover for other users to request joining. Owner
    # can flip this on/off and adjust `join_capacity` (how many more
    # co-travellers they want — independent of co_traveller_ids which
    # tracks already-confirmed companions).
    is_open_to_join:  bool = False
    join_capacity:    int  = 1

    # Lifecycle: draft → finalized. Every generated itinerary starts as
    # a draft and only flips to finalized after the user hits the
    # explicit approval gate on /itinerary. Finalized itineraries are
    # locked: no more automatic regeneration, ranker weights are
    # frozen, the trip transitions into the shared-itinerary surface
    # for collaborative editing.
    approval_status:  str  = "draft"   # "draft" | "finalized"
    finalized_at:     Optional[str] = None
    # Append-only record of revision turns — each entry stores the
    # feedback string, what changed, the dropped/replaced titles, and
    # the validator outcome. Used as the dedupe memory so a future
    # revision never resurfaces a title the user already rejected.
    revision_history: list[dict] = []
