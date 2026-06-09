import os
import json
import time
import requests
from pyproj import Transformer

BASE_URL = "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/PlanningOnline/MapServer"
FLOOD_BASE_URL = "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/SES_FloodMapping/MapServer"
INFRA_BASE_URL = "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/Infrastructure/MapServer"
GEO_BASE_URL = "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/GeologicalAndSoils/MapServer"

LAYER_CODE_OVERLAYS = 14
LAYER_GENERAL_OVERLAYS = 15
LAYER_ZONES = 13
LAYER_LGA = 8
LAYER_KINGBOROUGH_OVERLAY = 3
LAYER_PARCELS = 2

# Flood raster layers (SES_FloodMapping)
FLOOD_LAYER_HAZARD_RIVERINE = 10       # 1% AEP Hazard Riverine Flooding
FLOOD_LAYER_HAZARD_OVERLAND = 11       # 1% AEP Hazard Overland Flooding
FLOOD_LAYER_DEPTH_RIVERINE = 12        # 1% AEP Depth Riverine (m)
FLOOD_LAYER_DEPTH_OVERLAND = 13        # 1% AEP Depth Overland (m)
FLOOD_LAYER_WATERLEVEL_RIVERINE = 16   # 1% AEP Water Level Riverine (m AHD)
FLOOD_LAYER_WATERLEVEL_OVERLAND = 17   # 1% AEP Water Level Overland (m AHD)

# TasWater layers (Infrastructure)
INFRA_LAYER_SEWER = 0   # TasWater Sewer Serviced Land
INFRA_LAYER_WATER = 1   # TasWater Water Serviced Land

# Landslide layer (GeologicalAndSoils)
GEO_LAYER_LANDSLIP = 23  # Landslide Planning Map - Hazard Bands

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


def _identify_raster(base_url: str, layer_ids: list[int], lng: float, lat: float) -> list[dict]:
    """ArcGIS MapServer identify op for raster layers. Point in MGA55 (sr=7855)."""
    x, y = _wgs84_to_mga55.transform(lng, lat)
    layer_str = "all:" + ",".join(str(lid) for lid in layer_ids)
    params = {
        "geometry": f"{x},{y}",
        "geometryType": "esriGeometryPoint",
        "sr": "7855",
        "layers": layer_str,
        "tolerance": "2",
        "mapExtent": f"{x-50},{y-50},{x+50},{y+50}",
        "imageDisplay": "400,400,96",
        "returnGeometry": "false",
        "f": "json",
    }
    url = f"{base_url}/identify"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise requests.HTTPError(f"ArcGIS error {data['error'].get('code')}: {data['error'].get('message')}")
    return data.get("results", [])


def _query_layer_external(base_url: str, layer_id: int, lng: float, lat: float, out_fields: str, use_native: bool = False) -> list:
    """Like _query_layer but against an arbitrary base_url."""
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
    url = f"{base_url}/{layer_id}/query"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise requests.HTTPError(f"ArcGIS error {data['error'].get('code')}: {data['error'].get('message')}")
    return [f["attributes"] for f in data.get("features", [])]


def _query_external_with_fallback(base_url: str, layer_id: int, lng: float, lat: float, out_fields: str) -> list:
    features = _query_layer_external(base_url, layer_id, lng, lat, out_fields, use_native=False)
    if not features:
        features = _query_layer_external(base_url, layer_id, lng, lat, out_fields, use_native=True)
    return features


_FLOOD_DEFAULT = {"in_flood_area": False, "depth_1pct_m": None, "hazard_1pct": None, "water_level_1pct_ahd": None}
_TASWATER_DEFAULT = {"sewer_serviced": False, "water_serviced": False, "sewer_status": None, "water_status": None}
_LANDSLIP_DEFAULT = {"in_landslip_band": False, "band": None, "exposure": None}


