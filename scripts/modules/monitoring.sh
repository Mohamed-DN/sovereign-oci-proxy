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
