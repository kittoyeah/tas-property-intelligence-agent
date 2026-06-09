"""
geocoder.py — theLIST Address Geocodes (layer 7) authoritative address resolution.

Exports:
  suggest_addresses(q) -> list[dict]   # autocomplete: partial query -> candidates
  geocode_address(address) -> dict     # compat: best single match for full address string
  AddressNotFoundError
  OutsideTasmaniaError
"""

import requests

SEARCH_BASE_URL = (
    "https://services.thelist.tas.gov.au/arcgis/rest/services"
    "/Public/SearchService/MapServer/7/query"
)


class AddressNotFoundError(Exception):
    pass


class OutsideTasmaniaError(Exception):
    pass


def _build_where(q: str) -> str:
    """
    Build a LIKE WHERE clause from user query tokens.

    Each whitespace-delimited token becomes a wildcard segment:
      "1 de witt battery" -> UPPER(ADDRESS) LIKE '%1%DE%WITT%BATTERY%'

    Single quotes in user input are doubled to escape them.
    """
    safe_q = q.replace("'", "''")
    tokens = safe_q.upper().split()
    pattern = "%".join(tokens)
    return f"UPPER(ADDRESS) LIKE '%{pattern}%'"


def _query_layer7(where: str, record_count: int = 8) -> list[dict]:
    """
    Query theLIST Address Geocodes layer 7.

    Returns list of {address, pid, lat, lng} dicts.
    Empty list on any error.
    """
    try:
        resp = requests.get(
            SEARCH_BASE_URL,
            params={
                "where": where,
                "outFields": "ADDRESS,PID,LOCALITY,POSTCODE",
                "returnGeometry": "true",
                "outSR": "4326",
                "resultRecordCount": record_count,
                "orderByFields": "ADDRESS",
                "f": "json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            return []

        results = []
        for feat in data.get("features", []):
            attrs = feat.get("attributes", {})
            geom = feat.get("geometry", {})
            pid_raw = attrs.get("PID")
            pid = int(pid_raw) if pid_raw is not None else None
            results.append(
                {
                    "address": attrs.get("ADDRESS", ""),
                    "pid": pid,
                    "lat": geom.get("y"),
                    "lng": geom.get("x"),
                }
            )
        return results
    except Exception:
        return []


def suggest_addresses(q: str) -> list[dict]:
    """
    Autocomplete: partial address string -> up to 8 real theLIST candidates.

    Args:
        q: partial address typed by user (min ~3 chars recommended)

    Returns:
        list of {address, pid, lat, lng}  — empty list on error or no match
    """
    if not q or len(q.strip()) < 3:
        return []
    where = _build_where(q)
    return _query_layer7(where, record_count=8)


def geocode_address(address: str) -> dict:
    """
    Compat path: resolve a full address string to its single best theLIST match.

    Returns {lat, lng, pid, display_name}.
    Raises AddressNotFoundError on zero matches.
    """
    where = _build_where(address)
    results = _query_layer7(where, record_count=1)
    if not results:
        raise AddressNotFoundError(f"Address not found in theLIST: {address}")
    r = results[0]
    return {
        "lat": r["lat"],
        "lng": r["lng"],
        "pid": r["pid"],
        "display_name": r["address"],
    }
