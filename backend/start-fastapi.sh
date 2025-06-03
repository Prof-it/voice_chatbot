#!/bin/bash

# Set RAM limit to 500MB (in KB)
ulimit -v 512000

# Limit numerical libraries to 2 threads
export OPENBLAS_NUM_THREADS=2
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export NUMEXPR_NUM_THREADS=2

# Optional: log thread setting
echo "[INFO] Using 2 threads for all compute libraries"
echo "[INFO] Memory cap set to 500MB"

# Restart loop
while true; do
    echo "[INFO] Starting FastAPI app at $(date)"
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    echo "[WARN] FastAPI crashed with exit code $? at $(date)"
    echo "[INFO] Restarting in 5 seconds..."
    sleep 5
done
