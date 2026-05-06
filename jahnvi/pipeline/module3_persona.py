from jahnvi.schemas.user import UserProfile, PersonaQuestionAnswers
from jahnvi.schemas.enums import EmotionIntent


def infer_persona(answers: PersonaQuestionAnswers) -> dict:
    """
    Classify the user into a persona archetype based on their preference answers.
    Used by Ali's routing engine and Shreyas's matching algorithm.

    Suggested archetypes (your decision — add/remove as needed):
        "Cultural Explorer"   → high culture + food interest, relaxed pace
        "Adventure Seeker"    → high adventure + nature interest, packed pace
        "Relaxed Wanderer"    → low energy, relaxed pace, mid-range budget
        "Party Traveller"     → high nightlife interest, packed pace
        "Foodie"              → food_interest == 5, culture moderate

    Expected input:
        PersonaQuestionAnswers(food_interest=5, culture_interest=4, adventure_interest=2, pace_preference="relaxed")

    Expected output:
        {
            "archetype": "Cultural Explorer",
            "top_interests": ["food", "culture"],
            "energy": "low-moderate",
            "label": "You love discovering local culture through food and art at a relaxed pace."
        }
    """
    # TODO: rule-based or weighted classification into archetype
    raise NotImplementedError


def infer_emotion(signals: dict) -> EmotionIntent:
    """
    Detect the user's current travel mood from input signals.
    Feeds into itinerary generation to adjust tone and activity density.

    Expected input (from frontend context — pace slider, text hints, selections):
        {
            "pace_preference": "relaxed",
            "energy_level": 2,
            "keywords": ["unwind", "peaceful", "slow down"]
        }

    Expected output:
        EmotionIntent.relaxed

    Mapping hints:
        energy_level 1–2 + "unwind" keywords → tired / relaxed
        energy_level 4–5 + adventure keywords → excited / adventurous
        culture keywords → curious
    """
    # TODO: rule-based or lightweight classifier
    raise NotImplementedError


def build_compatibility_signals(profile: UserProfile) -> dict:
    """
    Extract structured signals used by Shreyas's co-traveller matching algorithm.

    Expected input:  fully populated UserProfile
    Expected output:
        {
            "pace":          "relaxed",
            "budget_style":  "mid_range",
            "travel_style":  "couple",
            "top_interests": ["food", "culture", "nature"],
            "energy":        3
        }
    """
    # TODO: extract from persona_answers and constraints
    raise NotImplementedError


def build_travel_style_embedding(profile: UserProfile) -> list[float]:
    """
    Generate a vector embedding from the user's persona for co-traveller search.
    Stores the result in profile.travel_style_embedding.

    This vector is what Shreyas queries Pinecone with to find compatible profiles.

    Expected input:  UserProfile with constraints + persona_answers populated
    Expected output: list[float] of length EMBED_DIMENSIONS
    """
    # TODO: build a descriptive string from the profile, call shreyas/retrieval/embeddings.py embed_text()
    raise NotImplementedError
