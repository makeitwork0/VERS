# Troubleshooting Guide

> **Common issues, debugging procedures, and recovery instructions for the VERS system.**

---

## Table of Contents

- [Service Management](#service-management)
- [MQTT Broker Issues](#mqtt-broker-issues)
- [Database Issues](#database-issues)
- [Email / SMTP Issues](#email--smtp-issues)
- [AI Engine Issues](#ai-engine-issues)
- [Map & UI Issues](#map--ui-issues)
- [Cloudflare Tunnel Issues](#cloudflare-tunnel-issues)
- [Sensor Node Issues](#sensor-node-issues)
- [Performance Issues](#performance-issues)
- [Recovery Procedures](#recovery-procedures)
- [Diagnostic Commands Reference](#diagnostic-commands-reference)

---

## Service Management

### Checking Service Status

```bash
# Main VERS application
sudo systemctl status vers

# Sensor simulator
sudo systemctl status vers-simulator

# MQTT broker
sudo systemctl status mosquitto

# Cloudflare tunnel
sudo systemctl status cloudflared-tunnel
```

### Viewing Live Logs

```bash
# Main application logs (live stream)
sudo journalctl -u vers -f

# Last 50 lines of VERS logs
sudo journalctl -u vers -n 50

# Today's logs only
sudo journalctl -u vers --since today

# Logs from a specific time
sudo journalctl -u vers --since "2026-08-10 08:00" --until "2026-08-10 12:00"
```

### Restarting Services

```bash
# Restart main application
sudo systemctl restart vers

# Restart everything
sudo systemctl restart mosquitto vers vers-simulator

# Full reset (stop all, clear logs, restart)
sudo systemctl stop vers vers-simulator
sudo journalctl --rotate && sudo journalctl --vacuum-time=1d
sudo systemctl start vers vers-simulator
```

### Service Won't Start

**Symptom**: `sudo systemctl status vers` shows `failed` or `inactive`.

**Diagnosis**:
```bash
# Check error details
sudo journalctl -u vers -n 30 --no-pager

# Test running manually
cd /home/rasp-pi/vers_project
source venv/bin/activate
python -u vers_system.py
```

**Common Causes**:
| Error Message | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'flask'` | Missing dependencies | `source venv/bin/activate && pip install flask flask-socketio eventlet paho-mqtt` |
| `Address already in use` | Port 5000 occupied | `sudo lsof -i :5000` then kill the process, or change `PORT` env var |
| `Missing dependency or import error` | Package not installed | Run the full pip install command from the deployment guide |
| `Permission denied: data/vers_data.db` | File permissions | `sudo chown -R rasp-pi:rasp-pi /home/rasp-pi/vers_project/data/` |

---

## MQTT Broker Issues

### Broker Not Running

```bash
# Check status
sudo systemctl status mosquitto

# Start if stopped
sudo systemctl start mosquitto

# Check if port 1883 is listening
ss -tlnp | grep 1883
```

### No Sensor Data Arriving

**Diagnosis**:
```bash
# Monitor all VERS MQTT traffic
mosquitto_sub -h localhost -t "vers/data/#" -v

# Publish a test message
mosquitto_pub -h localhost -t "vers/data/TEST" -m '{"id":"TEST","timestamp":"2026-01-01T00:00:00Z","sensors":{"fire":0,"flood":0,"life_form":0,"humidity":50,"gas":20},"battery":100,"lat":14.4681,"lon":121.0552}'
```

**Checklist**:
1. Is Mosquitto running? → `sudo systemctl status mosquitto`
2. Is VERS connected to MQTT? → Check logs: `sudo journalctl -u vers | grep "MQTT connected"`
3. Are nodes publishing? → Monitor with `mosquitto_sub`
4. Is the topic correct? → Nodes must publish to `vers/data/{node_id}`

### Mosquitto Config Issues

```bash
# Check config syntax
mosquitto -c /etc/mosquitto/mosquitto.conf --test

# View config
cat /etc/mosquitto/mosquitto.conf

# View Mosquitto logs
cat /var/log/mosquitto/mosquitto.log
```

---

## Database Issues

### Database Locked Error

**Symptom**: `sqlite3.OperationalError: database is locked`

**Cause**: Multiple processes or threads accessing the database simultaneously.

**Fix**:
```bash
# Check for stuck processes
sudo lsof data/vers_data.db

# Restart the service (clears all connections)
sudo systemctl restart vers
```

### Database Corruption

**Symptom**: `sqlite3.DatabaseError: database disk image is malformed`

**Recovery**:
```bash
# 1. Stop the service
sudo systemctl stop vers

# 2. Backup the corrupted file
cp data/vers_data.db data/vers_data.db.corrupt

# 3. Attempt repair
cd /home/rasp-pi/vers_project
sqlite3 data/vers_data.db ".dump" | sqlite3 data/vers_data_repaired.db
mv data/vers_data_repaired.db data/vers_data.db

# 4. If repair fails, start fresh (data loss)
rm data/vers_data.db
sudo systemctl start vers   # Tables auto-created on startup
```

### Viewing Database Contents

```bash
cd /home/rasp-pi/vers_project

# Count records
sqlite3 data/vers_data.db "SELECT COUNT(*) FROM sensor_logs;"

# View recent entries
sqlite3 data/vers_data.db "SELECT device_id, timestamp, substr(payload, 1, 80) FROM sensor_logs ORDER BY id DESC LIMIT 10;"

# List devices
sqlite3 data/vers_data.db "SELECT * FROM devices;"

# Check database size
ls -lh data/vers_data.db

# Full table list
sqlite3 data/vers_data.db ".tables"
```

### Database Growing Too Large

```bash
# Check size
du -h data/vers_data.db

# Prune old records (keep last 7 days)
sqlite3 data/vers_data.db "DELETE FROM sensor_logs WHERE datetime(timestamp) < datetime('now', '-7 days');"
sqlite3 data/vers_data.db "VACUUM;"
```

---

## Email / SMTP Issues

### Emails Not Sending

**Diagnosis**:
```bash
# Check VERS logs for SMTP errors
sudo journalctl -u vers | grep -i "smtp\|email\|mail"
```

**Common Causes**:

| Issue | Diagnosis | Fix |
|---|---|---|
| "SENDER_PASSWORD not configured" | Password is placeholder value | Set a real Gmail app password in settings.json |
| "Authentication failed" | Wrong app password | Generate a new 16-char app password at myaccount.google.com → Security → App Passwords |
| "Connection timed out" | No internet / firewall | Check `ping smtp.gmail.com` and ensure port 587 is open |
| "Less secure app blocked" | Gmail security policy | Must use App Password with 2FA enabled, not account password |
| Spaces in password | Password has spaces | Remove all spaces from `sender_password` in settings.json |

### Testing Email Manually

```bash
cd /home/rasp-pi/vers_project
source venv/bin/activate
python3 -c "
import json, smtplib
from email.mime.text import MIMEText
with open('data/settings.json') as f: s = json.load(f)
msg = MIMEText('VERS email test successful.')
msg['Subject'] = 'VERS Email Test'
msg['From'] = s['sender_email']
msg['To'] = s['recipient_email']
server = smtplib.SMTP(s['smtp_server'], s['smtp_port'])
server.starttls()
server.login(s['sender_email'], s['sender_password'])
server.send_message(msg)
server.quit()
print('Email sent successfully!')
"
```

---

## AI Engine Issues

### Gemini AI Not Working

**Symptom**: Log shows `Gemini API Error: ...`

**Checklist**:
1. Is `GEMINI_API_KEY` set in environment? → `echo $GEMINI_API_KEY`
2. Is there internet connectivity? → `curl -s https://generativelanguage.googleapis.com`
3. Is the API key valid? → Check at [Google AI Studio](https://aistudio.google.com/)

**Setting the API Key**:
```bash
# Add to environment
export GEMINI_API_KEY="your-api-key-here"

# Or add to service file
sudo systemctl edit vers
# Add: Environment=GEMINI_API_KEY=your-key
```

### Ollama Fallback Not Working

**Symptom**: Log shows `Ollama Backup Error: ...`

**Checklist**:
1. Is Ollama installed? → `which ollama`
2. Is Ollama running? → `curl http://localhost:11434/api/tags`
3. Is the model pulled? → `ollama list`
4. Pull the model: `ollama pull qwen2.5:0.5b`

### Both AI Engines Offline

If neither Gemini nor Ollama is available, the system falls back to:
> "Emergency AI systems offline. Please refer to the manual handbook protocols immediately."

This static message is still delivered via voice alert and email. The system continues to function — only AI-generated contextual advice is unavailable.

---

## Map & UI Issues

### Map Controls Not Clickable (Operator Mode)

**Symptom**: After logging in as operator, Leaflet map layer controls and zoom buttons don't respond to clicks.

**Cause**: The `#settingsModal` div has `display: block` set inline (from operator initialization), creating an invisible overlay with `z-index: 1000` that intercepts clicks.

**Fix**: Ensure `#settingsModal` does **not** have the `operator-only` class. The modal should only be visible when the `.active` class is toggled. A safety guard in `style.css` sets `pointer-events: none` on `.settings-modal` (without `.active`).

### Dashboard Not Loading

**Checklist**:
1. Is VERS running? → `sudo systemctl status vers`
2. Is port 5000 accessible? → `curl -s http://localhost:5000 | head -c 100`
3. Browser console errors? → Open DevTools (F12) → Console tab
4. CDN libraries blocked? → Dashboard loads Leaflet, Chart.js, Socket.IO from CDN. Check network connectivity.

### Mobile Menu Not Appearing

**Symptom**: On mobile viewports (< 900px), the top controls still show as desktop buttons.

**Fix**: The hamburger menu (`#mobileTopbarControls`) is controlled by CSS `@media (max-width: 900px)`. Force a hard refresh (`Ctrl+Shift+R`) to clear cached CSS. Ensure `style.css` has the responsive breakpoint rules.

### WebSocket Connection Failed

**Symptom**: Dashboard shows "Disconnected" or Socket.IO reconnection errors.

**Diagnosis**:
```bash
# Check if SocketIO is responding
curl -s "http://localhost:5000/socket.io/?transport=polling"
```

**Common Fixes**:
- Restart VERS: `sudo systemctl restart vers`
- Check for port conflicts: `ss -tlnp | grep 5000`
- Clear browser cache and reconnect

---

## Cloudflare Tunnel Issues

### Tunnel URL Not Detected

**Symptom**: `start_tunnel.sh` runs but no URL is found within 60 seconds.

**Diagnosis**:
```bash
# Check tunnel log
cat /tmp/cloudflared.log

# Test cloudflared manually
/usr/local/bin/cloudflared tunnel --url http://localhost:5000
```

**Common Causes**:
- No internet connection
- cloudflared binary not found at `/usr/local/bin/cloudflared`
- Cloudflare service temporarily unavailable
- VERS not running on port 5000 when tunnel starts

### Tunnel URL Email Not Sent

**Checklist**:
1. Is SMTP configured? → Check `data/settings.json`
2. Was the URL detected? → Check `/tmp/cloudflared.log`
3. Check email sending logs: `sudo journalctl -u cloudflared-tunnel`

### Tunnel URL Changed After Restart

This is **expected behavior**. Cloudflare Quick Tunnels generate ephemeral URLs that change on each restart. The `send_tunnel_email.py` script automatically emails the new URL to the operator.

For a persistent URL, consider setting up a [named Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) with a custom domain.

---

## Sensor Node Issues

### Node Not Appearing on Dashboard

**Checklist**:
1. Is the node publishing to the correct topic? → `mosquitto_sub -h localhost -t "vers/data/#" -v`
2. Is the JSON payload valid? → Check for malformed JSON in MQTT messages
3. Does the payload contain required fields? → `id`, `timestamp`, `sensors` are mandatory
4. Is the node's `id` field unique?

### Node Shows as "Faulty"

**Cause**: Sensor readings are outside physically plausible ranges (see [Fault Detection Heuristics](SENSOR_PROTOCOL.md#fault-detection-heuristics)):
- Humidity ≤ 0 or ≥ 100
- Gas ≥ 500
- Battery ≤ 0

**Fix**: Check physical sensor wiring, calibration, and ADC readings on the microcontroller.

### Simulator Not Generating Emergencies

The simulator has a 1% chance per tick to inject an emergency. This is intentionally low to avoid spam. To force-trigger:
1. Use the **Simulator** tab in the Settings modal
2. Or use the API:
```bash
curl -X POST http://localhost:5000/api/simulate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(curl -s http://localhost:5000/api/auth/key | python3 -c 'import json,sys;print(json.load(sys.stdin)["api_key"])')" \
  -d '{"id":"TEST-01","sensors":{"fire":1,"flood":0,"life_form":0,"humidity":25,"gas":30},"battery":80,"lat":14.4681,"lon":121.0552}'
```

---

## Performance Issues

### High CPU Usage

```bash
# Check VERS process
top -p $(pgrep -f vers_system)

# Check overall system
htop
```

**Common Causes**:
- Large database → Prune old records (see [Database Growing Too Large](#database-growing-too-large))
- Many WebSocket clients → Check `CONNECTED_CLIENTS` count via `/api/stats`
- Frequent PAGASA/GDACS polling → Interval is 5 minutes (configurable in `_threat_polling_task`)

### High Memory Usage

```bash
# Check memory
free -h

# Check VERS memory specifically
ps aux | grep vers_system
```

**Mitigations**:
- `provinces.json` is 16MB — loaded once into memory for geospatial checks
- SQLite database grows over time — prune periodically
- Reduce `CONNECTED_CLIENTS` by closing idle browser tabs

---

## Recovery Procedures

### Full System Reset

```bash
# Stop all services
sudo systemctl stop vers vers-simulator cloudflared-tunnel

# Backup current data
cp -r data/ data_backup_$(date +%Y%m%d)/

# Clear database (preserves config)
rm data/vers_data.db

# Clear audit log
> data/audit.log

# Restart
sudo systemctl start vers vers-simulator
```

### Restore from Email Backup

1. Download `vers_backup.zip` from your email
2. Extract to a temporary directory
3. Copy files to `/home/rasp-pi/vers_project/`:
   ```bash
   unzip vers_backup.zip -d /tmp/vers_restore/
   cp /tmp/vers_restore/vers_system.py /home/rasp-pi/vers_project/
   cp /tmp/vers_restore/vers_simulator.py /home/rasp-pi/vers_project/
   # ... etc
   sudo systemctl restart vers
   ```

### Emergency Manual Operation

If the system is completely down and cannot be restarted:
1. Monitor MQTT directly: `mosquitto_sub -h localhost -t "vers/data/#" -v`
2. Use `vers_top.py` for terminal monitoring: `python vers_top.py`
3. Contact PAGASA directly: `(02) 8284-0800`
4. Monitor GDACS at: `https://www.gdacs.org`

---

## Diagnostic Commands Reference

| Command | Purpose |
|---|---|
| `sudo systemctl status vers` | Check main app status |
| `sudo journalctl -u vers -f` | Live application log stream |
| `sudo journalctl -u vers -n 100` | Last 100 log lines |
| `mosquitto_sub -h localhost -t "vers/data/#" -v` | Monitor all MQTT sensor traffic |
| `curl http://localhost:5000/api/auth/status` | Check if server is responding |
| `curl http://localhost:5000/api/warnings` | Check cached warning data |
| `curl http://localhost:5000/api/class-suspensions` | Check class suspension status |
| `sqlite3 data/vers_data.db ".tables"` | List database tables |
| `sqlite3 data/vers_data.db "SELECT COUNT(*) FROM sensor_logs;"` | Count sensor records |
| `ss -tlnp \| grep 5000` | Check port 5000 listener |
| `ss -tlnp \| grep 1883` | Check MQTT port listener |
| `cat /tmp/cloudflared.log` | View Cloudflare tunnel log |
| `df -h` | Check disk space |
| `free -h` | Check memory usage |
| `python3 vers_top.py` | Launch terminal UI monitor |

---

*VERS Troubleshooting Guide v2.4*