def query_flood(lat: float, lng: float) -> dict:
    """Query SES_FloodMapping for 1% AEP riverine flood data at a WGS84 point."""
    try:
        flood_layer_ids = [
            FLOOD_LAYER_HAZARD_RIVERINE,
            FLOOD_LAYER_DEPTH_RIVERINE,
            FLOOD_LAYER_WATERLEVEL_RIVERINE,
        ]
        results = _identify_raster(FLOOD_BASE_URL, flood_layer_ids, lng, lat)

        hazard = None
        depth = None
        water_level = None

        for r in results:
            lid = r.get("layerId")
            attrs = r.get("attributes", {})
            # Pixel value stored under "Pixel Value" key
            val = attrs.get("Pixel Value") or attrs.get("Value")
            if val in (None, "NoData"):
                continue
            if lid == FLOOD_LAYER_HAZARD_RIVERINE:
                hazard = str(val)
            elif lid == FLOOD_LAYER_DEPTH_RIVERINE:
                try:
                    depth = round(float(val), 3)
                except (TypeError, ValueError):
                    pass
            elif lid == FLOOD_LAYER_WATERLEVEL_RIVERINE:
                try:
                    water_level = round(float(val), 3)
                except (TypeError, ValueError):
                    pass

        in_flood = hazard is not None or depth is not None or water_level is not None
        return {
            "in_flood_area": in_flood,
            "depth_1pct_m": depth,
            "hazard_1pct": hazard,
            "water_level_1pct_ahd": water_level,
        }
    except Exception:
        return dict(_FLOOD_DEFAULT)


def query_taswater(lat: float, lng: float) -> dict:
    """Query Infrastructure service for TasWater sewer/water serviced land status.

    Uses identify op (polygon layers respond correctly to identify; query returns empty
    due to service configuration). Attribute key is aliased 'Service Type' not SERVICETYPE.
    """
    try:
        results = _identify_raster(
            INFRA_BASE_URL, [INFRA_LAYER_SEWER, INFRA_LAYER_WATER], lng, lat
        )

        sewer_status = None
        water_status = None

        for r in results:
            lid = r.get("layerId")
            attrs = r.get("attributes", {})
            # ArcGIS returns alias keys for identify results
            status = attrs.get("Service Type") or attrs.get("SERVICETYPE")
            if lid == INFRA_LAYER_SEWER:
                sewer_status = status
            elif lid == INFRA_LAYER_WATER:
                water_status = status

        return {
            "sewer_serviced": sewer_status is not None,
            "water_serviced": water_status is not None,
            "sewer_status": sewer_status,
            "water_status": water_status,
        }
    except Exception:
        return dict(_TASWATER_DEFAULT)


def query_landslip(lat: float, lng: float) -> dict:
    """Query GeologicalAndSoils for landslide hazard band at a WGS84 point."""
    try:
        features = _query_external_with_fallback(
            GEO_BASE_URL, GEO_LAYER_LANDSLIP, lng, lat, "HAZARD_BAND_1,HAZARD_EXPOSURE"
        )
        if not features:
            return dict(_LANDSLIP_DEFAULT)

        f = features[0]
        band = f.get("HAZARD_BAND_1")
        exposure = f.get("HAZARD_EXPOSURE")
        return {
            "in_landslip_band": band is not None,
            "band": band,
            "exposure": exposure,
        }
    except Exception:
        return dict(_LANDSLIP_DEFAULT)


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

    parcel_features = _query_with_fallback(LAYER_PARCELS, lng, lat, "COMP_AREA,MEAS_AREA,PID,CID")
    lot_area_sqm = None
    if parcel_features:
        raw = parcel_features[0].get("COMP_AREA") or parcel_features[0].get("MEAS_AREA")
        if raw:
            lot_area_sqm = round(float(raw))

    zone_features = _query_with_retry(LAYER_ZONES, lng, lat, "ZONE,ZONE_ABB,LPS,LPS_NO")
    zone = None
    if zone_features:
        z = zone_features[0]
        zone = {
            "zone": z.get("ZONE"),
            "zone_abb": z.get("ZONE_ABB"),
            "lps": z.get("LPS"),
            "lps_ref": z.get("LPS_NO"),  # Layer 13 uses LPS_NO not LPS_REF
        }

    kingborough_warning = (
        council["name"] == "Kingborough" and not code_overlays
    )

    flood = query_flood(lat, lng)
    taswater = query_taswater(lat, lng)
    landslip = query_landslip(lat, lng)

    return {
        "council": council,
        "zone": zone,
        "overlays": overlays,
        "lot_area_sqm": lot_area_sqm,
        "kingborough_interim": kingborough_warning,
        "flood": flood,
        "taswater": taswater,
        "landslip": landslip,
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
        "lot_area_sqm": None,
        "kingborough_interim": False,
        "flood": dict(_FLOOD_DEFAULT),
        "taswater": dict(_TASWATER_DEFAULT),
        "landslip": dict(_LANDSLIP_DEFAULT),
    }
