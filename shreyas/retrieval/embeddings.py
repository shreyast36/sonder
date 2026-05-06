from shared.config import EMBED_MODEL, OPENAI_API_KEY
from shared.schemas import UserProfile

# Expected: text → vector using whichever embedding model Ali configures via EMBED_MODEL.

def embed_text(text: str) -> list[float]:
    """
    Embed a single string into a float vector.

    Expected input:  "beach trip, relaxed pace, budget $2000, food lover"
    Expected output: [0.023, -0.187, 0.094, ...]  # length == EMBED_DIMENSIONS

    Starter: use the OpenAI embeddings API (or swap provider based on EMBED_MODEL).
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
