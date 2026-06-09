"""
retriever.py — query MongoDB Atlas for relevant planning clauses

Primary:  Atlas $vectorSearch (semantic) — requires Voyage AI + vector index
Fallback: MongoDB text/regex search on clause_ref + heading keywords
"""

import os
import re
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


def _keyword_search(
    query: str,
    council: str | None = None,
    overlay_code: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """Regex search on clause_ref, heading, and text — no embeddings needed."""
    collection = _get_collection()

    terms = [t for t in re.split(r"\s+", query.strip()) if len(t) > 2]
    if not terms:
        return []

    # Match any term in clause_ref, heading, or text
    regex_parts = [{"clause_ref": {"$regex": t, "$options": "i"}} for t in terms]
    regex_parts += [{"heading": {"$regex": t, "$options": "i"}} for t in terms]
    text_filter = {"$or": regex_parts}

    council_filter = {}
    if council:
        council_filter = {"$or": [{"council": council}, {"council": "statewide"}]}
    if overlay_code:
        council_filter["overlay_code"] = overlay_code

    mongo_filter = {"$and": [text_filter, council_filter]} if council_filter else text_filter

    results = list(
        collection.find(mongo_filter, {"_id": 0, "embedding": 0}).limit(top_k)
    )
    return results


def retrieve(
    query: str,
    council: str | None = None,
    overlay_code: str | None = None,
    zone_code: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """
    Semantic search with keyword fallback.

    Tries Atlas $vectorSearch first; falls back to keyword search if
    Voyage AI is rate-limited or vector index not yet created.
    """
    try:
        embedding = _embed_query(query)
        collection = _get_collection()

        # Fetch more candidates then post-filter — avoids filter fields in index definition
        fetch_k = top_k * 20
        pipeline = [
            {"$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": embedding,
                "numCandidates": fetch_k,
                "limit": fetch_k,
            }},
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

        # Post-filter by council / overlay_code / zone_code
        if council:
            results = [r for r in results if r.get("council") in (council, "statewide")]
        if overlay_code:
            results = [r for r in results if r.get("overlay_code") == overlay_code]
        if zone_code:
            results = [
                r for r in results
                if r.get("code_ref") == zone_code
                or r.get("clause_ref", "").startswith(zone_code + ".")
            ]

        results = results[:top_k]
        if results:
            return results
        # Vector search returned nothing — try keyword fallback
        return _keyword_search(query, council, overlay_code, top_k)

    except Exception:
        # Voyage AI rate limit or no vector index — use keyword fallback
        return _keyword_search(query, council, overlay_code, top_k)


def retrieve_by_ref(lps_ref: str, council: str | None = None) -> list[dict]:
    """Direct lookup by clause reference.

    Handles both HOB-C6.2.1 (theLIST format) and C6.2.1 (SPP format).
    Also matches parent sections: HOB-C6.2.1 → C6, C6.2, C6.2.1
    """
    collection = _get_collection()

    # Normalise: strip council prefix (HOB-, GCC-, etc.)
    normalised = re.sub(r"^[A-Z]+-", "", lps_ref)

    # Try exact match first, then prefix match (C6.2.1 → C6.2 → C6)
    candidates = {lps_ref, normalised}
    parts = normalised.split(".")
    for i in range(len(parts), 0, -1):
        candidates.add(".".join(parts[:i]))

    council_filter: dict = {}
    if council:
        council_filter = {"$or": [{"council": council}, {"council": "statewide"}]}

    mongo_filter: dict = {"clause_ref": {"$in": list(candidates)}}
    if council_filter:
        mongo_filter = {"$and": [mongo_filter, council_filter]}

    return list(collection.find(mongo_filter, {"_id": 0, "embedding": 0}))


if __name__ == "__main__":
    import json
    print("Testing keyword fallback...")
    results = _keyword_search("HOB-C6.2.1 heritage", council="Hobart", top_k=3)
    for r in results:
        print(f"\n[{r['clause_ref']}] {r['heading'][:60]}")
        print(f"  {r['text'][:150]}...")

    print("\nTesting retrieve_by_ref...")
    results = retrieve_by_ref("HOB-C6.2.1")
    for r in results:
        print(f"\n[{r['clause_ref']}] {r['heading'][:60]}")
