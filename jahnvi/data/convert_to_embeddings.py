"""
HF embedding utilities for persona inference.

Lazy-loads sentence-transformers/all-mpnet-base-v2 (768-dim) and pre-computes
prototype embeddings for each PUSH/PULL dimension by embedding its keyword
list. module3_persona scores user persona text against these prototypes via
cosine similarity to produce dimension scores.

The model and prototypes are computed once and cached. For production,
FastAPI's lifespan should call `warm_up()` at startup so the first request
doesn't pay the ~1-2s model load.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from jahnvi.data.dimensions import ALL_DIMENSIONS
from jahnvi.data.persona_labels import label_for
from jahnvi.schemas.user import TripConstraints, PersonaQuestionAnswers

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Lazy singleton. Call warm_up() at app startup to avoid cold-start latency."""
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def dimension_prototypes() -> dict[str, list[float]]:
    """Pre-compute one prototype embedding per dimension from its keyword list."""
    model = get_model()
    return {
        dim: model.encode(" ".join(keywords), normalize_embeddings=True).tolist()
        for dim, keywords in ALL_DIMENSIONS.items()
    }


def embed_text(text: str) -> list[float]:
    """Embed arbitrary text. Returns 768-dim L2-normalized vector."""
    return get_model().encode(text or "", normalize_embeddings=True).tolist()


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


def embed_persona(
    constraints: TripConstraints | None,
    answers: PersonaQuestionAnswers | None,
) -> list[float]:
    """Build persona text from form payload and embed. Returns 768-dim normalized vector."""
    return embed_text(build_persona_text(constraints, answers))


def warm_up() -> None:
    """Load the model and pre-compute prototypes. Call at FastAPI startup."""
    get_model()
    dimension_prototypes()
