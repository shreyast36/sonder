from enum import Enum


class PacePreference(str, Enum):
    relaxed  = "relaxed"
    moderate = "moderate"
    packed   = "packed"


class BudgetStyle(str, Enum):
    budget    = "budget"
    mid_range = "mid_range"
    luxury    = "luxury"


class TravelStyle(str, Enum):
    solo    = "solo"
    couple  = "couple"
    family  = "family"
    friends = "friends"


class EmotionIntent(str, Enum):
    tired       = "tired"
    excited     = "excited"
    relaxed     = "relaxed"
    curious     = "curious"
    adventurous = "adventurous"


class Occasion(str, Enum):
    once_in_a_lifetime = "once_in_a_lifetime"
    anniversary        = "anniversary"
    escape             = "escape"
    reset              = "reset"
    adventure          = "adventure"
    just_because       = "just_because"
    work_play          = "work_play"


class EnergyLevel(str, Enum):
    chill    = "chill"
    balanced = "balanced"
    packed   = "packed"
