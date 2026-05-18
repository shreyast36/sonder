from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from jahnvi.schemas.enums import (
    PacePreference, BudgetStyle, TravelStyle, EmotionIntent,
    Occasion, EnergyLevel,
)


class TripConstraints(BaseModel):
    """
    Hard constraints + vibe selections from the trip preferences form.
    Vibe fields (occasion, contrast_seeking, energy_level, hotel_style,
    dining_vibe, day_activities) map directly to Pinecone metadata filters
    at retrieval time.
    """
    destination_query:          str = ""
    destination_type:           str = ""
    nationality:                str = ""
    start_date:                 Optional[date] = None
    end_date:                   Optional[date] = None
    flexible_dates:             bool = False
    budget_usd:                 float = 0.0
    budget_currency:            str = "USD"
    group_size:                 int = 1
    who_travelling_with:        Optional[TravelStyle] = None
    must_haves:                 list[str] = Field(default_factory=list)
    avoid_list:                 list[str] = Field(default_factory=list)

    # Vibe selections — drive Pinecone filters at retrieval
    occasion:                   Optional[Occasion] = None
    contrast_seeking:           list[str] = Field(default_factory=list)
    energy_level:               Optional[EnergyLevel] = None
    hotel_style:                list[str] = Field(default_factory=list)
    dining_vibe:                list[str] = Field(default_factory=list)
    day_activities:             list[str] = Field(default_factory=list)


class PersonaQuestionAnswers(BaseModel):
    """
    Free-text anchors. Embedded as travel_style_embedding for vector search.
    """
    loved_destination:  str = ""
    must_haves_text:    str = ""
    avoid_text:         str = ""


class CompatibilityAnswers(BaseModel):
    """
    Free-text answers from TravellerCompatibility — embedded into
    compatibility_embedding, used only by co-traveller matching.
    """
    trust_behaviour:          str = ""
    space_behaviour:          str = ""
    natural_role:             str = ""
    travelled_well_with:      str = ""
    travelled_badly_with:     str = ""
    when_plans_fall_apart:    str = ""
    comfortable_silence:      str = ""
    late_night_conversations: str = ""
    independence_needed:      str = ""
    travel_again:             str = ""


class UserProfile(BaseModel):
    user_id:                 str
    display_name:            str
    constraints:             Optional[TripConstraints] = None
    persona_answers:         Optional[PersonaQuestionAnswers] = None
    compatibility_answers:   Optional[CompatibilityAnswers] = None
    emotion_intent:          Optional[EmotionIntent] = None
    travel_style_embedding:  Optional[list[float]] = None
    compatibility_embedding: Optional[list[float]] = None
    compatibility_signals:   dict = Field(default_factory=dict)
