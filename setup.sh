#!/bin/bash

# StoryBrain AI - Manual Setup Script for Ubuntu/Debian VPS
# This script installs system dependencies, Rust, and Python environment.

set -e

echo "------------------------------------------------"
echo "StoryBrain AI - Starting Manual Setup"
echo "------------------------------------------------"

# 1. Update System
echo "[1/5] Updating system packages..."
sudo apt-get update
sudo apt-get install -y build-essential curl libgl1-mesa-glx libglib2.0-0 pkg-config git python3-venv python3-dev

# 2. Install Rust (Required for rust_predictor)
if ! command -v rustc &> /dev/null; then
    echo "[2/5] Installing Rust compiler..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
else
    echo "[2/5] Rust is already installed."
fi

# 3. Create Python Virtual Environment
echo "[3/5] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Install Dependencies
echo "[4/5] Installing Python dependencies (this may take a few minutes for 'prophet')..."
pip install --upgrade pip
pip install maturin
pip install -r requirements.txt

# 5. Build and Install Local Rust Predictor
echo "[5/5] Building local Rust extension..."
cd rust_predictor
maturin develop --release
cd ..

echo "------------------------------------------------"
echo "Setup Complete!"
echo "To start the server manually:"
echo "source venv/bin/activate && gunicorn -c gunicorn_conf.py main:app"
echo "------------------------------------------------"
