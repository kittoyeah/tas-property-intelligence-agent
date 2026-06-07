# Research Findings
# SiteCheck — Tasmania Property Intelligence Agent

Last updated: 2026-06-08

---

## 1. API Feasibility Summary

All overlay data queryable via ArcGIS REST — no scraping, no PDF parsing, no multimodal needed. API returns textual attributes directly.

**Two data paths — both required:**

| Path | Source | Returns | Role |
|---|---|---|---|
| Live API | theLIST PlanningOnline ArcGIS REST | Overlay flags + zone (factual) | WHAT exists on this land |
| Foundry IQ KB | Indexed planning rules (pre-built) | Permit pathways, rules, implications | SO WHAT it means |

---

## 2. theLIST ArcGIS REST — Confirmed Working Layers

Base URL: `https://services.thelist.tas.gov.au/arcgis/rest/services/Public/PlanningOnline/MapServer`

| Layer ID | Name | Coverage | Status | Purpose |
|---|---|---|---|---|
| **14** | TPS Code Overlay | Statewide (all TPS councils) | ✅ CONFIRMED | Flood, bushfire, heritage, landslip, coastal |
| **15** | TPS General Overlay | Statewide (all TPS councils) | ✅ CONFIRMED | Specific area plans, local area objectives |
| **13** | TPS Zones | Statewide (all TPS councils) | ✅ CONFIRMED | Planning zone for address |
| **8** | Local Government Areas | Statewide | ✅ CONFIRMED | Council name + LGA code → KB retrieval filter |
| 3 | Interim Planning Scheme Overlay | Kingborough only | ✅ Working | Kingborough-specific overlays (legacy, pre-TPS) |

Other services tested:

| Service | Type | Status | Notes |
|---|---|---|---|
| `SES_FloodMapping` | Raster, 38 layers | ✅ Queryable (identify only) | 1%/2%/0.5% AEP flood hazard. Returns pixel values. Use `identify` not `query`. |
| `Infrastructure/6` | Vector — TasWater Flood Inundation | ✅ Queryable | Fields: WATERCOURS, Dam, FILE_REFER |
| `Infrastructure/0` | Vector — TasWater Sewer Serviced Land | ✅ Queryable | Fields: Service Type, Description, Contact |
| `Infrastructure/1` | Vector — TasWater Water Serviced Land | ✅ Queryable | |

---

## 3. Query Pattern

### Step 1 — Geocode address to lat/lng

Use Nominatim (OpenStreetMap). Free, no API key, low-volume friendly.

```
GET https://nominatim.openstreetmap.org/search
  ?q=8+Nelson+Road+Sandy+Bay+Tasmania+7005
  &format=json
  &limit=1

→ returns lat, lng in WGS84 (EPSG:4326)
```

### Step 2 — Query overlays (Layer 14, statewide TPS code overlays)

```
GET /PlanningOnline/MapServer/14/query
  ?geometry={lng},{lat}
  &geometryType=esriGeometryPoint
  &inSR=4326
  &spatialRel=esriSpatialRelIntersects
  &outFields=CODE,OV_NAME,OV_CAT,DESCRIPT,LPS,LPS_REF
  &returnGeometry=false
  &f=json
```

### Step 3 — Query zone (Layer 13)

Same pattern, `outFields=LPS,ZONE,ZONE_ABB,LPS_REF`

### Step 4 — Query general overlays (Layer 15)

Same pattern, `outFields=OV_TYPE,OV_NAME,OV_CAT,DESCRIPT,LPS,LPS_REF`

### Step 4b — Query council LGA (Layer 8)

Same pattern, `outFields=NAME,LGA_CODE`. Run in parallel with Steps 2–4.

### Step 5 — SES Flood Mapping (raster — supplementary)

```
GET /SES_FloodMapping/MapServer/identify
  ?geometry={lng},{lat}
  &geometryType=esriGeometryPoint
  &sr=4326
  &layers=all
  &tolerance=2
  &mapExtent={bbox}
  &imageDisplay=800,600,96
  &f=json
```

---

## 4. Coordinate System Notes

- `inSR=4326` passes WGS84 lat/lng directly — works reliably for large area polygons (heritage precincts, broad zones)
- Web Mercator (EPSG:3857) is native — required for small/narrow polygons where floating-point miss at `inSR=4326` boundary may occur
- **Production**: use pyproj for coordinate conversion; implement fallback (try 4326, if empty retry with native Web Mercator)
- **Never**: manually compute Web Mercator — off by hundreds of metres, returns wrong LGA (tested: Sandy Bay query hit Huon Valley)

