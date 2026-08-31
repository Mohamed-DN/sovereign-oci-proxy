#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Hardened Dynamic DNS Updater (DuckDNS)
# Location: scripts/legacy_refactor/duckdns.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_HELPER="${SCRIPT_DIR}/secrets.sh"

source "${SECRETS_HELPER}"

DOMAIN="$(sovereign_load_secret DUCKDNS_DOMAIN "")"
TOKEN="$(sovereign_load_secret DUCKDNS_TOKEN "")"
NTFY_URL="$(sovereign_load_secret NTFY_URL "")"

if [[ -z "$DOMAIN" ]] || [[ -z "$TOKEN" ]]; then
    echo "[!] DUCKDNS_DOMAIN or DUCKDNS_TOKEN not configured. Skipping DDNS update."
    exit 0
fi

# Sanitize inputs
DOMAIN="$(sovereign_sanitize_token "$DOMAIN")"
TOKEN="$(sovereign_sanitize_token "$TOKEN")"

UPDATE_URL="https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip="
MAX_RETRIES=3
RETRY_COUNT=0
SUCCESS=false

while [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; do
    RESPONSE="$(curl -s -m 10 "$UPDATE_URL" || echo "CURL_ERROR")"
    if [[ "$RESPONSE" == "OK" ]]; then
        echo "[+] DuckDNS update successful for ${DOMAIN}.duckdns.org at $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
        SUCCESS=true
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "[!] DuckDNS update attempt ${RETRY_COUNT}/${MAX_RETRIES} failed: ${RESPONSE}"
        sleep 5
    fi
done

if [[ "$SUCCESS" == "false" ]]; then
    echo "[-] ERROR: DuckDNS update failed after ${MAX_RETRIES} attempts." >&2
    if [[ -n "$NTFY_URL" ]]; then
        curl -s -d "🚨 DuckDNS update failed for ${DOMAIN} after 3 retries." "$NTFY_URL" >/dev/null 2>&1 || true
    fi
    exit 1
fi
