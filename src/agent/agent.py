"""
agent.py — CanIBuild reasoning agent

Uses OpenAI-compatible SDK (OpenRouter + DeepSeek R1 for dev,
swap to Azure OpenAI for submission via env vars).

Flow:
  1. lat/lng/pid arrive pre-resolved from FE autocomplete (no geocoding at check-time)
     Fallback: if lat/lng missing, call geocode_address(address) -> theLIST layer 7
  2. query_overlays(lat, lng, pid) → overlays + zone + council (deterministic, no LLM tool loop)
  3. retrieve KB clauses per overlay lps_ref
  4. Generate mode + intent specific plain-English response (all claims cited)
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

from src.tools.geocoder import geocode_address, AddressNotFoundError, OutsideTasmaniaError
from src.tools.thelist import (
    query_overlays,
    _FLOOD_DEFAULT, _TASWATER_DEFAULT, _LANDSLIP_DEFAULT,
    _HERITAGE_DEFAULT, _COVERAGE_DEFAULT, _EPA_DEFAULT,
)
from src.tools.retriever import retrieve, retrieve_by_ref
from src.tools.schemas import QUERY_OVERLAYS_SCHEMA

ALL_TOOLS = [QUERY_OVERLAYS_SCHEMA]

load_dotenv()

TOOL_SYSTEM_PROMPT = """You are CanIBuild, a Tasmanian property planning assistant.
The address has already been geocoded. Use the provided tools to look up planning data."""

RESPONSE_SYSTEM_PROMPT = """You are CanIBuild, a Tasmanian property planning assistant.

Given planning data and clause text, write a plain-English summary focused on the user's INTENT.

CITATION RULES (strictly enforced):
- Every factual claim MUST end with a citation: [clause_ref — Source]
  Examples: [C6.2.1 — SPP 2024]  [HOB-S7.0 — Hobart LPS 2025]  [Z8.4.1 — SPP 2024]
- Only cite clause references from the CLAUSE blocks provided. DO NOT invent references.
- Hazard data citations use: [theLIST SES Flood Mapping], [theLIST Landslide Planning Map], [TasWater Serviced Land], [theLIST Tasmanian Heritage Register], [theLIST Building Footprints], [theLIST EPA Regulated Sites]
- If no clause supports a claim, omit it or say "Confirm with your council."
- Never estimate costs, fees, or timelines unless an exact figure appears in a clause.
- Never predict council decisions. Never give legal or engineering advice.
- For hazard data: report only the values returned — do NOT invent BAL ratings or flood predictions.

INTENT-SPECIFIC GUIDANCE:
- granny_flat / ancillary dwelling: state whether it's permitted/discretionary, cite setback and site coverage standards if present.
- extension / alterations: state whether exempt or requires permit, cite relevant threshold.
- additional_storey: cite building height limit for the zone.
- new_dwelling: state permitted/discretionary status, cite key standards (setback, height, coverage).
- outbuilding: state whether exempt, cite size/height thresholds if present.
- just_checking: summarise zone purpose and overlay constraints.

