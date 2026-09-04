# 🛰️ VERS (Versatile Emergency Response System)
### Advanced Multi-Sensor IoT Disaster Monitoring, Multi-Hazard Risk Assessment & Emergency Dispatch Platform

**VERS** (**Versatile Emergency Response System**) is an enterprise-grade IoT disaster management and multi-hazard emergency monitoring system. The name *Versatile* reflects its ability to ingest, calibrate, and correlate diverse hardware sensor streams (water level, MQ-2 gas/smoke, flame, temperature, humidity, life form, GPS) alongside real-time national meteorological data (PAGASA rainfall warnings, GDACS cyclone cones, weather radar) into a unified risk matrix.

---

## 🌟 Key Features

- 📡 **Real-Time IoT Node Telemetry**: Ingests multi-sensor environmental telemetry (water level, MQ-2 gas/smoke, flame, temperature, humidity, GPS) over local MQTT broker (`mosquitto`) in < 5ms.
- 🗺️ **High-Definition Disaster Map & Hazard Shading**:
  - Live GDACS Tropical Cyclone tracking with rainband cones.
  - Municipality-level PAGASA Heavy Rainfall Warnings & Advisories (Red, Orange, Yellow, Advisory).
  - OpenWeatherMap & RainViewer radar layers.
  - Multi-basemap support (Google Roads, Google Satellite, Hybrid, Dark Mode, OpenTopoMap, Offline Taguig tiles).
- 📱 **Responsive Mobile App Mode**:
  - Full-screen interactive map layout on mobile devices.
  - Floating action drawers for Alerts, Active Sensor Nodes, Hazard Crosshair assessment, and Reports.
- 🚨 **Automated & Manual Emergency Dispatch**:
  - Real-time emergency trigger and voice dispatch synthesis.
  - Instant SMTP emergency email alert broadcasts to response teams.
- 📸 **Public Incident Reporting**:
  - Community incident submission with photo upload and GPS tagging.
  - Real-time incident inbox and map marker visualization.
- 🧠 **AI Situation Analysis**:
  - Multi-agent hazard assessment and Ollama/Gemini threat synthesis.

---

## 🏗️ Architecture

- **Backend**: Python 3, Flask, Flask-SocketIO, Eventlet, SQLite3
- **IoT / Hardware**: ESP32 with multi-sensor payload, Mosquitto MQTT Broker (Port 1883)
- **Frontend**: Leaflet.js, HTML5, Vanilla JavaScript, SCADA/Palantir Dark Gotham Theme
- **Data Integrations**: GDACS REST API, PAGASA Heavy Rainfall Scraper, OpenWeatherMap, RainViewer

---

## 🚀 Getting Started

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/<your-username>/vers_project.git
cd vers_project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt # (or pip install flask flask-socketio paho-mqtt requests beautifulsoup4 eventlet)
```

### 2. Configuration

Copy the example configuration file:

```bash
cp data/settings.example.json data/settings.json
```

Edit `data/settings.json` with your SMTP and API keys.

### 3. Start MQTT Broker & System Server

```bash
# Start Mosquitto broker
sudo systemctl start mosquitto

# Run VERS System
python vers_system.py
```

Access the dashboard at: `http://localhost:5000` (or `http://<your-pi-ip>:5000`).

---

## 🔒 Security & Privacy

Sensitive database files (`data/*.db`), credentials (`data/settings.json`), and image uploads are excluded via `.gitignore` to ensure zero secret leakage.
