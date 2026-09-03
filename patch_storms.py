import re

with open('vers_system.py', 'r') as f:
    code = f.read()

storm_code = r'''
                    // --- Feature: PAR Boundary ---
                    const parCoords = [
                        [5, 115],
                        [15, 115],
                        [21, 120],
                        [25, 120],
                        [25, 135],
                        [5, 135]
                    ];
                    const parLayer = L.polygon(parCoords, {color: '#4287f5', weight: 2, fillOpacity: 0.05, dashArray: '5, 10'}).bindTooltip('Philippine Area of Responsibility (PAR)', {sticky: true});

                    // --- Feature: Active Storms (GDACS) ---
                    const cycloneLayer = L.layerGroup();
                    fetch('https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP?eventtypes=TC')
                        .then(r => r.json())
                        .then(data => {
                            L.geoJSON(data, {
                                pointToLayer: function (feature, latlng) {
                                    const iconUrl = feature.properties.icon || 'https://www.gdacs.org/images/gdacs_icons/maps/Green/TC.png';
                                    const tcIcon = L.icon({
                                        iconUrl: iconUrl,
                                        iconSize: [40, 40],
                                        iconAnchor: [20, 20],
                                        popupAnchor: [0, -20]
                                    });
                                    return L.marker(latlng, {icon: tcIcon})
                                        .bindPopup(`<b>${feature.properties.name}</b><br>Alert Level: ${feature.properties.alertlevel}<br><i>${feature.properties.htmldescription}</i><br><a href="${feature.properties.url.report}" target="_blank">View GDACS Report</a>`);
                                }
                            }).addTo(cycloneLayer);
                        }).catch(e => console.log("Cyclone load error", e));
                    
                    overlayMaps["🇵🇭 PAR Boundary"] = parLayer;
                    overlayMaps["🌀 Active Cyclones"] = cycloneLayer;
'''

code = re.sub(
    r'(overlayMaps\["☁️ Cloud Cover"\] = .*?\n                    \})',
    r'\1\n' + storm_code.strip('\n'),
    code
)

storm_code_off = r'''
                        // --- Feature: PAR Boundary (Offline) ---
                        const parCoordsOff = [ [5, 115], [15, 115], [21, 120], [25, 120], [25, 135], [5, 135] ];
                        const parLayerOff = L.polygon(parCoordsOff, {color: '#4287f5', weight: 2, fillOpacity: 0.05, dashArray: '5, 10'}).bindTooltip('Philippine Area of Responsibility (PAR)', {sticky: true});
                        overlayMapsOff["🇵🇭 PAR Boundary"] = parLayerOff;
'''

code = re.sub(
    r'(overlayMapsOff\["☁️ Cloud Cover"\] = .*?\n                    \})',
    r'\1\n' + storm_code_off.strip('\n'),
    code
)

with open('vers_system.py', 'w') as f:
    f.write(code)

print("Patch storms applied successfully.")
