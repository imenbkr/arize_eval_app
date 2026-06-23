#!/usr/bin/env bash
# Wrapper for cron: loads .env, then runs one batch via the venv's python.
# Cron has a minimal environment, so we set everything explicitly here.
#
# Make executable once:   chmod +x run_cron.sh
# Crontab line (every 5 min):
#   */5 * * * * /home/imen/Desktop/arize_eval/run_cron.sh >> /home/imen/Desktop/arize_eval/cron.log 2>&1

set -euo pipefail

# Resolve the directory this script lives in, so cron can call it from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables from .env if present.
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# Use the venv's python explicitly (cron does not know about an activated venv).
exec "$SCRIPT_DIR/.venv/bin/python" run_once.py
