#!/bin/bash

LOG_FILE="/tmp/cloudflared.log"
rm -f "$LOG_FILE"

# Start cloudflared in the background within script and capture PID
/usr/local/bin/cloudflared tunnel --url http://localhost:5000 > "$LOG_FILE" 2>&1 &
CF_PID=$!

echo "Started cloudflared with PID $CF_PID, waiting for tunnel URL..."

# Loop until trycloudflare URL is detected (max 60 seconds)
URL=""
for i in {1..60}; do
    if grep -o "https://[a-zA-Z0-9-]*\.trycloudflare\.com" "$LOG_FILE" > /tmp/tunnel_url.txt; then
        URL=$(cat /tmp/tunnel_url.txt | head -n 1)
        if [ -n "$URL" ]; then
            break
        fi
    fi
    sleep 1
done

if [ -n "$URL" ]; then
    echo "Cloudflare Tunnel URL found: $URL"
    /home/rasp-pi/vers_project/venv/bin/python3 /home/rasp-pi/vers_project/send_tunnel_email.py "$URL"
else
    echo "Failed to retrieve Cloudflare Tunnel URL within 60 seconds."
fi

# Keep script attached to cloudflared PID so systemd considers service active
wait $CF_PID
