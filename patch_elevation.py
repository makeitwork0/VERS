import re

with open('vers_system.py', 'r') as f:
    code = f.read()

# 1. Add Monitoring Card to left panel
monitoring_html = r'''
            <div class="card" style="margin-top: 15px;">
                <h3>🔍 Monitoring (Risk & Threats)</h3>
                <div id="monitoringList" style="max-height: 200px; overflow-y: auto; font-size: 11px;">
                    <div id="nodata_monitoring" style="color: #666; text-align: center; padding: 10px;">Scanning for threats...</div>
                </div>
            </div>
'''
code = re.sub(
    r'(<div class="card" style="margin-top: 15px;">\s*<h3>📢 Operator Broadcast</h3>)',
    monitoring_html.strip() + r'\n            \1',
    code
)

# 2. Add OpenTopoMap to baseMaps
topo_code = r'''
                    const elevationLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', { maxZoom: 17, attribution: '&copy; OpenTopoMap' });
'''
code = re.sub(
    r'(const googleTerrain = L\.tileLayer\(.*?\n                    \}\);)',
    r'\1\n' + topo_code.strip('\n'),
    code
)
code = re.sub(
    r'("Google Terrain": googleTerrain)',
    r'\1,\n                        "⛰️ Elevation (OpenTopoMap)": elevationLayer',
    code
)

topo_code_off = r'''
                        const elevationLayerOff = L.tileLayer('', { maxZoom: 17 });
'''
code = re.sub(
    r'(const localOfflineRoads = L\.tileLayer\(.*?\n                    \}\);)',
    r'\1\n' + topo_code_off.strip('\n'),
    code
)
code = re.sub(
    r'("Local Offline Map": localOfflineRoads)',
    r'\1,\n                        "⛰️ Elevation (OpenTopoMap)": elevationLayerOff',
    code
)

# 3. Add transparent storm path and populate monitoring tab
cyclone_patch = r'''
                            const monList = document.getElementById('monitoringList');
                            if(data.features && data.features.length > 0) {
                                monList.innerHTML = '';
                                data.features.forEach(f => {
                                    const div = document.createElement('div');
                                    div.className = 'alert-entry';
                                    div.style.borderLeftColor = f.properties.alertlevel === 'Red' ? '#ff5050' : (f.properties.alertlevel === 'Orange' ? '#fa0' : '#0f6');
                                    div.innerHTML = `<div class="alert-text"><strong>${f.properties.name}</strong><br>${f.properties.htmldescription}</div>`;
                                    monList.appendChild(div);
                                    
                                    if(f.properties.url && f.properties.url.geometry) {
                                        fetch(f.properties.url.geometry)
                                            .then(res => res.json())
                                            .then(geom => {
                                                L.geoJSON(geom, {
                                                    style: { color: f.properties.alertlevel === 'Red' ? '#ff5050' : (f.properties.alertlevel === 'Orange' ? '#fa0' : '#0f6'), weight: 1, fillOpacity: 0.15, dashArray: '4' }
                                                }).addTo(cycloneLayer);
                                            }).catch(e => console.log('Geom fetch error', e));
                                    }
                                });
                            } else {
                                monList.innerHTML = '<div id="nodata_monitoring" style="color:#0f6; text-align: center; padding: 10px;">No active global threats.</div>';
                            }
'''

code = re.sub(
    r'(\}\)\.addTo\(cycloneLayer\);)',
    r'\1\n' + cyclone_patch.strip('\n'),
    code
)

with open('vers_system.py', 'w') as f:
    f.write(code)

print("Patch applied")
