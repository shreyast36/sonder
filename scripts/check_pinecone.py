"""Quick Pinecone state check — namespaces + counts."""
import asyncio
from shreyas.retrieval.client import get_pinecone_index


async def main():
    idx = await get_pinecone_index()
    stats = idx.describe_index_stats()
    namespaces = getattr(stats, "namespaces", None) or stats.get("namespaces", {})
    total = getattr(stats, "total_vector_count", None) or stats.get("total_vector_count", 0)
    print(f"index: {idx}")
    print(f"total vectors: {total}")
    print("namespaces:")
    for name, ns_stats in (namespaces or {}).items():
        count = getattr(ns_stats, "vector_count", None) or ns_stats.get("vector_count", 0)
        print(f"  {name!r}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
