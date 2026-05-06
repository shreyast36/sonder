# TODO: Jahnvi — define all Pydantic models and enums here.
# Every module imports from this file. Never redefine models elsewhere.
#
# Models to define:
#   Enums:       PacePreference, BudgetStyle, TravelStyle, EmotionIntent,
#                ValidationStatus, VisaRequirement, ModelTier, ApprovalStatus
#   User:        TripConstraints, PersonaQuestionAnswers, UserProfile
#   Trip:        Destination, Activity, ItineraryActivity, ItineraryDay, Itinerary
#   Validation:  ConstraintSatisfaction, ValidationResult
#   CoTraveller: CoTravellerProfile, CoTravellerMatch
#   Chat:        ChatMessage, ChatSession, SharedItinerary, ItineraryUpdateEvent
#   Visa:        VisaInfo
#   API:         PlanTripRequest, PlanTripResponse, UpdateTripRequest,
#                UpdateTripResponse(itinerary, validation, refinement_attempts, reached_max_attempts: bool)
#                — reached_max_attempts=True means the loop gave up; the itinerary is the best
#                  result after MAX_REFINEMENT_ATTEMPTS tries, not a validator-approved result.
#                  The frontend should show a soft warning: "We couldn't fully optimise your
#                  itinerary — here's the best version we found."
