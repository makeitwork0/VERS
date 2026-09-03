
        const OWM_API_KEY = "__OWM_API_KEY__";

        // -- Text to Speech Setup --
        const synth = window.speechSynthesis;
        let voiceQueue = [];
        let isSpeaking = false;

        function speak(text) {
            voiceQueue.push(text);
            processVoiceQueue();
        }

        function processVoiceQueue() {
            if (isSpeaking || voiceQueue.length === 0) return;
            const text = voiceQueue.shift();
            const utterance = new SpeechSynthesisUtterance(text);
            
            const voices = synth.getVoices();
            const alertVoice = voices.find(v => v.name.includes('Google UK English Male') || v.name.includes('Samantha') || v.name.includes('Daniel')) || voices[0];
            if (alertVoice) utterance.voice = alertVoice;
            
            utterance.rate = 1.05;
            utterance.pitch = 1.1;
            utterance.onstart = () => { document.getElementById('voiceStatus').textContent = '🔊 Speaking...'; };
            utterance.onend = () => {
                isSpeaking = false;
                document.getElementById('voiceStatus').textContent = '🔇 TTS Ready';
                processVoiceQueue();
            };
            isSpeaking = true;
            synth.speak(utterance);
        }

        function testVoice() { speak("Voice synthesis systems online and ready."); }
        speechSynthesis.onvoiceschanged = () => { console.log("Voices loaded."); };

        // -- Web Audio Alert Tones (Feature 12) --
        function playAlertTone(type) {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const gainNode = ctx.createGain();
                gainNode.connect(ctx.destination);
                gainNode.gain.setValueAtTime(0.3, ctx.currentTime);

                if (type === 'fire') {
                    // 3 rapid high-pitched beeps at 880Hz, 100ms each
                    [0, 0.15, 0.3].forEach(offset => {
                        const osc = ctx.createOscillator();
                        osc.type = 'square';
                        osc.frequency.setValueAtTime(880, ctx.currentTime + offset);
                        osc.connect(gainNode);
                        osc.start(ctx.currentTime + offset);
                        osc.stop(ctx.currentTime + offset + 0.1);
                    });
                    setTimeout(() => ctx.close(), 700);
                } else if (type === 'flood') {
                    // Low descending sweep 300->150Hz over 600ms
                    const osc = ctx.createOscillator();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(300, ctx.currentTime);
                    osc.frequency.linearRampToValueAtTime(150, ctx.currentTime + 0.6);
                    osc.connect(gainNode);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.6);
                    setTimeout(() => ctx.close(), 800);
                } else if (type === 'gas') {
                    // Oscillating mid tone 440Hz +-50Hz wobble at 4Hz, 400ms
                    const osc = ctx.createOscillator();
                    const lfo = ctx.createOscillator();
                    const lfoGain = ctx.createGain();
                    lfo.frequency.setValueAtTime(4, ctx.currentTime);
                    lfoGain.gain.setValueAtTime(50, ctx.currentTime);
                    lfo.connect(lfoGain);
                    lfoGain.connect(osc.frequency);
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(440, ctx.currentTime);
                    osc.connect(gainNode);
                    lfo.start(ctx.currentTime);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.4);
                    lfo.stop(ctx.currentTime + 0.4);
                    setTimeout(() => ctx.close(), 600);
                } else if (type === 'life_form') {
                    // 2 short beeps at 600Hz, 80ms each
                    [0, 0.13].forEach(offset => {
                        const osc = ctx.createOscillator();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(600, ctx.currentTime + offset);
                        osc.connect(gainNode);
                        osc.start(ctx.currentTime + offset);
                        osc.stop(ctx.currentTime + offset + 0.08);
                    });
                    setTimeout(() => ctx.close(), 500);
                } else {
                    // Default: single medium beep 500Hz, 200ms
                    const osc = ctx.createOscillator();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(500, ctx.currentTime);
                    osc.connect(gainNode);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.2);
                    setTimeout(() => ctx.close(), 400);
                }
            } catch(e) { console.warn('AudioContext not available', e); }
        }

        function detectAlertType(msg) {
            const m = (msg || '').toLowerCase();
            if (m.includes('fire')) return 'fire';
            if (m.includes('flood') || m.includes('water')) return 'flood';
            if (m.includes('gas')) return 'gas';
            if (m.includes('life') || m.includes('intruder') || m.includes('motion')) return 'life_form';
            return 'default';
        }

        // -- Socket.IO Setup --
        const socket = io('/dashboard');
        
        socket.on('connect', () => {
            document.getElementById('socketStatus').innerHTML = 'Online <span class="sensor-status status-ok"></span>';
            updateGlobalBadge();
            setConnBanner(true);
        });

        socket.on('disconnect', () => {
            document.getElementById('socketStatus').innerHTML = 'Offline <span class="sensor-status status-warning"></span>';
            setConnBanner(false);
        });

        window.addEventListener('online',  () => setConnBanner(true));
        window.addEventListener('offline', () => setConnBanner(false));

        function setConnBanner(isOnline) {
            const b = document.getElementById('connBanner');
            if (isOnline) {
                b.textContent = '🌐 ONLINE';
                b.style.color = '#00ff66';
                b.classList.remove('offline-pulse');
            } else {
                b.textContent = ' OFFLINE MODE';
                b.style.color = '#fa0';
                b.classList.add('offline-pulse');
            }
        }

        socket.on('sensor_update', (data) => {
            if (isPlaybackMode) return;
            updateDeviceDisplay(data.device_id, data.payload);
            addOrUpdateMarker(data.device_id, data.payload.lat, data.payload.lon, data.payload);
        });

        socket.on('voice_alert', (data) => {
            if (isPlaybackMode) return;
            playAlertTone(detectAlertType(data.message));
            speak(data.message);
            addAlert('alert', `<strong>VOICE ALERT:</strong> ${data.message}`, data.device);
        });

        socket.on('alert_ack', (data) => {
            const entry = document.getElementById('alert-entry-' + data.timestamp);
            if (entry) {
                entry.classList.remove('unacked');
                entry.classList.add('acked');
                const btn = entry.querySelector('.ack-btn');
                if (btn) {
                    btn.textContent = '\u2713 Acknowledged';
                    btn.disabled = true;
                    btn.style.background = '#444';
                }
            }
        });

        socket.on('operator_broadcast', (data) => {
            showToast("📢 Broadcast: " + data.message, "info");
            addAlert('broadcast', `<strong>[BROADCAST]:</strong> ` + data.message + ` (` + data.timestamp + `)`);
        });

        socket.on('ai_analysis', (data) => {
            if (isPlaybackMode) return;
            
            let cleanAnalysis = data.analysis;
            let prefix = "";
            const match = data.analysis.match(/^\\[(.*?)\\] (.*)/);
            if (match) {
                prefix = `[${match[1]}] `;
                cleanAnalysis = match[2];
            }
            
            const htmlContent = `
                <div style="display: flex; flex-direction: column; gap: 6px; width: 100%; margin-top: 4px;">
                    <div><strong>🤖 AI INSTRUCTION (${data.device_id}):</strong> <span style="color:#fa0; font-size:10px; font-weight:bold;">${prefix}</span></div>
                    <textarea id="override_text_${data.device_id}" style="width:100%; height:60px; background:rgba(0,0,0,0.6); border:1px solid #fa0; color:#cfe8d6; font-family:sans-serif; font-size:11px; padding:6px; border-radius:4px; resize:none; outline:none;">${cleanAnalysis}</textarea>
                    <div style="text-align:right;">
                        <button style="font-size:10px; padding:2px 8px; background:#fa0; color:#000; border:none; border-radius:3px; cursor:pointer; font-weight:bold;" onclick="dispatchOverride('${data.device_id}')">📢 Dispatch & Announce</button>
                    </div>
                </div>
            `;
            addAlert('info', htmlContent);
        });

        socket.on('operator_override', (data) => {
            speak(data.instruction);
            addAlert('alert', `<strong>📢 DISPATCH OVERRIDE (${data.device_id}):</strong> ${data.instruction}`);
        });

        function dispatchOverride(deviceId) {
            const val = document.getElementById('override_text_' + deviceId).value;
            fetch('/api/dispatch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    device_id: deviceId,
                    instruction: val
                })
            }).catch(e => alert("Dispatch error: " + e));
        }

        function addAlert(type, htmlContent, deviceId) {
            const alertDiv = document.getElementById('alerts');
            const noData = document.getElementById('nodata');
            if(noData) noData.remove();

            const timeStr = new Date().toLocaleTimeString();
            const ts = Date.now();

            if (type === 'alert') {
                // Create ACK-able alert entry
                const entry = document.createElement('div');
                const safeId = (deviceId || 'unk') + '-' + ts;
                entry.className = 'alert-entry unacked';
                entry.id = 'alert-entry-' + safeId;
                entry.dataset.deviceId = deviceId || '';
                entry.dataset.ts = ts;
                entry.innerHTML = `<span class="alert-text">[${timeStr}] ${htmlContent}</span><button class="ack-btn" onclick="ackAlert(this,'${deviceId || ''}','${safeId}')">\u2713 ACK</button>`;
                alertDiv.insertBefore(entry, alertDiv.firstChild);
            } else {
                const alertItem = document.createElement('div');
                alertItem.className = 'alert-item ' + type;
                alertItem.innerHTML = `[${timeStr}] ${htmlContent}`;
                alertDiv.insertBefore(alertItem, alertDiv.firstChild);
            }

            // Limit to 20 alerts
            while(alertDiv.children.length > 20) {
                alertDiv.removeChild(alertDiv.lastChild);
            }
        }

        function ackAlert(btn, deviceId, entryId) {
            const entry = document.getElementById('alert-entry-' + entryId);
            if (entry) {
                entry.classList.remove('unacked');
                entry.classList.add('acked');
            }
            btn.textContent = '\u2713 Acknowledged';
            btn.disabled = true;
            btn.style.background = '#444';
            fetch('/api/ack', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({device_id: deviceId, timestamp: entryId})
            }).catch(e => console.warn('ACK post failed', e));
        }

        // Re-announce unacked alerts every 60 seconds
        setInterval(() => {
            const unacked = document.querySelectorAll('.alert-entry.unacked');
            if (unacked.length > 0 && voiceEnabled) {
                speak(`Warning: ${unacked.length} unacknowledged alert${unacked.length > 1 ? 's' : ''} require attention.`);
            }
        }, 60000);
        function showToast(message, type="info") {
            const container = document.getElementById('toastContainer');
            if (!container) return;
            const toast = document.createElement('div');
            toast.style.background = '#14232d';
            toast.style.color = (type === 'alert' ? '#ff5050' : '#00bcd4');
            toast.style.border = "1px solid " + (type === 'alert' ? '#ff5050' : '#00bcd4');
            toast.style.padding = '12px 18px';
            toast.style.borderRadius = '6px';
            toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)';
            toast.style.fontSize = '12px';
            toast.style.fontWeight = 'bold';
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s, transform 0.3s';
            toast.style.transform = 'translateY(-10px)';
            toast.textContent = message;
            
            container.appendChild(toast);
            
            setTimeout(() => {
                toast.style.opacity = '1';
                toast.style.transform = 'translateY(0)';
            }, 50);
            
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-10px)';
                setTimeout(() => toast.remove(), 300);
            }, 5000);
        }

        function sendBroadcast() {
            const input = document.getElementById('broadcastInput');
            const message = input.value.trim();
            if (!message) return;
            
            fetch('/api/broadcast', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: message})
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'ok') {
                    input.value = '';
                } else {
                    alert('Broadcast error: ' + data.message);
                }
            })
            .catch(e => console.warn('Broadcast send failed', e));
        }

        let nodeHistory = {};

        function drawSparkline(containerId, values, color) {
            const el = document.getElementById(containerId);
            if (!el) return;
            if (values.length < 2) {
                el.innerHTML = '<span style="font-size:8px; color:#666;">Waiting...</span>';
                return;
            }
            let min = Math.min(...values);
            let max = Math.max(...values);
            let range = max - min;
            let width = 100;
            let height = 24;
            let pts = [];
            for (let i = 0; i < values.length; i++) {
                let x = i * (width / (values.length - 1));
                let y = height - 2 - (range === 0 ? (height / 2) : ((values[i] - min) / range) * (height - 4));
                pts.push(x.toFixed(1) + ',' + y.toFixed(1));
            }
            let pointStr = pts.join(' ');
            el.innerHTML = '<svg width="' + width + '" height="' + height + '" style="display:inline-block; overflow:visible;"><polyline fill="none" stroke="' + color + '" stroke-width="1.5" points="' + pointStr + '" /></svg>';
        }

        let deviceSafeZoneTarget = {};
        let activeDeviceRoutes = {};

        function updateHeatmap(deviceId, lat, lon, riskScore) {
            if (!heatLayer) return;
            // Remove previous point for this device if exists
            heatPoints = heatPoints.filter(p => p[3] !== deviceId);
            
            if (riskScore > 50) {
                // Intensity ranges from 0.5 to 1.0 depending on riskScore (50 to 100)
                let intensity = 0.5 + ((riskScore - 50) / 50) * 0.5;
                let pt = [lat, lon, intensity, deviceId];
                heatPoints.push(pt);
            }
            
            heatLayer.setLatLngs(heatPoints.map(p => [p[0], p[1], p[2]]));
        }

        function updateGeofencing(deviceId, lat, lon, riskScore) {
            // Remove existing geofence circle
            if (geofenceCircles[deviceId]) {
                map.removeLayer(geofenceCircles[deviceId]);
                delete geofenceCircles[deviceId];
            }
            // Remove existing connector lines for this device
            if (geofenceConnectors[deviceId]) {
                geofenceConnectors[deviceId].forEach(line => map.removeLayer(line));
                delete geofenceConnectors[deviceId];
            }
            
            if (riskScore > 60) {
                // Create red pulsing geofence circle
                const circle = L.circle([lat, lon], {
                    radius: 300,
                    color: '#ff5050',
                    fillColor: '#ff3030',
                    fillOpacity: 0.15,
                    weight: 2,
                    dashArray: '6,4'
                }).addTo(map);
                geofenceCircles[deviceId] = circle;
                
                // Check proximity of emergency services
                geofenceConnectors[deviceId] = [];
                const incidentLatLng = L.latLng(lat, lon);
                
                EMERGENCY_SERVICES.forEach(es => {
                    const serviceLatLng = L.latLng(es.lat, es.lon);
                    const dist = incidentLatLng.distanceTo(serviceLatLng);
                    if (dist <= 300) {
                        const line = L.polyline([incidentLatLng, serviceLatLng], {
                            color: '#00bcd4',
                            weight: 2,
                            dashArray: '4,4'
                        }).addTo(map)
                        .bindPopup('⚠️ <b>' + es.name + '</b> is within ' + Math.round(dist) + 'm of incident!');
                        
                        geofenceConnectors[deviceId].push(line);
                    }
                });
            }
        }

        function updateSafeZoneCapacity() {
            // Reset counts
            for (let id in safeZoneLoad) {
                safeZoneLoad[id] = 0;
            }
            
            // Count active routes to safe zones
            for (let deviceId in deviceSafeZoneTarget) {
                let szId = deviceSafeZoneTarget[deviceId];
                if (szId && safeZoneLoad[szId] !== undefined) {
                    if (routeLines[deviceId]) {
                        safeZoneLoad[szId]++;
                    }
                }
            }
            
            // Update circle colors and popups based on load
            for (let szId in safeZoneCircleMap) {
                let circle = safeZoneCircleMap[szId];
                let load = safeZoneLoad[szId] || 0;
                let color = '#00ff66';
                if (load >= 3) {
                    color = '#ff5050';
                } else if (load > 0) {
                    color = '#fa0';
                }
                
                circle.setStyle({
                    color: color,
                    fillColor: color
                });
                
                let sz = SAFE_ZONES.find(s => s.id === szId);
                if (sz) {
                    circle.bindPopup('<b>🟢 SAFE ZONE</b><br><b>Name:</b> ' + sz.name + '<br><b>Active Routes:</b> ' + load + ' nodes');
                }
            }
        }

        function clearRoute(deviceId) {
            if (routeLines[deviceId]) {
                map.removeLayer(routeLines[deviceId]);
                delete routeLines[deviceId];
            }
            if (routeLayerGroups[deviceId]) {
                map.removeLayer(routeLayerGroups[deviceId]);
                delete routeLayerGroups[deviceId];
            }
            if (deviceSafeZoneTarget[deviceId]) {
                delete deviceSafeZoneTarget[deviceId];
            }
            document.getElementById('turnPanel').style.display = 'none';
            updateSafeZoneCapacity();
        }

        function displayDirections(steps) {
            const stepsDiv = document.getElementById('turnSteps');
            stepsDiv.innerHTML = '';
            
            steps.forEach((step, idx) => {
                let icon = '↑';
                const modifier = (step.maneuver.modifier || '').toLowerCase();
                const type = (step.maneuver.type || '').toLowerCase();
                
                if (type === 'arrive') icon = '🏁';
                else if (modifier.includes('left')) icon = '↰';
                else if (modifier.includes('right')) icon = '↱';
                
                const distText = step.distance > 1000 ? (step.distance / 1000).toFixed(1) + ' km' : Math.round(step.distance) + ' m';
                const stepEl = document.createElement('div');
                stepEl.style.padding = '6px 0';
                stepEl.style.borderBottom = '1px solid #1e3640';
                stepEl.style.display = 'flex';
                stepEl.style.gap = '8px';
                stepEl.style.alignItems = 'center';
                stepEl.innerHTML = `<span style="font-size:14px; color:#00ff66;">${icon}</span>
                                    <div>
                                        <span style="display:block;">${step.name || 'Continue'}</span>
                                        <span style="font-size:9px; color:#8a9fa0;">${distText}</span>
                                    </div>`;
                stepsDiv.appendChild(stepEl);
            });
            
            document.getElementById('turnPanel').style.display = 'block';
        }

        // -- UI Logic & Leaflet Map --
        let map;
        let markers = {};
        let deviceData = {};
        let isPlaybackMode = false;
        let playbackLogs = [];
        let routeLines = {};
        let serviceMarkers = [];
        let heatLayer = null;
        let heatPoints = [];
        let geofenceCircles = {};
        let geofenceConnectors = {};
        let safeZoneLoad = {};
        let safeZoneCircleMap = {};
        let routeLayerGroups = {};
        
        const SAFE_ZONES = [
            {id: "Safe-Zone_Alpha", name: "Safe Zone Alpha (North)", lat: 14.4721, lon: 121.0572},
            {id: "Safe-Zone_Beta", name: "Safe Zone Beta (South)", lat: 14.4641, lon: 121.0532}
        ];

        const EMERGENCY_SERVICES = [
            {name: "Taguig-Pateros District Hospital (TPDH)", type: "Hospital", lat: 14.5108, lon: 121.0342},
            {name: "Taguig City General Hospital (TCGH)", type: "Hospital", lat: 14.5139, lon: 121.0728},
            {name: "Medical Center Taguig", type: "Hospital", lat: 14.5360, lon: 121.0667},
            {name: "St. Luke's Medical Center - BGC", type: "Hospital", lat: 14.5546, lon: 121.0494},
            {name: "BFP Taguig Central Fire Station", type: "Fire Station", lat: 14.5269, lon: 121.0754},
            {name: "Taguig Fire Substation (Bagumbayan)", type: "Fire Station", lat: 14.4790, lon: 121.0610},
            {name: "BFP Bicutan Fire Substation", type: "Fire Station", lat: 14.4983, lon: 121.0456},
            {name: "Barangay Bagumbayan Evacuation Center", type: "Evacuation Center", lat: 14.4711, lon: 121.0542},
            {name: "Signal Village Evacuation Center", type: "Evacuation Center", lat: 14.5152, lon: 121.0526},
            {name: "Hagonoy Sports Complex Evacuation Center", type: "Evacuation Center", lat: 14.5115, lon: 121.0645},
            {name: "Taguig Lakeshore Hall Evacuation Site", type: "Evacuation Center", lat: 14.5098, lon: 121.0735}
        ];

        window.addEventListener('load', function() {
            map = L.map('map').setView([14.4681, 121.0552], 15);
            
            const googleRoads = L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
                attribution: '&copy; Google Maps (Roads)',
                maxZoom: 20
            });
            const googleSatellite = L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
                attribution: '&copy; Google Maps (Satellite)',
                maxZoom: 20
            });
            const googleHybrid = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
                attribution: '&copy; Google Maps (Hybrid)',
                maxZoom: 20
            });
            const googleTerrain = L.tileLayer('https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}', {
                attribution: '&copy; Google Maps (Terrain)',
                maxZoom: 20
            });
            const localOfflineRoads = L.tileLayer('/static/tiles/{z}/{x}/{y}.png', {
                attribution: '&copy; Offline Google Maps (Local Backup)',
                minZoom: 12,
                maxZoom: 17
            });
            
            // Listen to base layer changes to toggle dark mode filter on/off
            map.on('baselayerchange', function(e) {
                const mapEl = document.getElementById('map');
                if (e.name === 'Google Satellite' || e.name === 'Google Hybrid') {
                    mapEl.classList.add('no-filter');
                } else {
                    mapEl.classList.remove('no-filter');
                }
            });
            
            // Map Layers Initialization
            googleRoads.addTo(map);

            const rainLayer = L.tileLayer('', {
                attribution: '&copy; RainViewer',
                opacity: 0.6,
                maxZoom: 20,
                maxNativeZoom: 7
            });

            heatLayer = L.heatLayer([], {radius:25, blur:15, maxZoom:17, gradient:{0.4:'blue',0.6:'yellow',0.8:'orange',1.0:'red'}});
            const elevationLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', { maxZoom: 17, attribution: '&copy; OpenTopoMap' });

            const baseMaps = {
                "Google Roads": googleRoads,
                "Google Satellite": googleSatellite,
                "Google Hybrid": googleHybrid,
                "Google Terrain": googleTerrain,
                "⛰️ Elevation (OpenTopoMap)": elevationLayer,
                "Offline Backup (Taguig)": localOfflineRoads
            };

            const overlayMaps = {
                "🌧️ Rain Radar": rainLayer,
                "🔥 Incident Heat": heatLayer
            };

            if (OWM_API_KEY) {
                overlayMaps["💨 Wind Vectors"] = L.tileLayer(`https://tile.openweathermap.org/map/wind_new/{z}/{x}/{y}.png?appid=${OWM_API_KEY}`, { opacity: 0.6, attribution: '&copy; OpenWeatherMap' });
                overlayMaps["☁️ Cloud Cover"] = L.tileLayer(`https://tile.openweathermap.org/map/clouds_new/{z}/{x}/{y}.png?appid=${OWM_API_KEY}`, { opacity: 0.6, attribution: '&copy; OpenWeatherMap' });
            }

            const parCoords = [ [5, 115], [15, 115], [21, 120], [25, 120], [25, 135], [5, 135] ];
            const parLayer = L.polygon(parCoords, {color: '#4287f5', weight: 2, fillOpacity: 0.05, dashArray: '5, 10'}).bindTooltip('Philippine Area of Responsibility (PAR)', {sticky: true});
            overlayMaps["🇵🇭 PAR Boundary"] = parLayer;

            const cycloneLayer = L.layerGroup();
            overlayMaps["🌀 Active Cyclones"] = cycloneLayer;

            L.control.layers(baseMaps, overlayMaps).addTo(map);

            // Fetch dynamic layer data
            fetch('https://api.rainviewer.com/public/weather-maps.json')
                .then(r => r.json())
                .then(d => {
                    if(d && d.radar && d.radar.past && d.radar.past.length > 0) {
                        const path = d.radar.past[d.radar.past.length - 1].path;
                        rainLayer.setUrl(`https://tilecache.rainviewer.com${path}/256/{z}/{x}/{y}/2/1_1.png`);
                    }
                }).catch(e => console.log('Rain radar error', e));

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
                }).catch(e => console.log("Cyclone load error", e));

            // Draw Safe Zones
            SAFE_ZONES.forEach(sz => {
                const circle = L.circleMarker([sz.lat, sz.lon], {
                    radius: 14,
                    color: '#0f6',
                    fillColor: '#0f6',
                    weight: 3,
                    opacity: 0.9,
                    fillOpacity: 0.3
                }).addTo(map)
                .bindPopup(`<b>${sz.name}</b><br>Emergency Assembly Point`);
                
                safeZoneCircleMap[sz.id] = circle;
                safeZoneLoad[sz.id] = 0;
            });

            // Update timestamp
            setInterval(() => {
                const now = new Date();
                document.getElementById('timestamp').textContent = now.toLocaleDateString('en-US', { 
                    weekday: 'long', month: 'short', day: 'numeric',
                    hour: '2-digit', minute: '2-digit', second: '2-digit'
                }).toUpperCase();
            }, 1000);
        });

        // Format sensor data
        function formatSensorDisplay(data) {
            if (!data) return 'No data';
            let html = '';
            const thresholds = getThresholds();
            
            if (data.risk_score !== undefined) {
                let riskClass = 'status-ok';
                let color = '#0f6';
                if (data.risk_score > 50) { riskClass = 'status-warning'; color = '#fa0'; }
                if (data.risk_score > 80) { riskClass = 'status-alert'; color = '#f44'; }
                
                html += `<div class="sensor-row">
                    <span class="sensor-label">Risk Score</span>
                    <span class="sensor-value" style="color: ${color}">${data.risk_score}/100 <span class="sensor-status ${riskClass}"></span></span>
                </div>`;
            }
            
            if (data.sensors) {
                const s = data.sensors;
                const intruder = s.life_form || s.intruder;
                if (intruder !== undefined) {
                    html += `<div class="sensor-row">
                        <span class="sensor-label">Life Form</span>
                        <span class="sensor-value" style="color: ${intruder ? '#f44' : '#0f6'}">${intruder ? 'DETECTED' : 'Clear'} <span class="sensor-status ${intruder ? 'status-alert' : 'status-ok'}"></span></span>
                    </div>`;
                }
                
                if (s.flood !== undefined) {
                    const isFloodActive = thresholds.flood && s.flood;
                    html += `<div class="sensor-row">
                        <span class="sensor-label">Flood Sensor</span>
                        <span class="sensor-value" style="color: ${isFloodActive ? '#f44' : '#0f6'}">${s.flood ? 'Water Detected' : 'Dry'} <span class="sensor-status ${isFloodActive ? 'status-alert' : 'status-ok'}"></span></span>
                    </div>`;
                }
                
                if (s.fire !== undefined) {
                    const isFireActive = thresholds.fire && s.fire;
                    html += `<div class="sensor-row">
                        <span class="sensor-label">Fire Sensor</span>
                        <span class="sensor-value" style="color: ${isFireActive ? '#f44' : '#0f6'}">${s.fire ? 'FIRE' : 'Clear'} <span class="sensor-status ${isFireActive ? 'status-alert' : 'status-ok'}"></span></span>
                    </div>`;
                }
                
                if (s.humidity !== undefined) {
                    html += `<div class="sensor-row">
                        <span class="sensor-label">Humidity</span>
                        <span class="sensor-value">${s.humidity}%</span>
                    </div>`;
                }
                
                if (s.gas !== undefined) {
                    const isGasHigh = s.gas > thresholds.gas;
                    html += `<div class="sensor-row">
                        <span class="sensor-label">Gas Level</span>
                        <span class="sensor-value" style="color: ${isGasHigh ? '#f44' : '#0f6'}">${s.gas} ppm</span>
                    </div>`;
                }
            }
            
            if (data.battery !== undefined) {
                let batColor = '#0f6';
                if (data.battery < 20) batColor = '#f44';
                else if (data.battery < 50) batColor = '#fa0';
                
                html += `<div class="sensor-row">
                    <span class="sensor-label">Battery</span>
                    <span class="sensor-value" style="color: ${batColor}">${data.battery}%</span>
                </div>
                <div class="battery-bar"><div class="battery-fill" style="width: ${data.battery}%; background: ${batColor}"></div></div>`;
            }
            return html;
        }

        function updateGlobalBadge() {
            const hasHighRisk = Object.values(deviceData).some(d => d && d.risk_score > 50);
            const badge = document.getElementById('statusBadge');
            if (hasHighRisk) {
                badge.textContent = '⚠ CRITICAL ALERTS';
                badge.style.background = '#f44';
                badge.style.color = '#fff';
            } else {
                badge.textContent = 'ALL SYSTEMS SYNCED';
                badge.style.background = '#0f6';
                badge.style.color = '#000';
            }
        }

        // Update device displays
        function updateDeviceDisplay(deviceId, data) {
            deviceData[deviceId] = data;
            
            let containerId = 'device_card_' + deviceId;
            let el = document.getElementById(containerId + '_content');
            
            if (!el) {
                const card = document.createElement('div');
                card.className = 'card';
                card.id = containerId;
                card.innerHTML = '<h3>' + deviceId + '</h3><div id="' + containerId + '_content"></div>';
                
                const targetPanel = document.getElementById('rightpanel') || document.getElementById('leftpanel');
                if (targetPanel) {
                    targetPanel.appendChild(card);
                }
                el = document.getElementById(containerId + '_content');
            }
            
            el.innerHTML = formatSensorDisplay(data);
            
            // Maintain history for trend sparklines (Feature 6)
            if (!nodeHistory[deviceId]) {
                nodeHistory[deviceId] = { gas: [], battery: [] };
            }
            
            if (data.sensors && data.sensors.gas !== undefined) {
                nodeHistory[deviceId].gas.push(data.sensors.gas);
            }
            if (data.battery !== undefined) {
                nodeHistory[deviceId].battery.push(data.battery);
            }
            
            if (nodeHistory[deviceId].gas.length > 20) nodeHistory[deviceId].gas.shift();
            if (nodeHistory[deviceId].battery.length > 20) nodeHistory[deviceId].battery.shift();
            
            // Add sparkline container below sensor values
            const sparkContainer = document.createElement('div');
            sparkContainer.style.display = 'flex';
            sparkContainer.style.justifyContent = 'space-between';
            sparkContainer.style.marginTop = '8px';
            sparkContainer.style.paddingTop = '8px';
            sparkContainer.style.borderTop = '1px dashed #1e3640';
            sparkContainer.innerHTML = `
                <div style="flex:1; text-align:center;">
                    <span style="font-size:9px; color:#8a9fa0; display:block;">Gas Trend</span>
                    <div id="sparkline-gas-${deviceId}"></div>
                </div>
                <div style="flex:1; text-align:center;">
                    <span style="font-size:9px; color:#8a9fa0; display:block;">Battery Trend</span>
                    <div id="sparkline-bat-${deviceId}"></div>
                </div>
            `;
            el.appendChild(sparkContainer);
            
            drawSparkline('sparkline-gas-' + deviceId, nodeHistory[deviceId].gas, '#fa0');
            drawSparkline('sparkline-bat-' + deviceId, nodeHistory[deviceId].battery, '#0f6');
            
            // Add camera toggler (Feature 20)
            const camContainer = document.createElement('div');
            camContainer.style.marginTop = '6px';
            camContainer.innerHTML = `
                <div class="cam-section" id="cam-${deviceId}" style="display:none; margin-top:8px;">
                    <img id="cam-img-${deviceId}" style="width:100%; border-radius:4px; border:1px solid #1e3640;" src="" onerror="this.style.display='none'">
                </div>
                <button class="cam-toggle" onclick="toggleCam('${deviceId}')" style="margin-top:6px; background:#14232d; border:1px solid #1e3640; color:#00bcd4; font-size:10px; padding:3px 8px; border-radius:3px; cursor:pointer; width:100%;">📷 Camera Feed</button>
            `;
            el.appendChild(camContainer);
            
            if (data.lat !== undefined && data.lon !== undefined && data.risk_score !== undefined) {
                updateHeatmap(deviceId, data.lat, data.lon, data.risk_score);
                updateGeofencing(deviceId, data.lat, data.lon, data.risk_score);
            }
            
            updateGlobalBadge();
        }

        // Add or update marker on map and draw evacuation routing
        function addOrUpdateMarker(deviceId, lat, lon, data) {
            if(!lat || !lon) return;
            let color = (data.risk_score > 50) ? '#f44' : '#0f6';
            if (data.is_faulty) color = '#fa0';
            
            if (markers[deviceId]) {
                markers[deviceId].setLatLng([lat, lon]);
                markers[deviceId].setStyle({color: color, fillColor: color});
            } else {
                const marker = L.circleMarker([lat, lon], {
                    radius: 12, color: color, weight: 2, opacity: 0.8, fillOpacity: 0.6
                }).addTo(map);
                markers[deviceId] = marker;
            }
            markers[deviceId].bindPopup(`<b>${deviceId}</b><br>Risk Score: ${data.risk_score || 0}<br>Status: ${data.is_faulty ? 'Hardware Fault' : 'Normal'}`);
            
            // Route mapping to nearest safe zone
            if (data.risk_score > 50 && !data.is_faulty) {
                let nearest = null;
                let minDist = Infinity;
                SAFE_ZONES.forEach(sz => {
                    let d = Math.pow(sz.lat - lat, 2) + Math.pow(sz.lon - lon, 2);
                    if (d < minDist) {
                        minDist = d;
                        nearest = sz;
                    }
                });
                
                if (nearest) {
                    drawEvacuationRoute(deviceId, lat, lon, nearest);
                }
            } else {
                clearRoute(deviceId);
            }
        }


        function drawEvacuationRoute(deviceId, lat, lon, nearest) {
            clearRoute(deviceId);
            
            deviceSafeZoneTarget[deviceId] = nearest.id;
            
            const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${lon},${lat};${nearest.lon},${nearest.lat}?overview=full&geometries=geojson&alternatives=true&steps=true`;
            
            fetch(osrmUrl)
                .then(res => res.json())
                .then(data => {
                    if (data.routes && data.routes.length > 0) {
                        const group = L.layerGroup().addTo(map);
                        routeLayerGroups[deviceId] = group;
                        activeDeviceRoutes[deviceId] = [];
                        
                        data.routes.slice(0, 3).forEach((route, idx) => {
                            const coords = route.geometry.coordinates.map(c => [c[1], c[0]]);
                            
                            let style = {};
                            if (idx === 0) {
                                style = { color: '#00ff66', weight: 5, opacity: 0.9 };
                            } else if (idx === 1) {
                                style = { color: '#00bcd4', weight: 4, opacity: 0.5, dashArray: '8,4' };
                            } else {
                                style = { color: '#8a9fa0', weight: 4, opacity: 0.4, dashArray: '4,8' };
                            }
                            
                            const polyline = L.polyline(coords, style).addTo(group);
                            activeDeviceRoutes[deviceId].push({
                                polyline: polyline,
                                routeData: route,
                                index: idx
                            });
                            
                            const dist = (route.distance / 1000).toFixed(1) + ' km';
                            const dur = Math.round(route.duration / 60) + ' min';
                            polyline.bindTooltip('<b>Route ' + (idx + 1) + '</b><br>' + dur + ' (' + dist + ')', {
                                permanent: false,
                                sticky: true
                            });
                            
                            polyline.on('click', () => {
                                selectRoute(deviceId, idx);
                            });
                        });
                        
                        // Select primary route by default
                        selectRoute(deviceId, 0);
                    } else {
                        drawFallbackRoute(deviceId, lat, lon, nearest);
                    }
                })
                .catch(() => {
                    drawFallbackRoute(deviceId, lat, lon, nearest);
                });
        }

        function selectRoute(deviceId, routeIndex) {
            const routes = activeDeviceRoutes[deviceId];
            if (!routes) return;
            
            routes.forEach(r => {
                let style = {};
                if (r.index === routeIndex) {
                    if (r.index === 0) style = { color: '#00ff66', weight: 6, opacity: 1.0, dashArray: '' };
                    else if (r.index === 1) style = { color: '#00bcd4', weight: 6, opacity: 1.0, dashArray: '' };
                    else style = { color: '#fa0', weight: 6, opacity: 1.0, dashArray: '' };
                    
                    r.polyline.setStyle(style);
                    r.polyline.bringToFront();
                    
                    routeLines[deviceId] = r.polyline;
                    
                    if (r.routeData.legs && r.routeData.legs[0].steps) {
                        displayDirections(r.routeData.legs[0].steps);
                    }
                } else {
                    if (r.index === 0) style = { color: '#00ff66', weight: 3, opacity: 0.3, dashArray: '4,4' };
                    else if (r.index === 1) style = { color: '#00bcd4', weight: 3, opacity: 0.3, dashArray: '4,4' };
                    else style = { color: '#8a9fa0', weight: 3, opacity: 0.3, dashArray: '4,4' };
                    
                    r.polyline.setStyle(style);
                }
            });
            
            updateSafeZoneCapacity();
        }

        function drawFallbackRoute(deviceId, lat, lon, nearest) {
            clearRoute(deviceId);
            deviceSafeZoneTarget[deviceId] = nearest.id;
            
            routeLines[deviceId] = L.polyline([[lat, lon], [nearest.lat, nearest.lon]], {
                color: '#fa0',
                weight: 3,
                dashArray: '5, 10',
                opacity: 0.8
            }).addTo(map);
            
            updateSafeZoneCapacity();
        }

        function backupSystemCode() {
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = "Dispatched...";
            btn.disabled = true;
            
            fetch('/api/backup', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'ok') {
                        alert("System backup email dispatched to erosrohantorres@gmail.com!");
                    } else {
                        alert("Backup failed: " + data.message);
                    }
                })
                .catch(err => {
                    alert("Error sending backup request: " + err);
                })
                .finally(() => {
                    btn.textContent = originalText;
                    btn.disabled = false;
                });
        }

        /* ---- Settings Modal ---- */
        function openSettings() {
            document.getElementById('settingsModal').classList.add('active');
            loadSettingsIntoForm();
            loadThresholdSettings();
            populateCameraConfigList();
        }
        function closeSettings() {
            document.getElementById('settingsModal').classList.remove('active');
        }

        function getThresholds() {
            try {
                const t = localStorage.getItem('vers_thresholds');
                if (t) return JSON.parse(t);
            } catch(e) {}
            return { gas: 200, flood: true, fire: true };
        }

        function getCameraIPs() {
            try {
                const ips = localStorage.getItem('vers_cam_ips');
                if (ips) return JSON.parse(ips);
            } catch(e) {}
            return {};
        }

        function populateCameraConfigList() {
            const container = document.getElementById('cam_ips_config_list');
            if (!container) return;
            container.innerHTML = '';
            
            const ips = getCameraIPs();
            const nodes = ['Node_01','Node_02','Node_03','V-Node_01','V-Node_02','V-Node_03','V-Node_04','V-Node_05','V-Node_06','V-Node_07','V-Node_08','V-Node_09','V-Node_10'];
            
            nodes.forEach(n => {
                const ip = ips[n] || '';
                const row = document.createElement('div');
                row.style.display = 'flex';
                row.style.justifyContent = 'space-between';
                row.style.alignItems = 'center';
                row.style.marginBottom = '6px';
                row.innerHTML = `<span style="font-size:11px; font-weight:bold;">${n}</span>
                                 <input type="text" class="cam-ip-input" data-device-id="${n}" value="${ip}" placeholder="e.g. 192.168.1.50" style="width:160px; padding:4px 8px; background:#0b141c; border:1px solid #1e3640; color:#fff; border-radius:3px; font-size:11px;">`;
                container.appendChild(row);
            });
        }

        function toggleCam(deviceId) {
            const div = document.getElementById('cam-' + deviceId);
            const img = document.getElementById('cam-img-' + deviceId);
            if (!div || !img) return;
            
            if (div.style.display === 'none') {
                const ips = getCameraIPs();
                const ip = ips[deviceId];
                if (!ip) {
                    alert('No Camera IP configured for ' + deviceId + ' in Settings -> Thresholds');
                    return;
                }
                img.src = 'http://' + ip + ':8080/?action=stream';
                img.style.display = 'block';
                div.style.display = 'block';
            } else {
                div.style.display = 'none';
                img.src = '';
            }
        }

        function loadThresholdSettings() {
            const t = getThresholds();
            document.getElementById('th_gas_global').value = t.gas;
            document.getElementById('th_flood_global').checked = t.flood;
            document.getElementById('th_fire_global').checked = t.fire;
        }

        function saveThresholdSettings() {
            const gas = parseInt(document.getElementById('th_gas_global').value) || 200;
            const flood = document.getElementById('th_flood_global').checked;
            const fire = document.getElementById('th_fire_global').checked;
            
            localStorage.setItem('vers_thresholds', JSON.stringify({ gas, flood, fire }));
            
            // Save Camera IPs
            const ips = {};
            document.querySelectorAll('.cam-ip-input').forEach(input => {
                const devId = input.dataset.deviceId;
                const val = input.value.trim();
                if (devId && val) {
                    ips[devId] = val;
                }
            });
            localStorage.setItem('vers_cam_ips', JSON.stringify(ips));
            
            showToast("Settings saved locally", "info");
            closeSettings();
            
            // Re-render node cards to apply new settings immediately
            for (let devId in deviceData) {
                updateDeviceDisplay(devId, deviceData[devId]);
            }
        }

        function switchTab(tabId) {
            document.querySelectorAll('.stab-panel').forEach(p => p.style.display = 'none');
            document.querySelectorAll('.stab').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).style.display = 'block';
            const btnId = 'stab-' + tabId.replace('tab-', '');
            const btn = document.getElementById(btnId);
            if (btn) btn.classList.add('active');
        }

        function loadSettingsIntoForm() {
            fetch('/api/settings')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('cfg_smtp_server').value   = d.smtp_server  || '';
                    document.getElementById('cfg_smtp_port').value     = d.smtp_port    || '';
                    document.getElementById('cfg_sender_email').value  = d.sender_email || '';
                    document.getElementById('cfg_sender_password').value = '';  // always blank for security
                    document.getElementById('cfg_recipient_email').value = d.recipient_email || '';
                }).catch(() => {});
        }

        function saveSettings() {
            const msg = document.getElementById('settingsSaveMsg');
            const payload = {
                smtp_server:     document.getElementById('cfg_smtp_server').value.trim(),
                smtp_port:       parseInt(document.getElementById('cfg_smtp_port').value) || 587,
                sender_email:    document.getElementById('cfg_sender_email').value.trim(),
                sender_password: document.getElementById('cfg_sender_password').value,
                recipient_email: document.getElementById('cfg_recipient_email').value.trim(),
                dashboard_password: document.getElementById('cfg_dashboard_password').value
            };
            fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(d => {
                msg.style.display = 'block';
                if (d.status === 'ok') {
                    msg.style.background = 'rgba(0,255,102,.12)';
                    msg.style.color = '#00ff66';
                    msg.style.border = '1px solid #00ff66';
                    msg.textContent = '✅ Settings saved and applied.';
                    document.getElementById('cfg_dashboard_password').value = '';
                } else {
                    msg.style.background = 'rgba(255,80,80,.12)';
                    msg.style.color = '#ff5050';
                    msg.style.border = '1px solid #ff5050';
                    msg.textContent = '❌ ' + d.message;
                }
                setTimeout(() => { msg.style.display = 'none'; }, 4000);
            })
            .catch(e => {
                msg.style.display = 'block';
                msg.style.color = '#ff5050';
                msg.textContent = '❌ Network error: ' + e;
            });
        }

        let voiceEnabled = true;
        function applyDisplaySettings() {
            const showServices = document.getElementById('chk_services').checked;
            const showSafe     = document.getElementById('chk_safe_zones').checked;
            voiceEnabled       = document.getElementById('chk_voice').checked;

            // Toggle emergency service markers
            if (typeof emergencyMarkers !== 'undefined') {
                emergencyMarkers.forEach(m => showServices ? m.addTo(map) : m.remove());
            }
            // Toggle safe zone circles
            if (typeof safeZoneCircles !== 'undefined') {
                safeZoneCircles.forEach(c => showSafe ? c.addTo(map) : c.remove());
            }
            closeSettings();
        }

        function backupSystemCode() {
            const btn = document.getElementById('backupBtn');
            const msg = document.getElementById('backupMsg');
            btn.textContent = '⏳ Sending...';
            btn.disabled = true;

            fetch('/api/backup', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    msg.style.display = 'block';
                    if (d.status === 'ok') {
                        msg.style.background = 'rgba(0,188,212,.12)';
                        msg.style.color = '#00bcd4';
                        msg.style.border = '1px solid #00bcd4';
                        msg.textContent = '📤 Backup dispatched — check your inbox!';
                    } else {
                        msg.style.background = 'rgba(255,80,80,.12)';
                        msg.style.color = '#ff5050';
                        msg.style.border = '1px solid #ff5050';
                        msg.textContent = '❌ ' + d.message;
                    }
                })
                .catch(e => {
                    msg.style.display = 'block';
                    msg.style.color = '#ff5050';
                    msg.textContent = '❌ Error: ' + e;
                })
                .finally(() => {
                    btn.textContent = '📤 Send Email Backup';
                    btn.disabled = false;
                });
        }

        function sendSimulatedData() {
            // Try new sim2_ IDs first, fall back to legacy IDs
            const deviceEl = document.getElementById('sim2_device') || document.getElementById('simulateDevice');
            const deviceId = deviceEl ? deviceEl.value : '';
            if (!deviceId) return alert('Please select a device');

            function getVal(newId, oldId) {
                const el = document.getElementById(newId) || document.getElementById(oldId);
                return el ? el.value : '0';
            }

            const data = {
                id: deviceId,
                timestamp: new Date().toISOString(),
                sensors: {
                    life_form: parseInt(getVal('sim2_life_form', 'simLifeForm')),
                    flood:     parseInt(getVal('sim2_flood',     'simFlood')),
                    fire:      parseInt(getVal('sim2_fire',      'simFire')),
                    humidity:  50,
                    gas:       parseInt(getVal('sim2_gas',       'simGas'))
                },
                battery: parseInt(getVal('sim2_battery', 'simBattery')),
                lat: parseFloat(getVal('sim2_lat', 'simLat')),
                lon: parseFloat(getVal('sim2_lon', 'simLon'))
            };

            fetch('/api/simulate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            }).then(() => closeSettings()).catch(e => alert("Error: " + e));
        }

        function triggerEmergency() { fetch('/api/emergency', {method: 'POST'}); }

        function clearEmergency() {
            document.getElementById('alerts').innerHTML = '<div id="nodata">No active alerts</div>';
            for (let id in deviceData) {
                if (deviceData[id]) {
                    deviceData[id].risk_score = 0;
                    deviceData[id].is_faulty = false;
                }
            }
            updateGlobalBadge();
            for (let id in markers) {
                markers[id].setStyle({color: '#0f6', fillColor: '#0f6'});
            }
            Object.keys(routeLines).forEach(key => {
                map.removeLayer(routeLines[key]);
            });
            routeLines = {};
        }
        
        function togglePlaybackMode() {
            isPlaybackMode = !isPlaybackMode;
            const btn = document.getElementById('playbackToggleBtn');
            const controls = document.getElementById('playbackControls');
            const realTimeTs = document.getElementById('timestamp');
            const statusBadge = document.getElementById('statusBadge');
            
            if (isPlaybackMode) {
                btn.textContent = '🟢 Real-Time Mode';
                btn.style.background = '#0f6';
                btn.style.color = '#000';
                controls.style.display = 'flex';
                realTimeTs.style.display = 'none';
                statusBadge.textContent = 'PAUSED / PLAYBACK';
                statusBadge.style.background = '#fa0';
                statusBadge.style.color = '#000';
                
                fetch('/api/history')
                    .then(res => res.json())
                    .then(data => {
                        playbackLogs = data;
                        if (playbackLogs.length > 0) {
                            const slider = document.getElementById('playbackSlider');
                            slider.max = playbackLogs.length - 1;
                            slider.value = playbackLogs.length - 1;
                            showPlaybackLog(playbackLogs.length - 1);
                        } else {
                            alert("No historical logs available.");
                        }
                    });
            } else {
                btn.textContent = '⏮ Playback Mode';
                btn.style.background = '#3a2512';
                btn.style.color = '#fa0';
                controls.style.display = 'none';
                realTimeTs.style.display = 'block';
                statusBadge.textContent = 'ALL SYSTEMS SYNCED';
                statusBadge.style.background = '#0f6';
                statusBadge.style.color = '#000';
                Object.keys(routeLines).forEach(key => {
                    map.removeLayer(routeLines[key]);
                });
                routeLines = {};
                updateGlobalBadge();
            }
        }
        
        document.getElementById('playbackSlider').oninput = function() {
            showPlaybackLog(parseInt(this.value));
        };
        
        function showPlaybackLog(index) {
            if (index < 0 || index >= playbackLogs.length) return;
            const log = playbackLogs[index];
            const payload = log.payload;
            const ts = log.timestamp;
            
            const logTime = new Date(ts);
            document.getElementById('playbackTime').textContent = logTime.toLocaleTimeString() + ' (' + (index + 1) + '/' + playbackLogs.length + ')';
            
            updateDeviceDisplay(log.device_id, payload);
            addOrUpdateMarker(log.device_id, payload.lat, payload.lon, payload);
        }
        
        function toggleEmergencyServicesOverlay(show) {
            serviceMarkers.forEach(m => map.removeLayer(m));
            serviceMarkers = [];
            
            if (show) {
                EMERGENCY_SERVICES.forEach(es => {
                    const marker = L.circleMarker([es.lat, es.lon], {
                        radius: 8,
                        color: '#00bcd4',
                        fillColor: '#00bcd4',
                        weight: 2,
                        opacity: 0.9,
                        fillOpacity: 0.7
                    }).addTo(map)
                    .bindPopup(`<b>🚑 EMERGENCY SERVICES</b><br><b>Name:</b> ${es.name}<br><b>Type:</b> ${es.type}`);
                    serviceMarkers.push(marker);
                });
            }
        }

        function requestGPS() { alert("GPS Request sent to all devices"); }
        document.getElementById('settingsModal').addEventListener('click', function(e) { if (e.target === this) closeSettings(); });
        // Mobile map resize recalculation
        setTimeout(() => { if(typeof map !== 'undefined' && map) map.invalidateSize(); }, 500);
        window.addEventListener("resize", () => { if(typeof map !== 'undefined' && map) map.invalidateSize(); });
    

