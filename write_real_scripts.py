import os

base_dir = r"C:\home_server\sovereign-oci-proxy"

files = {
    "scripts/modules/xray-routing-fix.py": '''#!/usr/bin/env python3
"""
FIX ROUTING XRAY (SOVEREIGN HOMELAB)
Questo script modifica la configurazione xrayTemplateConfig nel DB di 3x-ui
per permettere al traffico VLESS di raggiungere gli IP privati (Homelab/Tailscale).
Senza questo script, Xray blocca tutto il traffico verso 192.168.x.x o 100.64.x.x.
"""
import sqlite3
import json
import sys

DB_PATH = "/etc/x-ui/x-ui.db"

def fix_routing():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key='xrayTemplateConfig'")
        row = c.fetchone()
        
        if not row:
            print("xrayTemplateConfig non trovato.")
            return

        config = json.loads(row[0])
        routing = config.get("routing", {})
        rules = routing.get("rules", [])
        
        # Cerca la regola di blocco (outboundTag: block) e rimuovi geoip:private
        for rule in rules:
            if rule.get("outboundTag") == "block":
                ip_list = rule.get("ip", [])
                if "geoip:private" in ip_list:
                    ip_list.remove("geoip:private")
                    print("Rimosso geoip:private dalla regola block")

        # Cerca la regola direct e assicurati che geoip:private sia instradato lì
        direct_rule_found = False
        for rule in rules:
            if rule.get("outboundTag") == "direct":
                ip_list = rule.get("ip", [])
                if "geoip:private" not in ip_list:
                    ip_list.append("geoip:private")
                    print("Aggiunto geoip:private alla regola direct")
                direct_rule_found = True
                
        if not direct_rule_found:
            rules.insert(0, {
                "type": "field",
                "outboundTag": "direct",
                "ip": ["geoip:private"]
            })
            print("Creata nuova regola direct per geoip:private")

        new_config = json.dumps(config, indent=2)
        c.execute("UPDATE settings SET value=? WHERE key='xrayTemplateConfig'", (new_config,))
        conn.commit()
        print("Routing aggiornato con successo. Riavviare x-ui (systemctl restart x-ui).")
        
    except Exception as e:
        print(f"Errore: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_routing()
''',

    "scripts/modules/xray-client-fix.py": '''#!/usr/bin/env python3
"""
FIX CLIENTI RELAZIONALI 3X-UI v3.6.0
Nelle nuove versioni di 3x-ui, i client non vengono più letti dal JSON settings della tabella inbounds,
ma devono essere inseriti obbligatoriamente nelle tabelle relazionali `clients` e `client_inbounds`.
Questo script inietta un client correttamente.
"""
import sqlite3
import uuid

DB_PATH = "/etc/x-ui/x-ui.db"

def add_client(inbound_id, email, client_uuid):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 1. Inserisci in clients
        c.execute("""
            INSERT OR IGNORE INTO clients (id, email, enable, up, down, expiry, total) 
            VALUES (?, ?, 1, 0, 0, 0, 0)
        """, (client_uuid, email))
        
        # 2. Collega in client_inbounds
        # L'ID in client_inbounds è tipicamente autoincrement o gestito diversamente, ma x-ui lo collega.
        c.execute("""
            INSERT OR IGNORE INTO client_inbounds (client_id, inbound_id)
            VALUES (?, ?)
        """, (client_uuid, inbound_id))
        
        conn.commit()
        print(f"Client {email} inserito correttamente nelle tabelle relazionali.")
    except Exception as e:
        print(f"Errore DB: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Esempio d'uso
    my_uuid = str(uuid.uuid4())
    print(f"Generato nuovo UUID: {my_uuid}")
    # add_client(1, "utente-mobile", my_uuid)
''',

    "scripts/modules/monitoring.sh": '''#!/bin/bash
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
            subprocess.run(["ufw", "deny", "from", addr[0], "comment", "honeypot"])
if __name__ == "__main__":
    main()
HONEY_EOF
chmod +x /usr/local/bin/sovereign-honeypot.py

# Aggiungere ai cron
echo "0 */4 * * * /usr/local/bin/oracle-keepalive.sh"
'''
}

for fpath, content in files.items():
    full_path = os.path.join(base_dir, fpath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Script reali generati e scritti con successo.")
