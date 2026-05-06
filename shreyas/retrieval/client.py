from shared.config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, EMBED_DIMENSIONS

# Expected: a single shared Pinecone index object reused across the app.
# Starter — fill in the initialisation logic:

_index = None

def get_pinecone_index():
    """
    Returns the live Pinecone index, creating it if it doesn't exist.

    Expected behaviour:
        - First call: connects to Pinecone, creates index if missing, caches it.
        - Subsequent calls: returns the cached index instantly.
        - Index config: cosine similarity, dimension = EMBED_DIMENSIONS.

    Returns:
        pinecone.Index
    """
    global _index
    if _index is not None:
        return _index
    # TODO: initialise Pinecone client with PINECONE_API_KEY
    # TODO: create index if not in pc.list_indexes()
    # TODO: assign _index = pc.Index(PINECONE_INDEX_NAME)
    raise NotImplementedError
