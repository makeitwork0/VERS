# VERS — Versatile Emergency Response System

> **Real-time critical infrastructure monitoring powered by IoT, AI, and geospatial intelligence.**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## Overview

**VERS** (Versatile Emergency Response System) is a comprehensive, AI-powered disaster monitoring and emergency management platform deployed on a Raspberry Pi edge server. Originally developed for **Barangay Bagumbayan, Taguig City, Philippines**, VERS integrates distributed IoT sensor networks, real-time weather intelligence from PAGASA and GDACS, and generative AI (Google Gemini / Ollama) to deliver actionable emergency guidance through voice alerts, email notifications, and a tactical web dashboard.

The system monitors for **fire**, **flood**, **gas leaks**, and **unauthorized life form detection** across a network of sensor nodes, calculates composite risk scores, and triggers automated emergency response workflows — including AI-generated safety instructions, evacuation routing, and multi-channel operator notifications.

---

## Key Features

### 🔥 Real-Time Sensor Monitoring
- Distributed IoT sensor nodes (ESP32/Arduino) reporting via MQTT
- Composite risk scoring engine (Fire=100, Flood=90, Life Form=80, Gas Leak=75)
- Hardware fault detection and diagnostic alerts
- Battery health forecasting with drain rate analysis

### 🤖 AI-Powered Emergency Response
- **Primary**: Google Gemini 2.5 Flash generates contextual safety instructions using the VERS Critical Infrastructure Handbook
- **Fallback**: Ollama local LLM (qwen2.5:0.5b) for offline/air-gapped operation
- Voice alerts via browser Text-to-Speech with custom Web Audio alarm tones

### 🌊 Weather & Disaster Intelligence
- **PAGASA** rainfall warning integration (Red/Orange/Yellow levels)
- **GDACS** tropical cyclone tracking with animated map markers
- **RainViewer** animated rainfall radar overlay
- **OpenWeatherMap** wind vectors and cloud layers
- Hazard assessment for any GPS coordinate

### 🎒 Class Suspension Monitoring ("Walang Pasok")
- Auto-derived from PAGASA warnings using DepEd Executive Order 77 rules
- Official LGU operator override posting
- Facebook page auto-polling from official government pages
- Real-time broadcast to all connected clients

### 🗺️ Interactive Tactical Map
- Leaflet.js with dark mode tactical styling
- 6 base layers (Google Roads/Satellite/Hybrid/Terrain, OpenTopoMap, Offline Tiles)
- 12+ overlay layers (radar, heatmap, wind, cyclones, fault lines, volcanoes, flood susceptibility)
- OSRM-powered evacuation routing with turn-by-turn directions
- Dynamic geofencing with Leaflet.Draw
- HazardHunterPH interactive risk assessment mode

### 📊 Operator Tools
- Configurable settings (SMTP, API keys, thresholds, display preferences)
- Historical data playback mode with timeline scrubber
- CSV data export and email backup
- Audit trail logging for all operator actions
- Public incident report management with photo review
- Multi-client text broadcast system

### 📱 Public Features
- Incident reporting web form with photo capture and GPS geolocation
- Real-time hazard assessment for current location
- Quick links to Philippine government emergency resources
- Responsive mobile layout with hamburger menu

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Runtime** | Python 3.9+ (Flask + Flask-SocketIO + eventlet) |
| **Database** | SQLite (`data/vers_data.db`) |
| **Messaging** | Mosquitto MQTT Broker (Paho client) |
| **AI Engine** | Google Gemini 2.5 Flash / Ollama qwen2.5:0.5b |
| **Frontend** | Leaflet.js, Chart.js, Socket.IO, Web Audio API |
| **Styling** | Custom CSS with glassmorphism, Inter font |
| **Geospatial** | Shapely, OSRM, Open-Meteo, GeoJSON |
| **Hosting** | Raspberry Pi + Cloudflare Quick Tunnel (HTTPS) |
| **Email** | Gmail SMTP with HTML templates |

---

## Quick Start

```bash
# 1. Clone the project
cd /home/rasp-pi
git clone <repo-url> vers_project && cd vers_project

# 2. Create virtual environment
python3 -m venv venv && source venv/bin/activate

# 3. Install dependencies
pip install flask flask-socketio eventlet paho-mqtt google-genai \
            shapely numpy beautifulsoup4 apscheduler requests httpx \
            cryptography PyPDF2 openlocationcode

# 4. Install & start MQTT broker
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto

# 5. Configure (edit data/settings.json with your SMTP credentials)
mkdir -p data

# 6. Run the application
python -u vers_system.py
```

Access the dashboard at **http://localhost:5000**. Default operator login: `operator` / `vers2024`.

For production deployment with systemd auto-restart, see the [Deployment Guide](docs/DEPLOYMENT_GUIDE.md).

---

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | System architecture, data flow, AI pipeline, database schema |
| [API Reference](docs/API_REFERENCE.md) | REST API endpoints, WebSocket events, MQTT topics |
| [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) | Installation, systemd services, Cloudflare tunnel, security |
| [Operator Manual](docs/OPERATOR_MANUAL.md) | Dashboard walkthrough, operator tools, daily operations |
| [Sensor Protocol](docs/SENSOR_PROTOCOL.md) | MQTT payload spec, risk scoring, hardware integration |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues, debugging commands, recovery procedures |

---

## Project Structure

```
vers_project/
├── vers_system.py              # Core server (Flask + SocketIO + MQTT + AI)
├── vers_simulator.py           # Virtual sensor node simulator
├── vers_top.py                 # Terminal UI monitor (curses)
├── vers.service                # Systemd service (main app)
├── vers-simulator.service      # Systemd service (simulator)
├── install_service.sh          # Service installer script
├── start_tunnel.sh             # Cloudflare tunnel launcher
├── send_tunnel_email.py        # Tunnel URL email notifier
├── templates/
│   └── index.html              # Dashboard template (46KB)
├── static/
│   ├── app.js                  # Frontend application (87KB)
│   ├── style.css               # Dark tactical stylesheet (13KB)
│   ├── provinces.json          # PH province boundaries GeoJSON (16MB)
│   ├── tiles/                  # Offline map tiles (z12-z17)
│   └── uploads/                # Public report photo storage
├── data/
│   ├── settings.json           # System configuration
│   ├── vers_data.db            # SQLite database
│   └── audit.log               # JSON audit trail
├── docs/                       # Documentation suite
└── venv/                       # Python virtual environment
```

---

## Deployment Target

- **Location**: Barangay Bagumbayan, Taguig City, Metro Manila, Philippines
- **Focal Coordinates**: 14.4681° N, 121.0552° E
- **Hardware**: Raspberry Pi edge server
- **Public Access**: Cloudflare Quick Tunnel (HTTPS, dynamic URL emailed to operator)

---

## License

This project is proprietary software developed for the Local Government Unit (LGU) of Taguig City. All rights reserved.

---

*VERS — Critical Infrastructure Monitoring System © 2026*
*Barangay Bagumbayan, Taguig City, Philippines*
