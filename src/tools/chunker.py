"""
chunker.py — PDF → clause chunks → JSON

Handles:
  - TPS State Planning Provisions (SPP): clause pattern C12.5.1
  - Hobart LPS: clause pattern HOB-C6.2.1

Output: list of chunk dicts ready for embedding + upload to Supabase pgvector.
"""

import re
import json
import argparse
import pdfplumber
from pathlib import Path

# --- Clause boundary patterns ---

SPP_CLAUSE = re.compile(r'^(C\d+\.\d+(?:\.\d+)?)\s+(.+)', re.MULTILINE)
LPS_CLAUSE = re.compile(r'^(HOB-[A-Z]\d+(?:\.\d+){1,3})\s+(.+)', re.MULTILINE)

# Map SPP top-level code refs to overlay names
SPP_CODE_MAP = {
    "C6":  "Local Historic Heritage Code",
    "C7":  "Natural Assets Code",
    "C10": "Coastal Erosion Hazard Code",
    "C11": "Coastal Inundation Hazard Code",
    "C12": "Flood-Prone Areas Hazard Code",
    "C13": "Bushfire-Prone Areas Code",
    "C15": "Landslip Hazard Code",
}

CLAUSE_TYPE_HINTS = {
    "purpose":       ["purpose", "objective"],
    "application":   ["application of this code", "applies to"],
    "exempt":        ["exempt", "exemption"],
    "use_standard":  ["use standard", "use or development standard"],
    "dev_standard":  ["development standard"],
    "definition":    ["definition", "means "],
    "general":       [],
}


def _detect_clause_type(heading: str) -> str:
    h = heading.lower()
    for ctype, hints in CLAUSE_TYPE_HINTS.items():
        if any(hint in h for hint in hints):
            return ctype
    return "general"


def _top_code(clause_ref: str) -> str:
    """C12.5.1 → C12"""
    parts = clause_ref.split(".")
    return parts[0]


def extract_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n".join(pages)


def chunk_spp(text: str, target_codes: list[str] | None = None) -> list[dict]:
    """
    Chunk SPP by clause. Optionally filter to specific top-level codes.
    target_codes: e.g. ["C12", "C15"] to only extract flood + landslip
    """
    chunks = []
    matches = list(SPP_CLAUSE.finditer(text))

    for i, match in enumerate(matches):
        clause_ref = match.group(1)
        heading = match.group(2).strip()
        top = _top_code(clause_ref)

        if target_codes and top not in target_codes:
            continue

        # Text = from this match to next match
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()

        # Skip very short chunks (page headers, noise)
        if len(chunk_text) < 80:
            continue

        overlay_code = SPP_CODE_MAP.get(top)

        chunks.append({
            "doc": "spp",
            "council": "statewide",
            "clause_ref": clause_ref,
            "parent_clause": ".".join(clause_ref.split(".")[:2]),
            "code_ref": top,
            "overlay_code": overlay_code,
            "clause_type": _detect_clause_type(heading),
            "heading": heading,
            "text": chunk_text,
            "source": "TPS State Planning Provisions (effective 25 Dec 2024)",
        })

    return chunks


def chunk_lps(text: str) -> list[dict]:
    """Chunk Hobart LPS by HOB-Cx.x.x clause boundaries."""
    chunks = []
    matches = list(LPS_CLAUSE.finditer(text))

    for i, match in enumerate(matches):
        clause_ref = match.group(1)
        heading = match.group(2).strip()

        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()

        if len(chunk_text) < 80:
            continue

        chunks.append({
            "doc": "lps",
            "council": "Hobart",
            "clause_ref": clause_ref,
            "parent_clause": ".".join(clause_ref.split(".")[:2]) if "." in clause_ref else clause_ref,
            "code_ref": clause_ref.split(".")[0],
            "overlay_code": None,
            "clause_type": _detect_clause_type(heading),
            "heading": heading,
            "text": chunk_text,
            "source": "Hobart Local Provisions Schedule (effective 22 Oct 2025)",
        })

    return chunks


def run(spp_path: str, lps_path: str, output_path: str, spp_codes: list[str] | None = None):
    print("Extracting SPP text...")
    spp_text = extract_text(spp_path)
    spp_chunks = chunk_spp(spp_text, target_codes=spp_codes)
    print(f"  SPP chunks: {len(spp_chunks)}")

    print("Extracting LPS text...")
    lps_text = extract_text(lps_path)
    lps_chunks = chunk_lps(lps_text)
    print(f"  LPS chunks: {len(lps_chunks)}")

    all_chunks = spp_chunks + lps_chunks
    print(f"  Total chunks: {len(all_chunks)}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"Written: {output_path}")
    return all_chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--spp",    default="data/raw/spp-2024.pdf")
    parser.add_argument("--lps",    default="data/raw/hobart-lps-2025.pdf")
    parser.add_argument("--output", default="data/chunks/hobart-chunks.json")
    parser.add_argument("--codes",  nargs="*", default=["C6", "C10", "C11", "C12", "C13", "C15"],
                        help="SPP top-level codes to extract (default: all overlay codes)")
    args = parser.parse_args()

    run(args.spp, args.lps, args.output, spp_codes=args.codes)
