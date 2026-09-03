import re

with open('vers_system.py', 'r') as f:
    code = f.read()

# 1. Globals
code = re.sub(r'API_KEY = ""', 'API_KEY = ""\nOWM_API_KEY = ""', code)
code = re.sub(r'global SMTP_SERVER, (.*?) DASHBOARD_PASSWORD\n', r'global SMTP_SERVER, \1 DASHBOARD_PASSWORD, OWM_API_KEY\n', code)
code = re.sub(r'(DASHBOARD_PASSWORD = data\.get\("dashboard_password", DASHBOARD_PASSWORD\))', r'\1\n                OWM_API_KEY = data.get("owm_api_key", "")', code)

# 2. Save settings
code = re.sub(
    r'def save_settings_to_file\(smtp_server, smtp_port, sender_email, sender_password, recipient_email, dashboard_password=None\):',
    r'def save_settings_to_file(smtp_server, smtp_port, sender_email, sender_password, recipient_email, dashboard_password=None, owm_api_key=None):',
    code
)
code = re.sub(
    r'global DASHBOARD_PASSWORD\n',
    r'global DASHBOARD_PASSWORD, OWM_API_KEY\n',
    code
)
code = re.sub(
    r'(DASHBOARD_PASSWORD = dashboard_password)',
    r'\1\n    if owm_api_key is not None:\n        OWM_API_KEY = owm_api_key',
    code
)
code = re.sub(
    r'("dashboard_password": DASHBOARD_PASSWORD)',
    r'\1,\n                "owm_api_key": OWM_API_KEY',
    code
)
code = re.sub(
    r'ok = save_settings_to_file\(SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL, DASHBOARD_PASSWORD\)',
    r'ok = save_settings_to_file(SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL, DASHBOARD_PASSWORD, OWM_API_KEY)',
    code
)

# 3. API endpoints
code = re.sub(
    r'("recipient_email": RECIPIENT_EMAIL)',
    r'\1,\n        "owm_api_key": OWM_API_KEY',
    code
)
code = re.sub(
    r'(new_dash_pw       = data\.get\("dashboard_password", ""\)\.strip\(\))',
    r'\1\n    new_owm_api_key   = data.get("owm_api_key", "").strip()',
    code
)
code = re.sub(
    r'(if new_dash_pw:\n        DASHBOARD_PASSWORD = new_dash_pw)',
    r'\1\n    if new_owm_api_key:\n        OWM_API_KEY = new_owm_api_key',
    code
)

# 4. Index route
code = re.sub(
    r'def index\(\):\n    return INDEX_HTML',
    r'def index():\n    return INDEX_HTML.replace("__OWM_API_KEY__", OWM_API_KEY)',
    code
)

# 5. HTML / JS changes
# Add to script start
code = re.sub(
    r'// -- Text to Speech Setup --',
    r'const OWM_API_KEY = "__OWM_API_KEY__";\n\n        // -- Text to Speech Setup --',
    code
)

# Add to layer control
layer_add_code = r'''
                    if (OWM_API_KEY) {
                        overlayMaps["💨 Wind Vectors"] = L.tileLayer(`https://tile.openweathermap.org/map/wind_new/{z}/{x}/{y}.png?appid=${OWM_API_KEY}`, { opacity: 0.6, attribution: '&copy; OpenWeatherMap' });
                        overlayMaps["☁️ Cloud Cover"] = L.tileLayer(`https://tile.openweathermap.org/map/clouds_new/{z}/{x}/{y}.png?appid=${OWM_API_KEY}`, { opacity: 0.6, attribution: '&copy; OpenWeatherMap' });
                        
                        overlayMapsOff["💨 Wind Vectors"] = L.tileLayer('', { opacity: 0.6 });
                        overlayMapsOff["☁️ Cloud Cover"] = L.tileLayer('', { opacity: 0.6 });
                    }
                    L.control.layers(baseMaps, overlayMaps).addTo(map);
'''
code = re.sub(r'L\.control\.layers\(baseMaps, overlayMaps\)\.addTo\(map\);', layer_add_code.strip(), code)

layer_add_code_off = r'''
                    if (OWM_API_KEY) {
                        overlayMapsOff["💨 Wind Vectors"] = L.tileLayer('', { opacity: 0.6 });
                        overlayMapsOff["☁️ Cloud Cover"] = L.tileLayer('', { opacity: 0.6 });
                    }
                    L.control.layers(baseMapsOff, overlayMapsOff).addTo(map);
'''
code = re.sub(r'L\.control\.layers\(baseMapsOff, overlayMapsOff\)\.addTo\(map\);', layer_add_code_off.strip(), code)


# HTML Settings modal
settings_html = r'''
                        <h4>Weather Integrations</h4>
                        <label style="font-size:12px; color:#aaa;">OpenWeatherMap API Key (For Wind & Clouds)</label>
                        <input type="text" id="set_owm_key" class="settings-input" placeholder="e.g. 5b3f...">
                        
                        <h4 style="margin-top:20px;">Email Settings</h4>
'''
code = re.sub(r'<h4>Email Settings</h4>', settings_html.strip(), code)

# JS JS load settings
code = re.sub(
    r"document\.getElementById\('set_recipient'\)\.value = data\.recipient_email;",
    r"document.getElementById('set_recipient').value = data.recipient_email;\n                    if(document.getElementById('set_owm_key')) document.getElementById('set_owm_key').value = data.owm_api_key || '';",
    code
)

# JS save settings
code = re.sub(
    r"const pw2 = document\.getElementById\('set_dash_pw'\)\.value;",
    r"const pw2 = document.getElementById('set_dash_pw').value;\n            const owm = document.getElementById('set_owm_key') ? document.getElementById('set_owm_key').value : '';",
    code
)
code = re.sub(
    r'dashboard_password: pw2',
    r'dashboard_password: pw2,\n                owm_api_key: owm',
    code
)

with open('vers_system.py', 'w') as f:
    f.write(code)

print("Patch applied successfully.")
