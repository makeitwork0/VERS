import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime, timezone

# =========================
# CONFIG
# =========================
# If running this on your PC, change to your Pi's IP (e.g., "192.168.100.154")
# If running directly on the Pi, leave as "localhost"
MQTT_BROKER = "localhost" 
MQTT_PORT = 1883
PUBLISH_INTERVAL = 5 # seconds between updates

# Define 10 Virtual Nodes with GPS coordinates
VIRTUAL_NODES = [
    {"id": "V-Node_01", "lat": 14.4681, "lon": 121.0552},
    {"id": "V-Node_02", "lat": 14.4691, "lon": 121.0562},
    {"id": "V-Node_03", "lat": 14.4671, "lon": 121.0542},
    {"id": "V-Node_04", "lat": 14.4701, "lon": 121.0572},
    {"id": "V-Node_05", "lat": 14.4661, "lon": 121.0532},
    {"id": "V-Node_06", "lat": 14.4686, "lon": 121.0557},
    {"id": "V-Node_07", "lat": 14.4676, "lon": 121.0547},
    {"id": "V-Node_08", "lat": 14.4696, "lon": 121.0567},
    {"id": "V-Node_09", "lat": 14.4666, "lon": 121.0537},
    {"id": "V-Node_10", "lat": 14.4706, "lon": 121.0577},
]

# Track state for each node to simulate battery drain and sustained emergencies
node_states = {
    node["id"]: {
        "battery": random.uniform(80.0, 100.0),
        "emergency_ticks": 0,
        "active_emergency": None
    }
    for node in VIRTUAL_NODES
}

def generate_payload(node):
    state = node_states[node["id"]]
    
    # 1. Update Battery (slow drain)
    state["battery"] -= random.uniform(0.01, 0.05)
    if state["battery"] <= 0:
        state["battery"] = 100.0 # Recharge simulation
        
    # 2. Baseline Sensors
    sensors = {
        "life_form": 0,
        "flood": 0,
        "fire": 0,
        "humidity": random.randint(45, 65),
        "gas": random.randint(10, 50)
    }
    
    # 3. Anomaly / Emergency Injection Engine
    # If no active emergency, small chance to trigger one
    if state["emergency_ticks"] <= 0:
        if random.random() < 0.01: # 1% chance per tick to avoid API rate limits
            events = ["fire", "flood", "life_form", "gas_leak"]
            state["active_emergency"] = random.choice(events)
            state["emergency_ticks"] = random.randint(3, 8) # Sustain for 3-8 ticks
            print(f"\n[!] INJECTING EMERGENCY: {state['active_emergency'].upper()} at {node['id']}!")
        else:
            state["active_emergency"] = None
    
    # Apply active emergency if any
    if state["emergency_ticks"] > 0:
        e = state["active_emergency"]
        if e == "fire":
            sensors["fire"] = 1
            sensors["humidity"] = random.randint(20, 30) # Fire drops humidity
        elif e == "flood":
            sensors["flood"] = 1
            sensors["humidity"] = random.randint(90, 100) # Flood raises humidity
        elif e == "life_form":
            sensors["life_form"] = 1
        elif e == "gas_leak":
            sensors["gas"] = random.randint(250, 400) # Critical gas levels
            
        state["emergency_ticks"] -= 1
        if state["emergency_ticks"] == 0:
            print(f"[*] Emergency cleared at {node['id']}")

    # 4. Build JSON Payload
    payload = {
        "id": node["id"],
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sensors": sensors,
        "battery": round(state["battery"], 1),
        "lat": node["lat"],
        "lon": node["lon"],
        "gps_response": True # Include GPS so map updates
    }
    return payload

def main():
    print(f"Starting VERS Virtual Node Simulator (Target: {MQTT_BROKER}:{MQTT_PORT})")
    def on_disconnect(client, userdata, rc, *args, **kwargs):
        if rc != 0:
            print("Unexpected MQTT disconnection. Auto-reconnecting in background...")

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="VERS_Simulator")
    except AttributeError:
        client = mqtt.Client(client_id="VERS_Simulator")

    client.on_disconnect = on_disconnect
    
    retry_delay = 1
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_start()
            print("Connected to MQTT Broker. Beginning simulation...")
            break
        except Exception as e:
            print(f"Failed to connect to broker: {e}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

    try:
        while True:
            for node in VIRTUAL_NODES:
                topic = f"vers/data/{node['id']}"
                payload = generate_payload(node)
                
                # Publish to MQTT with QoS 1 for fault tolerance
                client.publish(topic, json.dumps(payload), qos=1)
                
                # Terminal output for visual tracking
                emergency_flag = "🚨" if node_states[node['id']]['active_emergency'] else "✅"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {emergency_flag} Sent data for {node['id']} (Bat: {payload['battery']}%)")
                
            time.sleep(PUBLISH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping Simulator...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
