"""
hazard_reference_chunker.py — hazard reference KB chunks for CanIBuild

Emits explanatory chunks covering:
- 1% AEP flood (what it means, hazard categories, planning implications)
- Landslide hazard bands (Low/Medium/Active, SPP C15 cross-reference)
- TasWater serviced land (planning rule re secondary residences)

Usage:
  python -m src.tools.hazard_reference_chunker
  python src/tools/hazard_reference_chunker.py
"""

import json
import argparse
from pathlib import Path

OUTPUT_PATH = Path("data/chunks/hazard-reference-chunks.json")
SOURCE_FLOOD = "theLIST / CanIBuild reference note"
SOURCE_LANDSLIP = "theLIST / CanIBuild reference note"
SOURCE_TASWATER = "theLIST / CanIBuild reference note"


def _chunk(clause_ref: str, heading: str, text: str, source: str, clause_type: str = "reference") -> dict:
    return {
        "doc": "Hazard Reference Notes",
        "council": "statewide",
        "clause_ref": clause_ref,
        "parent_clause": clause_ref.rsplit("-", 1)[0] if "-" in clause_ref else clause_ref,
        "code_ref": clause_ref.split("-")[0] if "-" in clause_ref else clause_ref,
        "overlay_code": None,
        "clause_type": clause_type,
        "heading": heading,
        "text": text.strip(),
        "source": source,
    }


