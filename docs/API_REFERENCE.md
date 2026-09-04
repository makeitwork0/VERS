# VERS API Reference

This document provides a comprehensive reference for the VERS (Versatile Emergency Response System) REST API, WebSocket events, and MQTT topics.

## Authentication Methods

The VERS API supports multiple authentication methods depending on the endpoint:

1. **Session Auth**: Login via `POST /login` with `username=operator` and the configurable dashboard password. Successful login sets `session['logged_in'] = True`.
2. **API Key Auth**: Pass the API key via the `X-API-Key` header, the `api_key` query parameter, or as a JSON field in the request body. The API key is auto-generated on first run (`secrets.token_hex(16)`).
3. **Decorator**: The `@require_login` decorator checks the session status. Some specific endpoints accept either a valid session OR a valid API key.

---

## REST API Endpoints

### Public Endpoints (No Auth Required)

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Main Dashboard. Replaces `__OWM_API_KEY__` and `__IS_OPERATOR__` placeholders dynamically. |
| `GET`, `POST` | `/login` | Operator login form and handler. Username is fixed to `operator`, password is from system config. |
| `GET` | `/logout` | Clears current session and redirects to `/login`. |
| `GET` | `/api/auth/status` | Returns current authentication status: `{"logged_in": bool}`. |
| `GET` | `/api/auth/key` | Returns the current system API key: `{"api_key": "..."}`. |
| `GET` | `/api/history` | Retrieves the last 100 sensor logs in chronological order. Response is an array of `{device_id, timestamp, payload}`. |
| `GET` | `/api/warnings` | Retrieves cached GDACS and PAGASA GeoJSON warnings. This is pre-serialized for zero-latency response. |
| `GET` | `/api/pagasa` | Scrapes PAGASA TAMSS for the latest weather bulletin PDFs. Returns `{status, data: [{title, description, pubDate, link}]}`. |
| `GET` | `/api/hazard-assessment` | **Params:** `lat`, `lon`.<br>Checks coordinates against PAGASA warning polygons, GDACS cyclone proximity, and flood susceptibility. Returns `{hazards: [{type, level, source, area, description}]}`. |
| `GET` | `/api/class-suspensions` | Returns active official suspension OR auto-derived DepEd EO 77 status from PAGASA warnings. Response: `{source: "official"\|"auto_derived", data: {level, scope, reason, issued_by, timestamp}}`. |
| `GET` | `/api/settings` | Returns system config (SMTP, OWM key, FB handle). Note: Password is masked as `●●●●●●●●●●●●●●●●`. |
| `GET` | `/report` | Public incident reporting web form. Standalone page featuring photo capture and geolocation. |
| `POST` | `/api/reports/submit` | Submit a public incident report. Requires Multipart form: `report_type`, `description`, `lat`, `lon`, `reporter_name`, `photo` (file). Stores photo in `static/uploads/`. Emits `new_public_report` via SocketIO. |

### Authenticated Endpoints (Session OR API Key)

These endpoints require either an active operator session or a valid API Key provided via header/query/body.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/simulate` | Inject simulated sensor data.<br>**Body:** `{id, lat, lon, sensors: {fire, flood, life_form, gas, humidity}, battery}`.<br>Triggers risk calculation and AI analysis if readings are critical. |
| `POST` | `/api/emergency` | Manual emergency voice alert broadcast. Triggers an alert to all connected clients. |
| `POST` | `/api/dispatch` | Dispatch operator override instructions.<br>**Body:** `{device_id, instruction}`.<br>Emits SocketIO event and sends an email to the configured recipients. |

### Authenticated Endpoints (Session Only — `@require_login`)

These endpoints strictly require an active operator session (login via UI).

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/stats` | System metrics. **Params:** `hours` (default 24). Returns `{connected_now, total_connections, reports_count, alerts_count, reports: [...]}`. |
| `POST` | `/api/settings` | Save system config.<br>**Body:** `{smtp_server, smtp_port, sender_email, sender_password, recipient_email, dashboard_password, owm_api_key, fb_page_handle}`. |
| `POST` | `/api/backup` | Emails a ZIP backup of the system (`vers_system.py`, `vers_simulator.py`, templates, JS/CSS, `settings.json`, SQLite DB). |
| `GET` | `/api/audit` | Retrieves the last 100 audit log entries as a JSON array. |
| `GET` | `/api/history/csv` | Downloads the full sensor logs database as a CSV file. |
| `GET` | `/api/battery/forecast` | Returns battery drain rate and estimated hours remaining per device. |
| `POST` | `/api/report/send` | Manually triggers the daily summary email report generation and dispatch. |
| `POST` | `/api/ack` | Acknowledge an alert.<br>**Body:** `{device_id, timestamp}`.<br>Broadcasts `alert_ack` to all connected clients. |
| `POST` | `/api/broadcast` | Send a text announcement to all dashboards.<br>**Body:** `{message}`. |
| `GET` | `/api/reports` | Retrieves all public incident reports from the last 24 hours. |
| `GET` | `/api/heatmap` | Historical risk heatmap data. **Params:** `hours`. Returns `[[lat, lon, risk_score], ...]`. |
| `POST` | `/api/geofence` | Create a polygon geofence.<br>**Body:** `{name, coordinates: [[lat,lon],...]}`. |
| `GET` | `/api/geofences` | List all saved geofences. |
| `DELETE` | `/api/geofence/<id>` | Delete a geofence by its ID. |
| `POST` | `/api/class-suspensions` | Set an official class suspension.<br>**Body:** `{level, scope, reason}`.<br>Broadcasts via SocketIO. |

---

## WebSocket Events (Namespace: `/dashboard`)

The WebSocket server operates on the `/dashboard` namespace.

### Server → Client Events

| Event Name | Payload Data | Description |
|---|---|---|
| `sensor_update` | `{device_id: string, payload: {id, timestamp, sensors, battery, lat, lon, risk_score, is_faulty}}` | Real-time telemetry data broadcast. |
| `voice_alert` | `{message: string, priority: "high"\|"normal", device: string}` | Triggers TTS (Text-to-Speech) in the client browser. |
| `ai_analysis` | `{device_id: string, analysis: string}` | AI situation report (prefixed with the AI source name). |
| `operator_override` | `{device_id: string, instruction: string}` | Manual instructions dispatched by an operator. |
| `operator_broadcast` | `{message: string, timestamp: string}` | Global text announcement from operator. |
| `alert_ack` | `{device_id: string, timestamp: string}` | Notifies clients that an alert was acknowledged. |
| `warnings_update` | Full `CACHED_WARNINGS` object | GDACS and PAGASA GeoJSON data updates. |
| `new_public_report` | Incident report object | Notifies dashboard of a newly submitted public report. |
| `class_suspension_update`| `{id, level, scope, reason, issued_by, timestamp, source}` | Live update of active class suspension status. |
| `client_count` | `{current: int, total: int}` | Live dashboard connection statistics. |

### Client → Server Events

- `connect` / `disconnect` — Handled automatically by the SocketIO implementation.

---

## MQTT Topics

The system integrates with MQTT brokers for lightweight device communication.

| Topic | Direction | Payload Description |
|---|---|---|
| `vers/data/{node_id}` | Node → Server | JSON sensor telemetry (refer to `SENSOR_PROTOCOL.md` for schema details). |
| `vers/cmd/all` | Server → All Nodes | Broadcast command, e.g., `{"action": "REQUEST_GPS", "timestamp": "..."}`. |
