"""
indexer.py — chunks JSON → Voyage AI embeddings → MongoDB Atlas Vector Search

Run once per council to populate the KB.
Requires: VOYAGE_API_KEY, MONGODB_URI in .env

MongoDB Atlas setup (one-time, in Atlas UI):
1. Create free M0 cluster
2. Get connection string → MONGODB_URI in .env
3. After first index run, create Atlas Search index:
   Database: sitecheck  Collection: chunks
   Index name: vector_index
   JSON config:
   {
     "fields": [
       {
         "type": "vector",
         "path": "embedding",
         "numDimensions": 1024,
         "similarity": "cosine"
       },
       { "type": "filter", "path": "council" },
       { "type": "filter", "path": "overlay_code" },
       { "type": "filter", "path": "clause_ref" }
     ]
   }
"""

import os
import json
import time
import argparse
import voyageai
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

BATCH_SIZE = 20   # ~6.6K tokens/batch, safely under 10K TPM
RATE_LIMIT_SLEEP = 65  # 10K TPM free limit — 65s ensures < 10K/min
EMBED_MODEL = "voyage-law-2"
DB_NAME = "sitecheck"
COLLECTION_NAME = "chunks"


def embed_batch(vc: voyageai.Client, texts: list[str]) -> list[list[float]]:
    for attempt in range(5):
        try:
            result = vc.embed(texts, model=EMBED_MODEL, input_type="document")
            return result.embeddings
        except voyageai.error.RateLimitError:
            wait = RATE_LIMIT_SLEEP * (attempt + 1)
            print(f"  Rate limit hit, sleeping {wait}s...")
            time.sleep(wait)
    raise RuntimeError("Voyage AI rate limit: max retries exceeded")


def index_chunks(chunks_path: str, council_filter: str | None = None, dry_run: bool = False):
    voyage_key = os.environ["VOYAGE_API_KEY"]
    mongo_uri = os.environ["MONGODB_URI"]

    vc = voyageai.Client(api_key=voyage_key)
    client = MongoClient(mongo_uri)
    collection = client[DB_NAME][COLLECTION_NAME]

    with open(chunks_path) as f:
        chunks = json.load(f)

    if council_filter:
        chunks = [c for c in chunks if c["council"] in (council_filter, "statewide")]
        print(f"Filtered to council='{council_filter}' + statewide: {len(chunks)} chunks")
    else:
        print(f"Indexing all {len(chunks)} chunks")

    # Resume: skip already-indexed clause_refs
    existing = set(
        doc["clause_ref"]
        for doc in collection.find({}, {"clause_ref": 1, "_id": 0})
    )
    if existing:
        before = len(chunks)
        chunks = [c for c in chunks if c["clause_ref"] not in existing]
        print(f"Resuming: skipping {before - len(chunks)} already indexed, {len(chunks)} remaining")

    if dry_run:
        print("Dry run — no writes.")
        return

    total = len(chunks)
    inserted = 0

    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        print(f"Embedding batch {i//BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} chunks)...")
        embeddings = embed_batch(vc, texts)

        docs = []
        for chunk, embedding in zip(batch, embeddings):
            docs.append({
                "doc":           chunk["doc"],
                "council":       chunk["council"],
                "clause_ref":    chunk["clause_ref"],
                "parent_clause": chunk["parent_clause"],
                "code_ref":      chunk["code_ref"],
                "overlay_code":  chunk["overlay_code"],
                "clause_type":   chunk["clause_type"],
                "heading":       chunk["heading"],
                "text":          chunk["text"],
                "source":        chunk["source"],
                "embedding":     embedding,
            })

        result = collection.insert_many(docs)
        inserted += len(result.inserted_ids)
        print(f"  Inserted {len(result.inserted_ids)} docs.")

        if i + BATCH_SIZE < total:
            time.sleep(RATE_LIMIT_SLEEP)

    print(f"Done. {inserted}/{total} chunks indexed into {DB_NAME}.{COLLECTION_NAME}.")
    print("Next: create Atlas Vector Search index in Atlas UI (see module docstring).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks",  default="data/chunks/hobart-chunks.json")
    parser.add_argument("--council", default="Hobart")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    index_chunks(args.chunks, council_filter=args.council, dry_run=args.dry_run)
