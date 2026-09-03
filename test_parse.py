import re

def parse_provs_and_cities(match):
    if not match: return {}
    raw = match.group(1).replace(' and ', ',')
    # find provinces and their cities in parentheses
    # e.g., Metro Manila (Quezon City, Manila), Rizal, Bulacan (Meycauayan)
    result = {}
    
    # Split by comma but ignore commas inside parentheses
    # regex to split by comma outside parentheses:
    parts = re.split(r',\s*(?![^()]*\))', raw)
    
    for part in parts:
        part = part.strip()
        if not part: continue
        m = re.match(r'([^(]+)(?:\((.*?)\))?', part)
        if m:
            prov = m.group(1).strip()
            cities_str = m.group(2)
            cities = [c.strip() for c in cities_str.split(',')] if cities_str else []
            result[prov.lower()] = cities
    return result

text = "RED WARNING LEVEL: Metro Manila(Quezon City, Manila), Rizal, Bulacan(Meycauayan)"
match = re.search(r'RED WARNING LEVEL:\s*(.*?)$', text, re.IGNORECASE)
print(parse_provs_and_cities(match))
