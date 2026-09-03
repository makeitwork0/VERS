import urllib.request
import json

url = "https://raw.githubusercontent.com/macoymejia/geojsonph/master/Province/Provinces.json"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
    def find_prov(name):
        return next((f for f in data['features'] if f['properties']['PROVINCE'].lower() == name.lower()), None)
        
    ncr = find_prov("Metropolitan Manila") or find_prov("National Capital Region") or find_prov("Metropolitan Manila")
    rizal = find_prov("Rizal")
    laguna = find_prov("Laguna")
    
    out = {
        "ncr": ncr['geometry']['coordinates'] if ncr else None,
        "rizal": rizal['geometry']['coordinates'] if rizal else None,
        "laguna": laguna['geometry']['coordinates'] if laguna else None,
        "ncr_type": ncr['geometry']['type'] if ncr else None,
        "rizal_type": rizal['geometry']['type'] if rizal else None,
        "laguna_type": laguna['geometry']['type'] if laguna else None
    }
    
    with open('shapes.json', 'w') as f:
        json.dump(out, f)
    print("Downloaded shapes")
except Exception as e:
    print("Error:", e)
