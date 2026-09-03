import json

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Metro Manila", "alertlevel": "Red", "description": "Severe Flooding Expected. EVACUATE."},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[120.95, 14.75], [121.10, 14.75], [121.10, 14.35], [120.95, 14.35], [120.95, 14.75]]]
            }
        },
        {
            "type": "Feature",
            "properties": {"name": "Rizal", "alertlevel": "Orange", "description": "Intense Rain. Flooding is Threatening."},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[121.10, 14.75], [121.30, 14.75], [121.30, 14.50], [121.10, 14.50], [121.10, 14.75]]]
            }
        },
        {
            "type": "Feature",
            "properties": {"name": "Laguna", "alertlevel": "Yellow", "description": "Heavy Rain. Flooding is Possible."},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[121.10, 14.50], [121.30, 14.50], [121.30, 14.20], [121.10, 14.20], [121.10, 14.50]]]
            }
        }
    ]
}
print(json.dumps(geojson))
