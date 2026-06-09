"""
definitions_chunker.py — SPP definitions + exempt uses + NCC building classifications → KB chunks

Extracts from SPP PDF:
  - Table 3.1 Planning Terms and Definitions (pages 8-17)
  - Table 4.1/4.3 Exempt uses and exempt building works (pages 18-27)

Adds static NCC 2022 building classification chunks (Vol 2 not available).

Usage:
  python definitions_chunker.py --spp data/raw/spp-2024.pdf
"""

import re
import json
import argparse
import pdfplumber
from pathlib import Path

SPP_SOURCE = "TPS State Planning Provisions (effective 25 Dec 2024)"
NCC_SOURCE = "National Construction Code 2022 Volume Two"


def extract_spp_definitions(pdf_path: str) -> list[dict]:
    """Extract Table 3.1 definitions and Table 4.x exempt provisions from SPP."""
    chunks = []

    with pdfplumber.open(pdf_path) as pdf:
        # --- Definitions: pages 8-17 (0-indexed: 7-16) ---
        def_pages = []
        for page in pdf.pages[7:17]:
            t = page.extract_text()
            if t:
                def_pages.append(t)
        def_text = "\n".join(def_pages)

        # Split by letter groups (A-B, C-D, etc.) or just chunk whole section
        # Each ~2 pages = one chunk, by letter range
        # Chunk into groups of 2 pages (5 groups of ~2 pages each)
        pages_per_group = 2
        def_page_list = def_pages  # list of per-page strings
        group_idx = 1
        for i in range(0, len(def_page_list), pages_per_group):
            group_text = "\n".join(def_page_list[i:i + pages_per_group]).strip()
            if len(group_text) > 100:
                chunks.append(_def_chunk(group_idx, group_text))
                group_idx += 1

        # --- Exempt uses + works: pages 18-27 (0-indexed: 17-26) ---
        exempt_pages = []
        for page in pdf.pages[17:27]:
            t = page.extract_text()
            if t:
                exempt_pages.append(t)
        exempt_text = "\n".join(exempt_pages).strip()

        if len(exempt_text) > 100:
            chunks.append({
                "doc": "spp_exempt",
                "council": "statewide",
                "clause_ref": "SPP-EXEMPT",
                "parent_clause": "SPP-EXEMPT",
                "code_ref": "SPP-EXEMPT",
                "overlay_code": None,
                "clause_type": "exempt",
                "heading": "SPP Exempt Uses and Exempt Building Works",
                "text": exempt_text,
                "source": SPP_SOURCE,
            })

    return chunks


def _def_chunk(idx: int, text: str) -> dict:
    return {
        "doc": "spp_definitions",
        "council": "statewide",
        "clause_ref": f"SPP-DEFS-{idx}",
        "parent_clause": "SPP-DEFS",
        "code_ref": "SPP-DEFS",
        "overlay_code": None,
        "clause_type": "definition",
        "heading": f"SPP Planning Terms and Definitions (part {idx})",
        "text": text,
        "source": SPP_SOURCE,
    }


