"""
Pinecone client — manual embedding via OpenAI text-embedding-3-small.

Switched from Pinecone's integrated embedding (llama-text-embed-v2) because
that has a 10M-token/month cap on the Builder plan. OpenAI's text-embedding-3-small
is paid (~$0.02 per 1M tokens, ~$0.30 for our full seed) but uncapped.

Callers:
  1. Build records with a `text` field (whatever should be embedded)
  2. Call `embed_texts(texts)` to get 1536-dim vectors
  3. Upsert vectors manually via `index.upsert(vectors=[{id, values, metadata}, ...])`
"""

import asyncio
import logging
import os

from openai import AsyncOpenAI
from pinecone import Pinecone, ServerlessSpec

from shared.config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME

logger = logging.getLogger(__name__)

OPENAI_EMBED_MODEL = "text-embedding-3-small"
OPENAI_EMBED_DIM   = 1536
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")

_index = None
_index_lock = asyncio.Lock()
_openai_client: AsyncOpenAI | None = None


async def get_pinecone_index():
    """Returns the Pinecone index, creating a manual-embedding index if missing.

    The index is plain serverless cosine with 1536-dim (matching text-embedding-3-small).
    No integrated embedding model is attached — callers must embed text first.
    """
    global _index
    if _index is not None:
        return _index

    async with _index_lock:
        if _index is not None:
            return _index

        pc = Pinecone(api_key=PINECONE_API_KEY)
        existing = await asyncio.to_thread(lambda: [idx.name for idx in pc.list_indexes()])

        if PINECONE_INDEX_NAME not in existing:
            logger.info(
                "Creating Pinecone index '%s' (%s, %d-dim, cosine, serverless)",
                PINECONE_INDEX_NAME, OPENAI_EMBED_MODEL, OPENAI_EMBED_DIM,
            )
            region = (PINECONE_ENVIRONMENT or "us-east-1-aws").replace("-aws", "")
            await asyncio.to_thread(
                lambda: pc.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=OPENAI_EMBED_DIM,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=region),
                )
            )

        _index = pc.Index(PINECONE_INDEX_NAME)
    return _index


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed via OpenAI text-embedding-3-small. Returns one 1536-dim vector per input.

    The API accepts up to ~2048 inputs per call; callers should chunk if needed.
    Empty strings are replaced with a single space to avoid 400 errors.
    """
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    cleaned = [t if t and t.strip() else " " for t in texts]
    response = await _openai_client.embeddings.create(
        model=OPENAI_EMBED_MODEL,
        input=cleaned,
    )
    return [item.embedding for item in response.data]
