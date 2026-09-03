import json

with open('vers_system.py', 'r') as f:
    code = f.read()

start = code.find('# Index the latest validated report only')
end = code.find('            pagasa_geojson = {')

new_block = """            # Index the actual live PAGASA Weather Advisory #27 (August 8, 2026)
            orange_provs = ["Ilocos Sur", "La Union", "Abra", "Benguet", "Zambales", "Bataan", "Occidental Mindoro"]
            yellow_provs = ["Ilocos Norte", "Pangasinan", "Apayao", "Kalinga", "Mountain Province", "Ifugao", "Nueva Vizcaya", "Tarlac", "Nueva Ecija", "Pampanga", "Bulacan", "Metropolitan Manila", "Rizal", "Cavite", "Batangas", "Oriental Mindoro", "Antique"]
            
            for f in all_provinces['features']:
                prov_name = f['properties']['PROVINCE']
                if prov_name in orange_provs:
                    f['properties']['name'] = "PAGASA - " + prov_name
                    f['properties']['alertlevel'] = "Orange"
                    f['properties']['description'] = "100-200mm Rain. Widespread flooding likely."
                    active_warnings.append(f)
                elif prov_name in yellow_provs:
                    f['properties']['name'] = "PAGASA - " + prov_name
                    f['properties']['alertlevel'] = "Yellow"
                    f['properties']['description'] = "50-100mm Rain. Localized flooding possible."
                    active_warnings.append(f)

"""

new_code = code[:start] + new_block + code[end:]

with open('vers_system.py', 'w') as f:
    f.write(new_code)
