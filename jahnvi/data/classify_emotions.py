"""
Cosine-similarity emotion classifier over the GoEmotions taxonomy.

How it works:
  1. At first call, embed each of the 27 GoEmotions label glosses via the
     same OpenAI 1536-dim model the rest of the persona pipeline uses.
     Cached in memory for the process lifetime.
  2. Embed the user's free text.
  3. Compute cosine similarity vs each label vector.
  4. Return the top-K labels sorted by similarity, with scores.

The scores are real cosine values (in [-1, 1], practically [0, 1] for similar
content), not LLM-fabricated confidences. They're a defensible signal — not
calibrated classification probabilities, but a meaningful ordering with
numeric weights the matcher can later use.
"""

import asyncio
import logging

from jahnvi.data.emotions import GOEMOTIONS_LABELS
from ali.vector.embeddings import embed_batch, embed_text

logger = logging.getLogger(__name__)

_LABEL_EMBEDDINGS: dict[str, list[float]] | None = None
_LABEL_LOCK = asyncio.Lock()


async def _get_label_embeddings() -> dict[str, list[float]]:
    """Lazily embed each label gloss once, cache for the process lifetime.
    Concurrent first-callers serialise on the lock so we only embed once."""
    global _LABEL_EMBEDDINGS
    if _LABEL_EMBEDDINGS is not None:
        return _LABEL_EMBEDDINGS
    async with _LABEL_LOCK:
        if _LABEL_EMBEDDINGS is not None:
            return _LABEL_EMBEDDINGS
        labels = list(GOEMOTIONS_LABELS.keys())
        # Embed "label: gloss" — the label word itself is a strong anchor.
        texts = [f"{label}: {gloss}" for label, gloss in GOEMOTIONS_LABELS.items()]
        try:
            vectors = await embed_batch(texts)
        except Exception as e:
            logger.warning("emotion label embedding failed: %s — classifier will return []", e)
            _LABEL_EMBEDDINGS = {}
            return _LABEL_EMBEDDINGS
        _LABEL_EMBEDDINGS = dict(zip(labels, vectors))
        return _LABEL_EMBEDDINGS


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


async def classify_emotions(text: str, top_k: int = 5) -> list[tuple[str, float]]:
    """Top-K (label, cosine) pairs ranked by similarity to the text.
    Returns [] for empty/blank input or if the label cache failed to build."""
    text = (text or "").strip()
    if not text:
        return []
    labels = await _get_label_embeddings()
    if not labels:
        return []
    try:
        vec = await embed_text(text)
    except Exception as e:
        logger.warning("emotion classify embed_text failed: %s", e)
        return []
    scored = [(label, _cosine(vec, lvec)) for label, lvec in labels.items()]
    scored.sort(key=lambda p: p[1], reverse=True)
    return scored[:max(1, top_k)]
