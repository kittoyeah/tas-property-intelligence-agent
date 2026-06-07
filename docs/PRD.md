# Product Requirements Document
# Tasmania Property Intelligence Agent

## The Story

You own a block in Tassie. You want to build a granny flat for your mum. You call the council — wait three weeks — just to find out there's a flood overlay and you need an engineer's report before you can even apply. That call cost a planner an hour and cost you three weeks.

This tool gives you that answer in 30 seconds. Free. Before you pick up the phone.

**One-liner:** *"Find out what you can build on your land — before you wait weeks to be told no."*

---

## Problem

### The human problem
Tasmanians wanting to build — a granny flat, a shed, a fence, a renovation — face a fragmented, opaque planning system. The first step — finding out what overlays apply to their land — requires either navigating multiple government portals or calling the council and waiting weeks for a response.

### The systemic problem
Urban and Regional Planners are on the **Jobs and Skills Australia 2025 Occupation Shortage List**, in shortage in every state and territory except the ACT. 64% of planning organisations struggled to fill roles in the past 12 months. Tasmanian councils — particularly small ones — have the least resourcing and the most to gain from Tier-1 triage automation.

Repetitive Tier-1 enquiries (overlay checks, basic zoning questions) consume scarce planner time that should go to complex development applications. An agent handling Tier-1 frees planners for work only they can do.

### Evidence
- [JSA 2025 Occupation Shortage List — Urban and Regional Planners](https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles/occupations/2326-urban-and-regional-planners)
- [PIA: Urban planner shortage a hidden risk to Australia's housing future](https://www.planning.org.au/pia/news-resources/articles/latest-updates/national/urban-planner-shortage-a-hidden-risk-to-australias-housing-future-new-survey-shows.aspx)
- Tasman Council: permits received after 10 Nov 2025 may not be determined before year end

---

## Users

| User | Primary? | Question they ask | Frequency |
|---|---|---|---|
| **Tradie** | ✅ Primary | "Are there overlays on this site that affect my quote?" | Every job (repeat) |
| Homebuyer / owner | Secondary | "Can I build a granny flat / shed / pool?" | Once-off |
| Council staff | Secondary | "What overlays apply to this address?" | Daily |

Tradie is primary: repeat user, B2B monetisable, no existing platform conflict.

---

## Solution — Slice 1: Risk Screener

**Input:** a Tasmanian property address
**Output:** plain English summary of hazard overlays (flood, bushfire, heritage, landslip) with cited sources and next-step guidance

**What it does NOT do (Slice 1):**
- Answer "can I build X?" (requires zone rules — Slice 2)
- Check NCC compliance (Slice 3)
- Replace a planning permit application
- Provide legal advice

---

## Data Sources

All open, API-queryable, no PDF parsing required for Slice 1.

| Source | Overlays | Licence |
|---|---|---|
| theLIST PlanningOnline ArcGIS REST | Flood, bushfire, heritage, landslip, planning zone | CC BY 3.0 AU (per layer) |
| SES Flood Mapping ArcGIS REST | Hydraulic flood model | theLIST terms |
| OpenDataWFS | Additional spatial layers | CC BY 3.0 AU (per layer) |

Full data source detail: [Data Sources.md](../Data%20Sources.md)

---

## Azure Stack

| Component | Purpose |
|---|---|
| Azure AI Foundry | Agent loop + tool calling |
| Foundry IQ (AI Search) | Knowledge retrieval — grounded, cited answers |
| Azure OpenAI (gpt-4o-mini) | Language model |
| Azure Blob Storage | Knowledge source backing store |

---

## Success Criteria (Slice 1)

- [ ] Given a valid Tasmanian address, agent returns correct overlay flags within 10 seconds
- [ ] Every risk flag cites the source layer (not hallucinated)
- [ ] Graceful fallback if theLIST API is unavailable
- [ ] Demo video recorded and submission lodged by 14 Jun 2026

---

## Out of Scope

- NCC compliance checking
- Fee calculations
- DA form pre-fill
- Legal or engineering advice
- Addresses outside Tasmania
- State government systems (DPAC, TPC) — politically sensitive, avoid

---

## Positioning

Built for Tasmanians, using Tasmanian Government open data, on Microsoft Azure AI Foundry.
Submitted to Microsoft AI Skills Fest 2026 — Reasoning Agents track.

References:
- [microsoft/iq-series](https://github.com/microsoft/iq-series) — Foundry IQ implementation guide
- [theLIST ArcGIS REST services](https://services.thelist.tas.gov.au/arcgis/rest/services/Public/)
