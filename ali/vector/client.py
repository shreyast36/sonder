from shared.config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, EMBED_DIMENSIONS

_index = None

def get_pinecone_index():
    """
    Returns the live Pinecone index, creating it if it doesn't exist.
    First call connects and caches; subsequent calls return instantly.

    Returns:
        pinecone.Index
    """
    global _index
    if _index is not None:
        return _index
    # TODO: initialise Pinecone client with PINECONE_API_KEY
    # TODO: create index if not in pc.list_indexes() (cosine similarity, dim=EMBED_DIMENSIONS)
    # TODO: _index = pc.Index(PINECONE_INDEX_NAME)
    raise NotImplementedError