---

## 5. Layer Field Schemas

### Layer 8 — Local Government Areas

| Field | Example | Meaning |
|---|---|---|
| `NAME` | `"Hobart"` | Council name — display to user |
| `LGA_CODE` | `114` | Council ID — matches `LPS_NO` in theLIST, use as KB retrieval filter |

**Why query Layer 8:** Available even on clean sites (no overlays). Tells agent which council's LPS to search in KB. Also `LGA_CODE` matches the Hobart LPS filter used in overlay distinct queries.

### Layer 14 — TPS Code Overlays

| Field | Example | Meaning |
|---|---|---|
| `CODE` | `"Local Historical Heritage Code"` | Overlay type — use to classify and label |
| `OV_NAME` | `"Local heritage precinct"` | Specific designation within that overlay type |
| `OV_CAT` | `"Medium"` | Hazard band / category |
| `DESCRIPT` | `"Battery Point"` | Area description (often place name) |
| `LPS` | `"Hobart Local Provisions Schedule"` | Which council's LPS applies |
| `LPS_REF` | `"HOB-C6.2.1"` | Clause reference — use for KB lookup + citations |

---

## 6. Confirmed Overlay CODE Values — Hobart LPS

Queried via distinct `WHERE LPS_NO=114`:

| CODE | Our flag | Hazard level |
|---|---|---|
| `Flood-prone Hazard Areas Code` | Flood | High |
| `Landslip Hazard Code` | Landslip | Varies (band in OV_CAT: Low/Medium/High/Medium-active) |
| `Local Historical Heritage Code` | Heritage | Varies (precinct / place / tree / archaeological) |
| `Bushfire-prone Areas Code` | Bushfire | Varies (prone area / inner protection area) |
| `Coastal Inundation Hazard Code` | Coastal | Varies (Low/Medium/High band) |
| `Coastal Erosion Hazard Code` | Coastal | Varies (band + investigation area) |
| `Natural Assets Code` | Environmental | Priority vegetation / waterway protection |
| `Electricity Transmission Infrastructure Protection Code` | Infrastructure | Corridor / buffer zones |
| `Parking and Sustainable Transport Code` | Transport | Pedestrian priority streets |

---

## 7. Confirmed Test Results

### Battery Point, Hobart (lat=-42.8920, lng=147.3290)

Layer 14 — 2 features:
- `CODE="Local Historical Heritage Code"`, `OV_NAME="Local heritage precinct"`, `DESCRIPT="Battery Point"`, `LPS_REF="HOB-C6.2.1"`
- `CODE="Landslip Hazard Code"`, `OV_NAME="Medium landslip hazard band"`, `OV_CAT="Medium"`

### Lower Sandy Bay waterfront (Web Mercator: 16400206, -5296465)

Layer 14 — 2 features:
- `CODE="Local Historical Heritage Code"`, `OV_NAME="Local heritage precinct"`
- `CODE="Flood-prone Hazard Areas Code"`, `OV_NAME="Flood-prone areas"`, `LPS_REF="C12.0"`

### Kingston, Kingborough (lat=-42.9767, lng=147.2994)

Layer 3 (interim scheme):
- `O_CODE="120.FRE"`, `O_NAME="Bushfire Prone Areas"`, `PLANSCHEME="Kingborough Interim Planning Scheme 2015"`

### 8 Nelson Road Sandy Bay 7005 (lat=-42.9026379, lng=147.3323815)

Layer 14 + 15: **EMPTY — clean site** ✅
Layer 13 (zone): `ZONE="General Residential"`, `LPS="Hobart LPS"`
Layer 8 (LGA): `NAME="Hobart"`, `LGA_CODE=114`

Clean address returns empty features array — this is the valid no-overlay result. Handle gracefully in UI.

---

## 8. Known API Errors Encountered

| Error | Root cause | Fix |
|---|---|---|
| Layer 2 (OpenDataWFS) returning empty | Layer 2 is Interim Planning Scheme — Kingborough only, not statewide | Use Layer 14 for TPS statewide |
| SES Flood `/query` returning 400 | Raster service, `fields: null` — no vector attribute table | Use `/identify` operation |
| Layer 13 returning 400 intermittently | API instability | Add retry logic (exponential backoff, 3 attempts) |
| Manual Web Mercator yielding wrong LGA | Precision error in manual formula | Use `inSR=4326` or pyproj |
| Layer 14/15 not appearing in initial layer list | Only layers 0–11 listed for Kingborough; TPS layers 14, 15, 24, 25 exist in same service but not first-page listed | Documented fix: search `services.thelist.tas.gov.au "Tasmanian Planning Scheme"` to confirm layer IDs |

