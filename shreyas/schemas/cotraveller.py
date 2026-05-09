from pydantic import BaseModel, Field
from typing import Optional
from jahnvi.schemas.enums import PacePreference, BudgetStyle, TravelStyle


class CoTravellerProfile(BaseModel):
    """
    A synthetic or real co-traveller profile stored in Pinecone and Firestore.

    Example:
        CoTravellerProfile(
            profile_id   = "maya_001",
            display_name = "Maya Sharma",
            age          = 24,
            location     = "Delhi, India",
            archetype    = "Cultural Explorer",
            interests    = ["food", "culture", "photography"],
            pace         = PacePreference.relaxed,
            budget_style = BudgetStyle.mid_range,
            travel_style = TravelStyle.couple,
            avatar_url   = "https://...",
            embedding    = [0.031, ...]
        )
    """
    profile_id:   str
    display_name: str
    age:          int
    location:     str
    archetype:    str
    interests:    list[str]
    pace:         PacePreference
    budget_style: BudgetStyle
    travel_style: TravelStyle
    avatar_url:   Optional[str] = None
    embedding:    Optional[list[float]] = None


class CoTravellerMatch(BaseModel):
    """
    The result of Shreyas's compatibility scoring — shown on Screen 4.

    Example:
        CoTravellerMatch(
            profile         = CoTravellerProfile(display_name="Maya Sharma", ...),
            match_score     = 0.92,
            match_reasons   = [
                "Similar interests in food and culture",
                "Same travel pace",
                "Overlapping itinerary preferences",
                "Similar budget range"
            ],
            compatibility_breakdown = {
                "interests": 0.95,
                "pace":      1.0,
                "budget":    0.85,
                "itinerary": 0.88
            }
        )
    """
    profile:                 CoTravellerProfile
    match_score:             float = Field(ge=0.0, le=1.0)
    match_reasons:           list[str]
    compatibility_breakdown: dict
