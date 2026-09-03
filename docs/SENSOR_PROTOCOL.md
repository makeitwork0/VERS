# Sensor Protocol & Node Integration

> **MQTT payload specification, risk scoring algorithm, and hardware integration guide for VERS sensor nodes.**

---

## Table of Contents

- [MQTT Broker Configuration](#mqtt-broker-configuration)
- [Topic Architecture](#topic-architecture)
- [Sensor Telemetry Payload Schema](#sensor-telemetry-payload-schema)
- [Command Channel](#command-channel)
- [Risk Scoring Algorithm](#risk-scoring-algorithm)
- [Fault Detection Heuristics](#fault-detection-heuristics)
- [Alert Throttling](#alert-throttling)
- [Virtual Node Simulator](#virtual-node-simulator)
- [Hardware Integration Guide](#hardware-integration-guide)
- [Example Arduino/ESP32 Code](#example-arduino-esp32-code)

---

## MQTT Broker Configuration

| Parameter | Value |
|---|---|
| **Broker** | Mosquitto (localhost) |
| **Host** | `localhost` (`127.0.0.1`) |
| **Port** | `1883` (TCP, no TLS) |
| **Authentication** | None on loopback (configurable via `MQTT_USER`/`MQTT_PASS`) |
| **Persistence** | Enabled (`/var/lib/mosquitto/`) |
| **Log File** | `/var/log/mosquitto/mosquitto.log` |
| **QoS** | 0 (default, fire-and-forget for real-time telemetry) |

### Broker Service Management

```bash
sudo systemctl status mosquitto
sudo systemctl restart mosquitto
sudo journalctl -u mosquitto -f    # Live log stream
```

### Testing with CLI Tools

```bash
# Subscribe to all sensor topics (for debugging)
mosquitto_sub -h localhost -t "vers/data/#" -v

# Publish a test payload
mosquitto_pub -h localhost -t "vers/data/TEST-01" -m '{
  "id": "TEST-01",
  "timestamp": "2026-08-10T05:00:00Z",
  "sensors": {"fire": 0, "flood": 0, "life_form": 0, "humidity": 55, "gas": 30},
  "battery": 85.0,
  "lat": 14.4681,
  "lon": 121.0552,
  "gps_response": true
}'
```

---

## Topic Architecture

| Topic Pattern | Direction | Purpose |
|---|---|---|
| `vers/data/{node_id}` | Node → Server | Sensor telemetry data (JSON) |
| `vers/cmd/all` | Server → All Nodes | Broadcast commands to all nodes |

### Topic Naming Convention

- `{node_id}` should be a unique alphanumeric identifier (e.g., `Node_01`, `V-Node_05`, `ESP-BLDG-A`)
- No spaces or special characters (underscores and hyphens allowed)
- The server extracts `device_id` from the payload's `id` field first, falling back to the topic suffix

---

## Sensor Telemetry Payload Schema

Each sensor node publishes a JSON payload to `vers/data/{node_id}` at regular intervals.

### Complete Field Specification

```json
{
  "id": "V-Node_01",
  "timestamp": "2026-08-10T05:30:00.000Z",
  "sensors": {
    "fire": 0,
    "flood": 0,
    "life_form": 0,
    "humidity": 55,
    "gas": 30
  },
  "battery": 85.3,
  "lat": 14.4681,
  "lon": 121.0552,
  "gps_response": true
}
```

### Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | **Yes** | Unique node identifier (e.g., `"V-Node_01"`) |
| `timestamp` | `string` | **Yes** | ISO 8601 UTC timestamp (e.g., `"2026-08-10T05:30:00Z"`) |
| `sensors` | `object` | **Yes** | Sensor readings container (see below) |
| `battery` | `float` | **Yes** | Battery level in percentage (0.0–100.0) |
| `lat` | `float` | Recommended | GPS latitude in decimal degrees (WGS84) |
| `lon` | `float` | Recommended | GPS longitude in decimal degrees (WGS84) |
| `gps_response` | `boolean` | Optional | Set `true` when GPS data is fresh; triggers daily GPS logging |

### Sensor Object Fields

| Field | Type | Range | Description |
|---|---|---|---|
| `fire` | `int` | `0` or `1` | Fire detection flag (1 = fire detected) |
| `flood` | `int` | `0` or `1` | Flood detection flag (1 = flooding detected) |
| `life_form` | `int` | `0` or `1` | Life form / intruder detection flag (1 = detected). Also accepts `intruder` as an alias. |
| `humidity` | `int` | `0–100` | Relative humidity percentage |
| `gas` | `int` | `0–999` | Gas concentration in PPM (Parts Per Million) |

---

## Command Channel

The server publishes commands to `vers/cmd/all` for all nodes to process.

### GPS Request Command

Published daily at 02:00 AM via APScheduler:

```json
{
  "action": "REQUEST_GPS",
  "timestamp": "2026-08-10T18:00:00+00:00"
}
```

**Expected Node Behavior**: Upon receiving this command, nodes should:
1. Activate GPS module
2. Acquire fix
3. Publish a telemetry payload with `"gps_response": true` and updated `lat`/`lon` values

---

## Risk Scoring Algorithm

The server calculates a composite risk score (0–100) for each incoming telemetry payload using `calculate_risk()`.

### Scoring Rules

| Condition | Points | Emergency Label |
|---|---|---|
| `fire == 1` | **+100** | Fire |
| `flood == 1` | **+90** | Flood |
| `life_form == 1` (or `intruder == 1`) | **+80** | Life Form Detected |
| `gas > 200` (and not saturated) | **+75** | Gas Leak |
| Hardware fault detected | **min(30, current)** | Hardware Fault |

- Final score is capped at **100**
- Multiple emergencies stack (e.g., fire + flood = 190 → capped to 100)
- Score > 50 triggers the emergency response pipeline

### Risk Level Interpretation

| Score Range | Level | Dashboard Color | Action |
|---|---|---|---|
| 0 | Normal | 🟢 Green | No action |
| 1–30 | Low | 🟡 Yellow | Monitor |
| 31–50 | Moderate | 🟠 Orange | Investigate |
| 51–79 | High | 🔴 Red | Alert + AI advisory |
| 80–100 | Critical | 🔴 Red (pulsing) | Full emergency workflow |

---

## Fault Detection Heuristics

The system flags sensor hardware faults based on physically impossible readings:

| Fault Condition | Diagnosis |
|---|---|
| `humidity <= 0` or `humidity >= 100` | Humidity Sensor Saturated |
| `gas >= 500` | Gas Sensor Saturated |
| `battery <= 0` | Battery Reporting Failure |

When a fault is detected:
- `is_faulty` flag is set to `true`
- Risk score is set to at least 30
- AI prompt includes "SENSOR HARDWARE FAULT DETECTED" for diagnostic guidance
- Dashboard marker turns orange (faulty) instead of red (emergency)

---

## Alert Throttling

To prevent alert fatigue, the system throttles emergency processing:

- **Cooldown**: 60 seconds per device
- **Mechanism**: `last_alert_time[device_id]` tracks the last trigger time
- **Behavior**: If `current_time - last_alert_time[device_id] > 60`, the emergency pipeline fires:
  1. Immediate voice alert via WebSocket
  2. Background AI advisory generation (Gemini → Ollama → fallback)
  3. Email notification to operator
  4. All subsequent payloads within 60s are still logged and broadcast, but don't re-trigger AI/voice/email

---

## Virtual Node Simulator

The `vers_simulator.py` script simulates 10 sensor nodes for testing without physical hardware.

### Simulated Nodes

| Node ID | Latitude | Longitude |
|---|---|---|
| V-Node_01 | 14.4681 | 121.0552 |
| V-Node_02 | 14.4691 | 121.0562 |
| V-Node_03 | 14.4671 | 121.0542 |
| V-Node_04 | 14.4701 | 121.0572 |
| V-Node_05 | 14.4661 | 121.0532 |
| V-Node_06 | 14.4686 | 121.0557 |
| V-Node_07 | 14.4676 | 121.0547 |
| V-Node_08 | 14.4696 | 121.0567 |
| V-Node_09 | 14.4666 | 121.0537 |
| V-Node_10 | 14.4706 | 121.0577 |

### Simulation Behavior

- **Publish Interval**: Every 5 seconds (configurable via `PUBLISH_INTERVAL`)
- **Battery Drain**: Gradual drain of 0.01–0.05% per tick; auto-recharges at 0%
- **Baseline Readings**: humidity=45–65, gas=10–50, fire=0, flood=0, life_form=0
- **Emergency Injection Engine**:
  - 1% chance per tick to trigger an emergency event
  - Emergency types: `fire`, `flood`, `life_form`, `gas_leak`
  - Sustained for 3–8 consecutive ticks
  - Emergency sensor overrides:
    - Fire: `fire=1`, humidity drops to 20–30
    - Flood: `flood=1`, humidity rises to 90–100
    - Life Form: `life_form=1`
    - Gas Leak: `gas=250–400` PPM

### Running the Simulator

```bash
# As a systemd service
sudo systemctl start vers-simulator

# Or manually
source venv/bin/activate
python -u vers_simulator.py

# Remote mode (connect to Pi from another machine)
# Edit MQTT_BROKER in vers_simulator.py to the Pi's IP address
```

---

## Hardware Integration Guide

### Supported Sensor Types

| Sensor | Purpose | Recommended Hardware |
|---|---|---|
| Flame/IR Sensor | Fire detection | KY-026, DFRobot Flame Sensor |
| Water Level Sensor | Flood detection | HC-SR04 (ultrasonic), water level probe |
| PIR Motion Sensor | Life form / intrusion detection | HC-SR501 |
| Humidity Sensor | Environmental monitoring | DHT22, BME280 |
| Gas Sensor | Combustible gas / smoke detection | MQ-2, MQ-135, MQ-5 |
| GPS Module | Location tracking | NEO-6M, NEO-7M |
| Battery Monitor | Power level reporting | Voltage divider on ADC pin |

### Microcontroller Requirements

- **Recommended**: ESP32 (WiFi + Bluetooth) or ESP8266 (WiFi only)
- **Alternative**: Arduino Mega/Uno + WiFi shield or Ethernet shield
- **MQTT Library**: PubSubClient (Arduino) or MicroPython `umqtt`
- **JSON Library**: ArduinoJson

### Communication Pattern

```
┌──────────────┐         MQTT (TCP 1883)         ┌──────────────┐
│  ESP32 Node  │ ─────── vers/data/{id} ────────→ │  VERS Server │
│              │ ←────── vers/cmd/all ──────────── │  (Rasp Pi)   │
└──────────────┘                                   └──────────────┘
```

1. Node connects to MQTT broker on startup
2. Reads sensors every N seconds
3. Constructs JSON payload
4. Publishes to `vers/data/{node_id}`
5. Subscribes to `vers/cmd/all` for server commands
6. On `REQUEST_GPS` command, activates GPS and publishes fresh coordinates

---

## Example Arduino/ESP32 Code

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Configuration
const char* WIFI_SSID     = "YourNetwork";
const char* WIFI_PASS     = "YourPassword";
const char* MQTT_BROKER   = "192.168.100.154";  // Raspberry Pi IP
const int   MQTT_PORT     = 1883;
const char* NODE_ID       = "ESP-Node_01";
const char* TOPIC_DATA    = "vers/data/ESP-Node_01";
const char* TOPIC_CMD     = "vers/cmd/all";

// Sensor pins
const int PIN_FLAME       = 34;
const int PIN_FLOOD       = 35;
const int PIN_PIR         = 32;
const int PIN_GAS         = 33;
const int PUBLISH_INTERVAL = 5000;  // 5 seconds

WiFiClient espClient;
PubSubClient mqtt(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
    // Handle server commands
    StaticJsonDocument<256> doc;
    deserializeJson(doc, payload, length);
    
    const char* action = doc["action"];
    if (strcmp(action, "REQUEST_GPS") == 0) {
        // Activate GPS and publish location
        // ... GPS acquisition code ...
    }
}

void publishSensorData() {
    StaticJsonDocument<512> doc;
    doc["id"] = NODE_ID;
    doc["timestamp"] = getISOTimestamp();  // implement with NTP
    
    JsonObject sensors = doc.createNestedObject("sensors");
    sensors["fire"]      = digitalRead(PIN_FLAME) == LOW ? 1 : 0;
    sensors["flood"]     = analogRead(PIN_FLOOD) > 2000 ? 1 : 0;
    sensors["life_form"] = digitalRead(PIN_PIR);
    sensors["humidity"]  = readDHT22Humidity();     // implement
    sensors["gas"]       = map(analogRead(PIN_GAS), 0, 4095, 0, 500);
    
    doc["battery"]      = readBatteryVoltage();     // implement
    doc["lat"]          = 14.4681;                  // static or GPS
    doc["lon"]          = 121.0552;
    doc["gps_response"] = false;
    
    char buffer[512];
    serializeJson(doc, buffer);
    mqtt.publish(TOPIC_DATA, buffer);
}

void setup() {
    Serial.begin(115200);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) delay(500);
    
    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt.setCallback(callback);
    
    while (!mqtt.connected()) {
        mqtt.connect(NODE_ID);
        delay(1000);
    }
    mqtt.subscribe(TOPIC_CMD);
}

void loop() {
    mqtt.loop();
    publishSensorData();
    delay(PUBLISH_INTERVAL);
}
```

---

## Data Processing Pipeline

When a sensor payload arrives at the server, it passes through this pipeline:

```
MQTT Message Received (on_message)
    │
    ├── 1. Parse JSON payload
    ├── 2. Extract device_id (from payload.id or topic suffix)
    ├── 3. calculate_risk(sensors) → (risk_score, emergencies, is_faulty)
    ├── 4. Inject risk_score and is_faulty into payload
    ├── 5. log_sensor() → SQLite sensor_logs + devices upsert
    ├── 6. If risk > 50 OR is_faulty (throttled to 60s per device):
    │       ├── Voice alert via SocketIO (immediate)
    │       ├── AI advisory via Gemini/Ollama (background thread)
    │       └── Email notification (background thread)
    ├── 7. socketio.emit("sensor_update") → all dashboard clients
    └── 8. If gps_response == true → store_daily_gps()
```

---

*VERS Sensor Protocol Specification v2.4*
