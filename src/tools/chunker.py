"""
chunker.py — PDF → clause chunks → JSON

Handles:
  - TPS State Planning Provisions (SPP): clause pattern C12.5.1
  - Any council LPS:  clause pattern PREFIX-C6.2.1  (HOB-, GCC-, CLA-, LAU-, KIN-, …)

Usage:
  python chunker.py --council hobart  --lps data/raw/hobart-lps-2025.pdf
  python chunker.py --council kingborough --lps data/raw/kingborough-draft-lps-2024.pdf
  python chunker.py --spp-only   # just re-chunk SPP
"""

import re
import json
import argparse
import pdfplumber
from pathlib import Path

# --- Council config ---------------------------------------------------------

COUNCIL_CONFIG = {
    "hobart": {
        "prefix":   "HOB",
        "name":     "Hobart",
        "source":   "Hobart Local Provisions Schedule (effective 22 Oct 2025)",
    },
    "glenorchy": {
        "prefix":   "GLE",
        "name":     "Glenorchy",
        "source":   "Glenorchy Local Provisions Schedule (effective 26 Mar 2024)",
    },
    "clarence": {
        "prefix":   "CLA",
        "name":     "Clarence",
        "source":   "Clarence Local Provisions Schedule (effective 25 Jul 2024)",
    },
    "launceston": {
        "prefix":   "LAU",
        "name":     "Launceston",
        "source":   "Launceston Local Provisions Schedule (effective 31 May 2024)",
    },
    "kingborough": {
        "prefix":   "KIN",
        "name":     "Kingborough",
        "source":   "Kingborough Draft Local Provisions Schedule (2024)",
    },
}

# --- Clause patterns --------------------------------------------------------

SPP_CLAUSE = re.compile(r'^(C\d+\.\d+(?:\.\d+)?)\s+(.+)', re.MULTILINE)
SPP_ZONE_CLAUSE = re.compile(r'^(\d+\.\d+(?:\.\d+)?)\s+(.+)', re.MULTILINE)

# SPP top-level code → overlay name
SPP_CODE_MAP = {
    "C6":  "Local Historic Heritage Code",
    "C7":  "Natural Assets Code",
    "C10": "Coastal Erosion Hazard Code",
    "C11": "Coastal Inundation Hazard Code",
    "C12": "Flood-Prone Areas Hazard Code",
    "C13": "Bushfire-Prone Areas Code",
    "C15": "Landslip Hazard Code",
}

# SPP zone number → zone name (from TPS ToC)
SPP_ZONE_MAP = {
    "8":  "General Residential Zone",
    "9":  "Inner Residential Zone",
    "10": "Low Density Residential Zone",
    "11": "Rural Living Zone",
    "12": "Village Zone",
    "13": "Urban Mixed Use Zone",
    "14": "Local Business Zone",
    "15": "General Business Zone",
    "16": "Central Business Zone",
    "17": "Commercial Zone",
    "18": "Light Industrial Zone",
    "19": "General Industrial Zone",
    "20": "Rural Zone",
    "21": "Agriculture Zone",
    "22": "Landscape Conservation Zone",
    "23": "Environmental Management Zone",
    "24": "Major Tourism Zone",
}

CLAUSE_TYPE_HINTS = {
    "purpose":      ["purpose", "objective"],
    "application":  ["application of this code", "applies to"],
    "exempt":       ["exempt", "exemption"],
    "use_standard": ["use standard", "use or development standard"],
    "dev_standard": ["development standard"],
    "definition":   ["definition", "means "],
    "general":      [],
}


def _detect_clause_type(heading: str) -> str:
    h = heading.lower()
    for ctype, hints in CLAUSE_TYPE_HINTS.items():
        if any(hint in h for hint in hints):
            return ctype
    return "general"


def _top_code(clause_ref: str) -> str:
    """C12.5.1 → C12"""
    return clause_ref.split(".")[0]


def extract_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n".join(pages)


def chunk_spp(text: str, target_codes: list[str] | None = None) -> list[dict]:
    chunks = []
    matches = list(SPP_CLAUSE.finditer(text))

    for i, match in enumerate(matches):
        clause_ref = match.group(1)
        heading = match.group(2).strip()
        top = _top_code(clause_ref)

        if target_codes and top not in target_codes:
            continue

        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()

        if len(chunk_text) < 80:
            continue

        chunks.append({
            "doc":           "spp",
            "council":       "statewide",
            "clause_ref":    clause_ref,
            "parent_clause": ".".join(clause_ref.split(".")[:2]),
            "code_ref":      top,
            "overlay_code":  SPP_CODE_MAP.get(top),
            "clause_type":   _detect_clause_type(heading),
            "heading":       heading,
            "text":          chunk_text,
            "source":        "TPS State Planning Provisions (effective 25 Dec 2024)",
        })

    return chunks


