"""
retriever.py — query MongoDB Atlas Vector Search for relevant planning clauses

Requires Atlas Vector Search index named 'vector_index' on sitecheck.chunks.
Create in Atlas UI after indexing (JSON config in indexer.py docstring).
"""

import os
import voyageai
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = "voyage-law-2"
DB_NAME = "sitecheck"
COLLECTION_NAME = "chunks"
DEFAULT_TOP_K = 5


def _get_collection():
    client = MongoClient(os.environ["MONGODB_URI"])
    return client[DB_NAME][COLLECTION_NAME]


def _embed_query(query: str) -> list[float]:
    vc = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    result = vc.embed([query], model=EMBED_MODEL, input_type="query")
    return result.embeddings[0]


def retrieve(
    query: str,
    council: str | None = None,
    overlay_code: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """
    Semantic search over planning clauses.

    Args:
        query:        Natural language query or lps_ref (e.g. "C12.5.1" or "flood zone development")
        council:      Filter to council (e.g. "Hobart") — also returns statewide docs
        overlay_code: Filter to overlay (e.g. "Flood-Prone Areas Hazard Code")
        top_k:        Number of results to return

    Returns:
        List of chunk dicts with text, clause_ref, source, score
    """
    embedding = _embed_query(query)
    collection = _get_collection()

    # Build Atlas Vector Search pipeline
    vector_search = {
        "index": "vector_index",
        "path": "embedding",
        "queryVector": embedding,
        "numCandidates": top_k * 10,
        "limit": top_k,
    }

    # Add metadata filters
    filters = []
    if council:
        filters.append({"$or": [{"council": council}, {"council": "statewide"}]})
    if overlay_code:
        filters.append({"overlay_code": overlay_code})
    if filters:
        vector_search["filter"] = {"$and": filters} if len(filters) > 1 else filters[0]

    pipeline = [
        {"$vectorSearch": vector_search},
        {"$project": {
            "_id": 0,
            "clause_ref": 1,
            "heading": 1,
            "text": 1,
            "overlay_code": 1,
            "clause_type": 1,
            "council": 1,
            "source": 1,
            "score": {"$meta": "vectorSearchScore"},
        }},
    ]

    results = list(collection.aggregate(pipeline))
    return results


def retrieve_by_ref(lps_ref: str, council: str | None = None) -> list[dict]:
    """Direct lookup by clause reference (e.g. 'C12.5.1' or 'HOB-C6.2.1')."""
    collection = _get_collection()
    query = {"clause_ref": lps_ref}
    if council:
        query = {"clause_ref": lps_ref, "$or": [{"council": council}, {"council": "statewide"}]}

    results = list(collection.find(query, {"_id": 0, "embedding": 0}))
    return results


if __name__ == "__main__":
    # Quick test
    import json
    print("Testing retriever...")
    results = retrieve("flood zone development standards", council="Hobart", top_k=3)
    for r in results:
        print(f"\n[{r['clause_ref']}] {r['heading'][:60]} (score: {r.get('score', 'N/A'):.3f})")
        print(f"  {r['text'][:150]}...")
