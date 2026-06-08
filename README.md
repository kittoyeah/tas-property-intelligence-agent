# SiteCheck — Tasmania Property Intelligence Agent

> "Know your planning overlays before you build or buy."

Enter a Tasmanian address → get a plain-English summary of planning overlays, zone, and permit pathway — every claim cited to the source clause.

Built for **Microsoft AI Skills Fest 2026** — Reasoning Agents track.

---

## Local Setup (Teammates)

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Homebrew](https://brew.sh) (macOS)

### 1. Clone

```bash
git clone https://github.com/kittoyeah/tas-property-intelligence-agent.git
cd tas-property-intelligence-agent
```

### 2. Python environment

```bash
brew install proj          # required for pyproj (coordinate transforms)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to get it |
|---|---|
| `LLM_BASE_URL` | Leave as `https://api.groq.com/openai/v1` |
| `LLM_API_KEY` | **Get your own free key** → [console.groq.com](https://console.groq.com) → sign up → API Keys → Create Key |
| `LLM_MODEL` | Leave as `meta-llama/llama-4-scout-17b-16e-instruct` |
| `VOYAGE_API_KEY` | **Ask Chris** — shared key, do not create a new one (shared free token quota) |
| `MONGODB_URI` | **Ask Chris** — shared Atlas cluster with KB already indexed, saves you running the indexer |
| `USE_MOCK_DATA` | Leave as `false` |

> **Groq signup takes ~30 seconds** — GitHub login works. Free tier is 30 req/min, no credit card needed.

### 5. Run

**Terminal 1 — API:**
```bash
.venv/bin/python3 -m uvicorn src.api:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open **http://localhost:3001** (or 3000 if not taken).

### Test addresses

| Address | What to expect |
|---|---|
| `8 Nelson Road Sandy Bay TAS 7005` | Clean — no overlays, General Residential zone |
| `1 Napoleon Street Battery Point TAS 7004` | Heritage precinct + Battery Point SAP |
| `45 Elizabeth Street Hobart TAS 7000` | Archaeological + heritage overlays |
| `12 Main Road Glenorchy TAS 7010` | Glenorchy council, Utilities zone |

---

## Stack

| Component | Dev (free) | Submission (Azure) |
|---|---|---|
| Frontend | Vercel | Azure Static Web Apps |
| Backend | Railway (FastAPI) | Azure Functions |
| LLM | Groq (Llama 4 Scout) | Azure OpenAI gpt-4o-mini |
| Vector KB | MongoDB Atlas M0 | Azure AI Search |
| Embeddings | Voyage AI voyage-law-2 | Azure AI Search built-in |

Swap via env vars — `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.

## Architecture

```
Address + Mode + Intent
        │
        ▼
  geocode_address()          ← Nominatim (OSM)
        │
        ▼
  query_overlays()           ← theLIST ArcGIS REST (Layers 8, 13, 14, 15)
        │
        ▼
  retrieve_by_ref()          ← MongoDB Atlas (keyword + vector search)
        │ clause text
        ▼
  LLM (Llama 4 / gpt-4o-mini)
        │ cited plain-English response
        ▼
     Frontend
```

## Data Sources

| Source | Licence | Used for |
|---|---|---|
| theLIST PlanningOnline ArcGIS REST | CC BY 3.0 AU | Zones, overlays, LGA |
| Hobart LPS 2025 (PDF) | © HCC | KB clause text |
| SPP 2024 (PDF) | CC BY 3.0 AU | KB clause text |
| Nominatim / OpenStreetMap | ODbL | Geocoding |

## Repo Structure

```
tas-property-intelligence-agent/
├── docs/               # PRD, architecture, research notes
├── src/
│   ├── agent/          # LLM tool-loop agent
│   ├── tools/          # geocoder, theLIST wrapper, retriever, indexer
│   └── api.py          # FastAPI endpoints
├── frontend/           # Next.js 16 UI
├── data/
│   └── sample/         # Mock API responses for USE_MOCK_DATA=true
└── .env.example        # Required env vars
```

## Licence

Code: MIT. Data: theLIST (CC BY 3.0 AU), Nominatim (ODbL). Hobart LPS © Hobart City Council — used for non-commercial research.
