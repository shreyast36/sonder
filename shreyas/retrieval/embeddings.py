from shared.config import EMBED_MODEL, EMBED_MODEL_PROVIDER, BEDROCK_EMBED_MODEL_ID, AWS_REGION
from shared.schemas import UserProfile

# Expected: text → vector using whichever embedding provider/model Shreyas configures.
#
# Set EMBED_MODEL_PROVIDER in .env to select your embedding provider.
# Set EMBED_MODEL (or BEDROCK_EMBED_MODEL_ID for bedrock) to the specific model ID.
# Vectors always go into Pinecone regardless of which provider generates them.
# EMBED_DIMENSIONS must match the model you choose.

def embed_text(text: str) -> list[float]:
    """
    Embed a single string into a float vector.

    Expected input:  "beach trip, relaxed pace, budget $2000, food lover"
    Expected output: [0.023, -0.187, 0.094, ...]  # length == EMBED_DIMENSIONS

    Use whichever provider you set in EMBED_MODEL_PROVIDER.
    """
    # TODO: call embedding API with EMBED_MODEL, return response vector
    raise NotImplementedError


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of strings in a single API call.

    Expected input:  ["Bali, Indonesia", "Kyoto, Japan", "Lisbon, Portugal"]
    Expected output: [[0.023, ...], [0.041, ...], [-0.012, ...]]
    """
    # TODO: batch embed — most providers accept a list in one request
    raise NotImplementedError


def build_user_query(user_profile: UserProfile) -> str:
    """
    Flatten a UserProfile into a descriptive string for embedding.

    Expected input:
        UserProfile(
            constraints=TripConstraints(destination_type="beach", pace_preference="relaxed", budget_usd=2000),
            persona_answers=PersonaQuestionAnswers(food_interest=5, adventure_interest=2, culture_interest=4),
            emotion_intent="excited"
        )

    Expected output:
        "beach trip | relaxed pace | budget $2000 | food=5 adventure=2 culture=4 | mood: excited"
    """
    # TODO: concatenate relevant fields into a single descriptive sentence
    raise NotImplementedError


def build_refined_query(user_profile: UserProfile, feedback: str) -> str:
    """
    [Gap 2] Extend build_user_query() with the user's explicit feedback text so the
    re-embedding captures intent that wasn't in the original preference answers.
    Called by the refinement loop before re-querying Pinecone.

    Expected input:
        user_profile = UserProfile(compatibility_signals={"pace": "relaxed", "top_interests": ["adventure", "food"]})
        feedback     = "I want more adventure and less time in museums"

    Expected output:
        "beach trip | relaxed pace | budget $2000 | food=5 adventure=5 culture=1 | mood: excited | feedback: more adventure, less museums"

    This string is embedded and used to re-query Pinecone — giving the retrieval layer
    a fresh signal rather than reusing the stale original embedding.
    """
    # TODO: base = build_user_query(user_profile)
    # TODO: return f"{base} | feedback: {feedback}"
    raise NotImplementedError
