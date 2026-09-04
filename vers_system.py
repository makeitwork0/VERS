import eventlet
eventlet.monkey_patch()
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import time
import sqlite3
import os
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
import secrets
import csv
import io
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, date, timezone, timedelta
from threading import Thread, Event
import queue
import google.genai as genai

try:
    from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for, Response
    from flask_socketio import SocketIO, emit
    import paho.mqtt.client as mqtt
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception as e:
    raise SystemExit(f"Missing dependency or import error: {e}\nTry running: pip install flask flask-socketio paho-mqtt apscheduler google-genai")

# =========================
# CONFIG
# =========================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASS = None

MQTT_SENSOR_TOPIC = "vers/data/+"
MQTT_CMD_TOPIC_ALL = "vers/cmd/all"

DAILY_GPS_TIME = "02:00"
DB_PATH = os.path.join("data", "vers_data.db")

FLASK_HOST = "0.0.0.0"
FLASK_PORT = int(os.environ.get("PORT", 5000))

# Initialize Gemini AI client for processing emergencies
# This will pick up GEMINI_API_KEY from environment
ai_client = None
try:
    ai_client = genai.Client()
    print("Gemini AI client initialized successfully.")
except Exception as e:
    print(f"Warning: Gemini AI client initialization failed: {e}. Primary AI disabled, will use Ollama fallback.")

last_alert_time = {}

# =========================
# APP & SOCKETIO
# =========================
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "vers-super-secret-key-123")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# =========================
# CONTEXT & AI ENGINE
# =========================
HANDBOOK_CONTEXT = """
VERS Critical Infrastructure Handbook (v2.4)
============================================
1. FIRE EMERGENCY
- Priority: Immediate Evacuation.
- Protocol: Do not use elevators. If safe, use fire extinguishers for small localized fires. 
- Systems: Turn off gas valves. Secure HVAC systems to prevent smoke spread.

2. FLOOD THREAT
- Priority: Equipment Protection & High Ground.
- Protocol: Move personnel to higher ground immediately. Do not walk through moving water.
- Systems: Turn off main electrical breakers in affected zones. Deploy water barriers if available.

3. LIFE FORM DETECTION (Restricted Zones)
- Priority: Intrusion Assessment & Containment.
- Protocol: No life forms should be present in restricted zones during emergencies. Assess if it's trapped personnel or unauthorized entry.
- Systems: Lock down adjacent sectors. Activate intercom warning. Alert local authorities if unauthorized.

4. GAS LEAK
- Priority: Ventilation & Spark Prevention.
- Protocol: Evacuate area immediately upwind. Do NOT use electrical switches, radios, or cell phones in the hot zone.
- Systems: Ensure maximum ventilation if automated. Shut down main gas supply valves if safely accessible.

5. SEVERE WEATHER / HIGH WIND
- Priority: Structural Integrity.
- Protocol: Secure loose equipment. Stay clear of windows and exterior walls.
- Systems: Lower antennas or deployable structures. Switch to backup power if grid instability is detected.
"""

# =========================
# EMAIL/SMTP CONFIGURATION
# =========================
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "erosrohantorres@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "cfrdfizrjjnzsdwa").replace(" ", "")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "erosrohantorres@gmail.com")

SETTINGS_PATH = "data/settings.json"
AUDIT_LOG_PATH = "data/audit.log"

DASHBOARD_PASSWORD = "vers2024"
API_KEY = ""
OWM_API_KEY = ""

FB_PAGE_HANDLE = "IloveTaguig"
FB_ACCESS_TOKEN = ""

def load_settings():
    global SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL, API_KEY, DASHBOARD_PASSWORD, OWM_API_KEY, FB_PAGE_HANDLE, FB_ACCESS_TOKEN
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r") as f:
                data = json.load(f)
                SMTP_SERVER = data.get("smtp_server", SMTP_SERVER)
                SMTP_PORT = int(data.get("smtp_port", SMTP_PORT))
                SENDER_EMAIL = data.get("sender_email", SENDER_EMAIL)
                SENDER_PASSWORD = data.get("sender_password", SENDER_PASSWORD).replace(" ", "")
                RECIPIENT_EMAIL = data.get("recipient_email", RECIPIENT_EMAIL)
                API_KEY = data.get("api_key", "")
                DASHBOARD_PASSWORD = data.get("dashboard_password", DASHBOARD_PASSWORD)
                OWM_API_KEY = data.get("owm_api_key", "")
                FB_PAGE_HANDLE = data.get("fb_page_handle", "IloveTaguig")
                FB_ACCESS_TOKEN = data.get("fb_access_token", "")
                print("[CONFIG] Loaded settings from data/settings.json")
        except Exception as e:
            print(f"[CONFIG] Error loading settings.json: {e}")

def _ensure_api_key():
    """Ensures API_KEY is set; generates and persists one if missing."""
    global API_KEY
    if API_KEY:
        return
    API_KEY = secrets.token_hex(16)
    print(f"[CONFIG] Generated new API key: {API_KEY}")
    # Persist it alongside existing settings
    os.makedirs("data", exist_ok=True)
    existing = {}
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing["api_key"] = API_KEY
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(existing, f, indent=4)
    except Exception as e:
        print(f"[CONFIG] Could not persist API key: {e}")

def save_settings_to_file(smtp_server, smtp_port, sender_email, sender_password, recipient_email, dashboard_password=None, owm_api_key=None, fb_page_handle=None, fb_access_token=None):
    global DASHBOARD_PASSWORD, OWM_API_KEY, FB_PAGE_HANDLE, FB_ACCESS_TOKEN
    if dashboard_password is not None:
        DASHBOARD_PASSWORD = dashboard_password
    if owm_api_key is not None:
        OWM_API_KEY = owm_api_key
    if fb_page_handle is not None:
        FB_PAGE_HANDLE = fb_page_handle
    if fb_access_token is not None:
        FB_ACCESS_TOKEN = fb_access_token
    os.makedirs("data", exist_ok=True)
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump({
                "smtp_server": smtp_server,
                "smtp_port": int(smtp_port),
                "sender_email": sender_email,
                "sender_password": sender_password,
                "recipient_email": recipient_email,
                "api_key": API_KEY,
                "dashboard_password": DASHBOARD_PASSWORD,
                "owm_api_key": OWM_API_KEY,
                "fb_page_handle": FB_PAGE_HANDLE,
                "fb_access_token": FB_ACCESS_TOKEN
            }, f, indent=4)
        return True
    except Exception as e:
        print(f"[CONFIG] Error saving settings.json: {e}")
        return False

# Load persistent settings on startup
load_settings()
_ensure_api_key()

from functools import wraps

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =========================
# AUDIT LOG
# =========================
def write_audit(action, detail, session_id="system"):
    """Appends a JSON audit log entry to data/audit.log"""
    os.makedirs("data", exist_ok=True)
    entry = json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "detail": detail,
        "session": session_id
    })
    try:
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(entry + "\n")
    except Exception as e:
        print(f"[AUDIT] Error writing audit log: {e}")

# =========================
# API KEY AUTH
# =========================
def check_api_key():
    """Returns True if a valid API key is present in the request header or query param."""
    provided = request.headers.get("X-API-Key") or request.args.get("api_key") or \
               (request.get_json(silent=True) or {}).get("api_key")
    return provided == API_KEY

