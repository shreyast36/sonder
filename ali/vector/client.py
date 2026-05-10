import asyncio
from pinecone import Pinecone, ServerlessSpec
from shared.config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, EMBED_DIMENSIONS

_index = None
_index_lock = asyncio.Lock()


async def get_pinecone_index():
    """
    Returns the live Pinecone index, creating it if it doesn't exist.
    First call connects and caches; subsequent calls return instantly.
    Thread-safe via asyncio.Lock to prevent double-create under concurrent requests.
    """
    global _index
    if _index is not None:
        return _index
    async with _index_lock:
        if _index is None:
            pc = Pinecone(api_key=PINECONE_API_KEY)
            existing = await asyncio.to_thread(lambda: [idx.name for idx in pc.list_indexes()])
            if PINECONE_INDEX_NAME not in existing:
                await asyncio.to_thread(
                    lambda: pc.create_index(
                        name=PINECONE_INDEX_NAME,
                        dimension=EMBED_DIMENSIONS,
                        metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT),
                    )
                )
            _index = pc.Index(PINECONE_INDEX_NAME)
    return _index
