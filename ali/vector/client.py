from pinecone import Pinecone, ServerlessSpec
from shared.config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, EMBED_DIMENSIONS

_index = None


def get_pinecone_index():
    """
    Returns the live Pinecone index, creating it if it doesn't exist.
    First call connects and caches; subsequent calls return instantly.
    """
    global _index
    if _index is not None:
        return _index

    pc = Pinecone(api_key=PINECONE_API_KEY)

    existing = [idx.name for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBED_DIMENSIONS,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT),
        )

    _index = pc.Index(PINECONE_INDEX_NAME)
    return _index
