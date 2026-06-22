#!/usr/bin/env bash
# ============================================================
# run.sh — Entry point: calls deploy.sh
#
# First time:  sudo bash run.sh --setup
# Every time:  sudo bash run.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"
sudo bash deploy.sh "${1:-}"
