# Product Requirements Document
# SiteCheck — Tasmania Property Intelligence Agent

**Version:** 0.2 — 2026-06-08
**Hackathon:** Microsoft AI Skills Fest 2026 — Reasoning Agents track (Azure AI Foundry + Foundry IQ)
**Repo:** https://github.com/kittoyeah/tas-property-intelligence-agent

---

## The Story

You find a block in Tassie. Looks perfect. You sign. Then you find out there's a flood overlay — your lender won't finance it, insurance costs double, and anything you build needs an engineer's report first. That information was always public. You just had no way to find it in 30 seconds.

**One-liner:** *"Know your land before you buy, build, or apply."*

---

## Problem

### The human problem
Tasmanians making decisions about land — buying, building, or lodging a DA — can't get a fast plain English answer about what restrictions apply to their property. The information is public and free, but buried in government portals that require planning knowledge to navigate.

PlanBuild Tasmania covers the formal process (lodgement, tracking, compliance). It shows overlays. It does not tell you what they mean for your situation.

### The systemic problem
Urban and Regional Planners are on the **Jobs and Skills Australia 2025 Occupation Shortage List** — in shortage in every state including Tasmania. 64% of planning organisations struggled to fill roles in the past 12 months. Repetitive Tier-1 enquiries (overlay checks, basic zoning questions) consume scarce planner time that should go to complex DAs.

