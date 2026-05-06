from jahnvi.schemas.user import UserProfile, PersonaQuestionAnswers
from jahnvi.schemas.enums import EmotionIntent
from jahnvi.data.persona_templates import PERSONA_TEMPLATES, TEMPLATES_BY_ARCHETYPE


def infer_persona(answers: PersonaQuestionAnswers) -> dict:
    """
    Classify the user into a persona archetype based on their preference answers.
    Used by Ali's routing engine and Shreyas's matching algorithm.

    Canonical archetypes are defined in jahnvi/data/persona_templates.py — do not
    hardcode archetype names here. Use TEMPLATES_BY_ARCHETYPE for the label and
    embed_keywords once you've classified.

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
    # TODO: rule-based or weighted classification — score each PERSONA_TEMPLATE
    #       against answers.interests and answers.pace_preference, pick highest score.
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


def update_profile_from_feedback(profile: UserProfile, feedback: str) -> UserProfile:
    """
    [Gap 3] Merge explicit user feedback into the profile's signals and re-embed.
    Called by the refinement loop before every re-ranking pass so Pinecone is
    queried with signals that reflect what the user actually wants — not just the
    original preference answers.

    Expected input:
        profile  = UserProfile(compatibility_signals={"pace": "relaxed", "top_interests": ["food", "culture"]})
        feedback = "I want more adventure and less time in museums"

    Expected output:
        UserProfile with updated compatibility_signals:
            {"pace": "relaxed", "top_interests": ["adventure", "food"], "feedback_weight": 0.4}
        And updated travel_style_embedding (re-embedded from the merged signals).

    Steps:
        1. Parse feedback text for intent signals (boost adventure, drop culture, etc.)
           — rule-based keywords or a SMALL model call (Ali's route_request)
        2. Merge parsed signals into profile.compatibility_signals
        3. Rebuild the embedding string with the new signals + feedback text appended
        4. Re-call embed_text() to get a fresh travel_style_embedding
        5. Return the updated profile — caller writes it to Firestore
    """
    # TODO: parse feedback for signal updates
    # TODO: merge into profile.compatibility_signals
    # TODO: profile.travel_style_embedding = build_travel_style_embedding(profile)
    raise NotImplementedError
