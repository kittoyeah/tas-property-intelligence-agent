# Tasmania Property Intelligence Agent

> "Find out what you can build on your land — before you wait weeks to be told no."

An AI agent that tells Tasmanians what hazard overlays apply to their property in 30 seconds — using the Tasmanian Government's own open spatial data.

Built for the **Microsoft AI Skills Fest 2026** hackathon — Reasoning Agents track (Azure AI Foundry + Foundry IQ).

---

## The Problem

Tasmanians wanting to build face a fragmented planning system. The first step — finding out what overlays apply — requires either navigating multiple government portals or calling the council and waiting weeks. Meanwhile, planning officers across Australia are in [national shortage (JSA 2025)](https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles/occupations/2326-urban-and-regional-planners), and that time is scarce.

## What It Does (Slice 1 — Risk Screener)

Enter a Tasmanian address → get a plain English summary of:
- Flood overlay (statutory + hydraulic)
- Bushfire overlay
- Heritage overlay
- Landslip overlay

Every flag cites the source layer. No hallucination. Graceful fallback if the API is unavailable.

## Azure Stack

| Service | Role |
|---|---|
| Azure AI Foundry | Agent loop + tool calling |
| Foundry IQ (Azure AI Search) | Grounded, cited knowledge retrieval |
| Azure OpenAI gpt-4o-mini | Language model |
| Azure Blob Storage | Knowledge source |

## Data Sources

All open, CC-licensed, live REST APIs — no scraping, no PDFs for Slice 1.

- **theLIST PlanningOnline ArcGIS REST** — CC BY 3.0 AU
- **SES Flood Mapping ArcGIS REST** — theLIST terms
- **OpenDataWFS** — CC BY 3.0 AU

Full detail: [docs/PRD.md](docs/PRD.md) · [Data Sources.md](Data%20Sources.md)

## Repo Structure

```
tas-property-intelligence-agent/
├── docs/
│   ├── PRD.md              # Problem, users, scope, success criteria
│   └── ARCHITECTURE.md     # Azure services + data flow (coming)
├── src/
│   ├── agent/              # Azure AI Foundry agent
│   └── tools/              # theLIST API wrapper + geocoder
├── infra/
│   └── main.bicep          # Azure deployment
├── notebooks/
│   └── exploration.ipynb   # Foundry IQ cookbook (adapted)
├── data/
│   └── sample/             # Sample API responses for testing
└── Data Sources.md         # Full data source reference
```

## Getting Started

_Setup instructions coming once Azure resources are provisioned._

## Licence

Code: MIT. Data: sourced from theLIST (CC BY 3.0 AU) and data.gov.au (CC BY 4.0). See [Data Sources.md](Data%20Sources.md) for per-source licence details.
