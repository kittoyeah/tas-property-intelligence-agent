#!/usr/bin/env bash
# index_all.sh — chunk + index all councils + fee schedules
# Run from repo root: bash scripts/index_all.sh
# Requires: .env with VOYAGE_API_KEY + MONGODB_URI

set -e
RAW=data/raw
CHUNKS=data/chunks

echo "=== CHUNKING LPS ==="
# Hobart (includes SPP re-chunk)
[ -f "$RAW/hobart-lps-2025.pdf" ] && \
    python3 src/tools/chunker.py --council hobart --lps $RAW/hobart-lps-2025.pdf --spp $RAW/spp-2024.pdf

# Other councils — LPS only
for council in glenorchy clarence launceston; do
    pdf="$RAW/${council}-lps-2024.pdf"
    [ -f "$pdf" ] && python3 src/tools/chunker.py --council "$council" --lps "$pdf"
done

[ -f "$RAW/kingborough-draft-lps-2024.pdf" ] && \
    python3 src/tools/chunker.py --council kingborough --lps $RAW/kingborough-draft-lps-2024.pdf

echo ""
echo "=== CHUNKING FEES ==="
for council in hobart glenorchy clarence launceston kingborough; do
    pdf="$RAW/${council}-fees-2025-26.pdf"
    [ -f "$pdf" ] && python3 src/tools/fee_chunker.py --council "$council" --fees "$pdf"
done

echo ""
echo "=== INDEXING ==="
# Index all chunk files — indexer skips already-indexed clause_refs
# No --council flag: each file contains only one council's data already
for f in $CHUNKS/*-chunks.json; do
    # Skip intermediate combined files
    [[ "$f" == *"all-fees"* ]] && continue
    echo "Indexing $f..."
    python3 src/tools/indexer.py --chunks "$f"
done

echo ""
echo "Done."
