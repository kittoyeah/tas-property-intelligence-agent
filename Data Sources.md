---
tags:
  - research
  - ai-engineering
  - hackathon
created: 2026-06-07
---
# Data Sources — Tasmania Property Intelligence Agent

Filtered to sources that are open, queryable, and usable in a public repo. Full research in [[Tas Planning Copilot — Data Findings]].

## ✅ Primary — use these

| Source | URL | Format | Licence | Gotchas |
|---|---|---|---|---|
| **theLIST Planning Overlays** (PlanningOnline ArcGIS REST) | [MapServer](https://services.thelist.tas.gov.au/arcgis/rest/services/Public/PlanningOnline/MapServer) / [Layers](https://services.thelist.tas.gov.au/arcgis/rest/services/Public/PlanningOnline/MapServer/layers) | ArcGIS REST | CC BY 3.0 AU (check per layer) | Not every planning issue is mapped — Glenorchy warns some codes sit outside the scheme map |
| **SES Flood Mapping** | [MapServer](https://services.thelist.tas.gov.au/arcgis/rest/services/Public/SES_FloodMapping/MapServer) | ArcGIS REST | theLIST service terms | Hydraulic flood model ≠ statutory planning overlay — use both, cite the difference |
| **SES Flood Mapping Calibration 2** | [MapServer](https://services.thelist.tas.gov.au/arcgis/rest/services/Public/SES_FloodMapping_Calibration2/MapServer) | ArcGIS REST | theLIST service terms | Coverage not uniform statewide |
| **TasWater Flood Inundation** | [Infrastructure MapServer](https://services.thelist.tas.gov.au/arcgis/rest/services/Public/Infrastructure/MapServer) | ArcGIS REST | theLIST service terms | Context layer only — does not replace planning overlay |
| **OpenDataWFS** | [MapServer](https://services.thelist.tas.gov.au/arcgis/rest/services/Public/OpenDataWFS/MapServer) | ArcGIS REST + WFS / GeoJSON | CC BY 3.0 AU (per layer) | Hard limit: 2000 features per request, MaxRecordCount 1000 |
| **NCC 2022 Volume One XML** | [data.gov.au dataset](https://data.gov.au/data/dataset/national-construction-code-ncc-2022) / [XML ZIP](https://data.gov.au/data/dataset/ea6e2003-720c-4b9d-987b-31741c569c38/resource/ac9427be-13e5-4ee2-b41b-e953d306433d/download/ncc-2022-volume-one.zip) | XML | CC BY 4.0 | Current operative version = NCC 2022 Amendment 2. NCC 2025 is preview only. Referenced AS standards (e.g. AS 1428.1) are paywalled — return REVIEW not a fabricated answer |
| **Disability (Access to Premises) Standards 2010** | [Federal Register](https://www.legislation.gov.au/F2010L00668/latest/text) | HTML + PDF | CC BY 4.0 (Federal Register) | 2024 amendment took effect 29 Jul 2025 — updated AS reference. Clause system does not match NCC 2022 numbering |

## 🟡 Secondary — useful but not cleanly open

| Source | Notes |
|---|---|
| **Tasmanian Planning Scheme PDFs** | Tas Govt copyright — not CC. Keep raw PDFs local/private. Publish only your own summaries + source links. |
| **Hobart council guidance + fees** | No open licence. Fees change annually (2026-27 adopted Apr 2026). Use for workflow reference only. |
| **Glenorchy council checklist** | All Rights Reserved. Checklist lags scheme change. Keep out of public repo. |
| **CBOS forms + hazard determinations** | Tas Govt website terms. Use as reference only — building approvals layer on top of planning separately. |

## ❌ Do not use

| Source | Reason |
|---|---|
| **PlanBuild Tasmania** | Restrictive portal terms — no reproduce/distribute for public or commercial use |
| **AS 1428.1:2021 (Standards Australia)** | Paywalled, single-user, anti-sharing. Do not include in public repo. Return `REVIEW` when answer depends on it. |

## Key constraints for the hackathon build

- theLIST terms allow service changes/suspension without notice — build with graceful fallback
- Licence is per-layer, not per-platform — check each layer's copyright text before ingesting
- Statutory overlay ≠ hydraulic flood model — always cite which source a risk flag came from
- NCC XML = safe to chunk + publish snippets. AS standards = never publish text.

## Links
- [[Microsoft AI Skills Fest Hackathon]]
- [[Tas Planning Copilot — Data Findings]] — full deep research with all sources
