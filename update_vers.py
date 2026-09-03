import json

with open('shapes.json', 'r') as f:
    shapes = json.load(f)

with open('vers_system.py', 'r') as f:
    code = f.read()

import re

# Find the PAGASA GeoJSON definition block inside _threat_polling_task
pagasa_start = code.find('pagasa_geojson = {')
pagasa_end = code.find('CACHED_WARNINGS["pagasa"] = pagasa_geojson')

pagasa_block = """pagasa_geojson = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "PAGASA - Metro Manila", "alertlevel": "Red", "description": "Severe Flooding Expected. EVACUATE."},
                        "geometry": {
                            "type": "%s",
                            "coordinates": %s
                        }
                    },
                    {
                        "type": "Feature",
                        "properties": {"name": "PAGASA - Rizal", "alertlevel": "Orange", "description": "Intense Rain. Flooding is Threatening."},
                        "geometry": {
                            "type": "%s",
                            "coordinates": %s
                        }
                    },
                    {
                        "type": "Feature",
                        "properties": {"name": "PAGASA - Laguna", "alertlevel": "Yellow", "description": "Heavy Rain. Flooding is Possible."},
                        "geometry": {
                            "type": "%s",
                            "coordinates": %s
                        }
                    }
                ]
            }
            """ % (shapes['ncr_type'], json.dumps(shapes['ncr']), shapes['rizal_type'], json.dumps(shapes['rizal']), shapes['laguna_type'], json.dumps(shapes['laguna']))

new_code = code[:pagasa_start] + pagasa_block + code[pagasa_end:]

with open('vers_system.py', 'w') as f:
    f.write(new_code)
print("Updated vers_system.py with real shapes")
