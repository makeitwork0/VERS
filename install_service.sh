#!/bin/bash
# VERS Auto-Restart Watchdog Installer
# Run with: bash install_service.sh

set -e

echo "Installing VERS systemd watchdog service..."

# Copy service file to systemd
sudo cp vers.service /etc/systemd/system/vers.service

# Reload daemon, enable and start
sudo systemctl daemon-reload
sudo systemctl enable vers
sudo systemctl start vers

echo ""
echo "✅ VERS watchdog service installed and started!"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status vers       — Check service status"
echo "  sudo systemctl stop vers         — Stop the service"
echo "  sudo systemctl restart vers      — Restart the service"
echo "  sudo journalctl -u vers -f       — Live log stream"
echo "  sudo systemctl disable vers      — Uninstall auto-start"