OUTPUT STRUCTURE:
**Zone:** Zone name + what it allows/restricts for this intent + citation.
**Overlays:** List each with plain-English meaning + citation, or "No overlays."
**Permit Pathway:** Permitted / Discretionary / Exempt — cite the clause that determines this.
**Key Standards:** Any setbacks, height limits, or site coverage thresholds from the clauses.
**Site Hazards:** Report flood status, TasWater serviced status, and landslip band. Cite theLIST sources. If in flood area include depth and hazard category. If in landslip band state band and note SPP C15 may apply. If TasWater not serviced note this affects servicing options.
**Site Intelligence:** Report state Heritage Register status (if listed, note works need Heritage Tasmania approval), existing building site coverage % (compare to the zone's max site coverage standard if known — this shows remaining development headroom), and any nearby EPA-regulated/contaminated sites. Cite theLIST sources. Omit a line only if its data is unavailable.
**What This Means for You:** 2-3 sentences directly addressing the stated intent.
End with: "For professional advice, contact a building designer or your council."
"""

# Maps theLIST zone names (ZONE field) to KB clause_ref prefixes (Z8, Z9, …)
ZONE_CODE_MAP = {
    "General Residential":       "Z8",
    "Inner Residential":         "Z9",
    "Low Density Residential":   "Z10",
    "Rural Living":              "Z11",
    "Village":                   "Z12",
    "Urban Mixed Use":           "Z13",
    "Local Business":            "Z14",
    "General Business":          "Z15",
    "Central Business":          "Z16",
    "Commercial":                "Z17",
    "Light Industrial":          "Z18",
    "General Industrial":        "Z19",
    "Rural":                     "Z20",
    "Agriculture":               "Z21",
    "Landscape Conservation":    "Z22",
    "Environmental Management":  "Z23",
    "Major Tourism":             "Z24",
}

INTENT_QUERIES = {
    "granny_flat":       "ancillary dwelling secondary dwelling setback site coverage permit",
    "extension":         "alterations additions extension dwelling setback building height permit",
    "additional_storey": "building height additional storey storey setback",
    "new_dwelling":      "single dwelling new dwelling permitted use setback site coverage",
    "outbuilding":       "outbuilding garage shed carport exempt permitted development",
    "just_checking":     "permitted use discretionary prohibited zone purpose",
}

TOOL_FUNCTIONS = {
    "query_overlays": lambda lat, lng, pid=None: query_overlays(lat, lng, pid=pid),
}


def _call_tool(name: str, args: dict) -> str:
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = fn(**args)
        return json.dumps(result, ensure_ascii=False)
    except (AddressNotFoundError, OutsideTasmaniaError) as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Tool error: {str(e)}"})


def _enrich_with_kb(overlay_result: dict, intent: str = "just_checking") -> str:
    """Retrieve KB clauses for each overlay and zone, intent-aware."""
    council = overlay_result.get("council", {}).get("name")
    overlays = overlay_result.get("overlays", [])
    zone = overlay_result.get("zone")
    intent_terms = INTENT_QUERIES.get(intent, "permitted use development")

    kb_context = []
    seen_refs: set[str] = set()

    def _append(clauses: list[dict], limit: int = 3) -> None:
        for c in clauses[:limit]:
            ref = c.get("clause_ref", "")
            if ref not in seen_refs:
                seen_refs.add(ref)
                kb_context.append(
                    f"CLAUSE REF: {ref}\n"
                    f"SOURCE: {c['source']}\n"
                    f"HEADING: {c['heading']}\n"
                    f"TEXT: {c['text'][:1000]}"
                )

    def _top_code(lps_ref: str) -> str | None:
        """Extract SPP top code from lps_ref. 'HOB-C6.2.1' → 'C6'."""
        import re
        m = re.search(r'(C\d+)', lps_ref or "")
        return m.group(1) if m else None

    try:
        # 1. Overlay clauses — application clause + dev standards
        for overlay in overlays:
            lps_ref = overlay.get("lps_ref")
            overlay_code = overlay.get("code")
            overlay_name = overlay.get("ov_name") or overlay_code or ""

            if lps_ref:
                # 1a. Application clause (what area/precinct this covers)
                clauses = retrieve_by_ref(lps_ref, council=council)
                if not clauses:
                    clauses = retrieve(
                        f"{overlay_name} {intent_terms}",
                        council=council,
                        overlay_code=overlay_code,
                        top_k=5,
                    )
                _append(clauses, limit=2)

                # 1b. Dev standards for this overlay code (C6.6, C12.6, C13.5 etc.)
                top = _top_code(lps_ref)
                if top:
                    dev_clauses = retrieve(
                        f"{overlay_name} development standards {intent_terms}",
                        council=council,
                        zone_code=top,
                        top_k=5,
                    )
                    _append(dev_clauses, limit=3)

        # 2a. Zone use table + statewide provisions — NO zone_code filter so SPP-4/6 docs included
        if zone:
            zone_name = zone.get("zone", "")
            zone_code = ZONE_CODE_MAP.get(zone_name)

            q_uses = f"{zone_name} {intent_terms} permitted discretionary prohibited"
            _append(retrieve(q_uses, council=council, top_k=5), limit=3)

            # 2b. Zone-specific development standards — zone_code filter keeps results precise
            q_dev = f"{zone_name} development standards setback building height site coverage floor area"
            _append(retrieve(q_dev, council=council, zone_code=zone_code, top_k=5), limit=3)

            # 2c. Statewide exempt provisions for this intent (SPP Section 4)
            q_exempt = f"exempt {intent_terms} no permit required"
            _append(retrieve(q_exempt, council=council, top_k=5), limit=2)

    except Exception:
        return "KB unavailable — responding from overlay data only."

    return "\n\n---\n\n".join(kb_context) if kb_context else "No matching KB clauses found."


def run(
    address: str,
    mode: str,
    intent: str,
    lat: float | None = None,
    lng: float | None = None,
    pid: int | None = None,
) -> dict:
    """
    Run CanIBuild agent.

    Args:
        address: Tasmanian property address (display only — already geocoded)
        mode:    "buyer" | "construction" | "da_owner"
        intent:  "just_checking" | "granny_flat" | "extension" | "additional_storey" | "new_dwelling" | "outbuilding"
        lat:     WGS84 latitude (pre-resolved by FE autocomplete)
        lng:     WGS84 longitude (pre-resolved by FE autocomplete)
        pid:     Parcel ID from theLIST (pre-resolved by FE autocomplete, optional)

    Returns:
        dict with keys: address, overlays, zone, council, mode, intent, response, error
    """
    client = OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
    )
    model = os.environ.get("LLM_MODEL", "deepseek/deepseek-r1")

    # Step 1: resolve coords — use pre-resolved point; fallback to theLIST geocode if missing
    if lat is None or lng is None:
        try:
            geo = geocode_address(address)
            lat = geo["lat"]
            lng = geo["lng"]
            if pid is None:
                pid = geo.get("pid")
        except (AddressNotFoundError, OutsideTasmaniaError) as e:
            return {
                "address": address, "mode": mode, "intent": intent,
                "council": None, "zone": None, "overlays": [],
                "lot_area_sqm": None, "kingborough_interim": False,
                "flood": dict(_FLOOD_DEFAULT), "taswater": dict(_TASWATER_DEFAULT),
                "landslip": dict(_LANDSLIP_DEFAULT),
                "heritage_register": dict(_HERITAGE_DEFAULT),
                "existing_coverage": dict(_COVERAGE_DEFAULT),
                "epa_sites": dict(_EPA_DEFAULT),
                "response": None, "error": str(e),
            }

    # Step 2: deterministic spatial queries — no LLM geocode tool loop
    overlay_result = query_overlays(lat, lng, pid=pid)

    # (No agent tool-calling loop needed — point already resolved)

    # Step 3: Enrich with KB clauses
    kb_context = _enrich_with_kb(overlay_result, intent=intent)

    flood = overlay_result.get("flood", {})
    taswater = overlay_result.get("taswater", {})
    landslip = overlay_result.get("landslip", {})

    flood_summary = (
        f"IN FLOOD AREA — 1% AEP depth: {flood.get('depth_1pct_m')} m, "
        f"hazard category: {flood.get('hazard_1pct')}, "
        f"water level: {flood.get('water_level_1pct_ahd')} m AHD [theLIST SES Flood Mapping]"
        if flood.get("in_flood_area")
        else "Not in mapped 1% AEP flood area [theLIST SES Flood Mapping]"
    )
    taswater_summary = (
        f"Sewer: {taswater.get('sewer_status') or 'Not serviced'} [TasWater Serviced Land]; "
        f"Water: {taswater.get('water_status') or 'Not serviced'} [TasWater Serviced Land]"
    )
    landslip_summary = (
        f"IN LANDSLIP HAZARD BAND — Band: {landslip.get('band')}, "
        f"Exposure: {landslip.get('exposure')} [theLIST Landslide Planning Map]. "
        "SPP C15 Landslip Code may apply."
        if landslip.get("in_landslip_band")
        else "Not in mapped landslip hazard band [theLIST Landslide Planning Map]"
    )

    heritage = overlay_result.get("heritage_register", {})
    coverage = overlay_result.get("existing_coverage", {})
    epa = overlay_result.get("epa_sites", {})

    heritage_summary = (
        f"STATE HERITAGE REGISTER — '{heritage.get('name')}' "
        f"({heritage.get('status')}) [theLIST Tasmanian Heritage Register]. "
        "Works require Heritage Tasmania approval."
        if heritage.get("state_listed")
        else "Not on the Tasmanian Heritage Register [theLIST Tasmanian Heritage Register]"
    )
    coverage_summary = (
        f"Existing buildings cover ~{coverage.get('coverage_pct')}% of the lot "
        f"({coverage.get('building_area_sqm')} m² across {coverage.get('building_count')} "
        f"building(s), tallest ~{coverage.get('max_height_m')} m) [theLIST Building Footprints]"
        if coverage.get("coverage_pct") is not None
        else "Existing site coverage unavailable [theLIST Building Footprints]"
    )
    epa_summary = (
        f"{epa.get('sites_nearby')} EPA-regulated site(s) within {epa.get('radius_m')} m: "
        + "; ".join(f"{s.get('name')} ({s.get('category')})" for s in epa.get("sites", []))
        + " [theLIST EPA Regulated Sites]"
        if epa.get("sites_nearby")
        else f"No EPA-regulated sites within {epa.get('radius_m', 300)} m [theLIST EPA Regulated Sites]"
    )

    # Step 4: LLM briefing generation (only LLM call remaining)
    final = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": RESPONSE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Address: {address}\n"
                    f"User intent: {intent.replace('_', ' ').upper()}\n"
                    f"Mode: {mode}\n\n"
                    f"Council: {overlay_result.get('council', {}).get('name')}\n"
                    f"Zone: {overlay_result.get('zone', {})}\n"
                    f"Lot area: {overlay_result.get('lot_area_sqm')} m²\n"
                    f"Overlays: {overlay_result.get('overlays', [])}\n\n"
                    f"SITE HAZARDS:\n"
                    f"Flood: {flood_summary}\n"
                    f"TasWater: {taswater_summary}\n"
                    f"Landslip: {landslip_summary}\n"
                    f"Heritage: {heritage_summary}\n"
                    f"Existing coverage: {coverage_summary}\n"
                    f"Contamination: {epa_summary}\n\n"
                    f"PLANNING CLAUSES FROM KNOWLEDGE BASE:\n{kb_context}\n\n"
                    f"Answer specifically for intent '{intent.replace('_', ' ')}'. "
                    "Cite every factual claim. Write your cited plain-English summary now."
                ),
            },
        ],
    )
    response_text = final.choices[0].message.content

    return {
        "address": address,
        "mode": mode,
        "intent": intent,
        "council": overlay_result.get("council"),
        "zone": overlay_result.get("zone"),
        "overlays": overlay_result.get("overlays", []),
        "lot_area_sqm": overlay_result.get("lot_area_sqm"),
        "kingborough_interim": overlay_result.get("kingborough_interim", False),
        "flood": overlay_result.get("flood", dict(_FLOOD_DEFAULT)),
        "taswater": overlay_result.get("taswater", dict(_TASWATER_DEFAULT)),
        "landslip": overlay_result.get("landslip", dict(_LANDSLIP_DEFAULT)),
        "heritage_register": overlay_result.get("heritage_register", dict(_HERITAGE_DEFAULT)),
        "existing_coverage": overlay_result.get("existing_coverage", dict(_COVERAGE_DEFAULT)),
        "epa_sites": overlay_result.get("epa_sites", dict(_EPA_DEFAULT)),
        "response": response_text,
        "error": None,
    }


if __name__ == "__main__":
    result = run(
        address="8 Nelson Road Sandy Bay 7005",
        mode="buyer",
        intent="just_checking",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