### Evidence
- [JSA 2025 Occupation Shortage List — Urban and Regional Planners](https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles/occupations/2326-urban-and-regional-planners)
- [PIA: Urban planner shortage a hidden risk to Australia's housing future](https://www.planning.org.au/pia/news-resources/articles/latest-updates/national/urban-planner-shortage-a-hidden-risk-to-australias-housing-future-new-survey-shows.aspx)
- Tasman Council: permits received after 10 Nov 2025 may not be determined before year end

---

## Positioning

**Not a competitor to PlanBuild — an AI interpretation layer on top of the same open data.**

PlanBuild tells you what overlays exist. SiteCheck tells you what they mean for your specific situation. Built on Tasmanian Government open data (theLIST CC BY 3.0 AU) — the same source PlanBuild uses.

---

## Competitive Landscape

| Tool | Who for | What it does | Gap |
|---|---|---|---|
| **PlanBuild Tasmania** | Everyone (formal process) | Overlay lookup + DA lodgement portal | No plain English interpretation, portal UX, restrictive terms |
| **tasplanning.report** | Planners / building designers | AI scheme clause lookup (SPP/LPS text) | For experts, no spatial API, wrong user |
| **Landchecker** | Developers, agents | Property data + overlays | No Tasmania coverage |
| **SiteCheck** | Buyer, construction, DA owner | Plain English overlay interpretation | The gap |

---

## Users — Three Modes

Same tool, same data, same agent. Mode selected after address is entered.

### Mode 1 — Property Buyer
**Situation:** considering purchasing a block or property
**Question:** "Is there anything on this land I should know before I sign?"
**Stakes:** $300–500k decision, information asymmetry is massive
**Sample output:**
> ⚠️ 2 things to know before you sign.
> **Flood risk** — this block sits in a mapped flood zone. Some lenders won't finance flood-zoned land, insurance costs more, and any future build needs engineering sign-off. Ask your solicitor to flag this before settlement.
> **Heritage area** — this street is in a local heritage area. You can still renovate and build, but designs need council approval.

### Mode 2 — Construction / Tradie
**Situation:** quoting or planning a job at a Tasmanian address
**Question:** "Any overlays on this site that affect my quote or timeline?"
**Stakes:** blown margins, mid-job surprises, wrong quote
**Sample output:**
> ⚠️ 2 things to factor into your quote.
> **Flood overlay** — hydraulic engineer's report required before council will assess any new structure. Budget ~$2–4k and 3–4 weeks before you can even lodge.
> **Heritage overlay** — heritage impact statement required. Add $1–3k and 6–8 weeks to your timeline.

### Mode 3 — DA Owner (Current Owner Planning to Build)
**Situation:** own the property, planning to renovate or build, considering a DA
**Question:** "What will council need from me and how long will this take?"
**Stakes:** time, cost, application strategy
**Sample output:**
> ⚠️ Your DA will be discretionary — council must assess it.
> **Why:** heritage overlay means your application can't be approved as permitted development.
> **Expect:** 42+ days minimum, heritage impact statement, likely referral to Heritage Tasmania.
> **Next step:** engage a building designer familiar with heritage assessments before lodging.

---

## UX Approach

**Address first. Mode after.**

1. User enters Tasmanian address
2. Agent queries theLIST → overlay map + flags appear ← **wow moment**
3. "What's your situation?" → three task-based options
4. Agent returns mode-specific plain English interpretation

Task language (not role labels):
- "I'm buying this property"
- "I'm quoting or building here"
- "I own this and want to build"

---

## Solution Architecture

```
User enters address
        ↓
Tool: Geocoder (address → lat/lng)
        ↓
Tool: theLIST ArcGIS REST (lat/lng → overlay flags, live)
        ↓
Foundry IQ Knowledge Base (what each overlay means — pre-indexed)
        ↓
Agent: combines live flags + KB knowledge → mode-specific answer
```

**Two data paths — both required:**
- **Live API** (theLIST REST) → what overlays exist on this address
- **Knowledge Base** (Foundry IQ) → what each overlay means in practice

---

## Data Sources

All open, API-queryable, CC-licensed. No PDF parsing required for Slice 1.

| Source | What it provides | Licence |
|---|---|---|
| theLIST PlanningOnline ArcGIS REST | Flood, bushfire, heritage, landslip, planning zone overlays | CC BY 3.0 AU (per layer) |
| SES Flood Mapping ArcGIS REST | Hydraulic flood model (supplements statutory overlay) | theLIST terms |
| OpenDataWFS | Additional spatial layers | CC BY 3.0 AU (per layer) |

Full detail → [Data Sources.md](../Data%20Sources.md)

---

## Azure Stack

| Component | Role |
|---|---|
| Azure AI Foundry | Agent loop + tool calling + multi-turn conversation |
| Foundry IQ (Azure AI Search) | Knowledge retrieval — grounded, cited answers |
| Azure OpenAI (gpt-4o-mini) | Language model |
| Azure Blob Storage | Knowledge base backing store |

---

## Scope

### In (Slice 1 — ship by 14 Jun 2026)
- Address input → geocode → theLIST overlay query
- Four overlays: flood, bushfire, heritage, landslip
- Three modes: buyer, construction, DA owner
- Plain English output with cited sources
- Graceful fallback if theLIST API unavailable

### Out (later slices)
- Zone rules ("can I build X here?") — Slice 2
- NCC compliance checking — Slice 3
- Fee calculations
- Per-council variations (Hobart vs Glenorchy differ)
- Specific cost/time estimates (grounded data not available)
- DA form pre-fill
- Legal or engineering advice — ever
- Addresses outside Tasmania
- State government systems — politically sensitive, avoid

---

## Success Criteria

- [ ] Valid Tasmanian address → correct overlay flags within 10 seconds
- [ ] Every flag cites the source layer — no hallucination
- [ ] Three modes return meaningfully different interpretations
- [ ] Graceful fallback if theLIST API unavailable
- [ ] Publicly accessible demo URL for LinkedIn post
- [ ] Demo video recorded
- [ ] Submission lodged by 14 Jun 2026

---

## References
- [microsoft/iq-series](https://github.com/microsoft/iq-series) — Foundry IQ implementation guide
- [theLIST ArcGIS REST services](https://services.thelist.tas.gov.au/arcgis/rest/services/Public/)
- [JSA Occupation Shortage — Urban and Regional Planners](https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles/occupations/2326-urban-and-regional-planners)
- [PIA Planner Shortage Report](https://www.planning.org.au/pia/news-resources/articles/latest-updates/national/urban-planner-shortage-a-hidden-risk-to-australias-housing-future-new-survey-shows.aspx)
