from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from jahnvi.schemas.enums import (
    PacePreference, BudgetStyle, TravelStyle, EmotionIntent,
)


class TripConstraints(BaseModel):
    """
    Hard constraints + personality probes from the trip preferences form.
    Personality probes (friends_would_say, restaurant_order, what_you_notice,
    ideal_atmosphere) are non-travel single-select reveals that shape
    ranking; the embedding from PersonaQuestionAnswers handles vibe-level
    matching.
    """
    destination_query:    str = ""
    destination_type:     str = ""
    nationality:          str = ""
    start_date:           Optional[date] = None
    end_date:             Optional[date] = None
    flexible_dates:       bool = False
    budget_usd:           float = 0.0
    budget_currency:      str = "USD"
    group_size:           int = 1
    who_travelling_with:  Optional[TravelStyle] = None
    must_haves:           list[str] = Field(default_factory=list)
    avoid_list:           list[str] = Field(default_factory=list)

    # Personality probes — non-travel single-select reveals
    friends_would_say:    Optional[str] = None
    restaurant_order:     Optional[str] = None
    what_you_notice:      Optional[str] = None
    ideal_atmosphere:     Optional[str] = None


class PersonaQuestionAnswers(BaseModel):
    """
    Free-text anchor. Embedded as travel_style_embedding for vector search.
    """
    small_thing:  str = ""


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