def build_html_template(title, content_html, color_accent="#00ff66"):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                background-color: #0b0f10;
                color: #cfe8d6;
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #14232d;
                border: 1px solid #1e3640;
                border-radius: 8px;
                overflow: hidden;
            }}
            .header {{
                background-color: #071018;
                border-bottom: 2px solid {color_accent};
                padding: 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 20px;
                color: #ffffff;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
            .content {{
                padding: 25px;
                font-size: 14px;
                line-height: 1.6;
            }}
            .footer {{
                background-color: #071018;
                border-top: 1px solid #1e3640;
                padding: 15px;
                text-align: center;
                font-size: 11px;
                color: #8a9fa0;
            }}
            .highlight {{
                color: {color_accent};
                font-weight: bold;
            }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                margin-top: 15px;
                background-color: {color_accent};
                color: #000000;
                text-decoration: none;
                font-weight: bold;
                border-radius: 4px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{title}</h1>
            </div>
            <div class="content">
                {content_html}
            </div>
            <div class="footer">
                VERS - Critical Infrastructure Monitoring System &copy; 2026<br>
                Barangay Bagumbayan, Taguig City, Philippines
            </div>
        </div>
    </body>
    </html>
    """

email_queue = queue.Queue()

def email_worker_task():
    while True:
        try:
            task = email_queue.get(block=True)
            device_id = task.get("device_id")
            subject = task.get("subject")
            body = task.get("body")
            html_body = task.get("html_body")
            
            msg = MIMEMultipart("alternative")
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECIPIENT_EMAIL
            msg['Subject'] = f"[VERS ALERT] {subject} - {device_id}"
            
            msg.attach(MIMEText(body, 'plain'))
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
            server.close()
            print(f"[SMTP] Email alert sent successfully to {RECIPIENT_EMAIL} for {device_id}")
            write_audit("EMAIL_ALERT_SENT", f"device={device_id} subject={subject} to={RECIPIENT_EMAIL}")
            eventlet.sleep(0.5)
        except Exception as e:
            print(f"[SMTP] Error sending email alert: {e}")

email_thread = Thread(target=email_worker_task, daemon=True)
email_thread.start()

def send_email_alert(device_id, subject, body, html_body=None):
    """Sends an email alert using SMTP by queuing it for the background worker"""
    if not SENDER_PASSWORD or SENDER_PASSWORD == "your_16char_app_password":
        print(f"[SMTP] Email alert skipped: SENDER_PASSWORD not configured. Subject: {subject}")
        return False
    email_queue.put({
        "device_id": device_id,
        "subject": subject,
        "body": body,
        "html_body": html_body
    })

def calculate_risk(sensor_data):
    """Calculates risk score based on sensor state, identifies emergencies, and detects faults"""
    risk = 0
    emergencies = []
    is_faulty = False
    faults = []
    
    # Extract values safely
    humidity = int(sensor_data.get('humidity', 50))
    gas = int(sensor_data.get('gas', 0))
    battery = float(sensor_data.get('battery', 80))
    fire = int(sensor_data.get('fire', 0))
    flood = int(sensor_data.get('flood', 0))
    life_form = int(sensor_data.get('life_form', 0)) or int(sensor_data.get('intruder', 0))
    
    # Fault heuristic checks
    if humidity <= 0 or humidity >= 100:
        is_faulty = True
        faults.append('Humidity Sensor Saturated')
    if gas >= 500:
        is_faulty = True
        faults.append('Gas Sensor Saturated')
    if battery <= 0:
        is_faulty = True
        faults.append('Battery Reporting Failure')
        
    if fire == 1:
        risk += 100
        emergencies.append('Fire')
    if flood == 1:
        risk += 90
        emergencies.append('Flood')
    if life_form == 1:
        risk += 80
        emergencies.append('Life Form Detected')
    if gas > 200 and 'Gas Sensor Saturated' not in faults:
        risk += 75
        emergencies.append('Gas Leak')
        
    if is_faulty:
        emergencies.append(f"Hardware Fault ({', '.join(faults)})")
        risk = max(risk, 30)
        
    return min(risk, 100), emergencies, is_faulty

def process_abnormal_data(device_id, payload, risk_score, emergencies, is_faulty=False):
    """Triggers when abnormal data or sensor fault is detected"""
    lat = payload.get('lat', 'Unknown')
    lon = payload.get('lon', 'Unknown')
    emerg_str = ", ".join(emergencies)
    
    # 1. Immediate initial voice warning (Fast)
    if is_faulty and risk_score < 50:
        init_msg = f"Sensor diagnostic fault detected at {device_id}."
    else:
        init_msg = f"Emergency detected at {device_id}. Location {lat}, {lon}. Type: {emerg_str}."
    socketio.emit("voice_alert", {"message": init_msg, "priority": "high", "device": device_id}, namespace="/dashboard")
    
    # 2. Feed into AI for contextual instruction (Background)
    def ai_task():
        # Construct context-rich prompt
        prompt = f"""
{HANDBOOK_CONTEXT}

Current Incident Data:
- Device/Cell: {device_id}
- Location: {lat}, {lon}
- Emergency Types: {emerg_str}
- Risk Score: {risk_score}/100
- Raw Sensors: {json.dumps(payload.get('sensors', {}))}
- Weather/News Context: Wind 15km/h NW, localized severe weather warning active.
- Diagnostic Status: {"SENSOR HARDWARE FAULT DETECTED" if is_faulty else "SENSOR FUNCTIONING NORMAL"}

Based on the handbook and the environmental data, provide a concise, 2-3 sentence actionable instruction for the on-site operators or maintenance crew. If a sensor hardware fault is indicated, instruct technicians on how to inspect or reset the device. Make it clear, direct, and authoritative so it can be read out loud by text-to-speech. Do not use markdown or asterisks.
"""
        ai_instruction = ""
        ai_source = ""
        
        # Try primary Gemini AI if client is available
        if ai_client is not None:
            try:
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                ai_instruction = response.text.strip()
                ai_source = "Gemini AI"
            except Exception as e:
                print(f"Gemini API Error: {e}. Falling back to Ollama...")

        # Fallback to Ollama if Gemini failed or is not configured
        if not ai_instruction:
            try:
                import urllib.request
                import urllib.error
                
                req = urllib.request.Request(
                    "http://localhost:11434/api/generate",
                    data=json.dumps({
                        "model": "qwen2.5:0.5b",
                        "prompt": prompt,
                        "stream": False
                    }).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    ai_instruction = res_data.get("response", "").strip()
                    ai_source = "Ollama Local Backup"
            except Exception as ollama_e:
                print(f"Ollama Backup Error: {ollama_e}")
                ai_instruction = "Emergency AI systems offline. Please refer to the manual handbook protocols immediately."
                ai_source = "System Fallback"

        if ai_instruction:
            # Emit AI advisory back to frontend
            socketio.emit("voice_alert", {"message": ai_instruction, "priority": "normal", "device": device_id}, namespace="/dashboard")
            socketio.emit("ai_analysis", {"device_id": device_id, "analysis": f"[{ai_source}] {ai_instruction}"}, namespace="/dashboard")
            print(f"AI Instruction generated for {device_id} via {ai_source}: {ai_instruction}")
            
            # Generate styled HTML body based on emergency type
            color_accent = "#fa0" if not is_faulty else "#0f6"
            content_html = f"""
            <p>An emergency incident has been detected at monitoring node <span class="highlight">{device_id}</span>.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="border-bottom: 1px solid #1e3640;"><td style="padding: 8px 0; color: #8a9fa0;">Risk Score:</td><td style="padding: 8px 0; font-weight: bold; color: {color_accent};">{risk_score}/100</td></tr>
                <tr style="border-bottom: 1px solid #1e3640;"><td style="padding: 8px 0; color: #8a9fa0;">Active Hazards:</td><td style="padding: 8px 0; font-weight: bold; color: #ffffff;">{emerg_str}</td></tr>
                <tr style="border-bottom: 1px solid #1e3640;"><td style="padding: 8px 0; color: #8a9fa0;">Coordinates:</td><td style="padding: 8px 0; font-family: monospace;">{lat}, {lon}</td></tr>
            </table>
            <h3 style="color: {color_accent}; margin-top: 20px;">AI Advisory Instruction:</h3>
            <p style="background-color: #071018; padding: 15px; border-left: 4px solid {color_accent}; border-radius: 4px; font-style: italic; color: #cfe8d6;">
                {ai_instruction}
            </p>
            <p style="margin-top: 20px;">Please check the live operations dashboard for evacuation routes and proximity services.</p>
            <a href="http://localhost:5000" class="button" style="background-color: {color_accent};">Open Dashboard</a>
            """
            html_body = build_html_template(
                title=f"VERS - EMERGENCY ALERT",
                content_html=content_html,
                color_accent=color_accent
            )
            
            send_email_alert(
                device_id=device_id,
                subject=f"AI Advisory Alert ({'Sensor Fault' if is_faulty else 'Hazard'})",
                body=f"VERS EMERGENCY ALERT\n\nDevice ID: {device_id}\nRisk Score: {risk_score}/100\nEmergencies: {emerg_str}\nLocation: {lat}, {lon}\n\nGenerated Actionable Instruction:\n{ai_instruction}\n\nThis is an automated alert from the VERS Monitoring System.",
                html_body=html_body
            )

    # Run AI task in background so we don't block socket emitting
    socketio.start_background_task(ai_task)

# =========================
# DB UTILITIES
# =========================
def db_connect():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL;')
    # Ensure tables exist
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT, timestamp TEXT, payload TEXT)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_sensor_logs_timestamp ON sensor_logs(timestamp)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_sensor_logs_device_id ON sensor_logs(device_id)''')
    c.execute('''CREATE TABLE IF NOT EXISTS devices (id TEXT PRIMARY KEY, name TEXT, last_seen TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_gps (device_id TEXT, date TEXT, lat REAL, lon REAL, timestamp TEXT, PRIMARY KEY(device_id, date))''')
    c.execute('''CREATE TABLE IF NOT EXISTS public_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, report_type TEXT, description TEXT, lat REAL, lon REAL, reporter_name TEXT, timestamp TEXT, status TEXT DEFAULT 'unverified', image_path TEXT DEFAULT '')''')
    c.execute('''CREATE TABLE IF NOT EXISTS geofences (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, coordinates TEXT, created_at TEXT, created_by TEXT DEFAULT 'operator')''')
    c.execute('''CREATE TABLE IF NOT EXISTS class_suspensions (id INTEGER PRIMARY KEY AUTOINCREMENT, level TEXT, scope TEXT, reason TEXT, issued_by TEXT, timestamp TEXT, active INTEGER DEFAULT 1)''')
    try:
        c.execute("ALTER TABLE public_reports ADD COLUMN image_path TEXT DEFAULT ''")
    except Exception:
        pass
    conn.commit()
    return conn

# =========================
# ASYNC DB WRITER QUEUE
# =========================
db_write_queue = queue.Queue()

def db_writer_task():
    """Background thread that consumes telemetry writes from the queue and bulk inserts them."""
    # We maintain one long-lived connection for this writer thread
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    
    last_prune_time = 0
    
    while True:
        try:
            current_time = time.time()
            if current_time - last_prune_time > 3600:
                last_prune_time = current_time
                try:
                    c = conn.cursor()
                    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                    for table in ["sensor_logs", "public_reports", "class_suspensions", "daily_gps"]:
                        while True:
                            c.execute(f"DELETE FROM {table} WHERE rowid IN (SELECT rowid FROM {table} WHERE timestamp < ? LIMIT 500)", (cutoff_date,))
                            conn.commit()
                            eventlet.sleep(0.05)
                            if c.rowcount < 500:
                                break
                except Exception as e:
                    print(f"Error pruning DB: {e}")
                    try: conn.rollback()
                    except: pass
                    
            # Block until at least one item is available
            task = db_write_queue.get(block=True, timeout=5)
            
            # Start accumulating items for bulk commit
            items = [task]
            while not db_write_queue.empty() and len(items) < 200:
                try:
                    items.append(db_write_queue.get_nowait())
                except queue.Empty:
                    break
                    
            c = conn.cursor()
            c.execute('BEGIN TRANSACTION')
            for item in items:
                try:
                    task_type = item.get("type")
                    if task_type == "sensor_log":
                        c.execute("INSERT INTO sensor_logs (device_id, timestamp, payload) VALUES (?, ?, ?)",
                                  (item["device_id"], item["timestamp"], json.dumps(item["payload"])))
                        c.execute("INSERT OR REPLACE INTO devices (id, name, last_seen) VALUES (?, ?, ?)",
                                  (item["device_id"], item["device_id"], item["timestamp"]))
                    elif task_type == "daily_gps":
                        c.execute('''
                          INSERT INTO daily_gps (device_id, date, lat, lon, timestamp)
                          VALUES (?, ?, ?, ?, ?)
                          ON CONFLICT(device_id, date) DO UPDATE SET
                            lat=excluded.lat, lon=excluded.lon, timestamp=excluded.timestamp
                        ''', (item["device_id"], item["date"], item["lat"], item["lon"], item["timestamp"]))
                except Exception as e:
                    print(f"Error processing db task: {e}")
            c.execute('COMMIT')
        except queue.Empty:
            continue
        except Exception as e:
            print(f"DB Writer thread error: {e}")
            try:
                conn.rollback()
            except: pass

# Start the DB writer thread
db_thread = Thread(target=db_writer_task, daemon=True)
db_thread.start()

def log_sensor(device_id, payload):
    db_write_queue.put({
        "type": "sensor_log",
        "device_id": device_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload
    })

def store_daily_gps(device_id, lat, lon, ts):
    today = date.today().isoformat()
    db_write_queue.put({
        "type": "daily_gps",
        "device_id": device_id,
        "date": today,
        "lat": lat,
        "lon": lon,
        "timestamp": ts
    })

def get_daily_gps_all():
    conn = db_connect()
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute("SELECT device_id, lat, lon, timestamp FROM daily_gps WHERE date = ?", (today,))
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({"device_id": r[0], "lat": r[1], "lon": r[2], "timestamp": r[3]})
    return out

# Initialize DB on startup
db_connect().close()

# =========================
# MQTT CLIENT
# =========================
try:
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    mqtt_client = mqtt.Client()

if MQTT_USER:
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

def on_connect(client, userdata, flags, rc, *args, **kwargs):
    print("MQTT connected with rc=", rc)
    client.subscribe(MQTT_SENSOR_TOPIC, qos=1)
    print("Subscribed to", MQTT_SENSOR_TOPIC, "with QoS 1")

def on_disconnect(client, userdata, rc, *args, **kwargs):
    if rc != 0:
        print("Unexpected MQTT disconnection. Auto-reconnecting in background...")

active_earthquake_nodes = {}

def on_message(client, userdata, msg):
    global active_earthquake_nodes
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        try:
            j = json.loads(payload)
            if not isinstance(j, dict):
                return
        except Exception:
            return
        device_id = j.get("id") or topic.split("/")[-1]
        
        # Calculate risk before logging and emitting
        sensors = j.get('sensors', {})
        risk_score, emergencies, is_faulty = calculate_risk(sensors)
        
        # --- Earthquake / Network Movement Logic ---
        is_earthquake = int(sensors.get('earthquake', 0)) or int(sensors.get('movement', 0))
        current_time = time.time()
        
        if is_earthquake:
            active_earthquake_nodes[device_id] = current_time
            
        # Clean up old earthquake signals (older than 60s)
        stale_nodes = [did for did, ts in active_earthquake_nodes.items() if current_time - ts > 60]
        for did in stale_nodes:
            del active_earthquake_nodes[did]
            
        stale_alerts = [did for did, ts in last_alert_time.items() if current_time - ts > 3600]
        for did in stale_alerts:
            del last_alert_time[did]
            
        eq_count = len(active_earthquake_nodes)
        is_earthquake_local = False
        
        if is_earthquake:
            if eq_count >= 3:
                risk_score = max(risk_score, 100)
                if "Earthquake (System-Wide Warning)" not in emergencies:
                    emergencies.append("Earthquake (System-Wide Warning)")
                
                # System-wide voice alert logic
                if "system_earthquake" not in last_alert_time or current_time - last_alert_time.get("system_earthquake", 0) > 60:
                    last_alert_time["system_earthquake"] = current_time
                    socketio.emit("voice_alert", {"message": "SYSTEM WIDE WARNING. MAJOR EARTHQUAKE DETECTED BY MULTIPLE NODES. INITIATE EVACUATION PROTOCOLS IMMEDIATELY.", "priority": "high", "device": "SYSTEM"}, namespace="/dashboard")
            else:
                # 2 nodes and below will ONLY trigger a dashboard warning.
                # Setting risk_score to 51 ensures it shows up as an alert on the dashboard (yellow/orange),
                # but we will bypass the normal AI processing logic below.
                risk_score = max(risk_score, 51) 
                if "Movement (Localized)" not in emergencies:
                    emergencies.append("Movement (Localized)")
                is_earthquake_local = True
        # --------------------------------------------
        
        j['risk_score'] = risk_score
        j['is_faulty'] = is_faulty
        j['emergencies'] = emergencies
        
        log_sensor(device_id, j)
        
        # If risk is critical or fault detected, trigger processing (AI + Voice)
        # We skip AI processing for a minor localized movement, unless there is another emergency driving the risk above 51.
        should_trigger_abnormal = (risk_score > 51) or (risk_score > 50 and not is_earthquake_local) or is_faulty
        
        if should_trigger_abnormal:
            if device_id not in last_alert_time or current_time - last_alert_time[device_id] > 60:
                last_alert_time[device_id] = current_time
                process_abnormal_data(device_id, j, risk_score, emergencies, is_faulty)
            
        # Emit to websocket clients
        socketio.emit("sensor_update", {"device_id": device_id, "payload": j}, namespace="/dashboard")
        
        if "gps_response" in j and j["gps_response"] is True:
            lat = float(j.get("lat", 0))
            lon = float(j.get("lon", 0))
            store_daily_gps(device_id, lat, lon, j.get("timestamp", datetime.now(timezone.utc).isoformat()))
    except Exception as e:
        print("Error parsing MQTT message:", e)

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message

def mqtt_thread(stop_event):
    retry_delay = 1
    while not stop_event.is_set():
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            print("Successfully connected to MQTT broker.")
            break
        except Exception as e:
            print(f"MQTT connect failed: {e}. Retrying in {retry_delay}s...")
            stop_event.wait(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

    if stop_event.is_set():
        return

    mqtt_client.loop_start()
    while not stop_event.is_set():
        stop_event.wait(1)
    mqtt_client.loop_stop()

# =========================
# SCHEDULER: daily GPS requests
# =========================
scheduler = BackgroundScheduler()

def request_gps_from_all():
    cmd = {"action": "REQUEST_GPS", "timestamp": datetime.now(timezone.utc).isoformat()}
    mqtt_client.publish(MQTT_CMD_TOPIC_ALL, json.dumps(cmd))
    print("Published REQUEST_GPS to", MQTT_CMD_TOPIC_ALL)

hh, mm = DAILY_GPS_TIME.split(":")
scheduler.add_job(request_gps_from_all, 'cron', hour=int(hh), minute=int(mm))
scheduler.start()

# =========================
# FLASK ROUTES
# =========================
@app.route("/api/request-gps", methods=["POST"])
@require_login
def api_request_gps():
    request_gps_from_all()
    write_audit("GPS_REQUEST_MANUAL", "Manual GPS request triggered by operator", session_id=session.get('username'))
    return jsonify({"status": "ok", "message": "GPS request dispatched to all nodes via MQTT"})
def get_index_html():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route("/")
def index():
    is_operator = session.get('logged_in', False)
    html = get_index_html().replace("__OWM_API_KEY__", OWM_API_KEY)
    html = html.replace("__IS_OPERATOR__", "true" if is_operator else "false")
    return html

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "operator" and password == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            write_audit("LOGIN_SUCCESS", f"user={username}", session_id="operator")
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password"
            write_audit("LOGIN_FAILURE", f"user={username}", session_id="system")
            
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VERS Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { box-sizing: border-box; }
            body {
                background: #070b0d;
                background-image: radial-gradient(circle at 50% -20%, rgba(0, 255, 102, 0.05), transparent 60%);
                color: #e2f1e8;
                font-family: 'Inter', system-ui, sans-serif;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                padding: 20px;
            }
            .login-card {
                background: rgba(13, 20, 26, 0.7);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(30, 54, 64, 0.6);
                border-top: 4px solid #00ff66;
                padding: 40px;
                border-radius: 16px;
                width: 100%;
                max-width: 420px;
                box-shadow: 0 12px 48px rgba(0,0,0,0.6);
            }
            h1 {
                font-size: 24px;
                color: #fff;
                margin: 0 0 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-weight: 700;
            }
            p.subtitle {
                font-size: 13px;
                color: #8a9fa0;
                margin: 0 0 28px;
                line-height: 1.5;
            }
            .form-group {
                margin-bottom: 24px;
            }
            label {
                display: block;
                font-size: 11px;
                color: #00bcd4;
                text-transform: uppercase;
                font-weight: 600;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }
            input[type="text"], input[type="password"] {
                width: 100%;
                padding: 12px 14px;
                background: rgba(0,0,0,0.2);
                border: 1px solid rgba(30, 54, 64, 0.6);
                color: #e2f1e8;
                border-radius: 8px;
                font-size: 14px;
                outline: none;
                transition: all 0.2s;
                font-family: 'Inter', system-ui, sans-serif;
            }
            input[type="text"]:focus, input[type="password"]:focus {
                border-color: #00ff66;
                box-shadow: 0 0 0 3px rgba(0,255,102,0.15);
            }
            button {
                width: 100%;
                padding: 14px;
                background: #00ff66;
                color: #000;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 700;
                cursor: pointer;
                text-transform: uppercase;
                letter-spacing: 1px;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            }
            button:hover {
                background: #00cc55;
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(0,255,102,0.3);
            }
            .error-box {
                background: rgba(255, 71, 87, 0.08);
                border: 1px solid #ff4757;
                color: #ff4757;
                padding: 12px;
                border-radius: 8px;
                font-size: 13px;
                margin-bottom: 24px;
                text-align: center;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <div class="login-card">
            <h1>VERS System Access</h1>
            <p class="subtitle">Versatile Emergency Response Dashboard Gate</p>
            
            """ + (f'<div class="error-box">{error}</div>' if error else '') + """
            
            <form method="POST">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" name="username" placeholder="operator" required autofocus>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" placeholder="••••••••" required>
                </div>
                <button type="submit">Unlock Dashboard</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    write_audit("LOGOUT", "operator logged out", session_id="operator")
    return redirect(url_for("login"))

@app.route("/api/auth/status")
def auth_status():
    return jsonify({"logged_in": session.get('logged_in', False)})

@app.route('/api/stats')
@require_login
def get_stats():
    hours = request.args.get('hours', 24, type=int)
    conn = db_connect()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM public_reports WHERE datetime(timestamp) >= datetime('now', ?)", (f'-{hours} hours',))
        report_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM sensor_logs WHERE datetime(timestamp) >= datetime('now', ?)", (f'-{hours} hours',))
        alert_count = c.fetchone()[0]
        c.execute("SELECT id, report_type, description, lat, lon, reporter_name, timestamp, status, image_path FROM public_reports ORDER BY id DESC LIMIT 50")
        rows = c.fetchall()
        reports = []
        for r in rows:
            reports.append({
                "id": r[0], "report_type": r[1], "description": r[2],
                "lat": r[3], "lon": r[4], "reporter_name": r[5],
                "timestamp": r[6], "status": r[7], "image_path": r[8] or ''
            })
    finally:
        conn.close()

    return jsonify({
        "status": "ok",
        "connected_now": len(CONNECTED_CLIENTS),
        "total_connections": TOTAL_CONNECTIONS_EVER,
        "reports_count": report_count,
        "alerts_count": alert_count,
        "reports": reports
    })

@app.route('/api/hazard-assessment')
def hazard_assessment():
    """Quick hazard assessment for a given location using cached PAGASA data."""
    lat = request.args.get('lat', 0, type=float)
    lon = request.args.get('lon', 0, type=float)
    
    hazards = []
    
    # Check PAGASA rainfall warnings
    pagasa = CACHED_WARNINGS.get('pagasa', {})
    if pagasa.get('features'):
        for f in pagasa['features']:
            try:
                from shapely.geometry import Point, shape
                point = Point(lon, lat)
                polygon = shape(f['geometry'])
                if polygon.contains(point):
                    level = f['properties'].get('alertlevel', 'Unknown')
                    hazards.append({
                        'type': 'Rainfall Warning',
                        'level': level,
                        'source': 'PAGASA',
                        'area': f['properties'].get('name', 'Unknown'),
                        'description': f['properties'].get('description', '')
                    })
            except:
                pass
    
    # Check GDACS cyclones proximity
    gdacs = CACHED_WARNINGS.get('gdacs', {})
    if gdacs.get('features'):
        import math
        seen_cyclones = set()
        for f in gdacs['features']:
            name = f.get('properties', {}).get('name', '')
            if name in seen_cyclones:
                continue
            if f.get('geometry', {}).get('type') == 'Point':
                coords = f['geometry']['coordinates']
                dist = math.sqrt((lat - coords[1])**2 + (lon - coords[0])**2)
                if dist < 5:  # roughly 500km
                    seen_cyclones.add(name)
                    hazards.append({
                        'type': 'Tropical Cyclone',
                        'level': f['properties'].get('alertlevel', 'Unknown'),
                        'source': 'GDACS',
                        'area': name,
                        'description': f['properties'].get('htmldescription', '')
                    })
    
    # Flood susceptibility based on elevation (approximate)
    if lat > 0 and lon > 0:
        # Low-lying areas near Manila Bay are flood-prone
        if 14.3 <= lat <= 14.8 and 120.8 <= lon <= 121.2:
            hazards.append({
                'type': 'Flood Susceptibility',
                'level': 'High',
                'source': 'VERS Analysis',
                'area': 'Metro Manila / Cavite / Laguna Basin',
                'description': 'Low-lying area near major waterways. Historically flood-prone during monsoon season.'
            })
        elif 14.0 <= lat <= 15.5 and 120.0 <= lon <= 122.0:
            hazards.append({
                'type': 'Flood Susceptibility',
                'level': 'Moderate',
                'source': 'VERS Analysis',
                'area': 'Central Luzon Plains',
                'description': 'Area is within the Central Luzon flood plain. Monitor river levels during heavy rain.'
            })
    
    return jsonify({
        'status': 'ok',
        'latitude': lat,
        'longitude': lon,
        'hazard_count': len(hazards),
        'hazards': hazards
    })

@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """Receives simulation data from frontend, processes it through AI, and broadcasts via sockets"""
    if not (session.get("logged_in") or check_api_key()):
        return jsonify({"status": "error", "message": "Unauthorized: invalid session or missing API key"}), 401
    data = request.json
    device_id = data.get("id", "Unknown")
    
    sensors = data.get('sensors', {})
    risk_score, emergencies, is_faulty = calculate_risk(sensors)
    data['risk_score'] = risk_score
    data['is_faulty'] = is_faulty
    
    log_sensor(device_id, data)
    
    if risk_score > 50 or is_faulty:
        process_abnormal_data(device_id, data, risk_score, emergencies, is_faulty)
        
    socketio.emit("sensor_update", {"device_id": device_id, "payload": data}, namespace="/dashboard")
    return jsonify({"status": "ok", "message": "Simulation processed"})

@app.route("/api/emergency", methods=["POST"])
def api_emergency():
    """Manual emergency trigger"""
    if not (session.get("logged_in") or check_api_key()):
        return jsonify({"status": "error", "message": "Unauthorized: invalid session or missing API key"}), 401
    msg = "Manual emergency override activated by operator."
    socketio.emit("voice_alert", {"message": msg, "priority": "high"}, namespace="/dashboard")
    return jsonify({"status": "ok"})

@app.route("/api/history")
def api_history():
    """Returns the last 100 historical logs in chronological order"""
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT device_id, timestamp, payload FROM sensor_logs ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    
    out = []
    for r in rows:
        try:
            payload = json.loads(r[2])
        except Exception:
            payload = {}
        out.append({
            "device_id": r[0],
            "timestamp": r[1],
            "payload": payload
        })
    out.reverse()
    return jsonify(out)

@app.route("/api/dispatch", methods=["POST"])
def api_dispatch():
    """Manual operator override/dispatch instruction"""
    if not (session.get("logged_in") or check_api_key()):
        return jsonify({"status": "error", "message": "Unauthorized: invalid session or missing API key"}), 401
    data = request.json
    device_id = data.get("device_id", "Unknown")
    instruction = data.get("instruction", "")
    
    socketio.emit("operator_override", {
        "device_id": device_id,
        "instruction": instruction
    }, namespace="/dashboard")
    
    # Log the dispatch event
    conn = db_connect()
    c = conn.cursor()
    c.execute("INSERT INTO sensor_logs (device_id, timestamp, payload) VALUES (?, ?, ?)",
              (device_id, datetime.now(timezone.utc).isoformat(), json.dumps({
                  "id": device_id,
                  "type": "operator_override",
                  "instruction": instruction,
                  "risk_score": 0
              })))
    conn.commit()
    conn.close()
    
    write_audit("OPERATOR_OVERRIDE", f"device={device_id} instruction={instruction[:120]}",
                session_id=request.headers.get("X-API-Key", "api"))
    
    # Send SMTP Email Alert for Manual Dispatch Override
    color_accent = "#00bcd4"
    content_html = f"""
    <p>A manual operator override warning has been broadcasted for monitoring node <span class="highlight">{device_id}</span>.</p>
    <h3 style="color: {color_accent}; margin-top: 20px;">Custom Dispatch Instructions:</h3>
    <p style="background-color: #071018; padding: 15px; border-left: 4px solid {color_accent}; border-radius: 4px; font-weight: bold; color: #cfe8d6;">
        {instruction}
    </p>
    <p style="margin-top: 20px;">This command has been broadcasted and announced to all active client units.</p>
    <a href="http://localhost:5000" class="button" style="background-color: {color_accent};">Open Dashboard</a>
    """
    html_body = build_html_template(
        title="OPERATOR DISPATCH OVERRIDE",
        content_html=content_html,
        color_accent=color_accent
    )
    
    send_email_alert(
        device_id=device_id,
        subject="OPERATOR DISPATCH OVERRIDE",
        body=f"VERS EMERGENCY ALERT - MANUAL OPERATOR OVERRIDE DISPATCHED\n\nDevice ID: {device_id}\n\nCustom Instructions:\n{instruction}\n\nThis override instruction has been officially broadcasted and announced to all units.",
        html_body=html_body
    )
    
    return jsonify({"status": "ok", "message": "Override dispatched"})

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    """Returns current system & FB monitoring settings"""
    return jsonify({
        "smtp_server": SMTP_SERVER,
        "smtp_port": SMTP_PORT,
        "sender_email": SENDER_EMAIL,
        "sender_password": "●●●●●●●●●●●●●●●●",  # masked for security
        "recipient_email": RECIPIENT_EMAIL,
        "owm_api_key": OWM_API_KEY,
        "fb_page_handle": FB_PAGE_HANDLE
    })

@app.route("/api/settings", methods=["POST"])
@require_login
def api_save_settings():
    """Saves SMTP/email/FB page settings persistently to disk"""
    global SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL, DASHBOARD_PASSWORD, OWM_API_KEY, FB_PAGE_HANDLE
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    new_smtp_server   = data.get("smtp_server", SMTP_SERVER)
    new_smtp_port     = int(data.get("smtp_port", SMTP_PORT))
    new_sender_email  = data.get("sender_email", SENDER_EMAIL)
    new_sender_pw     = data.get("sender_password", "").strip()
    new_recipient     = data.get("recipient_email", RECIPIENT_EMAIL)
    new_dash_pw       = data.get("dashboard_password", "").strip()
    new_owm_api_key   = data.get("owm_api_key", "").strip()
    new_fb_handle     = data.get("fb_page_handle", FB_PAGE_HANDLE).strip()
    
    # Don't overwrite password if placeholder was sent back
    if new_sender_pw and "●" not in new_sender_pw:
        SENDER_PASSWORD = new_sender_pw.replace(" ", "")
    
    if new_dash_pw:
        DASHBOARD_PASSWORD = new_dash_pw
    if new_owm_api_key:
        OWM_API_KEY = new_owm_api_key
    if new_fb_handle:
        FB_PAGE_HANDLE = new_fb_handle

    SMTP_SERVER = new_smtp_server
    SMTP_PORT   = new_smtp_port
    SENDER_EMAIL = new_sender_email
    RECIPIENT_EMAIL = new_recipient
    
    ok = save_settings_to_file(
        SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL,
        dashboard_password=DASHBOARD_PASSWORD if new_dash_pw else None,
        owm_api_key=OWM_API_KEY,
        fb_page_handle=FB_PAGE_HANDLE
    )
    if ok:
        write_audit("SETTINGS_UPDATED", f"smtp={SMTP_SERVER} fb_page={FB_PAGE_HANDLE}", session_id="operator")
        return jsonify({"status": "ok", "message": "Settings saved successfully"})
    else:
        return jsonify({"status": "error", "message": "Failed to save settings to disk"}), 500

@app.route("/api/backup", methods=["POST"])
@require_login
def api_backup():
    """Emails the system python scripts as attachments to the operator"""
    if not SENDER_PASSWORD or SENDER_PASSWORD == "your_16char_app_password":
        return jsonify({"status": "error", "message": "Email SMTP not configured"}), 400
        
    def backup_task():
        try:
            import zipfile
            import io
            
            msg = MIMEMultipart("mixed")
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECIPIENT_EMAIL
            msg['Subject'] = f"[VERS BACKUP] System Code Backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Create alternative body part for text/html content
            body_part = MIMEMultipart("alternative")
            body_text = "Attached is the automated system code backup containing the current active Python scripts for the VERS Emergency Alert System."
            
            color_accent = "#00bcd4"
            content_html = f"""
            <p>An automated system code backup has been compiled for the VERS Emergency Alert System.</p>
            <p>The current active scripts are attached below:</p>
            <ul style="color: #cfe8d6; margin: 15px 0; padding-left: 20px;">
                <li><span style="font-family: monospace; color: {color_accent};">vers_system.py</span> (Web Server & Dashboard)</li>
                <li><span style="font-family: monospace; color: {color_accent};">vers_simulator.py</span> (Node Simulator)</li>
            </ul>
            <p>These files can be used to redeploy the environment in case of server failure.</p>
            """
            body_html = build_html_template(
                title="VERS - SYSTEM CODE BACKUP",
                content_html=content_html,
                color_accent=color_accent
            )
            
            body_part.attach(MIMEText(body_text, 'plain'))
            body_part.attach(MIMEText(body_html, 'html'))
            msg.attach(body_part)
            
            # Attach files as ZIP
            files_to_backup = ["vers_system.py", "vers_simulator.py", "templates/index.html", "static/app.js", "static/style.css", "data/settings.json", "data/vers_data.db"]
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname in files_to_backup:
                    if os.path.exists(fname):
                        zf.write(fname)
            
            zip_buffer.seek(0)
            part = MIMEBase("application", "zip")
            part.set_payload(zip_buffer.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment; filename=vers_backup.zip",
            )
            msg.attach(part)
                        
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
            server.close()
            print("[SMTP] System backup email sent successfully", flush=True)
            write_audit("BACKUP_SENT", f"to={RECIPIENT_EMAIL} files=vers_backup.zip")
            if os.path.exists("data/backup_error.txt"):
                try:
                    os.remove("data/backup_error.txt")
                except:
                    pass
        except Exception as e:
            print(f"[SMTP] Error sending backup email: {e}", flush=True)
            try:
                with open("data/backup_error.txt", "w") as err_f:
                    err_f.write(f"Backup Error: {str(e)}")
            except:
                pass
            
    t = Thread(target=backup_task)
    t.daemon = True
    t.start()
    return jsonify({"status": "ok", "message": "Backup email dispatched in background"})

@app.route("/api/backup/download")
@require_login
def api_backup_download():
    """Generates and downloads a fresh ZIP backup of all system code and data"""
    import zipfile
    files_to_backup = ["vers_system.py", "vers_simulator.py", "templates/index.html", "static/app.js", "static/style.css", "data/settings.json", "data/vers_data.db"]
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in files_to_backup:
            if os.path.exists(fname):
                zf.write(fname)
    zip_buffer.seek(0)
    filename = f"vers_source_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    write_audit("BACKUP_DOWNLOADED", f"filename={filename}", session_id=session.get('username'))
    return Response(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# =========================
# AUDIT LOG ROUTE
# =========================
@app.route("/api/audit")
@require_login
def api_audit():
    """Returns the last 100 audit log entries as a JSON array"""
    os.makedirs("data", exist_ok=True)
    entries = []
    if os.path.exists(AUDIT_LOG_PATH):
        try:
            with open(AUDIT_LOG_PATH, "r") as f:
                lines = f.readlines()
            for line in lines[-100:]:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify(entries)

# =========================
# API KEY AUTH ROUTE
# =========================
@app.route("/api/auth/key")
def api_auth_key():
    """Returns the current API key (no auth required — operators use this once to retrieve it)"""
    return jsonify({"api_key": API_KEY})

# =========================
# HISTORY CSV EXPORT
# =========================
@app.route("/api/history/csv")
@require_login
def api_history_csv():
    """Returns sensor_logs as a downloadable CSV file"""
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT device_id, timestamp, payload FROM sensor_logs ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["device_id", "timestamp", "risk_score", "emergencies",
                     "lat", "lon", "gas", "humidity", "fire", "flood", "battery"])
    for r in rows:
        device_id, timestamp, payload_str = r
        try:
            p = json.loads(payload_str)
        except Exception:
            p = {}
        sensors = p.get("sensors", {})
        writer.writerow([
            device_id,
            timestamp,
            p.get("risk_score", ""),
            "|".join(p.get("emergencies", [])) if isinstance(p.get("emergencies"), list) else p.get("emergencies", ""),
            p.get("lat", ""),
            p.get("lon", ""),
            sensors.get("gas", p.get("gas", "")),
            sensors.get("humidity", p.get("humidity", "")),
            sensors.get("fire", p.get("fire", "")),
            sensors.get("flood", p.get("flood", "")),
            sensors.get("battery", p.get("battery", ""))
        ])

    output.seek(0)
    from flask import Response
    filename = f"vers_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# =========================
# BATTERY HEALTH FORECAST
# =========================
@app.route("/api/battery/forecast")
@require_login
def api_battery_forecast():
    """Returns a battery health forecast per device based on recent drain rate"""
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT DISTINCT device_id FROM sensor_logs")
    device_ids = [row[0] for row in c.fetchall()]

    results = []
    for device_id in device_ids:
        # Fetch last 10 readings newest-first
        c.execute("""
            SELECT timestamp, payload FROM sensor_logs
            WHERE device_id = ?
            ORDER BY id DESC LIMIT 10
        """, (device_id,))
        rows = c.fetchall()
        if not rows:
            continue

        readings = []
        for ts_str, payload_str in rows:
            try:
                p = json.loads(payload_str)
                sensors = p.get("sensors", {})
                battery = sensors.get("battery", p.get("battery"))
                if battery is None:
                    continue
                battery = float(battery)
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                readings.append((ts, battery))
            except Exception:
                continue

        if not readings:
            continue

        # readings[0] = newest, readings[-1] = oldest
        current_battery = readings[0][1]
        drain_rate = None
        hours_remaining = None

        if len(readings) >= 2:
            newest_ts, newest_bat = readings[0]
            oldest_ts, oldest_bat = readings[-1]
            elapsed_seconds = (newest_ts - oldest_ts).total_seconds()
            elapsed_hours = elapsed_seconds / 3600.0
            if elapsed_hours > 0:
                battery_drop = oldest_bat - newest_bat  # positive = draining
                drain_rate = round(battery_drop / elapsed_hours, 4) if battery_drop > 0 else 0.0
                if drain_rate and drain_rate > 0:
                    hours_remaining = round(current_battery / drain_rate, 2)

        # Determine status
        if current_battery < 15 or (hours_remaining is not None and hours_remaining < 2):
            status = "critical"
        elif current_battery < 30 or (hours_remaining is not None and hours_remaining < 6):
            status = "warning"
        else:
            status = "ok"

        results.append({
            "device_id": device_id,
            "current_battery": current_battery,
            "drain_rate_pct_per_hour": drain_rate,
            "hours_remaining": hours_remaining,
            "status": status
        })

    conn.close()
    return jsonify(results)

# =========================
# DAILY SUMMARY REPORT
# =========================
_daily_report_last_date = None

def send_daily_report():
    """Builds and emails a 24-hour summary report to the operator"""
    global _daily_report_last_date
    conn = db_connect()
    c = conn.cursor()
    since_ts = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    c.execute("""
        SELECT device_id, timestamp, payload FROM sensor_logs
        WHERE timestamp >= ?
        ORDER BY id DESC
    """, (since_ts,))
    rows = c.fetchall()
    conn.close()

    # Aggregate per device
    device_stats = {}
    for device_id, timestamp, payload_str in rows:
        try:
            p = json.loads(payload_str)
        except Exception:
            p = {}
        risk = p.get("risk_score", 0) or 0
        if device_id not in device_stats:
            device_stats[device_id] = {"count": 0, "max_risk": 0}
        device_stats[device_id]["count"] += 1
        device_stats[device_id]["max_risk"] = max(device_stats[device_id]["max_risk"], risk)

    today_str = datetime.now().strftime("%Y-%m-%d")
    _daily_report_last_date = today_str

    if not SENDER_PASSWORD or SENDER_PASSWORD == "your_16char_app_password":
        print("[DAILY REPORT] Email not configured, skipping send.")
        write_audit("DAILY_REPORT_SENT", f"date={today_str} devices={len(device_stats)} (email skipped — not configured)")
        return

    rows_html = ""
    for dev, stats in device_stats.items():
        rows_html += f"""
        <tr style="border-bottom: 1px solid #1e3640;">
            <td style="padding: 8px; font-family: monospace; color: #0f6;">{dev}</td>
            <td style="padding: 8px; text-align: center;">{stats['count']}</td>
            <td style="padding: 8px; text-align: center; color: {'#f44' if stats['max_risk'] >= 70 else '#fa0' if stats['max_risk'] >= 40 else '#0f6'};">{stats['max_risk']}/100</td>
        </tr>"""

    if not rows_html:
        rows_html = "<tr><td colspan='3' style='padding: 12px; text-align: center; color: #8a9fa0;'>No sensor activity recorded today.</td></tr>"

    content_html = f"""
    <p>Automated daily summary for <strong>{today_str}</strong>. Below is a breakdown of all monitoring nodes active in the last 24 hours.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px;">
        <thead>
            <tr style="border-bottom: 2px solid #00ff66;">
                <th style="padding: 8px; text-align: left; color: #8a9fa0;">Device ID</th>
                <th style="padding: 8px; text-align: center; color: #8a9fa0;">Events</th>
                <th style="padding: 8px; text-align: center; color: #8a9fa0;">Max Risk</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    <p style="margin-top: 20px;">This is an automated report generated by the VERS Monitoring System.</p>
    <a href="http://localhost:5000" class="button">Open Dashboard</a>
    """
    html_body = build_html_template(
        title=f"VERS DAILY SUMMARY — {today_str}",
        content_html=content_html,
        color_accent="#00ff66"
    )
    subject = f"System Summary Report - {today_str}"
    body_text = f"VERS Daily Summary Report for {today_str}\n\nDevices monitored: {len(device_stats)}\nSee HTML version for details."

    try:
        msg = MIMEMultipart("alternative")
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"[VERS DAILY] {subject}"
        msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        server.close()
        print(f"[DAILY REPORT] Sent for {today_str} to {RECIPIENT_EMAIL}")
        write_audit("DAILY_REPORT_SENT", f"date={today_str} devices={len(device_stats)} to={RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"[DAILY REPORT] Error sending: {e}")
        write_audit("DAILY_REPORT_SENT", f"date={today_str} ERROR: {e}")

def _daily_report_scheduler():
    """Background thread: fires send_daily_report() once daily at 08:00 PHT (UTC+8)"""
    global _daily_report_last_date
    while True:
        now_pht = datetime.now(timezone.utc).astimezone(__import__('zoneinfo', fromlist=['ZoneInfo']).ZoneInfo('Asia/Manila') if hasattr(__import__('zoneinfo', fromlist=['ZoneInfo']), 'ZoneInfo') else timezone.utc)
        if now_pht.hour == 8 and now_pht.minute == 0:
            today_str = now_pht.strftime("%Y-%m-%d")
            if _daily_report_last_date != today_str:
                print(f"[DAILY REPORT] Triggering scheduled report for {today_str}")
                send_daily_report()
                _daily_report_last_date = today_str
        time.sleep(60)

@app.route("/api/report/send", methods=["POST"])
@require_login
def api_report_send():
    """Immediately triggers the daily summary report (for testing)"""
    def _task():
        send_daily_report()
    socketio.start_background_task(_task)
    return jsonify({"status": "ok", "message": "Daily report triggered in background"})

@app.route("/api/ack", methods=["POST"])
@require_login
def api_ack():
    """Acknowledges an active alert and logs it to the audit trail"""
    data = request.get_json() or {}
    device_id = data.get("device_id")
    timestamp = data.get("timestamp")
    
    if not device_id:
        return jsonify({"status": "error", "message": "Missing device_id"}), 400
        
    write_audit("ALERT_ACKNOWLEDGED", f"device={device_id} timestamp={timestamp}", session_id="operator")
    
    # Broadcast acknowledgement to other active operators so their UIs update
    socketio.emit("alert_ack", {"device_id": device_id, "timestamp": timestamp}, namespace="/dashboard")
    return jsonify({"status": "ok", "message": "Alert acknowledged"})

@app.route("/api/broadcast", methods=["POST"])
@require_login
def api_broadcast():
    """Broadcasts a manual text message to all connected operator dashboards"""
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"status": "error", "message": "Empty message"}), 400
        
    write_audit("OPERATOR_BROADCAST", f"message={message}", session_id="operator")
    
    # Broadcast to dashboard Socket.IO namespace
    socketio.emit("operator_broadcast", {"message": message, "timestamp": datetime.now().strftime("%H:%M:%S")}, namespace="/dashboard")
    return jsonify({"status": "ok", "message": "Broadcast sent"})

# =========================
# FEATURE 1: PAGASA BULLETIN
# =========================
_PAGASA_CACHE = {"ts": 0, "data": []}

@app.route('/api/pagasa', methods=['GET'])
def get_pagasa_bulletin():
    """Scrapes PAGASA TAMSS public file directory for latest weather bulletins and advisories"""
    global _PAGASA_CACHE
    if time.time() - _PAGASA_CACHE["ts"] < 300:
        return jsonify({"status": "ok", "data": _PAGASA_CACHE["data"]})
        
    items = []
    def _parse_date(d):
        try:
            return datetime.strptime(d, "%d-%b-%Y %H:%M")
        except Exception:
            return datetime.min
    try:
        import re as _re
        base_url = "https://pubfiles.pagasa.dost.gov.ph/tamss/weather/"
        req = urllib.request.Request(base_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        pattern = _re.compile(r'<a href="([^"]+\.pdf)">[^<]+</a>\s+([\d]{2}-\w{3}-\d{4}\s+[\d:]+)\s+(\S+)')
        matches = pattern.findall(html)
        
        for filename, date_str, size in matches:
            clean_name = urllib.parse.unquote(filename).replace('_', ' ').replace('.pdf', '')
            items.append({
                "title": clean_name,
                "description": f"PAGASA Official Document ({size})",
                "pubDate": date_str.strip(),
                "link": base_url + urllib.parse.quote(filename, safe='')
            })
        
        items.sort(key=lambda x: _parse_date(x['pubDate']), reverse=True)
        items = items[:10]
        
        # Also fetch TC bulletins from subdirectory
        try:
            tc_url = base_url + "bulletin/"
            req2 = urllib.request.Request(tc_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req2, timeout=10) as response2:
                html2 = response2.read().decode('utf-8', errors='ignore')
            matches2 = pattern.findall(html2)
            tc_items = []
            for filename, date_str, size in matches2:
                clean_name = urllib.parse.unquote(filename).replace('_', ' ').replace('.pdf', '').replace('%23', '#')
                tc_items.append({
                    "title": f"\U0001f300 {clean_name}",
                    "description": f"Tropical Cyclone Bulletin ({size})",
                    "pubDate": date_str.strip(),
                    "link": tc_url + urllib.parse.quote(filename, safe='')
                })
            tc_items.sort(key=lambda x: _parse_date(x['pubDate']), reverse=True)
            items = tc_items[:5] + items
        except Exception:
            pass
        _PAGASA_CACHE["ts"] = time.time()
        _PAGASA_CACHE["data"] = items
        return jsonify({"status": "ok", "data": items})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "data": []}), 500

# Connection tracking
CONNECTED_CLIENTS = set()
TOTAL_CONNECTIONS_EVER = 0

CACHED_WARNINGS = {"gdacs": {"features": []}, "pagasa": {"features": []}}
CACHED_WARNINGS_JSON = '{"status": "ok", "data": {"gdacs": {"features": []}, "pagasa": {"features": []}}}'

@app.route('/api/warnings', methods=['GET'])
def get_all_warnings():
    """Returns the globally cached GDACS and PAGASA warnings instantly using a pre-serialized JSON string."""
    return app.response_class(response=CACHED_WARNINGS_JSON, status=200, mimetype='application/json')

# =========================
# FEATURE 2: PUBLIC INCIDENT REPORTING
# =========================
@app.route('/report', methods=['GET'])
def public_report_form():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VERS - Report Incident</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { background: #070b0d; background-image: radial-gradient(circle at 50% -20%, rgba(0, 255, 102, 0.05), transparent 60%); color: #e2f1e8; font-family: 'Inter', system-ui, sans-serif; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
            .report-card { background: rgba(13, 20, 26, 0.7); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(30, 54, 64, 0.6); border-top: 4px solid #00ff66; border-radius: 16px; padding: 32px; width: 100%; max-width: 480px; box-shadow: 0 12px 48px rgba(0,0,0,0.6); }
            h2 { color: #00ff66; font-size: 22px; margin-bottom: 8px; font-weight: 700; letter-spacing: -0.5px; }
            .subtitle { color: #8a9fa0; font-size: 13px; margin-bottom: 28px; line-height: 1.5; }
            .form-group { margin-bottom: 20px; }
            label { display: block; font-size: 11px; color: #00bcd4; text-transform: uppercase; font-weight: 600; letter-spacing: 1px; margin-bottom: 8px; }
            select, textarea, input[type="text"] { width: 100%; padding: 12px 14px; background: rgba(0,0,0,0.2); border: 1px solid rgba(30, 54, 64, 0.6); color: #e2f1e8; border-radius: 8px; font-size: 14px; outline: none; transition: all 0.2s; font-family: 'Inter', system-ui, sans-serif; }
            select:focus, textarea:focus, input[type="text"]:focus { border-color: #00ff66; box-shadow: 0 0 0 3px rgba(0,255,102,0.15); }
            textarea { resize: vertical; min-height: 100px; }
            .loc-row { display: flex; gap: 10px; align-items: center; }
            .loc-btn { flex: 1; padding: 14px; background: linear-gradient(135deg, #00bcd4, #0097a7); color: #fff; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); text-align: center; box-shadow: 0 4px 12px rgba(0,188,212,0.2); }
            .loc-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,188,212,0.4); }
            .loc-btn:active { transform: translateY(0); }
            .loc-btn.success { background: linear-gradient(135deg, #00ff66, #00cc55); color: #000; box-shadow: 0 4px 12px rgba(0,255,102,0.2); }
            .loc-status { font-size: 12px; color: #8a9fa0; margin-top: 8px; font-weight: 500; }
            .upload-area { border: 2px dashed rgba(30, 54, 64, 0.8); border-radius: 12px; padding: 24px; text-align: center; cursor: pointer; transition: all 0.2s; position: relative; overflow: hidden; background: rgba(0,0,0,0.1); }
            .upload-area:hover { border-color: #00bcd4; background: rgba(0,188,212,0.05); }
            .upload-area.has-file { border-color: #00ff66; border-style: solid; background: rgba(0,255,102,0.05); }
            .upload-area input[type="file"] { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
            .upload-icon { font-size: 36px; margin-bottom: 12px; transition: transform 0.2s; }
            .upload-area:hover .upload-icon { transform: scale(1.1); }
            .upload-text { font-size: 13px; color: #8a9fa0; font-weight: 500; }
            .upload-preview { max-width: 100%; max-height: 200px; border-radius: 8px; margin-top: 16px; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
            .submit-btn { width: 100%; padding: 16px; background: #00ff66; color: #000; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); margin-top: 12px; }
            .submit-btn:hover { background: #00cc55; transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,255,102,0.3); }
            .submit-btn:disabled { background: rgba(30, 54, 64, 0.6); color: #8a9fa0; cursor: not-allowed; transform: none; box-shadow: none; }
            .success-msg { display: none; text-align: center; padding: 40px 20px; }
            .success-msg .check { font-size: 56px; margin-bottom: 16px; animation: scaleIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
            @keyframes scaleIn { from { transform: scale(0); } to { transform: scale(1); } }
            .success-msg h3 { color: #00ff66; margin-bottom: 12px; font-size: 24px; font-weight: 700; }
            .success-msg p { color: #e2f1e8; font-size: 14px; line-height: 1.6; }
            .back-link { display: inline-block; margin-top: 24px; color: #00bcd4; text-decoration: none; font-size: 14px; font-weight: 600; padding: 12px 24px; border: 1px solid rgba(0,188,212,0.3); border-radius: 6px; transition: all 0.2s; }
            .back-link:hover { color: #00ff66; border-color: #00ff66; background: rgba(0,255,102,0.05); }
        </style>
    </head>
    <body>
        <div class="report-card">
            <div id="formView">
                <h2>📢 Report an Incident</h2>
                <p class="subtitle">Help your community by reporting disasters and risks in your area</p>
                
                <form id="reportForm" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>Type of Incident</label>
                        <select id="report_type" required>
                            <option value="Flood">🌊 Flood</option>
                            <option value="Fire">🔥 Fire</option>
                            <option value="Landslide">⛰️ Landslide</option>
                            <option value="Earthquake Damage">🏚️ Earthquake Damage</option>
                            <option value="Road Blocked">🚧 Road Blocked</option>
                            <option value="Fallen Tree">🌳 Fallen Tree</option>
                            <option value="Power Outage">⚡ Power Outage</option>
                            <option value="Stranded Persons">🆘 Stranded Persons</option>
                            <option value="Other">📋 Other</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>Description</label>
                        <textarea id="description" placeholder="Describe the situation in detail..." required></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>📷 Photo Evidence</label>
                        <div class="upload-area" id="uploadArea">
                            <div class="upload-icon">📸</div>
                            <div class="upload-text" id="uploadText">Tap to take a photo or choose from gallery</div>
                            <input type="file" id="imageInput" accept="image/*" capture="environment">
                            <img class="upload-preview" id="imagePreview">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>📍 Your Location</label>
                        <div class="loc-row">
                            <button type="button" class="loc-btn" id="locBtn" onclick="getLocation()">📍 Use My Location</button>
                        </div>
                        <div class="loc-status" id="locStatus">Location not yet captured</div>
                        <input type="hidden" id="lat">
                        <input type="hidden" id="lon">
                    </div>
                    
                    <div class="form-group">
                        <label>Your Name (Optional)</label>
                        <input type="text" id="reporter_name" placeholder="Anonymous">
                    </div>
                    
                    <button type="submit" class="submit-btn" id="submitBtn">📤 Submit Report</button>
                </form>
            </div>
            
            <div class="success-msg" id="successView">
                <div class="check">✅</div>
                <h3>Report Submitted!</h3>
                <p>Thank you for helping your community. Operators have been notified and your report is now visible on the monitoring dashboard.</p>
                <a href="/report" class="back-link">← Submit Another Report</a>
                <br>
                <a href="/" class="back-link">🗺️ View Live Dashboard</a>
            </div>
        </div>
        
        <script>
            function getLocation() {
                const btn = document.getElementById('locBtn');
                const status = document.getElementById('locStatus');
                btn.textContent = '⏳ Getting location...';
                btn.disabled = true;
                
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        pos => {
                            document.getElementById('lat').value = pos.coords.latitude;
                            document.getElementById('lon').value = pos.coords.longitude;
                            btn.textContent = '✅ Location Captured!';
                            btn.classList.add('success');
                            status.textContent = `📍 ${pos.coords.latitude.toFixed(5)}, ${pos.coords.longitude.toFixed(5)}`;
                            status.style.color = '#00ff66';
                        },
                        err => {
                            btn.textContent = '❌ Failed - Try Again';
                            btn.disabled = false;
                            status.textContent = 'Could not get location. Please allow GPS access.';
                            status.style.color = '#ff5050';
                        },
                        { enableHighAccuracy: true, timeout: 10000 }
                    );
                } else {
                    status.textContent = 'GPS not supported on this device';
                    status.style.color = '#ff5050';
                    btn.textContent = '❌ Not Supported';
                }
            }
            
            // Image preview
            document.getElementById('imageInput').addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const preview = document.getElementById('imagePreview');
                    const reader = new FileReader();
                    reader.onload = function(ev) {
                        preview.src = ev.target.result;
                        preview.style.display = 'block';
                        document.getElementById('uploadArea').classList.add('has-file');
                        document.getElementById('uploadText').textContent = file.name;
                    };
                    reader.readAsDataURL(file);
                }
            });
            
            // Form submission
            document.getElementById('reportForm').onsubmit = async (e) => {
                e.preventDefault();
                const btn = document.getElementById('submitBtn');
                btn.disabled = true;
                btn.textContent = '⏳ Submitting...';
                
                const formData = new FormData();
                formData.append('report_type', document.getElementById('report_type').value);
                formData.append('description', document.getElementById('description').value);
                formData.append('reporter_name', document.getElementById('reporter_name').value);
                formData.append('lat', document.getElementById('lat').value || 0);
                formData.append('lon', document.getElementById('lon').value || 0);
                
                const imageFile = document.getElementById('imageInput').files[0];
                if (imageFile) {
                    formData.append('image', imageFile);
                }
                
                try {
                    const res = await fetch('/api/reports/submit', {
                        method: 'POST',
                        body: formData
                    });
                    if (res.ok) {
                        document.getElementById('formView').style.display = 'none';
                        document.getElementById('successView').style.display = 'block';
                    } else {
                        alert('Error submitting report. Please try again.');
                        btn.disabled = false;
                        btn.textContent = '📤 Submit Report';
                    }
                } catch(err) {
                    alert('Network error. Please check your connection.');
                    btn.disabled = false;
                    btn.textContent = '📤 Submit Report';
                }
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/api/reports/submit', methods=['POST'])
def submit_public_report():
    report_type = request.form.get('report_type', 'Other')
    desc = request.form.get('description', '')
    name = request.form.get('reporter_name', '')
    lat = float(request.form.get('lat', 0))
    lon = float(request.form.get('lon', 0))
    ts = datetime.now(timezone.utc).isoformat()
    
    image_path = ''
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            import uuid
            ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            image_path = f"/static/uploads/{filename}"
    
    conn = db_connect()
    try:
        c = conn.cursor()
        try:
            c.execute("ALTER TABLE public_reports ADD COLUMN image_path TEXT DEFAULT ''")
            conn.commit()
        except:
            pass
        c.execute("INSERT INTO public_reports (report_type, description, lat, lon, reporter_name, timestamp, image_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (report_type, desc, lat, lon, name, ts, image_path))
        report_id = c.lastrowid
        conn.commit()
    finally:
        conn.close()
    
    report_data = {
        "id": report_id,
        "report_type": report_type,
        "description": desc,
        "lat": lat,
        "lon": lon,
        "reporter_name": name,
        "timestamp": ts,
        "image_path": image_path,
        "status": "unverified"
    }
    socketio.emit('new_public_report', report_data, namespace='/dashboard')
    write_audit("PUBLIC_REPORT", f"type={report_type}, id={report_id}", session_id="public")
    
    return jsonify({"status": "ok", "id": report_id})

@app.route('/api/reports', methods=['GET'])
@require_login
def get_public_reports():
    conn = db_connect()
    try:
        c = conn.cursor()
        c.execute("SELECT id, report_type, description, lat, lon, reporter_name, timestamp, status FROM public_reports WHERE datetime(timestamp) >= datetime('now', '-1 day')")
        rows = c.fetchall()
        reports = []
        for r in rows:
            reports.append({
                "id": r[0],
                "report_type": r[1],
                "description": r[2],
                "lat": r[3],
                "lon": r[4],
                "reporter_name": r[5],
                "timestamp": r[6],
                "status": r[7]
            })
    finally:
        conn.close()
    return jsonify({"status": "ok", "data": reports})

# =========================
# FEATURE 3: HISTORICAL HEATMAP DATA
# =========================
@app.route('/api/heatmap', methods=['GET'])
@require_login
def get_heatmap_data():
    hours = request.args.get('hours', 24, type=int)
    
    conn = db_connect()
    try:
        c = conn.cursor()
        c.execute("SELECT payload FROM sensor_logs WHERE datetime(timestamp) >= datetime('now', ?)", (f"-{hours} hours",))
        rows = c.fetchall()
        
        heatmap_data = []
        for r in rows:
            try:
                payload = json.loads(r[0])
                risk = payload.get("risk_score", 0)
                if risk > 0:
                    lat = payload.get("lat")
                    lon = payload.get("lon")
                    if lat is not None and lon is not None:
                        heatmap_data.append([lat, lon, risk])
            except:
                pass
    finally:
        conn.close()
            
    return jsonify({"status": "ok", "data": heatmap_data})

# =========================
# FEATURE 5: GEO-FENCE STORAGE
# =========================
@app.route('/api/geofence', methods=['POST'])
@require_login
def create_geofence():
    data = request.json or {}
    name = data.get('name', 'Unnamed')
    coords = data.get('coordinates', [])
    ts = datetime.now(timezone.utc).isoformat()
    
    conn = db_connect()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO geofences (name, coordinates, created_at, created_by) VALUES (?, ?, ?, ?)",
                  (name, json.dumps(coords), ts, session.get('username', 'operator')))
        gid = c.lastrowid
        conn.commit()
    finally:
        conn.close()
    write_audit("GEOFENCE_CREATED", f"id={gid} name={name}", session_id=session.get('username'))
    return jsonify({"status": "ok", "id": gid})

@app.route('/api/geofences', methods=['GET'])
@require_login
def get_geofences():
    conn = db_connect()
    try:
        c = conn.cursor()
        c.execute("SELECT id, name, coordinates, created_at, created_by FROM geofences")
        rows = c.fetchall()
        
        data = []
        for r in rows:
            try:
                coords = json.loads(r[2])
            except:
                coords = []
            data.append({
                "id": r[0],
                "name": r[1],
                "coordinates": coords,
                "created_at": r[3],
                "created_by": r[4]
            })
    finally:
        conn.close()
    return jsonify({"status": "ok", "data": data})

@app.route('/api/geofence/<int:id>', methods=['DELETE'])
@require_login
def delete_geofence(id):
    conn = db_connect()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM geofences WHERE id=?", (id,))
        conn.commit()
    finally:
        conn.close()
    write_audit("GEOFENCE_DELETED", f"id={id}", session_id=session.get('username'))
    return jsonify({"status": "ok", "message": "Geofence deleted"})

# =========================
# FEATURE: CLASS SUSPENSION MONITORING (WALANG PASOK)
# =========================
@app.route('/api/class-suspensions', methods=['GET'])
def get_class_suspensions():
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id, level, scope, reason, issued_by, timestamp, active FROM class_suspensions WHERE active = 1 ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            "status": "ok",
            "source": "official",
            "data": {
                "id": row[0],
                "level": row[1],
                "scope": row[2],
                "reason": row[3],
                "issued_by": row[4],
                "timestamp": row[5]
            }
        })
        
    # Auto-derive from PAGASA warnings if no manual override
    pagasa = CACHED_WARNINGS.get('pagasa', {})
    auto_level = "Classes Normal"
    auto_reason = "No active automatic suspension guidelines triggered."
    auto_scope = "Taguig City / Metro Manila"
    
    if pagasa.get('features'):
        for f in pagasa['features']:
            level = str(f.get('properties', {}).get('alertlevel', '')).lower()
            if 'red' in level:
                auto_level = "All Levels (Public & Private)"
                auto_reason = "Automatic DepEd / NDRRMC Guidelines (Red Rainfall Warning Active)"
                break
            elif 'orange' in level and auto_level != "All Levels (Public & Private)":
                auto_level = "Pre-School to Senior High School"
                auto_reason = "Automatic DepEd Guidelines (Orange Rainfall Warning Active)"
            elif 'yellow' in level and auto_level == "Classes Normal":
                auto_level = "Pre-School / Kindergarten"
                auto_reason = "Automatic DepEd Guidelines (Yellow Rainfall Warning Active)"

    return jsonify({
        "status": "ok",
        "source": "auto_derived",
        "data": {
            "level": auto_level,
            "scope": auto_scope,
            "reason": auto_reason,
            "issued_by": "VERS Auto-Monitoring System (DepEd EO 77 Rule)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    })

@app.route('/api/class-suspensions', methods=['POST'])
@require_login
def update_class_suspensions():
    data = request.json or {}
    level = data.get('level', 'Classes Normal')
    scope = data.get('scope', 'Taguig City / Metro Manila')
    reason = data.get('reason', 'LGU Announcement / Disaster Protocols')
    ts = datetime.now(timezone.utc).isoformat()
    issued_by = session.get('username', 'operator')
    
    conn = db_connect()
    c = conn.cursor()
    c.execute("UPDATE class_suspensions SET active = 0")
    c.execute("INSERT INTO class_suspensions (level, scope, reason, issued_by, timestamp, active) VALUES (?, ?, ?, ?, ?, 1)",
              (level, scope, reason, issued_by, ts))
    cid = c.lastrowid
    conn.commit()
    conn.close()
    
    suspension_data = {
        "id": cid,
        "level": level,
        "scope": scope,
        "reason": reason,
        "issued_by": issued_by,
        "timestamp": ts,
        "source": "official"
    }
    
    socketio.emit('class_suspension_update', suspension_data, namespace='/dashboard')
    write_audit("CLASS_SUSPENSION_UPDATED", f"level={level} scope={scope}", session_id=issued_by)
    return jsonify({"status": "ok", "data": suspension_data})

def _extract_provs_from_text(match):
    if not match: return {}
    import re
    raw = match.group(1).replace(' and ', ',')
    result = {}
    parts = re.split(r',\s*(?![^()]*\))', raw)
    for part in parts:
        part = part.strip()
        if not part: continue
        m = re.match(r'([^(]+)(?:\((.*?)\))?', part)
        if m:
            prov = m.group(1).strip().lower()
            cities_str = m.group(2)
            cities = [c.strip().lower() for c in cities_str.split(',')] if cities_str else []
            result[prov] = cities
    return result

def normalize_name(s):
    import re
    s = s.lower().replace('ñ', 'n').replace('city', '').replace('kalookan', 'caloocan')
    return re.sub(r'[^a-z0-9]', '', s)

def parse_pagasa_bulletin(text, all_provinces):
    """Parses full PAGASA Heavy Rainfall Warning & Advisory text into municipality GeoJSON features."""
    import re, copy

    red_match = re.search(r'RED WARNING LEVEL:\s*(.*?)(?=ASSOCIATED|ORANGE|YELLOW|Meanwhile|$)', text, re.IGNORECASE | re.DOTALL)
    orange_match = re.search(r'ORANGE WARNING LEVEL:\s*(.*?)(?=ASSOCIATED|YELLOW|RED|Meanwhile|$)', text, re.IGNORECASE | re.DOTALL)
    yellow_match = re.search(r'YELLOW WARNING LEVEL:\s*(.*?)(?=ASSOCIATED|Meanwhile|RED|ORANGE|$)', text, re.IGNORECASE | re.DOTALL)
    light_match = re.search(r'Meanwhile,?\s*light to moderate.*?\s*affecting\s*(.*?)(?=which may persist|$)', text, re.IGNORECASE | re.DOTALL)

    red_provs = _extract_provs_from_text(red_match)
    orange_provs = _extract_provs_from_text(orange_match)
    yellow_provs = _extract_provs_from_text(yellow_match)
    light_provs = _extract_provs_from_text(light_match)

    def is_affected(provs_dict, prov_name, city_name):
        prov_match = prov_name.lower()
        if prov_match in ["metropolitan manila", "ncr, national capital region", "metro manila", "ncr", "national capital region"]:
            prov_match = "metro manila"
        norm_prov = normalize_name(prov_match)
        for k, v in provs_dict.items():
            k_norm = normalize_name(k)
            if k_norm == norm_prov or k_norm in norm_prov or norm_prov in k_norm:
                if not v: return True
                norm_city = normalize_name(city_name)
                for c in v:
                    norm_c = normalize_name(c)
                    if norm_c in norm_city or norm_city in norm_c: return True
        return False

    active_warnings = []
    for feature in all_provinces.get('features', []):
        f = copy.deepcopy(feature)
        prov_name = f['properties'].get('PROVINCE', '')
        city_name = f['properties'].get('NAME_2', '')

        if is_affected(red_provs, prov_name, city_name):
            f['properties']['name'] = f"{city_name}, {prov_name}"
            f['properties']['alertlevel'] = "Red"
            f['properties']['rainfall_rate'] = "Torrential (>30 mm/h)"
            f['properties']['description'] = "Serious FLOODING is expected in low-lying & lakeshore areas. Evacuation advised."
            active_warnings.append(f)
        elif is_affected(orange_provs, prov_name, city_name):
            f['properties']['name'] = f"{city_name}, {prov_name}"
            f['properties']['alertlevel'] = "Orange"
            f['properties']['rainfall_rate'] = "Intense (15-30 mm/h)"
            f['properties']['description'] = "FLOODING is THREATENING in flood-prone areas. High alert active."
            active_warnings.append(f)
        elif is_affected(yellow_provs, prov_name, city_name):
            f['properties']['name'] = f"{city_name}, {prov_name}"
            f['properties']['alertlevel'] = "Yellow"
            f['properties']['rainfall_rate'] = "Heavy (7.5-15 mm/h)"
            f['properties']['description'] = "Possible FLOODING in low-lying areas. Community preparedness active."
            active_warnings.append(f)
        elif is_affected(light_provs, prov_name, city_name):
            f['properties']['name'] = f"{city_name}, {prov_name}"
            f['properties']['alertlevel'] = "Advisory"
            f['properties']['rainfall_rate'] = "Light-to-Moderate with Occasional Heavy (2.5-7.5 mm/h)"
            f['properties']['description'] = "Thunderstorms & occasional heavy rains which may persist for 3 hours."
            active_warnings.append(f)

    return active_warnings

@app.route('/api/warnings/bulletin', methods=['POST'])
def post_manual_bulletin():
    """Allows operator or webhook to post a PAGASA Heavy Rainfall Warning bulletin text."""
    global CACHED_WARNINGS, CACHED_WARNINGS_JSON
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    if not text:
        return jsonify({"status": "error", "message": "Text is required"}), 400

    with open('static/municities.json', 'r') as f:
        all_provinces = json.load(f)

    active_warnings = parse_pagasa_bulletin(text, all_provinces)
    CACHED_WARNINGS["pagasa"] = {
        "type": "FeatureCollection",
        "features": active_warnings
    }
    CACHED_WARNINGS_JSON = json.dumps({"status": "ok", "data": CACHED_WARNINGS})
    if socketio:
        socketio.emit("warnings_update", CACHED_WARNINGS, namespace="/dashboard")
    return jsonify({"status": "ok", "count": len(active_warnings)})

def _threat_polling_task():
    """Background task to poll GDACS and PAGASA warnings actively."""
    global CACHED_WARNINGS, CACHED_WARNINGS_JSON
    import requests
    from bs4 import BeautifulSoup
    import re
    
    with open('static/municities.json', 'r') as f:
        all_provinces = json.load(f)

    # Initial seeding with current Habagat / Monsoon warning if available
    initial_text = """
    Heavy Rainfall Warning No. 2-A #NCR_PRSD
    Weather System: Southwest Monsoon (Habagat)
    ORANGE WARNING LEVEL: Bataan and Zambales(Olongapo, Subic, San Antonio, Castillejos, San Marcelino, San Narciso, San Felipe, Cabangan, Botolan).
    ASSOCIATED HAZARD: FLOODING is THREATENING.
    YELLOW WARNING LEVEL: Metro Manila, Zambales(Candelaria, Iba, Masinloc, Palauig, Santa Cruz), Pampanga(Floridablanca, Lubao, Sasmuan, Macabebe, Masantol, Guagua, Porac, Angeles, Santa Rita, Minalin, Bacolor, San Fernando, Mexico, Apalit, San Simon, Santo Tomas, San Luis, Mabalacat), Tarlac(Bamban, Capas, San Jose), Bulacan(Hagonoy, Paombong, Calumpit, Pulilan, Malolos, Bulakan, Obando, Meycauayan), Batangas(Nasugbu, Lian, Calatagan, Balayan, Tuy) and Cavite(Maragondon, Alfonso, Magallanes, General Emilio Aguinaldo, Ternate, Naic, Indang, Trece Martires, Tanza, Rosario, Noveleta, Cavite City, Kawit, General Trias, Imus, Bacoor).
    ASSOCIATED HAZARD: FLOODING in flood-prone areas.
    Meanwhile, light to moderate with occasional heavy rains affecting Tarlac(Mayantoc, San Clemente, Camiling, Santa Ignacia, Gerona, Concepcion, Anao, La Paz, Paniqui, Pura, Ramos, San Manuel, Victoria, Moncada, Tarlac City), Pampanga(Arayat, Candaba, Magalang, Santa Ana), Nueva Ecija(Cabiao, Licab, Zaragoza, San Antonio), Batangas(Calaca, Lemery, Laurel, Talisay, Tanauan, Agoncillo, San Nicolas, Taal), Cavite(Tagaytay, Amadeo, Mendez, Silang, Carmona, Dasmarinas, Gen. Mariano Alvarez), Laguna(San Pedro, Binan, Santa Rosa, Cabuyao, Calamba), Bulacan(Baliuag, Plaridel, Guiguinto, Balagtas, Bocaue, Marilao, San Jose del Monte, Santa Maria, Pandi, Bustos, Norzagaray, Dona Remedios Trinidad, Angat), Rizal(Rodriguez, Cainta, Taytay, Angono, Binangonan, Cardona) and Quezon(General Nakar, Infanta, Real, Panukulan, Burdeos) which may persist within 3 hours and may affect nearby areas.
    """
    try:
        init_warnings = parse_pagasa_bulletin(initial_text, all_provinces)
        CACHED_WARNINGS["pagasa"] = {
            "type": "FeatureCollection",
            "features": init_warnings
        }
        CACHED_WARNINGS_JSON = json.dumps({"status": "ok", "data": CACHED_WARNINGS})
    except Exception as e:
        print("Initial PAGASA Seed Error:", e)
        
    while True:
        try:
            # Poll GDACS
            url = 'https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP?eventtype=TC'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                gdacs_data = json.loads(response.read().decode('utf-8'))
                CACHED_WARNINGS["gdacs"] = gdacs_data
        except Exception as e:
            print("GDACS Poll Error:", e)

        try:
            # Live PAGASA scraper from the website
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                res = requests.get("https://www.pagasa.dost.gov.ph/regional-forecast/ncrprsd", headers=headers, timeout=10)
                eventlet.sleep(0)
                soup = BeautifulSoup(res.text, 'html.parser')
                text = soup.get_text(separator=' ')
                
                scraped_warnings = parse_pagasa_bulletin(text, all_provinces)
                if scraped_warnings:
                    CACHED_WARNINGS["pagasa"] = {
                        "type": "FeatureCollection",
                        "features": scraped_warnings
                    }
            except Exception as e:
                print("PAGASA Web Scrape Error:", e)

            # Pre-serialize the entire response to bypass jsonify latency on HTTP requests
            CACHED_WARNINGS_JSON = json.dumps({"status": "ok", "data": CACHED_WARNINGS})
            
            # Broadcast the updated cached warnings to all connected clients immediately
            if socketio:
                socketio.emit("warnings_update", CACHED_WARNINGS, namespace="/dashboard")
        except Exception as e:
            print("PAGASA Poll Error:", e)
            
        # Poll every 5 minutes
        time.sleep(300)

def parse_fb_suspension_text(text):
    """Analyzes text from official FB post to determine class suspension level and details."""
    text_lower = text.lower()
    keywords = ["suspension", "suspend", "walang pasok", "classes", "klase", "nagdeklara", "deklara"]
    if not any(k in text_lower for k in keywords):
        return None
        
    level = "Classes Normal"
    if "all levels" in text_lower or "lahat ng antas" in text_lower:
        level = "All Levels (Public & Private)"
    elif "senior high" in text_lower or "high school" in text_lower or "sekondarya" in text_lower:
        level = "Pre-School to Senior High School"
    elif "pre-school" in text_lower or "kinder" in text_lower or "elementary" in text_lower:
        level = "Pre-School / Kindergarten"
    elif "resumed" in text_lower or "may pasok" in text_lower or "tuloy ang klase" in text_lower:
        level = "Classes Normal / Resumed"
    else:
        level = "All Levels (Public & Private)"
        
    scope = "Taguig City / Metro Manila" if ("metro manila" in text_lower or "ncr" in text_lower or "taguig" in text_lower) else "Taguig City"
    reason = text[:140].strip() + ("..." if len(text) > 140 else "")
    
    return {
        "level": level,
        "scope": scope,
        "reason": f"FB Announcement (@{FB_PAGE_HANDLE}): {reason}",
        "issued_by": f"Facebook Page (@{FB_PAGE_HANDLE})"
    }

def _facebook_suspension_poller_task():
    """Background task to poll public Facebook page announcements for Class Suspensions."""
    import requests
    from bs4 import BeautifulSoup
    import re
    
    last_processed_text = ""
    
    while True:
        try:
            posts = []
            
            # Method 1: Official Facebook Graph API
            if FB_ACCESS_TOKEN and FB_PAGE_HANDLE:
                try:
                    url = f"https://graph.facebook.com/v18.0/{FB_PAGE_HANDLE}/posts?access_token={FB_ACCESS_TOKEN}&limit=5"
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        for item in data.get('data', []):
                            if 'message' in item:
                                posts.append(item['message'])
                except Exception as e:
                    print("[FB POLLER] Graph API error:", e)
            
            # Method 2: Public FB Page web scraper fallback
            if not posts and FB_PAGE_HANDLE:
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    url = f"https://mbasic.facebook.com/{FB_PAGE_HANDLE}"
                    r = requests.get(url, headers=headers, timeout=10)
                    if r.status_code == 200:
                        eventlet.sleep(0)
                        soup = BeautifulSoup(r.text, 'html.parser')
                        articles = soup.find_all(['article', 'div'], id=re.compile(r'u_\d+_\d+'))
                        for art in articles[:5]:
                            txt = art.get_text(separator=' ').strip()
                            if txt:
                                posts.append(txt)
                except Exception as e:
                    print("[FB POLLER] Web scrape error:", e)

            # Analyze posts
            for post_text in posts:
                if post_text == last_processed_text:
                    continue
                    
                parsed = parse_fb_suspension_text(post_text)
                if parsed:
                    last_processed_text = post_text
                    ts = datetime.now(timezone.utc).isoformat()
                    
                    conn = db_connect()
                    c = conn.cursor()
                    c.execute("UPDATE class_suspensions SET active = 0")
                    c.execute("INSERT INTO class_suspensions (level, scope, reason, issued_by, timestamp, active) VALUES (?, ?, ?, ?, ?, 1)",
                              (parsed['level'], parsed['scope'], parsed['reason'], parsed['issued_by'], ts))
                    cid = c.lastrowid
                    conn.commit()
                    conn.close()
                    
                    suspension_data = {
                        "id": cid,
                        "level": parsed['level'],
                        "scope": parsed['scope'],
                        "reason": parsed['reason'],
                        "issued_by": parsed['issued_by'],
                        "timestamp": ts,
                        "source": "official"
                    }
                    
                    socketio.emit('class_suspension_update', suspension_data, namespace='/dashboard')
                    write_audit("FB_CLASS_SUSPENSION_DETECTED", f"level={parsed['level']} page={FB_PAGE_HANDLE}", session_id="fb_poller")
                    print(f"[FB POLLER] Detected class suspension from @{FB_PAGE_HANDLE}: {parsed['level']}")
                    break
        except Exception as e:
            print("[FB POLLER] General Error:", e)
            
        time.sleep(180)

# Start background threads
_report_thread = Thread(target=_daily_report_scheduler, daemon=True)
_report_thread.start()

_polling_thread = Thread(target=_threat_polling_task, daemon=True)
_polling_thread.start()

_fb_thread = Thread(target=_facebook_suspension_poller_task, daemon=True)
_fb_thread.start()

# =========================
# SOCKET.IO EVENTS
# =========================
@socketio.on('connect', namespace='/dashboard')
def handle_connect():
    global TOTAL_CONNECTIONS_EVER
    CONNECTED_CLIENTS.add(request.sid)
    TOTAL_CONNECTIONS_EVER += 1
    socketio.emit('warnings_update', CACHED_WARNINGS, to=request.sid, namespace='/dashboard')
    # Broadcast updated client count to all
    socketio.emit('client_count', {'current': len(CONNECTED_CLIENTS), 'total': TOTAL_CONNECTIONS_EVER}, namespace='/dashboard')

@socketio.on('disconnect', namespace='/dashboard')
def handle_disconnect():
    CONNECTED_CLIENTS.discard(request.sid)
    socketio.emit('client_count', {'current': len(CONNECTED_CLIENTS), 'total': TOTAL_CONNECTIONS_EVER}, namespace='/dashboard')

# =========================
# STARTUP
# =========================
if __name__ == "__main__":
    stop_event = Event()
    socketio.start_background_task(mqtt_thread, stop_event)
    try:
        print("Starting VERS System (Flask + SocketIO + Gemini AI)")
        print(f"Server will run on http://{FLASK_HOST}:{FLASK_PORT}")
        socketio.run(app, host=FLASK_HOST, port=FLASK_PORT, debug=False)
    except KeyboardInterrupt:
        print("Shutting down")
    finally:
        stop_event.set()
        mqtt_client.disconnect()
        scheduler.shutdown()
