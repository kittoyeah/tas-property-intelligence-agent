"""
eval_golden.py — Accuracy regression guard for CanIBuild.

Golden address: 1 De Witt Street Battery Point
  PID:  5573887
  lat:  -42.89008 (approx; theLIST returns -42.890075)
  lng:  147.33224 (approx; theLIST returns 147.332239)

Run:
    source .venv/bin/activate
    python tests/eval_golden.py

Prints PASS/FAIL per assertion + overall result. Exit 0 on all-pass, 1 on any fail.
"""

import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.thelist import query_overlays
from src.tools.geocoder import suggest_addresses

GOLD_ADDRESS = "1 De Witt Street Battery Point"
GOLD_PID = 5573887
GOLD_LAT = -42.890075
GOLD_LNG = 147.332239

results: list[tuple[str, bool, str]] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    results.append((label, condition, detail))
    icon = "✓" if condition else "✗"
    print(f"  [{status}] {icon}  {label}{(' — ' + detail) if detail else ''}")


# ── Test 1: suggest_addresses returns the gold address ──────────────────────
print("\n=== /suggest (layer 7 autocomplete) ===")
suggestions = suggest_addresses("1 de witt battery")
check("suggest returns >= 1 result", len(suggestions) > 0, f"got {len(suggestions)}")
if suggestions:
    addresses = [s["address"] for s in suggestions]
    gold_in_list = any("1 DE WITT STREET BATTERY POINT" in a.upper() for a in addresses)
    check(
        "gold address '1 DE WITT STREET BATTERY POINT' in suggestions",
        gold_in_list,
        str(addresses),
    )
    gold_match = next(
        (s for s in suggestions if "1 DE WITT STREET BATTERY POINT" in s["address"].upper()), None
    )
    if gold_match:
        check(
            f"PID == {GOLD_PID}",
            gold_match["pid"] == GOLD_PID,
            f"got {gold_match['pid']}",
        )
        check(
            "lat within 0.001° of gold",
            abs(gold_match["lat"] - GOLD_LAT) < 0.001,
            f"got {gold_match['lat']:.6f}, expected ~{GOLD_LAT}",
        )
        check(
            "lng within 0.001° of gold",
            abs(gold_match["lng"] - GOLD_LNG) < 0.001,
            f"got {gold_match['lng']:.6f}, expected ~{GOLD_LNG}",
        )


# ── Test 2: query_overlays with PID returns correct spatial data ─────────────
print("\n=== query_overlays(lat, lng, pid=5573887) ===")
try:
    overlays = query_overlays(GOLD_LAT, GOLD_LNG, pid=GOLD_PID)

    # Council
    council_name = (overlays.get("council") or {}).get("name", "")
    check("council == Hobart", "hobart" in council_name.lower(), f"got '{council_name}'")

    # Zone
    zone = overlays.get("zone") or {}
    zone_name = zone.get("zone", "")
    check(
        "zone == Inner Residential",
        "inner residential" in zone_name.lower(),
        f"got '{zone_name}'",
    )

    # Lot area ~333 m² (±10%)
    lot_area = overlays.get("lot_area_sqm")
    LOT_EXPECTED = 333
    LOT_TOLERANCE = 0.10
    if lot_area is not None:
        within = abs(lot_area - LOT_EXPECTED) / LOT_EXPECTED <= LOT_TOLERANCE
        check(
            f"lot_area ≈ {LOT_EXPECTED} m² (±10%)",
            within,
            f"got {lot_area} m²",
        )
    else:
        check("lot_area not None", False, "got None")

    # Overlays — Local Historic Heritage Code C6 and Battery Point SAP HOB-S7
    ov_list = overlays.get("overlays", [])
    ov_codes = " ".join(
        (o.get("code") or "") + " " + (o.get("lps_ref") or "") + " " + (o.get("ov_name") or "")
        for o in ov_list
    ).upper()
    check(
        "C6 Local Historic Heritage overlay present",
        "C6" in ov_codes or "HERITAGE" in ov_codes,
        f"overlay refs: {[o.get('code') for o in ov_list]}",
    )
    check(
        "Battery Point SAP (HOB-S7 or SAP) present",
        "HOB-S7" in ov_codes or "S7" in ov_codes or "SPECIFIC AREA" in ov_codes or "BATTERY POINT" in ov_codes,
        f"overlay refs: {[o.get('lps_ref') for o in ov_list]}",
    )

    # TasWater — Full Service (sewer + water)
    taswater = overlays.get("taswater") or {}
    sewer_ok = taswater.get("sewer_status") is not None and "full" in str(taswater.get("sewer_status")).lower()
    water_ok = taswater.get("water_status") is not None and "full" in str(taswater.get("water_status")).lower()
    check(
        "taswater sewer Full Service",
        sewer_ok,
        f"got '{taswater.get('sewer_status')}'",
    )
    check(
        "taswater water Full Service",
        water_ok,
        f"got '{taswater.get('water_status')}'",
    )

    # Heritage register — state listed + Permanently Registered
    heritage = overlays.get("heritage_register") or {}
    check("heritage_register state_listed True", heritage.get("state_listed") is True, str(heritage))
    check(
        "heritage status 'Permanently Registered'",
        "permanently" in str(heritage.get("status") or "").lower(),
        f"got '{heritage.get('status')}'",
    )

    # Existing coverage ~34% (±5 pp absolute)
    coverage = overlays.get("existing_coverage") or {}
    cov_pct = coverage.get("coverage_pct")
    if cov_pct is not None:
        check(
            "existing_coverage ≈ 34% (±5pp)",
            abs(cov_pct - 34) <= 5,
            f"got {cov_pct}%",
        )
    else:
        check("existing_coverage not None", False, "got None")

    # Flood — not in flood area
    flood = overlays.get("flood") or {}
    check(
        "flood in_flood_area False",
        flood.get("in_flood_area") is False,
        str(flood),
    )

    # Landslip — no band
    landslip = overlays.get("landslip") or {}
    check(
        "landslip in_landslip_band False",
        landslip.get("in_landslip_band") is False,
        str(landslip),
    )

except Exception as exc:
    check("query_overlays raised no exception", False, str(exc))


# ── Test 3: Nominatim is gone ────────────────────────────────────────────────
print("\n=== Nominatim purge check ===")
import subprocess
grep = subprocess.run(
    ["grep", "-ri", "--include=*.py", "nominatim", "src/"],
    capture_output=True, text=True,
    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
check(
    "no Nominatim references in src/ *.py files",
    grep.returncode != 0 or grep.stdout.strip() == "",
    grep.stdout.strip() or "clean",
)


# ── Summary ──────────────────────────────────────────────────────────────────
print()
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
all_pass = passed == total
print("=" * 50)
print(f"  {'PASS' if all_pass else 'FAIL'}  {passed}/{total} assertions passed")
print("=" * 50)
sys.exit(0 if all_pass else 1)
