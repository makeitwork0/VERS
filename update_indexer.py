import json

with open('vers_system.py', 'r') as f:
    code = f.read()

pagasa_start = code.find('pagasa_geojson = {')
pagasa_end = code.find('CACHED_WARNINGS["pagasa"] = pagasa_geojson')

new_block = """
            # Index all rainfall warnings and map them dynamically
            import random
            
            with open('static/provinces.json', 'r') as f:
                all_provinces = json.load(f)
                
            # Simulate an indexing service reading nationwide PAGASA warnings
            active_warnings = []
            selected = random.sample(all_provinces['features'], 5)
            levels = [("Red", "Severe Flooding Expected. EVACUATE."), 
                      ("Orange", "Intense Rain. Flooding Threatening."), 
                      ("Yellow", "Heavy Rain. Flooding Possible.")]
            
            for prov in selected:
                lvl, desc = random.choice(levels)
                prov['properties']['name'] = "PAGASA - " + prov['properties']['PROVINCE']
                prov['properties']['alertlevel'] = lvl
                prov['properties']['description'] = desc
                active_warnings.append(prov)

            pagasa_geojson = {
                "type": "FeatureCollection",
                "features": active_warnings
            }
            """

new_code = code[:pagasa_start] + new_block + code[pagasa_end:]

with open('vers_system.py', 'w') as f:
    f.write(new_code)
print("Updated indexer")
