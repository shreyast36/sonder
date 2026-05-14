"""
Pinecone client — integrated embedding via llama-text-embed-v2.

The index is created with the model attached (Pattern A), so callers upsert
text via `upsert_records` and search via `search_records`. No separate embed
call needed.
"""

import asyncio
import logging

from pinecone import Pinecone

from shared.config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME

logger = logging.getLogger(__name__)

_index = None
_index_lock = asyncio.Lock()

# Maps the model's expected text field to the field name we use in records.
# Every record we upsert must have a `chunk_text` field — Pinecone embeds that.
_EMBED_MODEL = "llama-text-embed-v2"
_FIELD_MAP = {"text": "text"}


async def get_pinecone_index():
    """Returns the Pinecone index, creating it (with integrated embedding) if missing."""
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
                "Creating Pinecone index '%s' with model '%s'",
                PINECONE_INDEX_NAME, _EMBED_MODEL,
            )
            region = (PINECONE_ENVIRONMENT or "us-east-1-aws").replace("-aws", "")
            await asyncio.to_thread(
                lambda: pc.create_index_for_model(
                    name=PINECONE_INDEX_NAME,
                    cloud="aws",
                    region=region,
                    embed={"model": _EMBED_MODEL, "field_map": _FIELD_MAP},
                )
            )

        _index = pc.Index(PINECONE_INDEX_NAME)
    return _index
