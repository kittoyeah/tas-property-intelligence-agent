# Architecture — SiteCheck: Tasmania Property Intelligence Agent

---

## Stack

| Component | Service | Tier |
|---|---|---|
| Frontend | Vercel (Next.js 16) | Free |
| Backend | Railway (FastAPI) | Free |
| LLM | Groq — Llama 4 Scout 17B | Free (30 req/min) |
| Vector KB | MongoDB Atlas M0 | Free (512MB) |
| Embeddings | Voyage AI voyage-law-2 | Free (200M tokens) |
| Geocoding | Nominatim / OSM | Free |
| Spatial data | theLIST ArcGIS REST | Free (CC BY 3.0 AU) |

---

## Data Flow

```
User (Next.js)
    |
    | POST /check  { address, mode, intent }
    v
FastAPI (Railway)
    |
    v
Agent tool loop
    |-- geocode_address()  →  Nominatim → lat/lng
    |
    |-- query_overlays()   →  theLIST ArcGIS REST
    |     Layer 8:  LGA (council name)
    |     Layer 13: Zone
    |     Layer 14: Code overlays  → lps_ref (e.g. HOB-C6.2.1)
    |     Layer 15: General overlays
    |
    v
KB enrichment
    |-- retrieve_by_ref(lps_ref) → MongoDB Atlas (keyword search)
    |-- retrieve(query)          → Atlas $vectorSearch (when index active)
    |
    v
Groq LLM (Llama 4 Scout)
    |   system: RESPONSE_SYSTEM_PROMPT (strict citation rules)
    |   user:   overlay data + clause text blocks
    v
Cited plain-English response
    |
    v
Next.js renders results card
```

---

## Repo Structure

```
tas-property-intelligence-agent/
├── frontend/               # Next.js 16 UI
│   └── src/app/page.tsx    # Address + mode + intent picker, results card
├── src/
│   ├── api.py              # FastAPI /check + /health
│   ├── agent/agent.py      # LLM tool-loop agent
│   └── tools/
│       ├── geocoder.py     # Nominatim wrapper + TAS bbox guard
│       ├── thelist.py      # theLIST ArcGIS REST (layers 8,13,14,15)
│       ├── retriever.py    # MongoDB keyword + vector search
│       ├── indexer.py      # Voyage AI embeddings → MongoDB
│       ├── chunker.py      # PDF → clause-level chunks
│       └── schemas.py      # OpenAI tool schemas
├── data/
│   ├── sample/             # Mock API responses (USE_MOCK_DATA=true)
│   ├── raw/                # Source PDFs (gitignored)
│   └── chunks/             # Chunked JSON (gitignored)
└── docs/                   # PRD, research, architecture
```

---

## KB Strategy

**Source documents indexed:**
- Hobart LPS 2025 (PDF, 545 pages) — 498 LPS chunks
- TPS State Planning Provisions 2024 (PDF) — 90 SPP chunks
- Total: 588 chunks in MongoDB Atlas `sitecheck.chunks`

**Chunk unit:** One planning clause per chunk (e.g. `C6.2.1`, `HOB-S7.0`).

**Retrieval:** `lps_ref` from theLIST live API → `retrieve_by_ref()` strips council prefix (`HOB-C6.2.1` → try `C6.2.1`, `C6.2`, `C6`). Falls back to keyword regex if vector search unavailable.

**To enable semantic search:** Create Atlas Vector Search index `vector_index` on `sitecheck.chunks`:
```json
{"fields": [
  {"type": "vector", "path": "embedding", "numDimensions": 1024, "similarity": "cosine"},
  {"type": "filter", "path": "council"},
  {"type": "filter", "path": "overlay_code"}
]}
```

---

## Coordinate Handling

Nominatim → WGS84 (EPSG:4326). theLIST queries use `inSR=4326` directly.
pyproj fallback: WGS84 → GDA2020/MGA Zone 55 (EPSG:7855) if layer rejects `inSR=4326`.

---

## Local Development

```bash
# Backend
.venv/bin/python3 -m uvicorn src.api:app --port 8000

# Frontend
cd frontend && npm run dev
```

See README for full setup. Env vars in `.env.example`.
