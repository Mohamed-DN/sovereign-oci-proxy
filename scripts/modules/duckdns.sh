#!/bin/bash
# =========================================================
# DUCKDNS AUTO-UPDATER
# =========================================================

echo "Setting up DuckDNS auto-updater..."

mkdir -p /opt/duckdns

cat << 'DUCK_EOF' > /opt/duckdns/duck.sh
#!/bin/bash
# IMPORTANT: Replace these variables with your actual DuckDNS details
DOMAIN="YOUR-SUBDOMAIN"
TOKEN="YOUR-DUCKDNS-TOKEN"
LOG="/var/log/duckdns-update.log"
NTFY_URL="https://ntfy.sh/YOUR-SECRET-TOPIC-HERE"
MAX_RETRIES=3

for i in $(seq 1 $MAX_RETRIES); do
    RESPONSE=$(curl -s --max-time 10 "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip=")
    if [ "$RESPONSE" = "OK" ]; then
        echo "[$(date)] DuckDNS update OK" >> "$LOG"
        exit 0
    fi
    echo "[$(date)] Attempt $i failed: $RESPONSE" >> "$LOG"
    sleep 5
done

echo "[$(date)] ERROR: DuckDNS FAILED" >> "$LOG"
curl -s -d "🚨 Oracle Proxy: DuckDNS update FAILED!" "$NTFY_URL" 2>/dev/null || true
exit 1
DUCK_EOF

chmod +x /opt/duckdns/duck.sh
touch /var/log/duckdns-update.log

echo "Running initial DuckDNS update..."
/opt/duckdns/duck.sh

echo "Adding DuckDNS to Crontab (Runs every 5 minutes)..."
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/duckdns/duck.sh") | crontab -