def chunk_spp_zones(text: str, target_zones: list[str] | None = None) -> list[dict]:
    """
    Chunk SPP zone sections by numeric clause pattern (8.4.1, 9.4.2, …).
    target_zones: list of zone numbers e.g. ["8","9","10"] — omit for all.
    """
    chunks = []
    matches = list(SPP_ZONE_CLAUSE.finditer(text))

    for i, match in enumerate(matches):
        clause_ref = match.group(1)
        heading = match.group(2).strip()
        zone_num = clause_ref.split(".")[0]

        if zone_num not in SPP_ZONE_MAP:
            continue
        if target_zones and zone_num not in target_zones:
            continue

        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()

        if len(chunk_text) < 80:
            continue

        zone_name = SPP_ZONE_MAP[zone_num]

        chunks.append({
            "doc":           "spp_zone",
            "council":       "statewide",
            "clause_ref":    f"Z{clause_ref}",   # prefix Z to avoid collision with LPS numbers
            "parent_clause": f"Z{zone_num}.{clause_ref.split('.')[1]}",
            "code_ref":      f"Z{zone_num}",
            "overlay_code":  None,
            "zone_name":     zone_name,
            "clause_type":   _detect_clause_type(heading),
            "heading":       heading,
            "text":          chunk_text,
            "source":        "TPS State Planning Provisions (effective 25 Dec 2024)",
        })

    return chunks


def chunk_lps(text: str, prefix: str, council_name: str, source: str) -> list[dict]:
    """Chunk any council LPS by PREFIX-Cx.x.x clause boundaries."""
    pattern = re.compile(
        rf'^({re.escape(prefix)}-[A-Z]\d+(?:\.\d+){{0,3}})\s+(.+)',
        re.MULTILINE,
    )
    chunks = []
    matches = list(pattern.finditer(text))

    for i, match in enumerate(matches):
        clause_ref = match.group(1)
        heading = match.group(2).strip()

        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()

        if len(chunk_text) < 80:
            continue

        chunks.append({
            "doc":           "lps",
            "council":       council_name,
            "clause_ref":    clause_ref,
            "parent_clause": ".".join(clause_ref.split(".")[:2]) if "." in clause_ref else clause_ref,
            "code_ref":      clause_ref.split(".")[0],
            "overlay_code":  None,
            "clause_type":   _detect_clause_type(heading),
            "heading":       heading,
            "text":          chunk_text,
            "source":        source,
        })

    return chunks


def run(
    lps_path: str,
    council: str,
    output_path: str,
    spp_path: str | None = None,
    spp_codes: list[str] | None = None,
    spp_zones: list[str] | None = None,
) -> list[dict]:
    config = COUNCIL_CONFIG[council]
    all_chunks: list[dict] = []

    if spp_path:
        print("Extracting SPP text...")
        spp_text = extract_text(spp_path)
        spp_chunks = chunk_spp(spp_text, target_codes=spp_codes)
        print(f"  SPP overlay chunks: {len(spp_chunks)}")
        all_chunks += spp_chunks

        zone_chunks = chunk_spp_zones(spp_text, target_zones=spp_zones)
        print(f"  SPP zone chunks: {len(zone_chunks)}")
        all_chunks += zone_chunks

    print(f"Extracting {config['name']} LPS text...")
    lps_text = extract_text(lps_path)
    lps_chunks = chunk_lps(lps_text, config["prefix"], config["name"], config["source"])
    print(f"  LPS chunks: {len(lps_chunks)}")
    all_chunks += lps_chunks

    print(f"  Total: {len(all_chunks)}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"Written: {output_path}")
    return all_chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--council",
        required=True,
        choices=list(COUNCIL_CONFIG.keys()),
        help="Which council LPS to chunk",
    )
    parser.add_argument("--lps",    required=True, help="Path to council LPS PDF")
    parser.add_argument("--spp",    default=None,  help="Path to SPP PDF (omit to skip SPP)")
    parser.add_argument("--output", default=None,  help="Output JSON path (default: data/chunks/<council>-chunks.json)")
    parser.add_argument(
        "--codes",
        nargs="*",
        default=["C6", "C10", "C11", "C12", "C13", "C15"],
        help="SPP overlay codes to extract",
    )
    parser.add_argument(
        "--zones",
        nargs="*",
        default=list(SPP_ZONE_MAP.keys()),
        help="SPP zone numbers to extract (default: all zones)",
    )
    args = parser.parse_args()

    output = args.output or f"data/chunks/{args.council}-chunks.json"
    run(args.lps, args.council, output, spp_path=args.spp, spp_codes=args.codes, spp_zones=args.zones)
