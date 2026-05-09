import openai
from shared.config import OPENAI_API_KEY, EMBED_MODEL, EMBED_MODEL_PROVIDER
from shared.schemas import UserProfile

# Default embedding model — set EMBED_MODEL in .env to override.
# text-embedding-3-small: 1536 dims, $0.02/1M tokens, best cost/quality for retrieval.
_DEFAULT_EMBED_MODEL = "text-embedding-3-small"


def _get_model() -> str:
    return EMBED_MODEL or _DEFAULT_EMBED_MODEL


def embed_text(text: str) -> list[float]:
    """
    Embed a single string into a float vector using OpenAI embeddings.
    Length == EMBED_DIMENSIONS (default 1536 for text-embedding-3-small).
    """
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(model=_get_model(), input=text)
    return response.data[0].embedding


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of strings in a single API call.
    Returns vectors in the same order as the input list.
    """
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(model=_get_model(), input=texts)
    # OpenAI returns results in the same order as input
    return [item.embedding for item in response.data]


def build_user_query(user_profile: UserProfile) -> str:
    """
    Flatten a UserProfile into a descriptive string for embedding.
    Used by Shreyas's search functions to query Pinecone.
    """
    parts = []

    if user_profile.constraints:
        c = user_profile.constraints
        parts.append(f"{c.destination_type} trip")
        parts.append(f"{c.pace_preference.value} pace")
        parts.append(f"budget ${c.budget_usd:.0f}")

    if user_profile.persona_answers:
        pa = user_profile.persona_answers
        interest_str = (
            f"food={pa.food_interest} adventure={pa.adventure_interest} "
            f"culture={pa.culture_interest} nature={pa.nature_interest} "
            f"nightlife={pa.nightlife_interest}"
        )
        parts.append(interest_str)

    if user_profile.emotion_intent:
        parts.append(f"mood: {user_profile.emotion_intent.value}")

    return " | ".join(parts) if parts else user_profile.display_name


def build_refined_query(user_profile: UserProfile, feedback: str) -> str:
    """
    Extend build_user_query() with explicit feedback text for re-querying Pinecone
    after refinement — gives the retrieval layer a fresh signal.
    """
    base = build_user_query(user_profile)
    return f"{base} | feedback: {feedback}"
