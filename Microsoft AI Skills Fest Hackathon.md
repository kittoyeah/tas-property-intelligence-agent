---
tags:
  - project
  - ai-generated
status: active
created: 2026-06-05
---
# 🏆 Microsoft AI Skills Fest Hackathon

- **Status:** active — registered ✅. Now: build + submit an AI agent before the deadline.
- **One-liner:** Ship an AI agent to the Microsoft AI Skills Fest hackathon → bank fresh, dated, Microsoft-branded **AI-track proof** for the CV + [[Portfolio Website]].

## Why this matters (ties to the goal)
- Direct **AI-track** proof — on-brand for "BA who ships AI". Feeds [[Job Hunt — Internship 2026]] (esp. KPMG + Mode B + [[Rapid Circle]], a Microsoft partner).
- Submission → **digital badge**; playlist → Credly badge (+ a cert voucher, but I already hold the Akkodis one for [[Azure AI Fundamentals Certification]] — voucher is not the prize here, the *agent build* is).
- "Build in public, fresh proof monthly" = my strategy. This is one week of it.

## Key facts
- **Festival:** 8–12 Jun 2026 (virtual). Skilling playlists drop 8 Jun.
- **Hackathon:** build/submit an AI agent · esports-style leaderboard · cash prizes + category recognition.
- **Deadline: submit by 14 Jun 2026.** Registered before 8 Jun → double entry ✅.
- Portal: https://aiskillsnavigator.microsoft.com/events/AISF2026

## Concept (decided 2026-06-07)

**Track: Reasoning Agents (Azure AI Foundry)**

**Problem:**
Tasmanians — homeowners, tradies, developers, and council staff — can't get a fast, reliable answer to "what can I do with this land?" without manually cross-checking multiple planning overlays, scheme provisions, and council rules across fragmented government sources. The result: avoidable rejections, wasted consultant fees, and councils buried in repetitive enquiries.

**Solution: Tasmania Property Intelligence Agent**
One agent, three users:
- **Homeowner/tradie** → "can I build a shed/pool/fence?" (G2)
- **Developer/consultant** → full DA overlay + compliance check (G1)
- **Council staff** → spatial planning queries without GIS skills (G5)

Same data, same engine, different depth of answer.

**Scope for 7 days:** Risk Screener only — enter an address → query theLIST spatial overlays → return flood, bushfire, heritage, landslip risk in plain English with cited sources. Cleanest data, no PDF parsing needed, live API.

## Data sources
Full detail → [[Data Sources]] (in this folder)

| Source | What it feeds | Format | Open? |
|---|---|---|---|
| theLIST Planning Overlays (PlanningOnline ArcGIS REST) | Flood, bushfire, heritage, landslip, planning zone overlays | ArcGIS REST | ✅ CC BY 3.0 AU (per layer) |
| SES Flood Mapping (ArcGIS REST) | Hydraulic flood model — supplement to statutory overlay | ArcGIS REST | ✅ theLIST terms |
| OpenDataWFS | Additional spatial layers (GeoJSON via WFS) | ArcGIS REST + WFS | ✅ CC BY 3.0 AU (per layer) |
| NCC 2022 Volume One XML | Building compliance clauses (stretch — Standards Checker) | XML | ✅ CC BY 4.0 |
| Disability (Access to Premises) Standards 2010 | Access compliance (stretch) | HTML + PDF | ✅ CC BY 4.0 |
| Tasmanian Planning Scheme PDFs | Zone rules, acceptable solutions (stretch) | PDF | 🟡 Tas Govt copyright — not CC |
| Hobart / Glenorchy council guidance | Fee schedules, checklists (workflow reference) | Web | 🟡 no open licence |
| PlanBuild Tasmania | — | Portal | ❌ restrictive terms |
| AS 1428.1:2021 | Access standards | — | ❌ paywalled |

## Why Reasoning Agents track
Multi-step reasoning: address input → spatial overlay query → rules lookup → plain English verdict with citations. Azure AI Foundry handles the agent loop + tool calling natively.

## Scope (ship small, reuse — don't invent)
- Pick the Risk Screener as Slice 1 — smallest working demoable agent
- Stretch: add NCC Standards Checker as Slice 2 if time allows
- Links to [[Tas Planning Copilot]] — same problem, same data, Azure instead of Python

## Plan
- [x] Register (double entry) ✅
- [ ] Pick concept (A or B) + define the one agent it is 📅 2026-06-08 ⏫
- [ ] Build MVP agent (reuse existing code/data) 📅 2026-06-12 ⏫
- [ ] Test + polish + record a short demo 📅 2026-06-13 🔼
- [ ] **Submit** 📅 2026-06-14 ⏫
- [ ] (optional) Complete an AI Skills Fest playlist → Credly badge 🔽
- [ ] After: write it up → [[Portfolio Website]] + add bullet to CV + log in [[Hackathon Experience Summary]]

## Definition of Done
- A working AI agent **submitted** before 14 Jun → badge earned.
- Written up as a proof point (Portfolio + CV bullet + Hackathon log).

## Links
[[Job Hunt — Internship 2026]] · [[Roadmap 2026]] · [[Portfolio Website]] · [[SabaiHub]] · [[Tas Planning Copilot]] · [[Azure AI Fundamentals Certification]] · [[Hackathon Experience Summary]] · [[me]]
