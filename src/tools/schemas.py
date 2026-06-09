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
                "pid": {
                    "type": "integer",
                    "description": "Optional Parcel ID from theLIST Address Geocodes — enables exact parcel lookup instead of point-in-polygon.",
                },
            },
            "required": ["lat", "lng"],
        },
    },
}

ALL_TOOLS = [QUERY_OVERLAYS_SCHEMA]
