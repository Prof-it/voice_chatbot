#!/usr/bin/env bash
# start-all.sh
# ------------------------
# Starts backend API and static frontend server

set -euo pipefail

# 1. Activate the venv
source /home/pi/voice_chatbot/venv/bin/activate

# 2. Launch backend (FastAPI via Uvicorn)
echo "Starting backend..."
nohup uvicorn backend.main:app \
    --host 0.0.0.0 --port 8000 \
    --log-level info \
    > /home/pi/voice_chatbot/logs/backend.log 2>&1 &

# 3. Serve frontend build
echo "Starting frontend..."
nohup serve -s /home/pi/voice_chatbot/frontend/build \
    -l 3000 \
    > /home/pi/voice_chatbot/logs/frontend.log 2>&1 &

echo "All services started."
