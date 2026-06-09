"""
fee_chunker.py — Council fee schedule PDF → KB chunks

Extracts planning, building, and plumbing fee sections as searchable text.
One chunk per section per council.

Usage:
  python fee_chunker.py --council hobart --fees data/raw/hobart-fees-2025-26.pdf
  python fee_chunker.py --council kingborough --fees data/raw/kingborough-fees-2025-26.pdf
"""

import re
import json
import argparse
import pdfplumber
from pathlib import Path

COUNCIL_CONFIG = {
    "hobart": {
        "name":   "Hobart",
        "source": "Hobart Fees and Charges 2025-26",
        "prefix": "HOB",
    },
    "glenorchy": {
        "name":   "Glenorchy",
        "source": "Glenorchy City Council Fees and Charges 2025-26",
        "prefix": "GLE",
    },
    "clarence": {
        "name":   "Clarence",
        "source": "Clarence City Council Fees and Charges 2025-26",
        "prefix": "CLA",
    },
    "launceston": {
        "name":   "Launceston",
        "source": "City of Launceston Fees and Charges 2025-26",
        "prefix": "LAU",
    },
    "kingborough": {
        "name":   "Kingborough",
        "source": "Kingborough Council Fees and Charges 2025-26",
        "prefix": "KIN",
    },
}

# Keywords that mark a relevant fee section
FEE_SECTIONS = {
    "planning":  ["planning", "development application", "permit", "subdivision", "heritage"],
    "building":  ["building fee", "building permit", "building surveying", "certificate of completion"],
    "plumbing":  ["plumbing"],
}


def extract_pages(pdf_path: str) -> list[str]:
    with pdfplumber.open(pdf_path) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text()
            pages.append(text or "")
    return pages


def extract_fee_sections(
    pages: list[str], council_name: str, council_prefix: str, source: str
) -> list[dict]:
    """Group pages by fee category and create one chunk per category."""
    buckets: dict[str, list[str]] = {k: [] for k in FEE_SECTIONS}

    for page_text in pages:
        lower = page_text.lower()
        for category, keywords in FEE_SECTIONS.items():
            if any(kw in lower for kw in keywords):
                buckets[category].append(page_text)

    chunks = []
    for category, page_texts in buckets.items():
        if not page_texts:
            continue
        combined = "\n\n".join(page_texts).strip()
        if len(combined) < 100:
            continue

        clause_ref = f"{council_prefix}-FEES-{category.upper()}"
        heading = f"{council_name} {category.title()} Fees 2025-26"

        chunks.append({
            "doc":           "fees",
            "council":       council_name,
            "clause_ref":    clause_ref,
            "parent_clause": f"{council_prefix}-FEES",
            "code_ref":      f"{council_prefix}-FEES",
            "overlay_code":  None,
            "clause_type":   "fees",
            "heading":       heading,
            "text":          combined,
            "source":        source,
        })

    return chunks


def run(fees_path: str, council: str, output_path: str) -> list[dict]:
    config = COUNCIL_CONFIG[council]

    print(f"Extracting {config['name']} fee schedule text...")
    pages = extract_pages(fees_path)

    chunks = extract_fee_sections(pages, config["name"], config["prefix"], config["source"])
    print(f"  Fee chunks: {len(chunks)}")

    if not chunks:
        print("  Warning: no relevant fee sections found.")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"Written: {output_path}")
    return chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--council", required=True, choices=list(COUNCIL_CONFIG.keys()))
    parser.add_argument("--fees",    required=True, help="Path to fee schedule PDF")
    parser.add_argument("--output",  default=None)
    args = parser.parse_args()

    output = args.output or f"data/chunks/{args.council}-fees-chunks.json"
    run(args.fees, args.council, output)
