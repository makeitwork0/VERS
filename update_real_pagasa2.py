import json

with open('vers_system.py', 'r') as f:
    code = f.read()

start = code.find('# Index the actual live PAGASA Weather Advisory')
end = code.find('            pagasa_geojson = {')

new_block = """            # Index the actual live PAGASA Heavy Rainfall Warning No. 27 (2:00 PM, August 8, 2026)
            red_provs = ["Bataan", "Cavite", "Metropolitan Manila", "Zambales", "Batangas", "Pampanga", "Bulacan", "Laguna"]
            orange_provs = ["Rizal", "Quezon"]
            yellow_provs = ["Tarlac"]
            
            for f in all_provinces['features']:
                prov_name = f['properties']['PROVINCE']
                # Match exact names (case-insensitive) or variants like "Metro Manila"
                prov_match = prov_name
                if prov_name.lower() == "metropolitan manila":
                    prov_match = "Metropolitan Manila"
                    
                if prov_match in red_provs:
                    f['properties']['name'] = "PAGASA - " + prov_name
                    f['properties']['alertlevel'] = "Red"
                    f['properties']['description'] = "Heavy Rainfall: Serious FLOODING is expected in flood-prone areas."
                    active_warnings.append(f)
                elif prov_match in orange_provs:
                    f['properties']['name'] = "PAGASA - " + prov_name
                    f['properties']['alertlevel'] = "Orange"
                    f['properties']['description'] = "Heavy Rainfall: FLOODING is THREATENING."
                    active_warnings.append(f)
                elif prov_match in yellow_provs:
                    f['properties']['name'] = "PAGASA - " + prov_name
                    f['properties']['alertlevel'] = "Yellow"
                    f['properties']['description'] = "Heavy Rainfall: Possible FLOODING in flood-prone areas."
                    active_warnings.append(f)

"""

new_code = code[:start] + new_block + code[end:]

with open('vers_system.py', 'w') as f:
    f.write(new_code)
