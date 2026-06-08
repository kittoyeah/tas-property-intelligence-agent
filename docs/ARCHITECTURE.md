# Architecture — SiteCheck: Tasmania Property Intelligence Agent

Technical reference for the SiteCheck system. All decisions finalised.

---

## Two-Plan Strategy

SiteCheck runs on two parallel stacks — same code, different backends via env vars.

| Component | Plan A — Dev (free) | Plan B — Submission (Azure) |
|---|---|---|
| Frontend hosting | Vercel (free) | Azure Static Web Apps |
| Backend | Railway (FastAPI, free tier) | Azure Functions (Python) |
| LLM | OpenRouter :free → DeepSeek R1 | Azure OpenAI gpt-4o-mini |
| Agent loop | Manual tool loop (OpenAI SDK) | Azure AI Foundry SDK |
| Vector KB | Supabase pgvector | Azure AI Search (Foundry IQ) |
| File storage | Supabase Storage | Azure Blob Storage |
| Geocoder | Nominatim | Nominatim (unchanged) |
| Live spatial data | theLIST ArcGIS REST | theLIST ArcGIS REST (unchanged) |

**Swap mechanism — env vars only, no code changes:**

```bash
# Plan A (dev)
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-...
KB_BACKEND=supabase
AGENT_BACKEND=manual

# Plan B (submission)
LLM_BASE_URL=https://{azure-resource}.openai.azure.com
LLM_API_KEY=...
KB_BACKEND=azure-search
AGENT_BACKEND=foundry
```

**Why:** Azure AI Foundry quota pending. Dev proceeds on free cloud stack. Submission swaps to Azure to satisfy hackathon IQ layer requirement and target $5k "Best use of IQ tools" bonus prize.

---

## Overview

SiteCheck accepts a Tasmanian property address + user mode + intent, resolves planning overlays via live spatial APIs, then uses an AI agent to produce plain-English planning interpretation cited to relevant LPS clauses.

---

## Data Flow

```
User (Next.js UI)
    |
    | POST /api/analyze  { address, mode }
    v
Azure Functions (Python)
    |
    |-- Nominatim (OpenStreetMap) ---------> lat/lng (WGS84)
    |
    |-- theLIST ArcGIS REST
    |     Layer 14: code overlays   -------> overlay CODEs + OV_NAMEs + LPS_REFs
    |     Layer 15: general overlays
    |     Layer 13: zone            -------> zone name
    |
    v
Azure AI Foundry Agent
    |
    |-- Foundry IQ (Azure AI Search) ------> planning clauses (lookup by LPS_REF)
    |
    |-- Azure OpenAI gpt-4o-mini ----------> plain-English interpretation + citations
    |
    v
Azure Functions returns JSON response
    |
    v
Next.js renders results card
```

---

## Azure Services

| Service | Tier | Role |
|---|---|---|
| Azure Static Web Apps | Free | Next.js frontend hosting |
| Azure Functions (Python runtime) | Consumption | Agent backend — serverless, scales to zero |
| Azure AI Foundry | Standard | Agent loop + tool calling |
| Azure AI Search | Basic | Foundry IQ KB — vector + keyword hybrid search |
| Azure OpenAI (gpt-4o-mini) | Pay-per-use | Language model |
| Azure Blob Storage | LRS | KB source document store (PDFs, XML) |

---

## Repo Structure

```
src/
  agent/agent.py        # Pure agent logic — no UI deps
  tools/geocoder.py     # Nominatim wrapper
  tools/thelist.py      # theLIST ArcGIS REST wrapper (pyproj for coords)
  app/                  # Next.js frontend (to be created)
infra/
  main.bicep            # Azure IaC deployment (scaffolded)
data/
  sample/               # Mock API responses for offline dev
docs/
  ARCHITECTURE.md       # This file
```

---

## KB Chunking Strategy

**Source documents:** TPS SPP PDFs (RAG only), Hobart LPS PDF, NCC 2022 XML (CC BY 4.0).
Stored in Azure Blob Storage; indexed into Azure AI Search via Foundry IQ.

**Chunk unit:** One planning clause per chunk (e.g. C6.2.1.1, C6.2.1.2).

**Metadata per chunk:**

| Field | Description |
|---|---|
| `lps_ref` | Primary lookup key — matches LPS_REF from theLIST live API |
| `overlay_code` | Overlay code (e.g. `SLZ`) |
| `clause_type` | `objectives` / `standards` / `acceptable_solutions` |
| `lps_name` | Human-readable LPS name |
| `council` | Council name (e.g. `Hobart`) |

**Retrieval method:** LPS_REF from live spatial API -> direct lookup in KB. Targeted, not fuzzy. Agent does not need semantic search for clause retrieval; vector search used as fallback for ambiguous refs.

**Chunk size rules:**
- Oversized clauses: split by sub-clause boundary.
- Micro-clauses (too short to be meaningful): merge with sibling clauses under same parent.

---

## Coordinate Handling

Nominatim returns WGS84 (EPSG:4326) lat/lng.

theLIST ArcGIS REST queries use `inSR=4326` to pass coords directly — no reprojection needed in the common path.

`pyproj` included in `tools/thelist.py` as fallback: if a layer rejects `inSR=4326` or returns no results, pyproj reprojects WGS84 -> GDA2020 / MGA Zone 55 (EPSG:7855) before retry.

---

## Not in Scope

| Feature | Reason excluded |
|---|---|
| Authentication | Anonymous use; hackathon scope |
| Response caching | Low traffic; adds infra complexity |
| Streaming responses | Simplifies Functions → Next.js boundary |
| Database | No persistent state required |
| Rate limiting | Deferred; Functions consumption plan throttles naturally |

---

## Local Development

**Prerequisites:**
- Azure Functions Core Tools v4
- Python 3.11+
- Node.js 20+ (for Next.js)
- `.env` file at repo root (see `.env.example`)

**Key env vars:**

```
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_AI_SEARCH_ENDPOINT=
AZURE_AI_SEARCH_KEY=
AZURE_AI_SEARCH_INDEX=
```

**Offline dev:** Mock API responses in `data/sample/` stand in for Nominatim and theLIST responses. Set `USE_MOCK_DATA=true` in `.env` to activate.

**Run backend locally:**

```bash
cd src
func start
```

**Run frontend locally:**

```bash
cd src/app
npm run dev
```

Frontend proxies `/api/*` to `http://localhost:7071` via `next.config.js` rewrites.
