#!/bin/bash
# =========================================================
# Sovereign Proxy - Health Check Test
# Simulates the health check logic locally for validation.
# =========================================================

echo "Running health check simulation..."
ERRORS=""

# Check core services
systemctl is-active --quiet x-ui || ERRORS+="x-ui is DOWN. "
systemctl is-active --quiet nginx || ERRORS+="Nginx is DOWN. "
systemctl is-active --quiet honeypot || ERRORS+="Honeypot is DOWN. "

# Check port 443
ss -tlnp | grep -q ':443 ' || ERRORS+="Port 443 is not listening. "

# Check disk usage
DISK=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
[ "$DISK" -gt 85 ] && ERRORS+="Disk usage is ${DISK}% (threshold: 85%). "

# Check swap usage
SWAP=$(free | awk '/Swap/ {if($2>0) print int($3/$2*100); else print 0}')
[ "$SWAP" -gt 50 ] && ERRORS+="Swap usage is ${SWAP}% (threshold: 50%). "

# Check Tailscale
tailscale status > /dev/null 2>&1 || ERRORS+="Tailscale is not connected. "

if [ -z "$ERRORS" ]; then
    echo "All health checks PASSED."
else
    echo "ISSUES FOUND: $ERRORS"
    exit 1
fi
