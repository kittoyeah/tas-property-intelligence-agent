"""
spp_provisions_chunker.py — SPP Sections 4, 6, 7 → granular KB chunks

Extracts from spp-2024.pdf:
  - Section 4: Individual exempt use/works entries (4.1.x, 4.3.x, 4.4.x, 4.5.x, 4.6.x)
  - Section 6: Use class descriptions (Table 6.2) + permit pathway rules (6.6–6.9)
  - Section 7: General provisions (change of use, heritage, temporary housing)

Replaces the single SPP-EXEMPT blob with granular retrievable chunks.

Usage:
  python -m src.tools.spp_provisions_chunker --spp data/raw/spp-2024.pdf
"""

import re
import json
import argparse
import pdfplumber
from pathlib import Path

SPP_SOURCE = "TPS State Planning Provisions (effective 25 Dec 2024)"

# Page ranges (0-indexed)
SECTION_4_PAGES = (17, 27)   # p18–27: exemptions
SECTION_6_PAGES = (32, 38)   # p33–38: use classes + permit rules
SECTION_7_PAGES = (38, 47)   # p39–47: general provisions


def _extract_pages(pdf, start: int, end: int) -> str:
    parts = []
    for page in pdf.pages[start:end]:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n".join(parts)


def _base_chunk(doc: str, clause_ref: str, heading: str, text: str, clause_type: str = "exempt") -> dict:
    return {
        "doc": doc,
        "council": "statewide",
        "clause_ref": clause_ref,
        "parent_clause": clause_ref.rsplit(".", 1)[0] if "." in clause_ref else clause_ref,
        "code_ref": clause_ref.split(".")[0],
        "overlay_code": None,
        "clause_type": clause_type,
        "heading": heading,
        "text": text.strip(),
        "source": SPP_SOURCE,
    }


# ── Section 4: Exempt entries ──────────────────────────────────────────────

_EXEMPT_ENTRY = re.compile(r'^(4\.\d+\.\d+)\s+(.+)', re.MULTILINE)


def chunk_section4(pdf) -> list[dict]:
    text = _extract_pages(pdf, *SECTION_4_PAGES)
    chunks = []
    matches = list(_EXEMPT_ENTRY.finditer(text))

    for i, m in enumerate(matches):
        clause_ref = m.group(1)
        heading = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        if len(body) < 40:
            continue

        chunks.append(_base_chunk("spp_exempt", f"SPP-{clause_ref}", heading, body, "exempt"))

    return chunks


# ── Section 6: Use classes + permit pathway rules ─────────────────────────

# Use class names in Table 6.2 (start of a line, followed by "use of land")
_USE_CLASS = re.compile(
    r'^(Bulky Goods Sales|Business and\nProfessional\nServices|Business and Professional Services|'
    r'Community Meeting\nand Entertainment|Community Meeting and Entertainment|'
    r'Crematoria and\nCemeteries|Crematoria and Cemeteries|'
    r'Custodial Facility|Domestic Animal\nBreeding, Boarding\nor Training|Domestic Animal Breeding, Boarding or Training|'
    r'Educational and\nOccasional Care|Educational and Occasional Care|Emergency Services|'
    r'Equipment and\nMachinery Sales\nand Hire|Equipment and Machinery Sales and Hire|'
    r'Extractive Industry|Food Services|General Retail and\nHire|General Retail and Hire|'
    r'Hospital Services|Hotel Industry|Manufacturing and\nProcessing|Manufacturing and Processing|'
    r'Motor Racing\nFacility|Motor Racing Facility|Natural and Cultural\nValues Management|Natural and Cultural Values Management|'
    r'Passive Recreation|Pleasure Boat\nFacility|Pleasure Boat Facility|Port and Shipping|'
    r'Recycling and\nWaste Disposal|Recycling and Waste Disposal|Research and\nDevelopment|Research and Development|'
    r'Residential|Resource\nDevelopment|Resource Development|Resource\nProcessing|Resource Processing|'
    r'Service Industry|Sports and\nRecreation|Sports and Recreation|Storage|Tourist Operation|'
    r'Transport Depot and\nDistribution|Transport Depot and Distribution|Utilities|'
    r'Vehicle Fuel Sales\nand Service|Vehicle Fuel Sales and Service|Vehicle Parking|'
    r'Visitor\nAccommodation|Visitor Accommodation)',
    re.MULTILINE,
)

# Simpler: chunk whole Table 6.2 as one doc + 6.6-6.9 rules as individual docs
_CLAUSE_6X = re.compile(r'^(6\.\d+(?:\.\d+)?)\s+(.+)', re.MULTILINE)


def chunk_section6(pdf) -> list[dict]:
    text = _extract_pages(pdf, *SECTION_6_PAGES)
    chunks = []

    # 1. Table 6.2 — one chunk covering all use class descriptions
    table_start = text.find("Table 6.2 Use Classes")
    table_end = text.find("6.3 Qualification")
    if table_start != -1 and table_end != -1:
        table_text = text[table_start:table_end].strip()
        chunks.append(_base_chunk(
            "spp_provisions", "SPP-6.2",
            "SPP Table 6.2 Use Classes — all use class descriptions",
            table_text, "definition",
        ))

    # 2. Individual 6.x clauses (6.6 NPR, 6.7 Permitted, 6.8 Discretionary, 6.9 Prohibited etc.)
    matches = list(_CLAUSE_6X.finditer(text))
    for i, m in enumerate(matches):
        clause_ref = f"SPP-{m.group(1)}"
        heading = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        if len(body) < 60:
            continue

        chunks.append(_base_chunk(
            "spp_provisions", clause_ref, heading, body,
            "use_standard" if m.group(1).startswith("6.") else "general",
        ))

    return chunks


# ── Section 7: General provisions ─────────────────────────────────────────

_CLAUSE_7X = re.compile(r'^(7\.\d+(?:\.\d+)?)\s+(.+)', re.MULTILINE)


def chunk_section7(pdf) -> list[dict]:
    text = _extract_pages(pdf, *SECTION_7_PAGES)
    chunks = []
    matches = list(_CLAUSE_7X.finditer(text))

    for i, m in enumerate(matches):
        clause_ref = f"SPP-{m.group(1)}"
        heading = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        if len(body) < 60:
            continue

        chunks.append(_base_chunk("spp_provisions", clause_ref, heading, body, "general"))

    return chunks


# ── Runner ─────────────────────────────────────────────────────────────────

def run(spp_path: str, output_path: str) -> list[dict]:
    chunks = []
    with pdfplumber.open(spp_path) as pdf:
        s4 = chunk_section4(pdf)
        print(f"  Section 4 exempt entries: {len(s4)}")
        chunks += s4

        s6 = chunk_section6(pdf)
        print(f"  Section 6 use classes + permit rules: {len(s6)}")
        chunks += s6

        s7 = chunk_section7(pdf)
        print(f"  Section 7 general provisions: {len(s7)}")
        chunks += s7

    print(f"  Total: {len(chunks)}")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"Written: {output_path}")
    return chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--spp", default="data/raw/spp-2024.pdf")
    parser.add_argument("--output", default="data/chunks/spp-provisions-chunks.json")
    args = parser.parse_args()
    run(args.spp, args.output)
