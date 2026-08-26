#!/bin/bash
# =========================================================
# MONITORING, HONEYPOT AND KEEPALIVE SCRIPT
# =========================================================

# NTFY_URL is sourced from config.env in the master install script
if [ -z "$NTFY_URL" ]; then
  NTFY_URL="https://ntfy.sh/YOUR-SECRET-TOPIC-HERE"
fi

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
BANNER = b"HTTP/1.1 200 OK\r\nServer: nginx\r\nContent-Length: 0\r\n\r\n"

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

# 3. WIREGUARD HEALTH MONITOR (Optional: alerts if wg0 goes down)
echo "Deploying WireGuard Health Monitor..."
cat << 'WG_MON_EOF' > /usr/local/bin/sovereign-wg-monitor.sh
#!/bin/bash
# Check if WireGuard interface is active and report via Ntfy
NTFY_URL="${NTFY_URL:-https://ntfy.sh/YOUR-SECRET-TOPIC-HERE}"

if command -v wg &>/dev/null && [ -f /etc/wireguard/wg0.conf ]; then
    if ! wg show wg0 &>/dev/null; then
        curl -s -d "⚠️ WireGuard wg0 is DOWN! Attempting restart..." "$NTFY_URL"
        systemctl restart wg-quick@wg0
        sleep 3
        if wg show wg0 &>/dev/null; then
            curl -s -d "✅ WireGuard wg0 recovered after restart." "$NTFY_URL"
        else
            curl -s -d "🚨 WireGuard wg0 FAILED to restart! Manual intervention needed." "$NTFY_URL"
        fi
    fi
fi
WG_MON_EOF

chmod +x /usr/local/bin/sovereign-wg-monitor.sh

# Add WireGuard monitor to the existing keepalive cron (runs every 4 hours alongside it)
(crontab -l 2>/dev/null; echo "5 */4 * * * /usr/local/bin/sovereign-wg-monitor.sh") | sort -u | crontab -

