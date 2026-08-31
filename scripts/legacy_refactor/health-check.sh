#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Health Check & Self-Healing Sentinel
# Location: scripts/legacy_refactor/health-check.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_HELPER="${SCRIPT_DIR}/secrets.sh"

source "${SECRETS_HELPER}"

NTFY_URL="$(sovereign_load_secret NTFY_URL "")"

ALL_HEALTHY=true
declare -a ISSUES=()

report_issue() {
    ALL_HEALTHY=false
    ISSUES+=("$1")
    echo "[!] HEALTH ALERT: $1" >&2
}

# 1. Check Nginx Decoy
if command -v systemctl >/dev/null 2>&1; then
    if ! systemctl is-active --quiet nginx 2>/dev/null; then
        report_issue "Nginx decoy service is down. Attempting auto-restart..."
        systemctl restart nginx 2>/dev/null || true
    fi
fi

# 2. Check Port 443 Ingress Socket
if command -v ss >/dev/null 2>&1; then
    if ! ss -tln | grep -q ":443 "; then
        report_issue "Ingress port 443 is not actively listening."
    fi
fi

# 3. Check Disk Usage Threshold (< 85%)
DISK_USAGE="$(df / | awk 'NR==2 {print $5}' | tr -d '%')"
if [[ "$DISK_USAGE" -gt 85 ]]; then
    report_issue "Disk usage is critically high: ${DISK_USAGE}%"
fi

# 4. Check Decoy Status Endpoint
DECOY_STATUS="$(curl -s -m 3 http://127.0.0.1:8443/api/status || echo "")"
if [[ -z "$DECOY_STATUS" ]]; then
    report_issue "Decoy API endpoint on 127.0.0.1:8443 is unresponsive."
fi

# Summary
if [[ "$ALL_HEALTHY" == "true" ]]; then
    echo "[✓] All Sovereign Proxy system health checks passed."
    exit 0
else
    echo "[-] System health check detected issues: ${#ISSUES[@]} failure(s)"
    if [[ -n "$NTFY_URL" ]]; then
        MSG="🚨 Sovereign Proxy Health Check Alert: ${ISSUES[*]}"
        curl -s -d "$MSG" "$NTFY_URL" >/dev/null 2>&1 || true
    fi
    exit 1
fi
