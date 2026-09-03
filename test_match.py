import re

def _extract_provs_from_text(match_group):
    if not match_group: return {}
    raw = match_group.replace(' and ', ',')
    result = {}
    parts = re.split(r',\s*(?![^()]*\))', raw)
    for part in parts:
        part = part.strip()
        if not part: continue
        m = re.match(r'([^(]+)(?:\((.*?)\))?', part)
        if m:
            prov = m.group(1).strip().lower()
            cities_str = m.group(2)
            cities = [c.strip().lower() for c in cities_str.split(',')] if cities_str else []
            result[prov] = cities
    return result

def normalize(s):
    s = s.lower().replace('ñ', 'n').replace('city', '').replace('kalookan', 'caloocan')
    return re.sub(r'[^a-z0-9]', '', s)

def is_affected(provs_dict, prov_name, city_name):
    prov_match = prov_name.lower()
    if prov_match == "metropolitan manila": prov_match = "metro manila"
    norm_prov = normalize(prov_match)
    
    for k, v in provs_dict.items():
        if normalize(k) == norm_prov:
            if not v: return True
            norm_city = normalize(city_name)
            for c in v:
                norm_c = normalize(c)
                if norm_c in norm_city or norm_city in norm_c:
                    return True
    return False

red_provs = _extract_provs_from_text("Metro Manila(Quezon City, Parañaque, Caloocan), Rizal")

print("Quezon City:", is_affected(red_provs, "Metropolitan Manila", "Quezon City"))
print("Paranaque:", is_affected(red_provs, "Metropolitan Manila", "Paranaque"))
print("Kalookan:", is_affected(red_provs, "Metropolitan Manila", "Kalookan"))
print("Taguig:", is_affected(red_provs, "Metropolitan Manila", "Taguig"))
print("Antipolo:", is_affected(red_provs, "Rizal", "Antipolo"))
print("Cebu:", is_affected(red_provs, "Cebu", "Cebu City"))
