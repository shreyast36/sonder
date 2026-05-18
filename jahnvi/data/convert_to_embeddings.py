"""
Persona text builder + embedding wrapper.

Embedding is delegated to ali.vector.embeddings.embed_text, which reads
EMBED_MODEL_PROVIDER from .env (currently openai → text-embedding-3-small,
1536-dim — same model + space as the seeded Pinecone corpus). No local
HF model is loaded, so this module has no startup cost and zero memory
footprint beyond the OpenAI client.
"""

from ali.vector.embeddings import embed_text as _provider_embed_text

from jahnvi.data.persona_labels import label_for
from jahnvi.schemas.user import TripConstraints, PersonaQuestionAnswers


async def embed_text(text: str) -> list[float]:
    """Embed arbitrary text. Returns the configured provider's vector (1536-dim for OpenAI)."""
    return await _provider_embed_text(text or "")


def build_persona_text(
    constraints: TripConstraints | None,
    answers: PersonaQuestionAnswers | None,
) -> str:
    """Concatenate all natural-language signals from the form payload."""
    parts: list[str] = []

    if constraints:
        if constraints.must_haves:
            parts.extend(constraints.must_haves)
        for field in ("friends_would_say", "restaurant_order", "what_you_notice", "ideal_atmosphere"):
            label = label_for(field, getattr(constraints, field, None))
            if label:
                parts.append(label)
        if constraints.pace:
            parts.append(constraints.pace.value)
        if constraints.who_travelling_with:
            parts.append(constraints.who_travelling_with.value)

    if answers and answers.small_thing:
        parts.append(answers.small_thing)

    return ". ".join(p.strip() for p in parts if p and p.strip())


async def embed_persona(
    constraints: TripConstraints | None,
    answers: PersonaQuestionAnswers | None,
) -> list[float]:
    """Build persona text from form payload and embed via the configured provider."""
    return await embed_text(build_persona_text(constraints, answers))