CHUNKS = [
    # ── Flood ─────────────────────────────────────────────────────────────────
    _chunk(
        clause_ref="REF-FLOOD-AEP",
        heading="1% AEP Flood — What Annual Exceedance Probability Means",
        text=(
            "Annual Exceedance Probability (AEP) expresses flood frequency as the probability of "
            "a flood occurring in any given year. A 1% AEP flood (commonly called the '1-in-100-year "
            "flood') has a 1% chance of being equalled or exceeded in any year. This is the standard "
            "design flood event used in Tasmanian land use planning. The SES_FloodMapping service on "
            "theLIST maps areas affected by the 1% AEP riverine and overland flow flood events across "
            "Tasmania. Being within the 1% AEP flood extent does not automatically prohibit development "
            "but triggers assessment under the relevant planning scheme flood overlay or the SPP Flood "
            "Hazard Code."
        ),
        source=SOURCE_FLOOD,
    ),
    _chunk(
        clause_ref="REF-FLOOD-HAZARD-CATS",
        heading="1% AEP Flood Hazard Categories — Riverine Flooding",
        text=(
            "The SES Flood Mapping layer assigns a hazard category value to each flood-affected cell. "
            "Category 1 (Low Hazard): shallow or slow-moving water; generally safe for people to wade, "
            "minor property damage expected. Category 2 (Medium Hazard): deeper or faster water; "
            "dangerous for people on foot, moderate damage likely. Category 3 (High Hazard): deep "
            "fast-moving water or combination of depth and velocity that is dangerous to life and "
            "structures. Category 4 (Very High/Extreme Hazard): extreme velocity or depth; structural "
            "damage to buildings likely, unsafe for all uses. Higher hazard categories typically require "
            "stricter assessment and may trigger requirements for flood-compatible construction, floor "
            "level freeboard, or restrict habitable floor space below the flood level. Confirm "
            "applicable code thresholds with your council or a registered surveyor."
        ),
        source=SOURCE_FLOOD,
    ),
    _chunk(
        clause_ref="REF-FLOOD-DEPTH",
        heading="1% AEP Flood Depth and Water Level — Planning Use",
        text=(
            "The SES Flood Mapping service provides two additional raster layers for the 1% AEP event: "
            "flood depth (metres above ground) and water level (metres Australian Height Datum, m AHD). "
            "Flood depth is used to assess impacts on existing structures and to determine freeboard "
            "requirements for new habitable floor levels. Water level (m AHD) is used by engineers and "
            "surveyors to design finished floor levels — the standard Tasmanian planning approach "
            "requires the habitable floor level to be set at or above the 1% AEP water level plus a "
            "freeboard allowance (typically 300–500 mm, confirmed in the relevant planning scheme). "
            "These values from theLIST are indicative; a registered surveyor should confirm site levels."
        ),
        source=SOURCE_FLOOD,
    ),
    _chunk(
        clause_ref="REF-FLOOD-PLANNING-TRIGGER",
        heading="Flood Overlay — Planning Scheme Trigger and SPP C17",
        text=(
            "In Tasmanian planning schemes, land within the 1% AEP flood extent is typically mapped "
            "under the Flood Hazard Overlay. The SPP Flood Hazard Code (C17 in many LPS documents) "
            "sets out acceptable solutions and performance criteria for development in flood-prone areas. "
            "Common requirements include: habitable floor levels at or above the 1% AEP flood level "
            "plus freeboard; flood-compatible materials below the flood level; no storage of hazardous "
            "materials in the flood zone. Ancillary dwellings and new dwellings in flood areas are "
            "generally discretionary and must address flood risk in a planning permit application. "
            "Check your council's LPS for the specific flood overlay provisions."
        ),
        source=SOURCE_FLOOD,
    ),

    # ── Landslip ──────────────────────────────────────────────────────────────
    _chunk(
        clause_ref="REF-LANDSLIP-BANDS",
        heading="Landslide Hazard Bands — Low / Medium / Active",
        text=(
            "The theLIST Landslide Planning Map (GeologicalAndSoils service, Layer 23) classifies land "
            "into hazard bands based on geology, slope, and historical landslide data. "
            "Low Band: some susceptibility to shallow landsliding; development is generally permitted "
            "but a geotechnical assessment may be recommended for sensitive uses or significant earthworks. "
            "Medium Band: moderate susceptibility; development is typically discretionary and a "
            "geotechnical investigation by a suitably qualified engineer is usually required as part of "
            "any planning permit application. "
            "Active Band: known active or recently active landslide area; development is generally "
            "prohibited or highly restricted; comprehensive geotechnical investigation mandatory. "
            "Hazard bands are indicative overlays — site-specific conditions may differ. Always seek "
            "independent geotechnical advice for any Medium or Active band site."
        ),
        source=SOURCE_LANDSLIP,
    ),
    _chunk(
        clause_ref="REF-LANDSLIP-SPP-C15",
        heading="SPP C15 Landslip Code — Planning Requirements",
        text=(
            "The State Planning Provisions Landslip Code (C15) applies to land within a mapped Landslide "
            "Hazard Band as shown on theLIST. The code aims to ensure development does not increase "
            "landslip risk to people, property, or the environment. Key requirements under C15: "
            "(1) A geotechnical report from a suitably qualified and experienced professional (SQEP) is "
            "required for discretionary development in Medium and Active hazard bands. "
            "(2) The report must assess landslip risk, identify mitigation measures, and confirm the "
            "site is suitable for the proposed use. "
            "(3) Earthworks, vegetation removal, and changes to drainage that could destabilise slopes "
            "require assessment. "
            "(4) Buildings must be sited and designed to avoid or manage landslip risk. "
            "Check the applicable LPS for council-specific provisions that may supplement C15."
        ),
        source=SOURCE_LANDSLIP,
    ),

    # ── TasWater ──────────────────────────────────────────────────────────────
    _chunk(
        clause_ref="REF-TASWATER-SERVICED",
        heading="TasWater Serviced Land — Sewer and Water Supply",
        text=(
            "The theLIST Infrastructure service (TasWater Sewer Serviced Land / TasWater Water Serviced "
            "Land layers) shows whether a property falls within TasWater's reticulated sewer and water "
            "supply service areas. 'Full Service' means the property has access to both sewer and water "
            "connection. Being within the serviced land boundary does not guarantee immediate connection "
            "— a connection application to TasWater is required. Properties outside the serviced land "
            "boundary must use on-site wastewater management systems (septic/AWTS) and rainwater tanks "
            "or groundwater bores for water supply, subject to Environmental Health and council approval."
        ),
        source=SOURCE_TASWATER,
    ),
    _chunk(
        clause_ref="REF-TASWATER-SECONDARY-DWELLING",
        heading="TasWater — Secondary/Ancillary Dwelling Servicing Rule",
        text=(
            "Under Tasmanian planning provisions, an ancillary dwelling (granny flat) on a serviced lot "
            "cannot have a separate sewer or water connection from the primary dwelling — it must share "
            "the existing property connection. This means TasWater will not issue a separate meter or "
            "connection point for an ancillary dwelling on a lot that already has a reticulated "
            "connection. Implications: the ancillary dwelling relies on the primary dwelling's "
            "connection capacity; any upgrade to pipe size or meter must be coordinated with TasWater; "
            "on unserviced lots an ancillary dwelling requires its own compliant on-site wastewater "
            "system approved by the council's Environmental Health Officer. Confirm current TasWater "
            "policy directly with TasWater before finalising design."
        ),
        source=SOURCE_TASWATER,
    ),
    _chunk(
        clause_ref="REF-TASWATER-UNSERVICED",
        heading="TasWater — Unserviced Land: On-site Requirements",
        text=(
            "Where a property is outside TasWater's reticulated sewer or water supply service areas, "
            "development (including new dwellings, ancillary dwellings, and extensions that add "
            "habitable area) must demonstrate adequate on-site servicing. For wastewater: a compliant "
            "on-site wastewater management system (septic tank, aerated wastewater treatment system, "
            "or composting toilet) sized for the proposed dwelling must be designed to AS/NZS 1547 and "
            "approved by the council's Environmental Health Officer. For water: a rainwater collection "
            "system with adequate capacity or a tested bore/spring supply is required. Lot size and "
            "soil type affect system suitability — a site assessment by a licensed wastewater designer "
            "is recommended before lodging a planning application on unserviced land."
        ),
        source=SOURCE_TASWATER,
    ),
]


def build_chunks() -> list[dict]:
    return CHUNKS


def main():
    parser = argparse.ArgumentParser(description="Generate hazard reference KB chunks")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output JSON path")
    args = parser.parse_args()

    chunks = build_chunks()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(chunks)} chunks to {out}")


if __name__ == "__main__":
    main()