---

## 9. Foundry IQ Knowledge Base — Content Plan

The live API returns what overlays exist. Foundry IQ KB returns what they mean for the user's situation. The agent combines both.

### Priority 1 — Must index before ship

| Content | Source | Licence | Notes |
|---|---|---|---|
| TPS zone use tables (permitted / discretionary / prohibited by zone) | SPP PDFs — Tas Govt | Tas Govt copyright | RAG use only — do not republish raw text |
| TPS code provisions per overlay type (flood, bushfire, heritage, landslip) | SPP PDFs | Tas Govt copyright | Chunk by code clause; reference LPS_REF field for lookup key |
| Permit pathway explainer | Write ourselves | Original — can publish | Permitted (14 days), Discretionary (42 days), what triggers each |
| Referral agency triggers — when TasWater, TFS, Heritage Tas, EPA get involved | SPP provisions | RAG use only | Critical for DA mode |

### Priority 2 — Should index

| Content | Source | Licence | Notes |
|---|---|---|---|
| Hobart LPS local variations | Hobart LPS PDF | Tas Govt copyright | Hobart-specific zone variations, local heritage rules |
| NCC 2022 Volume One — construction classes, Part A | data.gov.au XML | CC BY 4.0 | Can publish. What BAL rating triggers what build standard |
| Standard permit processing times per council | Write ourselves | Original | Permitted = 14 days, Discretionary = 42 days standard |
| BAL (Bushfire Attack Level) explanation | Write ourselves + TFS guidance | Original | What "bushfire prone" actually means for construction cost |

### Priority 3 — Nice to have (post-hackathon)

| Content | Source | Notes |
|---|---|---|
| Council fee schedules | Each council publishes annually | Version carefully — changes yearly |
| State Heritage Register entries | Heritage Tasmania | Formal state listings beyond LPS local codes |
| Standard permit conditions per overlay | Write ourselves | Tradie mode richness |
| RMPAT appeal rights + timeframes | Write ourselves | DA mode completeness |

### Do not index

| Content | Reason |
|---|---|
| Land title easements / covenants | Land Titles Office — not public API |
| AS 1428.1 (accessibility standards) | Paywalled — never publish text |
| PlanBuild portal data | Restrictive terms |
| Flood insurance implications | Out of scope — different domain |

---

## 10. Enrichment Sources — Secondary Data

| Source | What it adds | Access |
|---|---|---|
| Heritage Tasmania — State Heritage Register | Formal state heritage listings (separate from LPS local codes) | Public search, no API |
| TasWater — service availability | Whether sewer/water connected (not just coverage area) | Infrastructure layers confirmed above |
| TFS (Tasmania Fire Service) | BAL assessment guidance | PDF guidance |
| EPA Tasmania | When EPA referral triggered | SPP provisions |
| RMPAT (Resource Management and Planning Appeal Tribunal) | Appeal rights after council refusal | Public website |

---

## 11. Data Sources — Licence Summary

| Source | Endpoint | Format | Licence | Status |
|---|---|---|---|---|
| theLIST PlanningOnline Layer 14 | ArcGIS REST `/14/query` | JSON | CC BY 3.0 AU | ✅ Confirmed working |
| theLIST PlanningOnline Layer 15 | ArcGIS REST `/15/query` | JSON | CC BY 3.0 AU | ✅ Confirmed working |
| theLIST PlanningOnline Layer 13 | ArcGIS REST `/13/query` | JSON | CC BY 3.0 AU | ✅ Confirmed working |
| SES Flood Mapping | ArcGIS REST `/identify` | Pixel values | theLIST terms | ✅ Queryable (raster) |
| TasWater Infrastructure | ArcGIS REST query | JSON | theLIST terms | ✅ Queryable |
| Nominatim geocoder | REST | JSON | ODbL (OpenStreetMap) | ✅ Free, no key needed |
| TPS SPP provisions | PDF download (thelist.tas.gov.au) | PDF | Tas Govt copyright | RAG only — do not republish |
| Hobart LPS | PDF download | PDF | Tas Govt copyright | RAG only |
| NCC 2022 Volume One | data.gov.au XML | XML | CC BY 4.0 | ✅ Can publish |
