#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Run the full deploy pipeline
bash deploy.sh
