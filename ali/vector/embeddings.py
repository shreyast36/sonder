import asyncio
import openai
from shared.config import OPENAI_API_KEY, EMBED_MODEL, EMBED_MODEL_PROVIDER
from shared.schemas import UserProfile

_local_model = None
_openai_embed_client: openai.AsyncOpenAI | None = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _local_model


def _get_openai_embed_client() -> openai.AsyncOpenAI:
    global _openai_embed_client
    if _openai_embed_client is None:
        _openai_embed_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_embed_client


async def embed_text(text: str) -> list[float]:
    """
    Embed a single string into a float vector.
    Provider controlled by EMBED_MODEL_PROVIDER in .env:
      local  -> sentence-transformers all-MiniLM-L6-v2 (384 dims, no API key)
      openai -> text-embedding-3-small (1536 dims, requires OPENAI_API_KEY)
    """
    if EMBED_MODEL_PROVIDER == "local":
        result = await asyncio.to_thread(_get_local_model().encode, text)
        return result.tolist()
    response = await _get_openai_embed_client().embeddings.create(
        model=EMBED_MODEL or "text-embedding-3-small", input=text
    )
    return response.data[0].embedding


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of strings. Returns vectors in the same order as input.
    """
    if EMBED_MODEL_PROVIDER == "local":
        result = await asyncio.to_thread(_get_local_model().encode, texts)
        return result.tolist()
    response = await _get_openai_embed_client().embeddings.create(
        model=EMBED_MODEL or "text-embedding-3-small", input=texts
    )
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
        parts.append(
            f"food={pa.food_interest} adventure={pa.adventure_interest} "
            f"culture={pa.culture_interest} nature={pa.nature_interest} "
            f"nightlife={pa.nightlife_interest}"
        )

    if user_profile.emotion_intent:
        parts.append(f"mood: {user_profile.emotion_intent.value}")

    return " | ".join(parts) if parts else user_profile.display_name


def build_refined_query(user_profile: UserProfile, feedback: str) -> str:
    """
    Extend build_user_query() with explicit feedback for re-querying Pinecone after refinement.
    """
    return f"{build_user_query(user_profile)} | feedback: {feedback}"
