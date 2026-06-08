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
# Copy the service file to the systemd directory
sudo cp storybrain.service /etc/systemd/system/storybrain.service

# Reload systemd to pick up any changes made to the service file
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