# NCC 2022 building classification definitions (Vol 2 — Class 1 and 10 buildings)
NCC_CLASSIFICATIONS = [
    {
        "ref": "NCC-A6-CLASS1A",
        "heading": "NCC Building Classification — Class 1a (single dwelling)",
        "text": (
            "NCC 2022 A6 Building Classification — Class 1a\n\n"
            "Class 1a: A single dwelling being a detached house; or one of a group of two or more "
            "attached dwellings, each being a building, separated by a fire-resisting wall, including "
            "a row house, terrace house, town house or villa unit.\n\n"
            "Class 1a is the most common residential building type. A typical single-storey or "
            "two-storey detached house on a residential lot is Class 1a. Townhouses and villas "
            "where each unit is separated by a wall are also Class 1a.\n\n"
            "Relevance to TPS planning: A new Class 1a dwelling in the General Residential Zone "
            "(Z8) requires assessment against use and development standards. A single dwelling is "
            "typically a permitted use in residential zones."
        ),
    },
    {
        "ref": "NCC-A6-CLASS1B",
        "heading": "NCC Building Classification — Class 1b (secondary/ancillary dwelling, boarding house)",
        "text": (
            "NCC 2022 A6 Building Classification — Class 1b\n\n"
            "Class 1b: A boarding house, guest house, hostel, or the like with a total area of "
            "all floors not more than 300m² and ordinarily with not more than 12 residents; OR "
            "4 or more single dwellings located on one allotment and used for short-term holiday "
            "accommodation.\n\n"
            "In Tasmanian planning practice, a secondary dwelling (granny flat / ancillary dwelling) "
            "that is self-contained and attached or detached from the main house may be treated as "
            "Class 1b for building permit purposes, depending on configuration. An ancillary "
            "dwelling is a self-contained dwelling located on the same lot as a single dwelling "
            "and subservient to it in scale and use.\n\n"
            "Relevance to TPS planning: Ancillary dwellings (granny flats) in General Residential "
            "Zone are typically discretionary. Check LPS for local area objectives."
        ),
    },
    {
        "ref": "NCC-A6-CLASS2",
        "heading": "NCC Building Classification — Class 2 (apartment building)",
        "text": (
            "NCC 2022 A6 Building Classification — Class 2\n\n"
            "Class 2: A building containing 2 or more sole-occupancy units each being a separate "
            "dwelling. This includes apartment buildings, flats, and units where each dwelling is "
            "a sole-occupancy unit sharing a common structure.\n\n"
            "Class 2 buildings are subject to Volume One of the NCC (not Volume Two). They require "
            "fire-resistance provisions, inter-tenancy separation, and additional compliance.\n\n"
            "Relevance to TPS planning: Multiple dwellings (apartments) in General Residential Zone "
            "require site area of at least 325m² per dwelling [Z8.4.1 — SPP 2024]. In Inner "
            "Residential Zone, higher density applies. Always discretionary unless zone specifically "
            "permits multiple dwellings."
        ),
    },
    {
        "ref": "NCC-A6-CLASS10A",
        "heading": "NCC Building Classification — Class 10a (shed, garage, carport)",
        "text": (
            "NCC 2022 A6 Building Classification — Class 10a\n\n"
            "Class 10a: A non-habitable building being a private garage, carport, shed or "
            "similar structure.\n\n"
            "Class 10a buildings are non-habitable structures. They include: detached garages, "
            "carports, garden sheds, farm sheds (when not used by workers), boat sheds, greenhouses, "
            "and similar structures. They cannot be used for sleeping, cooking, or living purposes.\n\n"
            "Relevance to TPS planning: In most Tasmanian residential zones, Class 10a outbuildings "
            "are permitted or exempt from a planning permit if they meet the exempt building works "
            "criteria in Table 4.3 of the SPP [SPP-EXEMPT — SPP 2024]. A shed or carport under "
            "the threshold area/height is typically exempt."
        ),
    },
    {
        "ref": "NCC-A6-CLASS10B",
        "heading": "NCC Building Classification — Class 10b (fence, retaining wall, swimming pool, antenna)",
        "text": (
            "NCC 2022 A6 Building Classification — Class 10b\n\n"
            "Class 10b: A structure being a fence, mast, antenna, retaining or free-standing wall, "
            "swimming pool, or the like.\n\n"
            "Class 10b structures are not buildings but are structures that may still require "
            "planning approval depending on height, location, or zone.\n\n"
            "Relevance to TPS planning: Fences in residential zones have exempt provisions in "
            "Table 4.3 of the SPP. A front fence not exceeding 1.2m generally requires no permit "
            "[SPP-EXEMPT — SPP 2024]. Swimming pools may require a building permit but are "
            "typically exempt from planning permits in residential zones if not in a sensitive "
            "overlay area."
        ),
    },
]


def ncc_classification_chunks() -> list[dict]:
    chunks = []
    for item in NCC_CLASSIFICATIONS:
        chunks.append({
            "doc": "ncc",
            "council": "statewide",
            "clause_ref": item["ref"],
            "parent_clause": "NCC-A6",
            "code_ref": "NCC-A6",
            "overlay_code": None,
            "clause_type": "definition",
            "heading": item["heading"],
            "text": item["text"],
            "source": NCC_SOURCE,
        })
    return chunks


def run(spp_path: str, output_path: str) -> list[dict]:
    print("Extracting SPP definitions and exempt provisions...")
    spp_chunks = extract_spp_definitions(spp_path)
    print(f"  SPP definition/exempt chunks: {len(spp_chunks)}")

    print("Adding NCC building classification chunks...")
    ncc_chunks = ncc_classification_chunks()
    print(f"  NCC chunks: {len(ncc_chunks)}")

    all_chunks = spp_chunks + ncc_chunks
    print(f"  Total: {len(all_chunks)}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"Written: {output_path}")
    return all_chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--spp",    default="data/raw/spp-2024.pdf")
    parser.add_argument("--output", default="data/chunks/definitions-chunks.json")
    args = parser.parse_args()
    run(args.spp, args.output)
