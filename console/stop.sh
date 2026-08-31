#!/usr/bin/env bash
# ==============================================================================
# NeroNet Sovereign Mesh Enterprise Management Console - Graceful Shutdown
# Stops staging processes running on ports 8081 (UI) and 8082 (API)
# ==============================================================================

echo "[+] Terminating any running NeroNet Console staging processes on ports 8081 / 8082..."

# Find and kill processes on port 8081
PID_8081=$(lsof -ti:8081 2>/dev/null || true)
if [ -n "$PID_8081" ]; then
    echo "[+] Stopping Frontend process on port 8081 (PID: $PID_8081)..."
    kill -15 $PID_8081 2>/dev/null || kill -9 $PID_8081 2>/dev/null || true
fi

# Find and kill processes on port 8082
PID_8082=$(lsof -ti:8082 2>/dev/null || true)
if [ -n "$PID_8082" ]; then
    echo "[+] Stopping Backend process on port 8082 (PID: $PID_8082)..."
    kill -15 $PID_8082 2>/dev/null || kill -9 $PID_8082 2>/dev/null || true
fi

echo "[✔] Staging environment stopped cleanly."
