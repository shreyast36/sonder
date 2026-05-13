from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from jahnvi.schemas.enums import PacePreference, BudgetStyle, TravelStyle, EmotionIntent


class TripConstraints(BaseModel):
    """
    Hard constraints captured in Part 1 of the trip preferences form.
    All free-text fields are parsed by module1_constraints.py before use.

    Example:
        TripConstraints(
            destination_query       = "Bali",
            destination_type        = "beach",
            nationality             = "British",
            start_date              = date(2025, 6, 1),
            end_date                = date(2025, 6, 7),
            flexible_dates          = False,
            budget_usd              = 2000.0,
            budget_currency         = "GBP",
            group_size              = 2,
            who_travelling_with     = TravelStyle.couple,
            accommodation_preference= "boutique hotel with a view",
            hire_car                = True,
            has_driving_licence     = True,
            must_haves              = ["snorkeling", "local food"],
            avoid_list              = ["nightclubs"]
        )
    """
    destination_query:          str = ""           # specific city/country the user named
    destination_type:           str = ""           # descriptor when undecided ("beach", "city")
    nationality:                str = ""           # free text — used for visa checks
    start_date:                 Optional[date] = None
    end_date:                   Optional[date] = None
    flexible_dates:             bool = False
    budget_usd:                 float = 0.0        # always USD — converted by capture_constraints()
    budget_currency:            str = "USD"        # ISO 4217 code the user entered; kept for display
    group_size:                 int = 1
    who_travelling_with:        Optional[TravelStyle] = None
    accommodation_preference:   str = ""           # free text — parsed to tags in module1
    hire_car:                   bool = False
    has_driving_licence:        Optional[bool] = None  # only relevant if hire_car=True
    must_haves:                 list[str] = Field(default_factory=list)
    avoid_list:                 list[str] = Field(default_factory=list)


class PersonaQuestionAnswers(BaseModel):
    """
    Free-text answers from Part 2 of the trip preferences form.
    All fields are embedded together to produce travel_style_embedding on UserProfile.
    All fields are optional — users can skip any question.

    Example:
        PersonaQuestionAnswers(
            travel_goal       = "I want to feel alive again after a long stretch of work",
            travel_personality= "My friends say I always find the hidden spots no one else knows about",
            pace_preference   = "I like mornings packed and afternoons free to wander",
            must_not_miss     = "Eating at a place with no English menu",
            leave_behind      = "My phone and the urge to document everything",
            ideal_companion   = "Someone who can sit in comfortable silence but goes deep when we talk",
            dream_trip        = "Slow mornings, long lunches, discovering something unexpected every day",
        )
    """
    # Part 2 — core persona questions
    travel_goal:        str = ""
    travel_personality: str = ""
    pace_preference:    str = ""
    must_not_miss:      str = ""
    leave_behind:       str = ""
    ideal_companion:    str = ""
    dream_trip:         str = ""

    # Screen 3 deep-dive personality questions (one at a time)
    memorable_moment:    str = ""
    natural_drift:       str = ""
    impulsive_decision:  str = ""
    experiences_avoided: str = ""
    perfect_afternoon:   str = ""
    lose_track_of_time:  str = ""
    small_special:       str = ""


class CompatibilityAnswers(BaseModel):
    """
    Free-text answers from Screen 11 (TravellerCompatibility).
    Embedded separately from PersonaQuestionAnswers to produce compatibility_embedding —
    used exclusively by Shreyas's co-traveller matching algorithm.
    All fields are optional — users can skip any question.

    Example:
        CompatibilityAnswers(
            trust_behaviour  = "They adapt without complaining when something goes wrong",
            natural_role     = "The one who finds the restaurant — I always research food",
            travelled_well_with = "My friend Mia — she matched my energy without needing to fill every silence",
        )
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
    """
    Full user profile built progressively through the pipeline.
    Populated by Modules 1–3; used by every downstream module.

    Two separate embedding vectors:
      travel_style_embedding  — from PersonaQuestionAnswers (itinerary generation + destination search)
      compatibility_embedding — from CompatibilityAnswers (co-traveller matching only)

    Example (fully populated):
        UserProfile(
            user_id                 = "firebase_uid_abc123",
            display_name            = "Arjun",
            constraints             = TripConstraints(...),
            persona_answers         = PersonaQuestionAnswers(...),
            compatibility_answers   = CompatibilityAnswers(...),
            emotion_intent          = EmotionIntent.excited,
            travel_style_embedding  = [0.023, -0.187, ...],   # 1536-dim
            compatibility_embedding = [0.041, -0.093, ...],   # 1536-dim
            compatibility_signals   = {"pace": "relaxed", "top_interests": ["food", "culture"]}
        )
    """
    user_id:                 str
    display_name:            str
    constraints:             Optional[TripConstraints] = None
    persona_answers:         Optional[PersonaQuestionAnswers] = None
    compatibility_answers:   Optional[CompatibilityAnswers] = None
    emotion_intent:          Optional[EmotionIntent] = None
    travel_style_embedding:  Optional[list[float]] = None
    compatibility_embedding: Optional[list[float]] = None
    compatibility_signals:   dict = Field(default_factory=dict)
