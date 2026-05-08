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
    solo   = "solo"
    couple = "couple"
    family = "family"
    group  = "group"


class EmotionIntent(str, Enum):
    tired       = "tired"
    excited     = "excited"
    relaxed     = "relaxed"
    curious     = "curious"
    adventurous = "adventurous"


class ValidationStatus(str, Enum):
    approved = "approved"
    revise   = "revise"


class VisaRequirement(str, Enum):
    visa_free       = "visa_free"
    visa_on_arrival = "visa_on_arrival"
    visa_required   = "visa_required"
    unknown         = "unknown"


class ModelTier(str, Enum):
    small = "small"
    large = "large"


class ApprovalStatus(str, Enum):
    pending  = "pending"
    approved = "approved"
    denied   = "denied"
