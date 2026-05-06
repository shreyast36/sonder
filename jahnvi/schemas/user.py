from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from jahnvi.schemas.enums import PacePreference, BudgetStyle, TravelStyle, EmotionIntent


class TripConstraints(BaseModel):
    """
    Hard constraints captured on Screen 2 (Trip Preferences form).

    Example:
        TripConstraints(
            destination_type = "beach",
            start_date       = date(2025, 6, 1),
            end_date         = date(2025, 6, 7),
            budget_usd       = 2000.0,
            group_size       = 2,
            pace_preference  = PacePreference.relaxed,
            must_haves       = ["snorkeling", "local food"],
            avoid_list       = ["nightclubs", "theme parks"]
        )
    """
    destination_type: str
    start_date: date
    end_date: date
    budget_usd: float
    group_size: int
    pace_preference: PacePreference
    must_haves: list[str] = Field(default_factory=list)
    avoid_list: list[str] = Field(default_factory=list)


class PersonaQuestionAnswers(BaseModel):
    """
    Soft preference answers captured on Screen 2.
    All interest fields are 1–5 scales.

    Example:
        PersonaQuestionAnswers(
            food_interest      = 5,
            adventure_interest = 2,
            culture_interest   = 4,
            nature_interest    = 3,
            nightlife_interest = 1,
            budget_style       = BudgetStyle.mid_range,
            travel_style       = TravelStyle.couple,
            pace_preference    = PacePreference.relaxed,
            energy_level       = 3
        )
    """
    food_interest:      int = Field(ge=1, le=5)
    adventure_interest: int = Field(ge=1, le=5)
    culture_interest:   int = Field(ge=1, le=5)
    nature_interest:    int = Field(ge=1, le=5)
    nightlife_interest: int = Field(ge=1, le=5)
    budget_style:       BudgetStyle
    travel_style:       TravelStyle
    pace_preference:    PacePreference
    energy_level:       int = Field(ge=1, le=5)


class UserProfile(BaseModel):
    """
    Full user profile built progressively through the pipeline.
    Populated by Modules 1–3; used by every downstream module.

    Example (fully populated):
        UserProfile(
            user_id                  = "firebase_uid_abc123",
            display_name             = "Arjun",
            constraints              = TripConstraints(...),
            persona_answers          = PersonaQuestionAnswers(...),
            emotion_intent           = EmotionIntent.excited,
            travel_style_embedding   = [0.023, -0.187, ...],  # 1536-dim vector
            compatibility_signals    = {"pace": "relaxed", "top_interests": ["food", "culture"]}
        )
    """
    user_id: str
    display_name: str
    constraints: Optional[TripConstraints] = None
    persona_answers: Optional[PersonaQuestionAnswers] = None
    emotion_intent: Optional[EmotionIntent] = None
    travel_style_embedding: Optional[list[float]] = None
    compatibility_signals: dict = Field(default_factory=dict)
