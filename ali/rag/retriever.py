from shared.schemas import Activity, Destination


async def retrieve_activity_context(activity: Activity, top_k: int = 5) -> list[str]:
    """
    Retrieve relevant review snippets and descriptions for an activity from Pinecone.
    These are used by explainer.py to ground the "Why this?" explanation.

    Expected input:
        activity = Activity(name="Uluwatu Temple", tags=["culture","scenic","spiritual"])
        top_k    = 5

    Expected output:
        [
            "Uluwatu Temple sits on a dramatic 70m cliff overlooking the Indian Ocean...",
            "Visitors often describe the sunset Kecak dance here as one of Bali's highlights...",
            "Perfect for slow travellers — the walk around the temple complex takes about 90 minutes...",
            ...
        ]
    """
    # TODO: embed activity description + tags, search Pinecone with filter={"type": "review"}
    # Uses shreyas/retrieval/search.py under the hood
    raise NotImplementedError


async def retrieve_destination_context(destination: Destination, top_k: int = 5) -> list[str]:
    """
    Retrieve general destination context (travel tips, highlights, cultural notes).

    Expected input:  Destination(city="Bali", country="Indonesia", tags=["beach","culture"])
    Expected output:
        [
            "Bali's southern peninsula is ideal for couples looking for a mix of culture and beach...",
            "The dry season (May–September) offers the best weather for outdoor activities...",
            ...
        ]
    """
    # TODO: embed destination description, search Pinecone for relevant context
    raise NotImplementedError
