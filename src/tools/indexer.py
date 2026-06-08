"""
indexer.py — chunks JSON → Voyage AI embeddings → Supabase pgvector

Run once per council to populate the KB.
Requires: VOYAGE_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY in .env

Supabase SQL to run once before indexing:
    create extension if not exists vector;

    create table if not exists chunks (
        id              bigserial primary key,
        doc             text,
        council         text,
        clause_ref      text,
        parent_clause   text,
        code_ref        text,
        overlay_code    text,
        clause_type     text,
        heading         text,
        text            text,
        source          text,
        embedding       vector(1024)
    );

    create index if not exists chunks_embedding_idx
        on chunks using ivfflat (embedding vector_cosine_ops)
        with (lists = 100);

    create index if not exists chunks_council_idx on chunks (council);
    create index if not exists chunks_overlay_idx on chunks (overlay_code);
"""

import os
import json
import time
import argparse
import voyageai
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

BATCH_SIZE = 64  # Voyage AI max batch size
EMBED_MODEL = "voyage-law-2"  # Legal/regulatory domain model


def embed_batch(vc: voyageai.Client, texts: list[str]) -> list[list[float]]:
    result = vc.embed(texts, model=EMBED_MODEL, input_type="document")
    return result.embeddings


def index_chunks(chunks_path: str, council_filter: str | None = None, dry_run: bool = False):
    voyage_key = os.environ["VOYAGE_API_KEY"]
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]

    vc = voyageai.Client(api_key=voyage_key)
    sb = create_client(supabase_url, supabase_key)

    with open(chunks_path) as f:
        chunks = json.load(f)

    if council_filter:
        chunks = [c for c in chunks if c["council"] in (council_filter, "statewide")]
        print(f"Filtered to council='{council_filter}' + statewide: {len(chunks)} chunks")
    else:
        print(f"Indexing all {len(chunks)} chunks")

    if dry_run:
        print("Dry run — no writes.")
        return

    # Process in batches
    total = len(chunks)
    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        print(f"Embedding batch {i//BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} chunks)...")
        embeddings = embed_batch(vc, texts)

        rows = []
        for chunk, embedding in zip(batch, embeddings):
            rows.append({
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

        sb.table("chunks").insert(rows).execute()
        print(f"  Inserted {len(rows)} rows.")

        # Respect Voyage AI rate limit
        if i + BATCH_SIZE < total:
            time.sleep(0.5)

    print(f"Done. {total} chunks indexed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks",  default="data/chunks/hobart-chunks.json")
    parser.add_argument("--council", default="Hobart", help="Filter to council (also includes statewide)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    index_chunks(args.chunks, council_filter=args.council, dry_run=args.dry_run)
