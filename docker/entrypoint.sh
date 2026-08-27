#!/bin/sh
# ==============================================================================
# Sovereign Proxy v4.0 - Rootless Container Entrypoint
# Location: docker/entrypoint.sh
# ==============================================================================
set -eu

echo "[+] Starting Sovereign Proxy v4.0 Container (UID: $(id -u), GID: $(id -g))..."

# Deploy decoy site assets to /var/www/decoy if empty
if [ ! -f /var/www/decoy/index.html ]; then
    /app/scripts/decoy.sh || true
fi

# Render Xray configuration if template exists
if [ -f /etc/sovereign/config.json.template ]; then
    SOVEREIGN_XRAY_CONF_OUTPUT="/etc/sovereign/config.json" /app/scripts/xray.sh || true
fi

# Start Active Defense Security Daemon in background if requested
if [ "${ENABLE_SECURITY_DAEMON:-1}" = "1" ]; then
    echo "[+] Launching Sovereign Active Defense Daemon..."
    python3 /app/sovereign-security-daemon.py --port "${HONEYPOT_PORT:-8080}" --dry-run &
fi

# Start Nginx Decoy in background
echo "[+] Starting Nginx Decoy Web Server..."
nginx -g "daemon off;" &
NGINX_PID=$!

# Handle graceful shutdown
trap 'kill -TERM $NGINX_PID 2>/dev/null; exit 0' TERM INT

# Wait for master process
wait $NGINX_PID
