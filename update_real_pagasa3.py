import json

with open('vers_system.py', 'r') as f:
    code = f.read()

start = code.find('# Index the actual live PAGASA Heavy Rainfall Warning')
end = code.find('            pagasa_geojson = {')

new_block = """            # Live PAGASA scraper from the website
            import requests
            from bs4 import BeautifulSoup
            import re
            
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                res = requests.get("https://www.pagasa.dost.gov.ph/regional-forecast/ncrprsd", headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                text = soup.get_text(separator=' ')
                
                red_match = re.search(r'RED WARNING LEVEL:\s*(.*?)(?=ASSOCIATED|ORANGE|YELLOW|$)', text, re.IGNORECASE | re.DOTALL)
                orange_match = re.search(r'ORANGE WARNING LEVEL:\s*(.*?)(?=ASSOCIATED|YELLOW|RED|$)', text, re.IGNORECASE | re.DOTALL)
                yellow_match = re.search(r'YELLOW WARNING LEVEL:\s*(.*?)(?=ASSOCIATED|Meanwhile|$)', text, re.IGNORECASE | re.DOTALL)
                
                def extract_provs(match):
                    if not match: return []
                    raw = match.group(1).replace(' and ', ',')
                    raw = re.sub(r'\(.*?\)', '', raw) # Remove municipalities in parentheses
                    return [p.strip() for p in raw.split(',') if p.strip()]

                red_provs = extract_provs(red_match)
                orange_provs = extract_provs(orange_match)
                yellow_provs = extract_provs(yellow_match)
                
                for f in all_provinces['features']:
                    prov_name = f['properties']['PROVINCE']
                    prov_match = prov_name
                    if prov_name.lower() == "metropolitan manila": prov_match = "Metro Manila"
                        
                    if any(prov_match.lower() == p.lower() for p in red_provs):
                        f['properties']['name'] = "PAGASA - " + prov_name
                        f['properties']['alertlevel'] = "Red"
                        f['properties']['description'] = "Serious FLOODING is expected."
                        active_warnings.append(f)
                    elif any(prov_match.lower() == p.lower() for p in orange_provs):
                        f['properties']['name'] = "PAGASA - " + prov_name
                        f['properties']['alertlevel'] = "Orange"
                        f['properties']['description'] = "FLOODING is THREATENING."
                        active_warnings.append(f)
                    elif any(prov_match.lower() == p.lower() for p in yellow_provs):
                        f['properties']['name'] = "PAGASA - " + prov_name
                        f['properties']['alertlevel'] = "Yellow"
                        f['properties']['description'] = "Possible FLOODING."
                        active_warnings.append(f)
            except Exception as e:
                print("PAGASA Web Scrape Error:", e)

"""

new_code = code[:start] + new_block + code[end:]

# Add socketio connect event to immediately push CACHED_WARNINGS on connect
socket_hook = """
@socketio.on('connect', namespace='/dashboard')
def dashboard_connect():
    print("Dashboard connected, resending warnings immediately")
    socketio.emit('warnings_update', CACHED_WARNINGS, to=request.sid, namespace='/dashboard')
"""
if "@socketio.on('connect', namespace='/dashboard')" not in new_code:
    # insert before @socketio.on('join', namespace='/dashboard') if exists, else append
    join_idx = new_code.find("@socketio.on('join'")
    if join_idx != -1:
        new_code = new_code[:join_idx] + socket_hook + "\n" + new_code[join_idx:]
    else:
        # just append before run
        run_idx = new_code.rfind("if __name__ == '__main__':")
        new_code = new_code[:run_idx] + socket_hook + "\n" + new_code[run_idx:]

with open('vers_system.py', 'w') as f:
    f.write(new_code)
