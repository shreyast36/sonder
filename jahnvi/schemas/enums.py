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
