#!/bin/bash

# StoryBrain AI - One-Click Production Deployment Script

set -e

echo "=================================================="
echo "🚀 StoryBrain AI - Production One-Click Deploy 🚀"
echo "=================================================="

echo "[1/4] Pulling latest code from GitHub..."
git pull origin main

echo "[2/4] Running setup and building Rust extensions..."
# Run the existing setup script to build dependencies and Rust code
bash setup.sh

echo "[3/4] Registering/Updating the Systemd Service..."
# Dynamically generate the systemd service file with correct paths
CURRENT_DIR=$(pwd)
cat <<EOF > storybrain.service
[Unit]
Description=StoryBrainAI Production Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${CURRENT_DIR}
Environment=PORT=8090
Environment=PATH=${CURRENT_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=${CURRENT_DIR}/venv/bin/gunicorn -c ${CURRENT_DIR}/gunicorn_conf.py main:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo cp storybrain.service /etc/systemd/system/storybrain.service
sudo systemctl daemon-reload

echo "[4/4] Restarting the Production Server..."
# Enable it to start on boot
sudo systemctl enable storybrain.service
# Restart the service to apply new code
sudo systemctl restart storybrain.service

echo "=================================================="
echo "✅ Deployment Successful! Your production server is live on Port 8090."
echo "You can check the logs anytime using this command:"
echo "sudo journalctl -u storybrain -f"
echo "=================================================="
