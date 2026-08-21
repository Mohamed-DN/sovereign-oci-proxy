import os

base_dir = r"C:\home_server\sovereign-oci-proxy"

scripts_to_update = {
    "scripts/install.sh": """#!/bin/bash
# Sovereign OCI Proxy - Master Installer
# Run this script as root to orchestrate the entire deployment.

set -e

# Colors for output
GREEN='\\033[0;32m'
RED='\\033[0;31m'
NC='\\033[0m' # No Color

echo -e "${GREEN}[*] Starting Sovereign Proxy Installation...${NC}"

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[!] Please run this script as root (sudo ./scripts/install.sh)${NC}"
  exit 1
fi

chmod +x scripts/modules/*.sh

echo -e "${GREEN}[1/6] Running System Hardening (Swap, BBR, Firewall)...${NC}"
./scripts/modules/hardening.sh

echo -e "${GREEN}[2/6] Setting up Nginx Decoy...${NC}"
./scripts/modules/decoy.sh

echo -e "${GREEN}[3/6] Installing Monitoring & Honeypot...${NC}"
./scripts/modules/monitoring.sh

echo -e "${GREEN}[4/6] Setting up DuckDNS Auto-Updater...${NC}"
./scripts/modules/duckdns.sh

echo -e "${GREEN}[5/6] Setting up Xray Core (3x-ui)...${NC}"
./scripts/modules/xray.sh

echo -e "${GREEN}[6/6] Installation Complete!${NC}"
echo -e "${GREEN}Please remember to configure your GPG keys before enabling backup.sh${NC}"
""",

    "scripts/modules/monitoring.sh": """#!/bin/bash
# =========================================================
# MONITORING, HONEYPOT AND KEEPALIVE SCRIPT
# =========================================================

# Ensure you replace this with your actual ntfy URL before running
NTFY_URL="https://ntfy.sh/YOUR-SECRET-TOPIC-HERE" 

echo "Deploying Oracle Keepalive (Anti-Idle)..."
# 1. ORACLE KEEPALIVE (Prevents Instance Deletion)
cat << 'ALIVE_EOF' > /usr/local/bin/oracle-keepalive.sh
#!/bin/bash
# Spike CPU for 30 seconds
timeout 30 bash -c 'while true; do echo "scale=5000; 4*a(1)" | bc -l > /dev/null 2>&1; done' &
# Generate minimal network traffic
ping -c 10 8.8.8.8 > /dev/null 2>&1
curl -s https://www.google.com > /dev/null 2>&1
# Allocate 500MB of RAM and release it
python3 -c "x = bytearray(500*1024*1024); del x" 2>/dev/null
ALIVE_EOF

chmod +x /usr/local/bin/oracle-keepalive.sh

echo "Deploying Python Honeypot..."
# 2. PYTHON HONEYPOT (Catches and bans scanners on port 8080)
cat << 'HONEY_EOF' > /usr/local/bin/sovereign-honeypot.py
#!/usr/bin/env python3
import socket, subprocess

PORT = 8080
# Valid HTTP Response to trick scanners
BANNER = b"HTTP/1.1 200 OK\\r\\nServer: nginx\\r\\nContent-Length: 0\\r\\n\\r\\n"

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', PORT))
        s.listen(10)
        while True:
            conn, addr = s.accept()
            conn.sendall(BANNER)
            conn.close()
            # Ban the IP immediately using UFW
            subprocess.run(["ufw", "deny", "from", addr[0], "comment", "honeypot"])
if __name__ == "__main__":
    main()
HONEY_EOF

chmod +x /usr/local/bin/sovereign-honeypot.py

echo "Creating Systemd Service for Honeypot..."
cat << 'SVC_EOF' > /etc/systemd/system/honeypot.service
[Unit]
Description=Sovereign Honeypot Python
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/sovereign-honeypot.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
SVC_EOF

systemctl daemon-reload
systemctl enable --now honeypot

echo "Adding Keepalive to Crontab (Runs every 4 hours)..."
(crontab -l 2>/dev/null; echo "0 */4 * * * /usr/local/bin/oracle-keepalive.sh") | crontab -
""",

    "scripts/modules/duckdns.sh": """#!/bin/bash
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
""",

    "scripts/modules/xray.sh": """#!/bin/bash
# =========================================================
# 3X-UI AND XRAY CORE SETUP
# =========================================================

echo "Installing 3x-ui panel..."
bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh)

echo "3x-ui installed successfully."
echo "Please configure your inbound settings via the Web UI."
echo "If you need to route Tailscale private IPs (192.168.x.x), run:"
echo "python3 /root/sovereign-oci-proxy/scripts/modules/xray-routing-fix.py"
"""
}

for fpath, content in scripts_to_update.items():
    full_path = os.path.join(base_dir, fpath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Comprehensive script review and update complete.")
