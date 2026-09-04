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
            utterance.onstart = () => { const el = document.getElementById('voiceStatus'); if (el) el.textContent = '🔊 Speaking...'; };
            utterance.onend = () => {
                isSpeaking = false;
                const el = document.getElementById('voiceStatus'); if (el) el.textContent = '🔇 TTS Ready';
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
            
            // Feature 4: Automated Evacuation Routing
            if (data.priority === 'high' && data.device && markers[data.device]) {
                const devLatLng = markers[data.device].getLatLng();
                const evapCenters = EMERGENCY_SERVICES.filter(es => es.type === 'Evacuation Center');
                if (evapCenters.length > 0) {
                    let nearest = evapCenters[0];
                    let minDist = devLatLng.distanceTo(L.latLng(nearest.lat, nearest.lon));
                    evapCenters.forEach(es => {
                        let dist = devLatLng.distanceTo(L.latLng(es.lat, es.lon));
                        if (dist < minDist) { minDist = dist; nearest = es; }
                    });
                    
                    const distKm = (minDist / 1000).toFixed(2);
                    const etaMins = Math.round((minDist / 1000) / 5 * 60);
                    
                    const evapLine = L.polyline([devLatLng, [nearest.lat, nearest.lon]], {
                        color: 'green', weight: 4, dashArray: '10, 10'
                    }).addTo(map).bindPopup(`<b>To ${nearest.name}</b><br>Distance: ${distKm} km<br>ETA (Walking): ${etaMins} mins`);
                    
                    const pulsingMarker = L.marker([nearest.lat, nearest.lon], {
                        icon: L.divIcon({ className: 'pulsing-evac' })
                    }).addTo(map);
                    
                    setTimeout(() => {
                        if (map.hasLayer(evapLine)) map.removeLayer(evapLine);
                        if (map.hasLayer(pulsingMarker)) map.removeLayer(pulsingMarker);
                    }, 5 * 60 * 1000);
                }
            }
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

        socket.on('class_suspension_update', (data) => {
            showToast("🎒 Class Suspension Alert: " + data.level, "warning");
            if (typeof renderClassSuspension === 'function') {
                renderClassSuspension(data, 'official');
            }
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
                    <div><strong>🤖 AI INSTRUCTION (${data.device_id}):</strong> <span style="color:#fa0; font-size:12px; font-weight:bold;">${prefix}</span></div>
                    <textarea id="override_text_${data.device_id}" style="width:100%; height:60px; background:rgba(0,0,0,0.6); border:1px solid #fa0; color:#cfe8d6; font-family:sans-serif; font-size:13px; padding:6px; border-radius:4px; resize:none; outline:none;">${cleanAnalysis}</textarea>
                    <div style="text-align:right;">
                        <button style="font-size:12px; padding:2px 8px; background:#fa0; color:#000; border:none; border-radius:3px; cursor:pointer; font-weight:bold;" onclick="dispatchOverride('${data.device_id}')">📢 Dispatch & Announce</button>
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
            
            // Anti-thrashing: check if similar alert exists
            const existing = Array.from(alertDiv.children).find(el => el.dataset.content === htmlContent);
            if (existing) {
                // Just update timestamp, prevent DOM jump
                const tsSpan = existing.querySelector('.alert-ts');
                if(tsSpan) tsSpan.textContent = `[${timeStr}]`;
                return;
            }

            if (type === 'alert') {
                const entry = document.createElement('div');
                const safeId = (deviceId || 'unk') + '-' + ts;
                entry.className = 'alert-entry unacked';
                entry.id = 'alert-entry-' + safeId;
                entry.dataset.deviceId = deviceId || '';
                entry.dataset.ts = ts;
                entry.dataset.content = htmlContent;
                entry.innerHTML = `<span class="alert-ts">[${timeStr}]</span> <span class="alert-text">${htmlContent}</span><button class="ack-btn" onclick="ackAlert(this,'${deviceId || ''}','${safeId}')">✓ ACK</button>`;
                alertDiv.insertBefore(entry, alertDiv.firstChild);
            } else {
                const alertItem = document.createElement('div');
                alertItem.className = 'alert-item ' + type;
                alertItem.dataset.content = htmlContent;
                alertItem.innerHTML = `<span class="alert-ts">[${timeStr}]</span> ${htmlContent}`;
                alertDiv.insertBefore(alertItem, alertDiv.firstChild);
            }

            // Limit to 20 alerts
            while(alertDiv.children.length > 20) {
                alertDiv.removeChild(alertDiv.lastChild);
            }
            updateMobileAlertBadge();
        }

        function updateMobileAlertBadge() {
            const unackedCount = document.querySelectorAll('#alerts .alert-entry.unacked').length;
            const badge = document.getElementById('mobileAlertBadge');
            if (badge) {
                if (unackedCount > 0) {
                    badge.textContent = unackedCount;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
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
            updateMobileAlertBadge();
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
            let savedState = { lat: 14.4681, lng: 121.0552, zoom: 15, baseMap: "Google Roads" };
            try { 
                const savedStr = localStorage.getItem('vers_map_state');
                if (savedStr) savedState = JSON.parse(savedStr); 
            } catch (e) {}

            map = L.map('map', { preferCanvas: true }).setView([savedState.lat, savedState.lng], savedState.zoom);
            
            const googleRoads = L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
                attribution: '&copy; Google Maps (Roads)',
                maxZoom: 20
            });
            const darkMatter = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; CartoDB Dark Matter',
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
            const osmStandard = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap',
                maxZoom: 19
            });
            const localOfflineRoads = L.tileLayer('/static/tiles/{z}/{x}/{y}.png', {
                attribution: '&copy; Offline Google Maps (Local Backup)',
                minZoom: 12,
                maxZoom: 17
            });
            
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
                "Dark Mode (CartoDB)": darkMatter,
                "OpenStreetMap": osmStandard,
                "⛰️ Elevation (OpenTopoMap)": elevationLayer,
                "Offline Backup (Taguig)": localOfflineRoads
            };

            const selectedBaseMap = baseMaps[savedState.baseMap] || googleRoads;
            selectedBaseMap.addTo(map);

            const overlayMaps = {
                "🌧️ Rain Radar": rainLayer,
                "🔥 Incident Heat": heatLayer
            };

            const owmKey = (typeof window.OWM_API_KEY !== 'undefined' && window.OWM_API_KEY && window.OWM_API_KEY !== "__OWM_API_KEY__") ? window.OWM_API_KEY.trim() : "";
            if (owmKey) {
                overlayMaps["💨 Wind Vectors"] = L.tileLayer(`https://tile.openweathermap.org/map/wind_new/{z}/{x}/{y}.png?appid=${owmKey}`, { opacity: 0.6, attribution: '&copy; OpenWeatherMap' });
                overlayMaps["☁️ Cloud Cover"] = L.tileLayer(`https://tile.openweathermap.org/map/clouds_new/{z}/{x}/{y}.png?appid=${owmKey}`, { opacity: 0.6, attribution: '&copy; OpenWeatherMap' });
            }

            const parCoords = [ [5, 115], [15, 115], [21, 120], [25, 120], [25, 135], [5, 135] ];
            const parLayer = L.polygon(parCoords, {color: '#4287f5', weight: 2, fillOpacity: 0.05, dashArray: '5, 10'}).bindTooltip('Philippine Area of Responsibility (PAR)', {sticky: true});
            overlayMaps["🇵🇭 PAR Boundary"] = parLayer;

            const cycloneLayer = L.layerGroup();
            cycloneLayer.addTo(map);
            overlayMaps["🌀 Cyclones & Rainfall Warnings"] = cycloneLayer;

            const animatedWindLayer = L.layerGroup();
            overlayMaps["💨 Animated Wind"] = animatedWindLayer;

            const floodLayer = L.layerGroup();
            L.polygon([[14.465, 121.050], [14.465, 121.062], [14.475, 121.062], [14.475, 121.050]], {color: 'red', fillColor: 'red', fillOpacity: 0.25}).bindPopup('<b>Barangay Bagumbayan</b><br>Risk: HIGH (Lakeshore)').addTo(floodLayer);
            L.polygon([[14.493, 121.040], [14.493, 121.055], [14.503, 121.055], [14.503, 121.040]], {color: 'orange', fillColor: 'orange', fillOpacity: 0.2}).bindPopup('<b>Lower Bicutan</b><br>Risk: MODERATE').addTo(floodLayer);
            L.polygon([[14.505, 121.060], [14.505, 121.075], [14.515, 121.075], [14.515, 121.060]], {color: 'red', fillColor: 'red', fillOpacity: 0.25}).bindPopup('<b>Hagonoy</b><br>Risk: HIGH (Near Lake)').addTo(floodLayer);
            L.polygon([[14.510, 121.048], [14.510, 121.058], [14.520, 121.058], [14.520, 121.048]], {color: 'orange', fillColor: 'orange', fillOpacity: 0.2}).bindPopup('<b>Signal Village</b><br>Risk: MODERATE').addTo(floodLayer);
            overlayMaps["🌊 Flood Susceptibility"] = floodLayer;

            const publicReportsLayer = L.layerGroup();
            overlayMaps["📱 Public Reports"] = publicReportsLayer;

            const emojiMap = { 'Flood': '🌊', 'Fire': '🔥', 'Landslide': '⛰️', 'Earthquake Damage': '🏚️', 'Road Blocked': '🚧', 'Other': '❓' };
            function renderPublicReport(report) {
                const emoji = emojiMap[report.report_type] || '❓';
                const icon = L.divIcon({ html: `<div style="font-size: 20px;">${emoji}</div>`, className: 'public-report-icon', iconSize: [24, 24] });
                const marker = L.marker([report.lat, report.lon], { icon }).addTo(publicReportsLayer);
                marker.bindPopup(`<b>${emoji} ${report.report_type}</b> <span style="background:red;color:white;padding:2px 4px;border-radius:3px;font-size:12px;">UNVERIFIED</span><br><b>Desc:</b> ${report.description}<br><b>Reporter:</b> ${report.reporter_name}<br><b>Time:</b> ${new Date(report.timestamp).toLocaleString()}`);
            }

            function fetchPublicReports() {
                publicReportsLayer.clearLayers();
                fetch('/api/reports').then(res => res.json()).then(data => {
                    if (data && Array.isArray(data.data)) data.data.forEach(renderPublicReport);
                }).catch(e => console.warn('No public reports found'));
            }
            fetchPublicReports();
            setInterval(fetchPublicReports, 5 * 60 * 1000);
            
            socket.on('new_public_report', (data) => {
                renderPublicReport(data);
                showToast(`New Public Report: ${data.report_type}`);
            });

            // --- HazardHunterPH Feature ---
            let hazardModeActive = false;
            let hazardMarker = null;
            let hazardCircle = null;
            
            const PH_VOLCANOES = [
                {name: "Taal Volcano", lat: 14.0113, lon: 120.9977, type: "Active"},
                {name: "Mount Mayon", lat: 13.2548, lon: 123.6861, type: "Active"},
                {name: "Mount Pinatubo", lat: 15.1432, lon: 120.3500, type: "Active"},
                {name: "Mount Kanlaon", lat: 10.4116, lon: 123.1328, type: "Active"}
            ];
            
            const WEST_VALLEY_FAULT = [
                [14.7333, 121.1000], [14.6333, 121.0833], [14.5500, 121.0500],
                [14.4833, 121.0500], [14.4000, 121.0333], [14.2333, 121.0500]
            ];

            const wvFaultLayer = L.polyline(WEST_VALLEY_FAULT, {color: 'red', weight: 3, dashArray: '10, 10'}).bindTooltip('West Valley Fault Line (Approx)', {sticky: true});
            overlayMaps["⚠️ West Valley Fault"] = wvFaultLayer;
            
            const volcanoLayer = L.layerGroup();
            PH_VOLCANOES.forEach(v => {
                L.marker([v.lat, v.lon], {
                    icon: L.divIcon({className: 'custom-div-icon', html: '<div style="font-size:20px;">🌋</div>', iconSize: [24,24]})
                }).bindTooltip(`${v.name} (${v.type})`, {sticky: true}).addTo(volcanoLayer);
            });
            overlayMaps["🌋 Active Volcanoes"] = volcanoLayer;

            window.toggleHazardHunter = function() {
                hazardModeActive = !hazardModeActive;
                const btn = document.getElementById('hazardHunterBtn');
                if(hazardModeActive) {
                    btn.style.background = '#0f6';
                    btn.style.color = '#000';
                    document.getElementById('map').style.cursor = 'crosshair';
                    showToast('Hazard Hunter Mode ACTIVE. Click anywhere on the map to run a site-specific risk assessment.');
                } else {
                    btn.style.background = '#1e3640';
                    btn.style.color = '#0f6';
                    document.getElementById('map').style.cursor = '';
                    if(hazardMarker) map.removeLayer(hazardMarker);
                    if(hazardCircle) map.removeLayer(hazardCircle);
                    showToast('Hazard Hunter Mode Disabled.');
                }
            };

            map.on('click', function(e) {
                if(!hazardModeActive) return;
                
                if(hazardMarker) map.removeLayer(hazardMarker);
                if(hazardCircle) map.removeLayer(hazardCircle);
                
                let minFaultDist = Infinity;
                WEST_VALLEY_FAULT.forEach(coord => {
                    const d = map.distance(e.latlng, L.latLng(coord[0], coord[1]));
                    if(d < minFaultDist) minFaultDist = d;
                });
                
                let minVolcDist = Infinity;
                let nearestVolc = "";
                PH_VOLCANOES.forEach(v => {
                    const d = map.distance(e.latlng, L.latLng(v.lat, v.lon));
                    if(d < minVolcDist) {
                        minVolcDist = d;
                        nearestVolc = v.name;
                    }
                });

                const faultKm = (minFaultDist / 1000).toFixed(2);
                const volcKm = (minVolcDist / 1000).toFixed(2);
                
                let faultRisk = faultKm < 5 ? '<span style="color:#f44;font-weight:bold;">HIGH RISK</span>' : '<span style="color:#0f6;">SAFE</span>';
                let volcRisk = volcKm < 20 ? '<span style="color:#f44;font-weight:bold;">HIGH RISK</span>' : (volcKm < 50 ? '<span style="color:#fa0;font-weight:bold;">ASHFALL RISK</span>' : '<span style="color:#0f6;">SAFE</span>');

                hazardCircle = L.circle(e.latlng, {radius: 5000, color: '#f44', fillOpacity: 0.1, dashArray: '5,10'}).addTo(map);
                hazardMarker = L.marker(e.latlng).addTo(map)
                    .bindPopup(`
                        <div style="font-family:monospace; font-size:12px; width:220px;">
                            <h3 style="color:#00bcd4; margin-bottom:8px; border-bottom:1px solid #00bcd4; padding-bottom:4px;">🎯 Hazard Assessment</h3>
                            <strong>Location:</strong> ${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}<br><br>
                            <strong>〰️ Nearest Active Fault:</strong><br>
                            West Valley Fault: ${faultKm} km<br>
                            Risk: ${faultRisk}<br><br>
                            <strong>🌋 Nearest Volcano:</strong><br>
                            ${nearestVolc}: ${volcKm} km<br>
                            Risk: ${volcRisk}<br><br>
                            <i style="color:#888;font-size:12px;">Generated via HazardHunter Protocol</i>
                        </div>
                    `).openPopup();
            });

            L.control.layers(baseMaps, overlayMaps).addTo(map);

            function saveMapState() {
                const center = map.getCenter();
                let activeBase = savedState.baseMap;
                localStorage.setItem('vers_map_state', JSON.stringify({
                    lat: center.lat,
                    lng: center.lng,
                    zoom: map.getZoom(),
                    baseMap: activeBase
                }));
            }
            map.on('moveend', saveMapState);
            map.on('zoomend', saveMapState);
            map.on('baselayerchange', function(e) {
                savedState.baseMap = e.name;
                saveMapState();
            });

            const drawnItems = new L.FeatureGroup();
            map.addLayer(drawnItems);
            const drawControl = new L.Control.Draw({
                edit: { featureGroup: drawnItems },
                draw: { polygon: true, polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false }
            });
            map.addControl(drawControl);

            map.on(L.Draw.Event.CREATED, function (event) {
                const layer = event.layer;
                const name = prompt("Enter a name for this Geo-Fence zone:");
                if (!name) return;
                
                layer.setStyle({ color: 'red', fillColor: 'red', fillOpacity: 0.2 });
                layer.bindTooltip(name);
                drawnItems.addLayer(layer);
                const coords = layer.getLatLngs()[0].map(ll => [ll.lat, ll.lng]);
                
                fetch('/api/geofence', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, coordinates: coords })
                })
                .then(res => res.json())
                .then(data => {
                    layer.geofenceId = data.id || Date.now();
                    bindGeofencePopup(layer, name, layer.geofenceId);
                    showToast('Geofence saved');
                });
            });

            function bindGeofencePopup(layer, name, id) {
                const popupContent = document.createElement('div');
                popupContent.innerHTML = `<b>${name}</b><br><button style="background:#f44;color:#fff;border:none;padding:2px 6px;margin-top:4px;cursor:pointer;">Delete</button>`;
                popupContent.querySelector('button').onclick = () => {
                    fetch(`/api/geofence/${id}`, { method: 'DELETE' }).then(() => {
                        drawnItems.removeLayer(layer);
                        showToast('Geofence deleted');
                    });
                };
                layer.bindPopup(popupContent);
            }

            fetch('/api/geofences')
                .then(res => res.json())
                .then(data => {
                    if (data && Array.isArray(data.data)) {
                        data.data.forEach(gf => {
                            const polygon = L.polygon(gf.coordinates, { color: 'red', fillColor: 'red', fillOpacity: 0.2 });
                            polygon.bindTooltip(gf.name);
                            polygon.geofenceId = gf.id;
                            bindGeofencePopup(polygon, gf.name, gf.id);
                            drawnItems.addLayer(polygon);
                        });
                    }
                })
                .catch(e => console.warn('No geofences found'));

            // Fetch dynamic animated wind data
            fetch('https://onaci.github.io/leaflet-velocity/wind-global.json')
                .then(r => r.json())
                .then(data => {
                    const velocityLayer = L.velocityLayer({
                        displayValues: true,
                        displayOptions: {
                            velocityType: 'Global Wind',
                            position: 'bottomleft',
                            emptyString: 'No wind data',
                            displayPosition: 'bottomleft',
                            displayEmptyString: 'No wind data'
                        },
                        data: data,
                        maxVelocity: 15,
                        velocityScale: 0.005,
                        colorScale: ["#00bcd4", "#0f6", "#fa0", "#ff5050"]
                    });
                    velocityLayer.addTo(animatedWindLayer);
                }).catch(e => console.log('Wind animation error', e));

            // Fetch dynamic layer data
            fetch('https://api.rainviewer.com/public/weather-maps.json')
                .then(r => r.json())
                .then(d => {
                    if(d && d.radar && d.radar.past && d.radar.past.length > 0) {
                        const path = d.radar.past[d.radar.past.length - 1].path;
                        rainLayer.options.maxNativeZoom = 7;
                        rainLayer.setUrl(`https://tilecache.rainviewer.com${path}/512/{z}/{x}/{y}/2/1_1.png`);
                    }
                }).catch(e => console.log('Rain radar error', e));


            let lastWarningsDataStr = "";
            function renderWarnings(data) {
                const dataStr = JSON.stringify(data);
                if (dataStr === lastWarningsDataStr) return;
                lastWarningsDataStr = dataStr;
                
                const monList = document.getElementById('monitoringList');
                monList.innerHTML = '';
                let hasData = false;
                cycloneLayer.clearLayers();
                
                const gdacsData = data.gdacs || {features: []};
                const pagasaData = data.pagasa || {features: []};
                
                // Process GDACS Cyclones with Rainfall & Wind Shading
                if(gdacsData.features && gdacsData.features.length > 0) {
                    hasData = true;
                    
                    // Render paths and cones with dynamic Rainfall Advisory & Warning Shading
                    L.geoJSON(gdacsData, {
                        style: function(feature) {
                            const p = feature.properties || {};
                            const level = (p.alertlevel || p.episodealertlevel || '').toLowerCase();
                            const severity = p.severitydata?.severity || 0;
                            const cls = (p.Class || '').toLowerCase();

                            // Rainfall & Cyclone gradient classification
                            let strokeColor = '#00ff66';
                            let fillColor = '#00ff66';
                            let fillOpacity = 0.20;
                            let dashArray = '4, 4';
                            let weight = 2;

                            if (level === 'red' || severity >= 118 || cls.includes('64kt') || cls.includes('red')) {
                                // Red: Severe Cyclone Core / Torrential Rainfall Warning (>30 mm/h)
                                strokeColor = '#ff3838';
                                fillColor = '#ff3838';
                                fillOpacity = 0.38;
                                dashArray = '6, 3';
                                weight = 3;
                            } else if (level === 'orange' || (severity >= 88 && severity < 118) || cls.includes('50kt') || cls.includes('orange')) {
                                // Orange: Intense Rainbands & High Rainfall Warning (15-30 mm/h)
                                strokeColor = '#ffa502';
                                fillColor = '#ffa502';
                                fillOpacity = 0.28;
                                dashArray = '5, 5';
                                weight = 2.5;
                            } else if (level === 'yellow' || (severity >= 62 && severity < 88) || cls.includes('34kt') || cls.includes('yellow')) {
                                // Yellow: Moderate-to-Heavy Rainfall Advisory (7.5-15 mm/h)
                                strokeColor = '#ffd32a';
                                fillColor = '#ffd32a';
                                fillOpacity = 0.22;
                                dashArray = '4, 6';
                                weight = 2;
                            } else {
                                // Green/Cyan: Monitored Track & Distant Gale Perimeter
                                strokeColor = '#00bcd4';
                                fillColor = '#00bcd4';
                                fillOpacity = 0.16;
                                dashArray = '2, 6';
                                weight = 1.5;
                            }

                            return {
                                color: strokeColor,
                                fillColor: fillColor,
                                fillOpacity: fillOpacity,
                                weight: weight,
                                dashArray: dashArray
                            };
                        },
                        pointToLayer: function (feature, latlng) {
                            const tcIcon = L.divIcon({ className: 'cyclone-icon', html: '<div style="font-size: 26px; text-shadow: 0 0 8px #ff5050; animation: spin-slow 4s linear infinite;">🌀</div>', iconSize: [32, 32], iconAnchor: [16, 16] });
                            return L.marker(latlng, {icon: tcIcon})
                                .bindPopup(`
                                    <div style="font-family: var(--font-main, sans-serif); min-width: 210px;">
                                        <div style="font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 4px;">🌀 ${feature.properties.name}</div>
                                        <div style="font-size: 12px; margin-bottom: 4px;"><strong>Alert Level:</strong> <span style="color:${feature.properties.alertlevel === 'Red' ? '#ff3838' : (feature.properties.alertlevel === 'Orange' ? '#ffa502' : '#00ff66')}; font-weight:bold;">${feature.properties.alertlevel}</span></div>
                                        <div style="font-size: 11px; color: #a3b8c2; margin-bottom: 6px;"><i>${feature.properties.htmldescription}</i></div>
                                        ${feature.properties.url?.report ? `<a href="${feature.properties.url.report}" target="_blank" style="color: #00bcd4; font-size: 12px; font-weight: 600; text-decoration: none;">📄 View GDACS Report &rarr;</a>` : ''}
                                    </div>
                                `);
                        },
                        onEachFeature: function(feature, layer) {
                            if (feature.geometry && feature.geometry.type !== 'Point') {
                                const p = feature.properties || {};
                                const level = p.alertlevel || p.episodealertlevel || 'Monitored';
                                const rainAdvisory = level === 'Red' ? '🔴 Torrential Rainfall Warning (>30 mm/h) - High Flooding Risk' :
                                                     (level === 'Orange' ? '🟠 Intense Rainfall Warning (15-30 mm/h) - Flooding Threat' :
                                                     (level === 'Yellow' ? '🟡 Heavy Rainfall Advisory (7.5-15 mm/h) - Flooding Possible' : '🟢 Moderate Rainfall / Rainband Zone'));
                                
                                layer.bindPopup(`
                                    <div style="font-family: var(--font-main, sans-serif); min-width: 220px;">
                                        <div style="font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 4px;">🌀 ${p.name || 'Tropical Cyclone Rainband / Cone'}</div>
                                        <div style="font-size: 12px; margin-bottom: 4px;"><strong>Rainfall Status:</strong> <span style="font-weight: bold; color: ${level === 'Red' ? '#ff3838' : (level === 'Orange' ? '#ffa502' : '#00ff66')};">${rainAdvisory}</span></div>
                                        <div style="font-size: 12px; color: #a3b8c2; margin-bottom: 4px;"><strong>Wind Severity:</strong> ${p.severitydata?.severitytext || level}</div>
                                        <div style="font-size: 11px; color: #8a9fa0; line-height: 1.4; margin-bottom: 6px;">${p.htmldescription || p.description || ''}</div>
                                        ${p.url?.report ? `<a href="${p.url.report}" target="_blank" style="color: #00bcd4; font-size: 12px; font-weight: 600; text-decoration: none;">📄 Full GDACS Bulletin &rarr;</a>` : ''}
                                    </div>
                                `);
                            }
                        }
                    }).addTo(cycloneLayer);

                    // Manually ensure icon and sidebar entry exist for each unique storm
                    let processedStorms = new Set();
                    
                    gdacsData.features.forEach(f => {
                        const name = f.properties.name;
                        if(!processedStorms.has(name)) {
                            processedStorms.add(name);
                            
                            // If it wasn't a point, the geoJSON didn't render an icon. Let's add one at the first coordinate.
                            if(f.geometry && f.geometry.type !== 'Point') {
                                let coords = f.geometry.type === 'Polygon' || f.geometry.type === 'MultiLineString' ? f.geometry.coordinates[0][0] : (f.geometry.type === 'MultiPolygon' ? f.geometry.coordinates[0][0][0] : f.geometry.coordinates[0]);
                                if (Array.isArray(coords) && coords.length >= 2) {
                                    while (Array.isArray(coords[0])) { coords = coords[0]; }
                                    const lat = coords[1];
                                    const lon = coords[0];
                                    if (lat && lon) {
                                        const tcIcon = L.divIcon({ className: 'cyclone-icon', html: '<div style="font-size: 26px; text-shadow: 0 0 8px #ff5050; animation: spin-slow 4s linear infinite;">🌀</div>', iconSize: [32, 32], iconAnchor: [16, 16] });
                                        L.marker([lat, lon], {icon: tcIcon})
                                            .bindPopup(`<b>${name}</b><br>Alert Level: ${f.properties.alertlevel}<br><i>${f.properties.htmldescription}</i><br><a href="${f.properties.url.report}" target="_blank">View GDACS Report</a>`)
                                            .addTo(cycloneLayer);
                                    }
                                }
                            }
                            
                            // Add to monitoring list
                            const div = document.createElement('div');
                            div.className = 'alert-entry';
                            const borderCol = f.properties.alertlevel === 'Red' ? '#ff3838' : (f.properties.alertlevel === 'Orange' ? '#ffa502' : '#00ff66');
                            div.style.borderLeftColor = borderCol;
                            div.innerHTML = `<div class="alert-text"><strong>🌀 Cyclone: ${name}</strong><br>${f.properties.htmldescription}</div>`;
                            monList.appendChild(div);
                        }
                    });
                }
                
                // Process PAGASA Heavy Rainfall Warnings & Advisories
                if(pagasaData.features && pagasaData.features.length > 0) {
                    hasData = true;
                    
                    // Summarize by warning level for clean sidebar
                    const groupedLevels = {
                        "Red": [],
                        "Orange": [],
                        "Yellow": [],
                        "Advisory": []
                    };

                    pagasaData.features.forEach(f => {
                        const level = f.properties.alertlevel || 'Yellow';
                        const isRed = level === 'Red';
                        const isOrange = level === 'Orange';
                        const isYellow = level === 'Yellow';
                        const isAdvisory = level === 'Advisory';

                        let color = '#00bcd4';
                        let rainTitle = '🔵 LIGHT-TO-MODERATE RAINFALL ADVISORY';
                        let rainDesc = f.properties.description || 'Occasional heavy rains affecting the area.';
                        let fillOpacity = 0.16;
                        let weight = 1.5;
                        let dashArray = '2, 6';

                        if (isRed) {
                            color = '#ff3838';
                            rainTitle = '🔴 RED RAINFALL WARNING (Torrential)';
                            rainDesc = f.properties.description || 'Serious FLOODING expected in low-lying areas.';
                            fillOpacity = 0.40;
                            weight = 3;
                            dashArray = '6, 3';
                        } else if (isOrange) {
                            color = '#ffa502';
                            rainTitle = '🟠 ORANGE RAINFALL WARNING (Intense)';
                            rainDesc = f.properties.description || 'FLOODING is THREATENING in flood-prone areas.';
                            fillOpacity = 0.32;
                            weight = 2.5;
                            dashArray = '5, 5';
                        } else if (isYellow) {
                            color = '#ffd32a';
                            rainTitle = '🟡 YELLOW RAINFALL ADVISORY (Heavy)';
                            rainDesc = f.properties.description || 'Possible FLOODING in low-lying areas.';
                            fillOpacity = 0.24;
                            weight = 2;
                            dashArray = '4, 4';
                        }

                        // Collect for sidebar grouping
                        const nameParts = (f.properties.name || '').split(',');
                        const provName = nameParts.length > 1 ? nameParts[1].trim() : nameParts[0].trim();
                        if (!groupedLevels[level]) groupedLevels[level] = [];
                        if (!groupedLevels[level].includes(provName)) groupedLevels[level].push(provName);

                        // Render on Map with High-Definition Municipality Polygon
                        L.geoJSON(f, {
                            style: { 
                                color: color, 
                                fillColor: color,
                                weight: weight, 
                                fillOpacity: fillOpacity, 
                                dashArray: dashArray 
                            }
                        }).bindPopup(`
                            <div style="font-family: var(--font-main, sans-serif); min-width: 220px;">
                                <div style="font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 4px;">🌧️ ${f.properties.name}</div>
                                <div style="font-size: 12px; margin-bottom: 4px;"><strong>Warning Status:</strong> <span style="color:${color}; font-weight:bold;">${rainTitle}</span></div>
                                ${f.properties.rainfall_rate ? `<div style="font-size: 12px; color: #00ff66; margin-bottom: 4px;"><strong>Rainfall Rate:</strong> ${f.properties.rainfall_rate}</div>` : ''}
                                <div style="font-size: 12px; color: #cfe8d6; margin-bottom: 6px; line-height: 1.4;">${rainDesc}</div>
                                <div style="font-size: 11px; color: #8a9fa0;">PAGASA NCR-PRSD Heavy Rainfall Warning & Hazard Monitoring</div>
                            </div>
                        `).addTo(cycloneLayer);
                    });

                    // Add structured summary entries to sidebar
                    if (groupedLevels["Red"].length > 0) {
                        const div = document.createElement('div');
                        div.className = 'alert-entry';
                        div.style.borderLeftColor = '#ff3838';
                        div.innerHTML = `<div class="alert-text"><strong>🔴 RED RAINFALL WARNING</strong><br>Torrential rain (>30 mm/h). Serious Flooding.<br><span style="color:#ff8888; font-size:12px;">Affected: ${groupedLevels["Red"].join(', ')}</span></div>`;
                        monList.appendChild(div);
                    }
                    if (groupedLevels["Orange"].length > 0) {
                        const div = document.createElement('div');
                        div.className = 'alert-entry';
                        div.style.borderLeftColor = '#ffa502';
                        div.innerHTML = `<div class="alert-text"><strong>🟠 ORANGE RAINFALL WARNING</strong><br>Intense rain (15-30 mm/h). Flooding Threatening.<br><span style="color:#ffcc66; font-size:12px;">Affected: ${groupedLevels["Orange"].join(', ')}</span></div>`;
                        monList.appendChild(div);
                    }
                    if (groupedLevels["Yellow"].length > 0) {
                        const div = document.createElement('div');
                        div.className = 'alert-entry';
                        div.style.borderLeftColor = '#ffd32a';
                        div.innerHTML = `<div class="alert-text"><strong>🟡 YELLOW RAINFALL ADVISORY</strong><br>Heavy rain (7.5-15 mm/h). Flooding Possible.<br><span style="color:#ffee88; font-size:12px;">Affected: ${groupedLevels["Yellow"].join(', ')}</span></div>`;
                        monList.appendChild(div);
                    }
                    if (groupedLevels["Advisory"].length > 0) {
                        const div = document.createElement('div');
                        div.className = 'alert-entry';
                        div.style.borderLeftColor = '#00bcd4';
                        div.innerHTML = `<div class="alert-text"><strong>🔵 RAINFALL ADVISORY (HABAGAT)</strong><br>Light to moderate with occasional heavy rains.<br><span style="color:#80deea; font-size:12px;">Affected: ${groupedLevels["Advisory"].join(', ')}</span></div>`;
                        monList.appendChild(div);
                    }
                }
                
                if(!hasData) {
                    monList.innerHTML = '<div id="nodata_monitoring" style="color:#0f6; text-align: center; padding: 10px;">No active global threats.</div>';
                }
            }

            // Initial fetch from backend cache (Instant)
            fetch('/api/warnings')
                .then(r => r.json())
                .then(res => renderWarnings(res.data))
                .catch(e => console.log("Warnings load error", e));
                
            // Listen for background polling updates
            socket.on('warnings_update', function(data) {
                console.log("Received warnings update from background thread");
                renderWarnings(data);
            });

            // Live Precipitation Hover Display
            const precipControl = L.control({position: 'topright'});
            precipControl.onAdd = function (map) {
                this._div = L.DomUtil.create('div', 'precip-info');
                this._div.style.background = 'rgba(20, 35, 45, 0.8)';
                this._div.style.color = '#0f6';
                this._div.style.padding = '8px 12px';
                this._div.style.borderRadius = '6px';
                this._div.style.border = '1px solid #0f6';
                this._div.style.fontSize = '14px';
                this._div.style.fontWeight = 'bold';
                this._div.style.display = 'none'; // Hidden by default
                this._div.style.boxShadow = '0 0 10px rgba(0, 255, 102, 0.3)';
                this.update('Hover map for rain data...');
                return this._div;
            };
            precipControl.update = function (text) {
                this._div.innerHTML = text;
            };
            precipControl.addTo(map);

            let precipTimeout = null;
            let lastMousePos = null;

            map.on('mousemove', function(e) {
                // Show the box when hovering begins
                precipControl._div.style.display = 'block';
                
                if(precipTimeout) clearTimeout(precipTimeout);
                lastMousePos = e.latlng;
                
                precipControl.update('Measuring rain at this spot...');
                
                precipTimeout = setTimeout(() => {
                    const lat = lastMousePos.lat.toFixed(4);
                    const lon = lastMousePos.lng.toFixed(4);
                    fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=precipitation`)
                        .then(r => r.json())
                        .then(data => {
                            if(data && data.current) {
                                const rain = data.current.precipitation;
                                const color = rain > 10 ? '#ff5050' : (rain > 0 ? '#fa0' : '#0f6');
                                precipControl.update(`Precipitation: <span style="color:${color}; font-size:16px;">${rain} mm/h</span>`);
                            } else {
                                precipControl.update('Rain data unavailable');
                            }
                        }).catch(() => {
                            precipControl.update('Rain data unavailable');
                        });
                }, 600);
            });
            
            map.on('mouseout', function() {
                if(precipTimeout) clearTimeout(precipTimeout);
                precipControl._div.style.display = 'none';
            });

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

        function formatSensorDisplay(data, deviceId) {
            if (!data) return 'No data';
            let html = '';
            const thresholds = getThresholds();
            
            html += `<div class="sensor-row">
                <span class="sensor-label">Risk Score</span>
                <span class="sensor-value" id="val_risk_${deviceId}" style="color: #0f6">-</span>
            </div>`;
            
            html += `<div class="sensor-row">
                <span class="sensor-label">Life Form</span>
                <span class="sensor-value" id="val_life_${deviceId}" style="color: #0f6">-</span>
            </div>`;
            
            html += `<div class="sensor-row">
                <span class="sensor-label">Flood Sensor</span>
                <span class="sensor-value" id="val_flood_${deviceId}" style="color: #0f6">-</span>
            </div>`;
            
            html += `<div class="sensor-row">
                <span class="sensor-label">Fire Sensor</span>
                <span class="sensor-value" id="val_fire_${deviceId}" style="color: #0f6">-</span>
            </div>`;
            
            html += `<div class="sensor-row" id="row_humidity_${deviceId}" style="display:none;">
                <span class="sensor-label">Humidity</span>
                <span class="sensor-value" id="val_humidity_${deviceId}">-</span>
            </div>`;
            
            html += `<div class="sensor-row">
                <span class="sensor-label">Gas Level</span>
                <span class="sensor-value" id="val_gas_${deviceId}" style="color: #0f6">-</span>
            </div>`;
            
            html += `<div class="sensor-row">
                <span class="sensor-label">Battery</span>
                <span class="sensor-value" id="val_bat_${deviceId}" style="color: #0f6">-</span>
            </div>
            <div class="battery-bar"><div class="battery-fill" id="bar_bat_${deviceId}" style="width: 0%; background: #0f6"></div></div>`;
            
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
                el.innerHTML = formatSensorDisplay(data, deviceId);
                
                // Add camera toggler (Feature 20)
                const camContainer = document.createElement('div');
                camContainer.style.marginTop = '6px';
                camContainer.innerHTML = `
                    <div class="cam-section" id="cam-${deviceId}" style="display:none; margin-top:8px;">
                        <img id="cam-img-${deviceId}" style="width:100%; border-radius:4px; border:1px solid #1e3640;" src="" onerror="this.style.display='none'">
                    </div>
                    <button class="cam-toggle" onclick="toggleCam('${deviceId}')" style="margin-top:6px; background:#14232d; border:1px solid #1e3640; color:#00bcd4; font-size:12px; padding:3px 8px; border-radius:3px; cursor:pointer; width:100%;">📷 Camera Feed</button>
                `;
                el.appendChild(camContainer);
            }
            
            const thresholds = typeof getThresholds === 'function' ? getThresholds() : { flood: true, fire: true, gas: 200 };
            
            // Update values directly instead of replacing HTML
            if (data.risk_score !== undefined) {
                let riskClass = 'status-ok';
                let color = '#0f6';
                if (data.risk_score > 50) { riskClass = 'status-warning'; color = '#fa0'; }
                if (data.risk_score > 80) { riskClass = 'status-alert'; color = '#f44'; }
                
                const elRisk = document.getElementById(`val_risk_${deviceId}`);
                if (elRisk) {
                    elRisk.style.color = color;
                    elRisk.innerHTML = `${data.risk_score}/100 <span class="sensor-status ${riskClass}"></span>`;
                }
            }
            
            if (data.sensors) {
                const s = data.sensors;
                const intruder = s.life_form || s.intruder;
                if (intruder !== undefined) {
                    const elLife = document.getElementById(`val_life_${deviceId}`);
                    if (elLife) {
                        elLife.style.color = intruder ? '#f44' : '#0f6';
                        elLife.innerHTML = `${intruder ? 'DETECTED' : 'Clear'} <span class="sensor-status ${intruder ? 'status-alert' : 'status-ok'}"></span>`;
                    }
                }
                
                if (s.flood !== undefined) {
                    const isFloodActive = thresholds.flood && s.flood;
                    const elFlood = document.getElementById(`val_flood_${deviceId}`);
                    if (elFlood) {
                        elFlood.style.color = isFloodActive ? '#f44' : '#0f6';
                        elFlood.innerHTML = `${s.flood ? 'Water Detected' : 'Dry'} <span class="sensor-status ${isFloodActive ? 'status-alert' : 'status-ok'}"></span>`;
                    }
                }
                
                if (s.fire !== undefined) {
                    const isFireActive = thresholds.fire && s.fire;
                    const elFire = document.getElementById(`val_fire_${deviceId}`);
                    if (elFire) {
                        elFire.style.color = isFireActive ? '#f44' : '#0f6';
                        elFire.innerHTML = `${s.fire ? 'FIRE' : 'Clear'} <span class="sensor-status ${isFireActive ? 'status-alert' : 'status-ok'}"></span>`;
                    }
                }
                
                if (s.humidity !== undefined) {
                    const rowHum = document.getElementById(`row_humidity_${deviceId}`);
                    const valHum = document.getElementById(`val_humidity_${deviceId}`);
                    if (rowHum) rowHum.style.display = 'flex';
                    if (valHum) valHum.innerHTML = `${s.humidity}%`;
                }
                
                if (s.gas !== undefined) {
                    const isGasHigh = s.gas > thresholds.gas;
                    const elGas = document.getElementById(`val_gas_${deviceId}`);
                    if (elGas) {
                        elGas.style.color = isGasHigh ? '#f44' : '#0f6';
                        elGas.innerHTML = `${s.gas} ppm`;
                    }
                }
            }
            
            if (data.battery !== undefined) {
                let batColor = '#0f6';
                if (data.battery < 20) batColor = '#f44';
                else if (data.battery < 50) batColor = '#fa0';
                
                const elBat = document.getElementById(`val_bat_${deviceId}`);
                const barBat = document.getElementById(`bar_bat_${deviceId}`);
                if (elBat) {
                    elBat.style.color = batColor;
                    elBat.innerHTML = `${data.battery}%`;
                }
                if (barBat) {
                    barBat.style.width = `${data.battery}%`;
                    barBat.style.background = batColor;
                }
            }
            
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
                row.innerHTML = `<span style="font-size:13px; font-weight:bold;">${n}</span>
                                 <input type="text" class="cam-ip-input" data-device-id="${n}" value="${ip}" placeholder="e.g. 192.168.1.50" style="width:160px; padding:4px 8px; background:#0b141c; border:1px solid #1e3640; color:#fff; border-radius:3px; font-size:13px;">`;
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
                    if (document.getElementById('cfg_fb_page_handle')) document.getElementById('cfg_fb_page_handle').value = d.fb_page_handle || 'IloveTaguig';
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
                dashboard_password: document.getElementById('cfg_dashboard_password').value,
                fb_page_handle: document.getElementById('cfg_fb_page_handle') ? document.getElementById('cfg_fb_page_handle').value.trim() : 'IloveTaguig'
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
                
                fetch('/api/history?limit=1500')
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
            const timeStr = logTime.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + logTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            document.getElementById('playbackTime').textContent = timeStr + ' (' + (index + 1) + '/' + playbackLogs.length + ')';
            
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

        function requestGPS() {
            fetch('/api/request-gps', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    showToast(data.message || 'GPS Request sent to all devices');
                })
                .catch(e => showToast('Failed to request GPS: ' + e));
        }
        const _settingsModalEl = document.getElementById('settingsModal');
        if (_settingsModalEl) {
            _settingsModalEl.addEventListener('click', function(e) { if (e.target === this) closeSettings(); });
        }
        // Close all dropdown menus if clicked outside
        window.addEventListener('click', function(e) {
            document.querySelectorAll('.ql-dropdown-menu.open').forEach(menu => {
                const parent = menu.closest('.ql-dropdown');
                if (parent && !parent.contains(e.target)) {
                    menu.classList.remove('open');
                }
            });
        });

        // Mobile map resize recalculation
        setTimeout(() => { if(typeof map !== 'undefined' && map) map.invalidateSize(); }, 500);
        window.addEventListener("resize", () => { if(typeof map !== 'undefined' && map) map.invalidateSize(); });
        // Feature 1: PAGASA Ticker
        function fetchPagasaTicker() {
            fetch('/api/pagasa')
                .then(res => res.json())
                .then(data => {
                    const content = document.getElementById('pagasaTickerContent');
                    if (data.data && data.data.length > 0) {
                        content.textContent = data.data.map(b => b.title + ' (' + b.pubDate + ')').join(' ● ');
                    } else {
                        content.textContent = 'PAGASA feed unavailable';
                    }
                })
                .catch(() => {
                    document.getElementById('pagasaTickerContent').textContent = 'PAGASA feed unavailable';
                });
        }
        
        // Feature 6: Analytics Heatmap
        function generateAnalyticsHeatmap() {
            const hours = document.getElementById('analytics_hours').value;
            fetch(`/api/heatmap?hours=${hours}`)
                .then(res => res.json())
                .then(data => {
                    if (heatLayer && Array.isArray(data.points)) {
                        heatLayer.setLatLngs(data.points);
                        document.getElementById('analytics_summary').style.display = 'block';
                        document.getElementById('asum_total').textContent = data.summary?.total || data.points.length;
                        document.getElementById('asum_device').textContent = data.summary?.highest_risk_device || 'N/A';
                        document.getElementById('asum_zone').textContent = data.summary?.most_active_zone || 'N/A';
                        showToast(`Heatmap updated for last ${hours} hours.`);
                        closeSettings();
                    }
                })
                .catch(e => {
                    console.warn(e);
                    showToast('Failed to fetch heatmap data', 'alert');
                });
        }
        
        window.addEventListener('load', () => {
            fetchPagasaTicker();
            setInterval(fetchPagasaTicker, 10 * 60 * 1000); // 10 minutes
        });

        // ==========================================
        // MOBILE APP MODE: FULLSCREEN MAP CONTROLLERS
        // ==========================================
        window.openMobilePanel = function(panelId) {
            const panel = document.getElementById(panelId);
            const isAlreadyOpen = panel && panel.classList.contains('mobile-open');
            window.closeMobilePanels();
            if (isAlreadyOpen) return;
            
            const backdrop = document.getElementById('mobileDrawerBackdrop');
            if (panel) panel.classList.add('mobile-open');
            if (backdrop) backdrop.classList.add('active');
            
            // Highlight active bottom nav button
            document.querySelectorAll('.mobile-nav-btn').forEach(b => b.classList.remove('active'));
            if (panelId === 'leftpanel') document.getElementById('mobNavAlerts')?.classList.add('active');
            if (panelId === 'rightpanel') document.getElementById('mobNavNodes')?.classList.add('active');
            if (panelId === 'mobileMenuDrawer') document.getElementById('mobNavMenu')?.classList.add('active');
        };

        window.closeMobilePanels = function() {
            document.querySelectorAll('#leftpanel, #rightpanel, #mobileMenuDrawer').forEach(el => el.classList.remove('mobile-open'));
            const backdrop = document.getElementById('mobileDrawerBackdrop');
            if (backdrop) backdrop.classList.remove('active');
            document.querySelectorAll('.mobile-nav-btn').forEach(b => b.classList.remove('active'));
            if (typeof map !== 'undefined' && map) setTimeout(() => map.invalidateSize(), 300);
        };

        // Close mobile drawers with Escape key
        window.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') window.closeMobilePanels();
        });