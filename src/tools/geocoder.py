import os
import json
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "CanIBuild/1.0 (chris.kittichod@gmail.com)"

TAS_BBOX = {
    "lat_min": -43.65,
    "lat_max": -39.57,
    "lng_min": 143.82,
    "lng_max": 148.35,
}

MOCK_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/sample/nominatim_8nelson.json")


class AddressNotFoundError(Exception):
    pass


class OutsideTasmaniaError(Exception):
    pass


def geocode_address(address: str) -> dict:
    """Convert a Tasmanian address string to lat/lng (WGS84)."""
    if os.getenv("USE_MOCK_DATA") == "true":
        with open(MOCK_DATA_PATH) as f:
            return json.load(f)

    params = {
        "q": f"{address}, Tasmania, Australia",
        "format": "json",
        "limit": 1,
        "countrycodes": "au",
        "addressdetails": 1,
    }
    headers = {"User-Agent": USER_AGENT}

    resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    results = resp.json()

    if not results:
        raise AddressNotFoundError(f"Address not found: {address}")

    result = results[0]
    lat = float(result["lat"])
    lng = float(result["lon"])

    if not (
        TAS_BBOX["lat_min"] <= lat <= TAS_BBOX["lat_max"]
        and TAS_BBOX["lng_min"] <= lng <= TAS_BBOX["lng_max"]
    ):
        raise OutsideTasmaniaError(f"Address resolved outside Tasmania: {result['display_name']}")

    return {
        "lat": lat,
        "lng": lng,
        "display_name": result["display_name"],
    }
