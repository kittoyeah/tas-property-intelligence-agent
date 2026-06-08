GEOCODE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "geocode_address",
        "description": "Convert a Tasmanian property address to WGS84 lat/lng coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Full Tasmanian address including street number, suburb, and postcode. Example: '8 Nelson Road Sandy Bay 7005'",
                }
            },
            "required": ["address"],
        },
    },
}

QUERY_OVERLAYS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "query_overlays",
        "description": "Query theLIST ArcGIS REST API for planning overlays, zone, and council at a given WGS84 lat/lng point in Tasmania.",
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude in WGS84 (negative for southern hemisphere). Example: -42.9026379",
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude in WGS84. Example: 147.3323815",
                },
            },
            "required": ["lat", "lng"],
        },
    },
}

ALL_TOOLS = [GEOCODE_SCHEMA, QUERY_OVERLAYS_SCHEMA]
