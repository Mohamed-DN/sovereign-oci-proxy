#!/bin/bash
# =========================================================
# MONITORING, HONEYPOT E KEEPALIVE (Validati OCI)
# =========================================================

NTFY_URL="https://ntfy.sh/TUO-SEGRETO" # <-- Inserire URL prima di usare

# 1. KEEPALIVE ANTI-IDLE ORACLE (Evita la cancellazione dell'istanza)
cat << 'ALIVE_EOF' > /usr/local/bin/oracle-keepalive.sh
#!/bin/bash
timeout 30 bash -c 'while true; do echo "scale=5000; 4*a(1)" | bc -l > /dev/null 2>&1; done' &
ping -c 10 8.8.8.8 > /dev/null 2>&1
curl -s https://www.google.com > /dev/null 2>&1
python3 -c "x = bytearray(500*1024*1024); del x" 2>/dev/null
ALIVE_EOF
chmod +x /usr/local/bin/oracle-keepalive.sh

# 2. HONEYPOT IN PYTHON (Trappola per scanner cinesi)
cat << 'HONEY_EOF' > /usr/local/bin/sovereign-honeypot.py
#!/usr/bin/env python3
import socket, subprocess

PORT = 8080
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
            subprocess.run(["ufw", "deny", "from", addr[0], "comment", "honeypot"])
if __name__ == "__main__":
    main()
HONEY_EOF
chmod +x /usr/local/bin/sovereign-honeypot.py

# Aggiungere ai cron
echo "0 */4 * * * /usr/local/bin/oracle-keepalive.sh"
