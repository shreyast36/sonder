# Jahnvi — copy all finalised models here from jahnvi/schemas/ so every module
# can import from a single location. Never redefine models — re-export only.
#
# Schemas are defined in:
#   jahnvi/schemas/enums.py       → PacePreference, BudgetStyle, TravelStyle, EmotionIntent,
#                                    ValidationStatus, VisaRequirement, ModelTier, ApprovalStatus
#   jahnvi/schemas/user.py        → TripConstraints, PersonaQuestionAnswers, UserProfile
#   jahnvi/schemas/trip.py        → Destination, Activity, ItineraryActivity, ItineraryDay, Itinerary
#   jahnvi/schemas/validation.py  → ConstraintSatisfaction, ValidationResult
#   jahnvi/schemas/cotraveller.py → CoTravellerProfile, CoTravellerMatch
#   jahnvi/schemas/chat.py        → ChatMessage, ChatSession, SharedItinerary, ItineraryUpdateEvent
#   jahnvi/schemas/api.py         → VisaInfo, PlanTripRequest, PlanTripResponse,
#                                    UpdateTripRequest, UpdateTripResponse
#
# Once schemas are finalised, replace the TODOs below with real imports:
# TODO: from jahnvi.schemas.enums       import *
# TODO: from jahnvi.schemas.user        import *
# TODO: from jahnvi.schemas.trip        import *
# TODO: from jahnvi.schemas.validation  import *
# TODO: from jahnvi.schemas.cotraveller import *
# TODO: from jahnvi.schemas.chat        import *
# TODO: from jahnvi.schemas.api         import *
