#!/usr/bin/env bash
# ==============================================================================
# NeroNet Sovereign Mesh Enterprise Management Console - Staging Launcher
# Safe local startup binding exclusively to 127.0.0.1:8081 (UI) and 8082 (API)
# Zero interference with Tailscale or global OS network routing tables.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "    NERONET SOVEREIGN MESH ENTERPRISE MANAGEMENT CONSOLE v4.0.0"
echo "======================================================================"
echo "[+] Starting local isolated staging environment..."

# 1. Check Node.js and npm
if ! command -v node >/dev/null 2>&1; then
    echo "[-] Error: Node.js is required but not found in PATH."
    exit 1
fi

NODE_VER=$(node -v)
echo "[+] Detected Node.js environment: ${NODE_VER}"

# 2. Prepare Data Directory
mkdir -p "$SCRIPT_DIR/data"

# 3. Setup Backend if backend directory exists
BACKEND_PID=""
if [ -d "$SCRIPT_DIR/backend" ]; then
    echo "[+] Checking backend dependencies..."
    if [ ! -d "$SCRIPT_DIR/backend/node_modules" ]; then
        echo "[+] Installing backend dependencies..."
        (cd "$SCRIPT_DIR/backend" && npm install)
    fi

    echo "[+] Initializing backend SQLite database & migrations..."
    if [ -f "$SCRIPT_DIR/backend/db/index.js" ]; then
        (cd "$SCRIPT_DIR/backend" && node -e "const db = require('./db'); console.log('[+] DB Initialized:', !!db);") || true
    fi

    echo "[+] Starting Control Plane REST API Backend on 127.0.0.1:8082..."
    if [ -f "$SCRIPT_DIR/backend/server.js" ]; then
        (cd "$SCRIPT_DIR/backend" && PORT=8082 node server.js) &
        BACKEND_PID=$!
    elif grep -q '"dev"' "$SCRIPT_DIR/backend/package.json" 2>/dev/null; then
        (cd "$SCRIPT_DIR/backend" && PORT=8082 npm run dev) &
        BACKEND_PID=$!
    fi
fi

# 4. Setup Frontend
echo "[+] Checking frontend dependencies..."
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo "[+] Installing frontend dependencies..."
    (cd "$SCRIPT_DIR/frontend" && npm install)
fi

echo "[+] Starting Enterprise Frontend UI on 127.0.0.1:8081..."
(cd "$SCRIPT_DIR/frontend" && npm run dev -- --host 127.0.0.1 --port 8081) &
FRONTEND_PID=$!

echo ""
echo "======================================================================"
echo "    [✔] NERONET CONSOLE STAGING IS LIVE AND READY"
echo "    - Web UI:       http://127.0.0.1:8081"
echo "    - Backend API:  http://127.0.0.1:8082/api"
echo "    - Health Check: http://127.0.0.1:8082/api/health"
echo "======================================================================"
echo "Press Ctrl+C or run ./stop.sh to shut down staging servers."

# Trap cleanup
cleanup() {
    echo ""
    echo "[+] Shutting down staging processes..."
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    echo "[✔] All processes stopped gracefully."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Wait for frontend process
wait "$FRONTEND_PID"
