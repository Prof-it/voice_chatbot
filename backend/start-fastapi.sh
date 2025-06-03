#!/bin/bash

ulimit -v 512000  # Limit RAM to 1.5 GB (in KB)

while true; do
    echo "[INFO] Starting FastAPI app at $(date)"
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    echo "[WARN] FastAPI crashed with exit code $? at $(date)"
    echo "[INFO] Restarting in 5 seconds..."
    sleep 5
done
