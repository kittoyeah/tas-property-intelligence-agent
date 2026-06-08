import os
import json
import time
import requests
from pyproj import Transformer

BASE_URL = "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/PlanningOnline/MapServer"

LAYER_CODE_OVERLAYS = 14
LAYER_GENERAL_OVERLAYS = 15
LAYER_ZONES = 13
LAYER_LGA = 8
LAYER_KINGBOROUGH_OVERLAY = 3

MOCK_DIR = os.path.join(os.path.dirname(__file__), "../../data/sample")

_wgs84_to_mga55 = Transformer.from_crs("EPSG:4326", "EPSG:7855", always_xy=True)


def _query_layer(layer_id: int, lng: float, lat: float, out_fields: str, use_native: bool = False) -> list:
    if use_native:
        x, y = _wgs84_to_mga55.transform(lng, lat)
        params = {
            "geometry": f"{x},{y}",
            "geometryType": "esriGeometryPoint",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": out_fields,
            "returnGeometry": "false",
            "f": "json",
        }
    else:
        params = {
            "geometry": f"{lng},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": out_fields,
            "returnGeometry": "false",
            "f": "json",
        }

    url = f"{BASE_URL}/{layer_id}/query"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise requests.HTTPError(f"ArcGIS error {data['error'].get('code')}: {data['error'].get('message')}")
    return [f["attributes"] for f in data.get("features", [])]


def _query_with_fallback(layer_id: int, lng: float, lat: float, out_fields: str) -> list:
    features = _query_layer(layer_id, lng, lat, out_fields, use_native=False)
    if not features:
        features = _query_layer(layer_id, lng, lat, out_fields, use_native=True)
    return features


def _query_with_retry(layer_id: int, lng: float, lat: float, out_fields: str, retries: int = 3) -> list:
    for attempt in range(retries):
        try:
            return _query_with_fallback(layer_id, lng, lat, out_fields)
        except requests.HTTPError:
            if attempt < retries - 1:
                time.sleep(1)
    return []


def query_overlays(lat: float, lng: float) -> dict:
    """Query theLIST planning overlays, zone, and council for a WGS84 point."""
    if os.getenv("USE_MOCK_DATA") == "true":
        return _load_mock()

    lga_features = _query_with_fallback(LAYER_LGA, lng, lat, "NAME,LGA_CODE")
    if not lga_features:
        raise ValueError("Address not found in Tasmania — no LGA returned.")

    council = {
        "name": lga_features[0].get("NAME"),
        "lga_code": lga_features[0].get("LGA_CODE"),
    }

    code_overlays = _query_with_fallback(LAYER_CODE_OVERLAYS, lng, lat, "CODE,OV_NAME,OV_CAT,DESCRIPT,LPS,LPS_REF")
    general_overlays = _query_with_fallback(LAYER_GENERAL_OVERLAYS, lng, lat, "OV_TYPE,OV_NAME,OV_CAT,DESCRIPT,LPS,LPS_REF")

    # Kingborough fallback — interim scheme on Layer 3
    if not code_overlays and council["name"] == "Kingborough":
        kingborough_raw = _query_with_fallback(LAYER_KINGBOROUGH_OVERLAY, lng, lat, "O_CODE,O_NAME,PLANSCHEME")
        code_overlays = [
            {
                "CODE": f["O_CODE"],
                "OV_NAME": f["O_NAME"],
                "OV_CAT": None,
                "DESCRIPT": f.get("PLANSCHEME"),
                "LPS": "Kingborough Interim Planning Scheme 2015",
                "LPS_REF": f["O_CODE"],
                "source_layer": LAYER_KINGBOROUGH_OVERLAY,
            }
            for f in kingborough_raw
        ]

    overlays = []
    for f in code_overlays:
        overlays.append({
            "code": f.get("CODE"),
            "ov_name": f.get("OV_NAME"),
            "ov_cat": f.get("OV_CAT"),
            "descript": f.get("DESCRIPT"),
            "lps": f.get("LPS"),
            "lps_ref": f.get("LPS_REF"),
            "layer": f.get("source_layer", LAYER_CODE_OVERLAYS),
        })
    for f in general_overlays:
        overlays.append({
            "code": f.get("OV_TYPE"),
            "ov_name": f.get("OV_NAME"),
            "ov_cat": f.get("OV_CAT"),
            "descript": f.get("DESCRIPT"),
            "lps": f.get("LPS"),
            "lps_ref": f.get("LPS_REF"),
            "layer": LAYER_GENERAL_OVERLAYS,
        })

    zone_features = _query_with_retry(LAYER_ZONES, lng, lat, "ZONE,ZONE_ABB,LPS,LPS_REF")
    zone = None
    if zone_features:
        z = zone_features[0]
        zone = {
            "zone": z.get("ZONE"),
            "zone_abb": z.get("ZONE_ABB"),
            "lps": z.get("LPS"),
            "lps_ref": z.get("LPS_REF"),
        }

    kingborough_warning = (
        council["name"] == "Kingborough" and not code_overlays
    )

    return {
        "council": council,
        "zone": zone,
        "overlays": overlays,
        "kingborough_interim": kingborough_warning,
    }


def _load_mock() -> dict:
    parts = []
    for fname in ["layer8_lga.json", "layer14_with_overlays.json", "layer13_zone.json"]:
        path = os.path.join(MOCK_DIR, fname)
        try:
            with open(path) as f:
                parts.append(json.load(f))
        except FileNotFoundError:
            parts.append({})

    lga = parts[0]
    overlays_raw = parts[1] if isinstance(parts[1], list) else []
    zone_raw = parts[2]

    return {
        "council": {"name": lga.get("NAME"), "lga_code": lga.get("LGA_CODE")},
        "zone": zone_raw,
        "overlays": overlays_raw,
        "kingborough_interim": False,
    }
