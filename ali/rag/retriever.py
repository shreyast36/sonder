from shared.schemas import Activity, Destination
from ali.vector.embeddings import embed_text
from ali.vector.client import get_pinecone_index


async def retrieve_activity_context(activity: Activity, top_k: int = 5) -> list[str]:
    """
    Retrieve review snippets and descriptions for an activity from Pinecone.
    Used by explainer.py to ground "Why this?" explanations.
    """
    query_text = f"{activity.name}. {activity.description}. Tags: {', '.join(activity.tags)}"
    vector = embed_text(query_text)

    index = get_pinecone_index()
    results = index.query(
        vector=vector,
        top_k=top_k,
        filter={"type": "activity_context"},
        include_metadata=True,
    )

    return [
        match["metadata"]["text"]
        for match in results["matches"]
        if "text" in match.get("metadata", {})
    ]


async def retrieve_destination_context(destination: Destination, top_k: int = 5) -> list[str]:
    """
    Retrieve general destination context (travel tips, highlights, cultural notes).
    """
    query_text = f"{destination.city}, {destination.country}. {destination.description}. Tags: {', '.join(destination.tags)}"
    vector = embed_text(query_text)

    index = get_pinecone_index()
    results = index.query(
        vector=vector,
        top_k=top_k,
        filter={"type": "destination_context"},
        include_metadata=True,
    )

    return [
        match["metadata"]["text"]
        for match in results["matches"]
        if "text" in match.get("metadata", {})
    ]
