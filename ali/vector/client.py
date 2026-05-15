"""
Pinecone client. Embeddings via OpenAI text-embedding-3-small (1536-dim, cosine).
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
    global _index
    if _index is not None:
        return _index

    async with _index_lock:
        if _index is not None:
            return _index

        pc = Pinecone(api_key=PINECONE_API_KEY)
        existing = await asyncio.to_thread(lambda: [idx.name for idx in pc.list_indexes()])

        if PINECONE_INDEX_NAME not in existing:
            logger.info("Creating Pinecone index '%s'", PINECONE_INDEX_NAME)
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
    """Batch-embed via OpenAI. Empty strings replaced with space to avoid 400s."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    cleaned = [t if t and t.strip() else " " for t in texts]
    response = await _openai_client.embeddings.create(
        model=OPENAI_EMBED_MODEL,
        input=cleaned,
    )
    return [item.embedding for item in response.data]
