import os
import glob

base_dir = r"C:\home_server\sovereign-oci-proxy"

readme_en = """# 🛡️ Sovereign OCI Proxy (Ultimate Edition)

![Sovereign Proxy](https://img.shields.io/badge/Status-Active-success.svg) ![Platform](https://img.shields.io/badge/Platform-Oracle_Cloud-red.svg) ![Protocol](https://img.shields.io/badge/Protocol-VLESS%2BReality-blue.svg) ![License](https://img.shields.io/badge/License-AGPL_3.0-green.svg)

**Sovereign OCI Proxy** is a comprehensive, field-tested architecture for building an anti-censorship fortress (VPN Proxy) using the Oracle Cloud Always Free Tier.

This project was built with a dual purpose:
1. **Ensure freedom of communication** and bypass government DPI (Deep Packet Inspection) in hostile networks (e.g., Egypt, China, corporate firewalls) by disguising traffic as normal HTTPS connections to commercial servers (like AWS).
2. **Securely connect to your private Homelab** by routing decrypted traffic into a secure mesh network (Tailscale), acting as an external shield and *Exit Node* without ever exposing ports on your home router.

---

## 🏗️ Architecture Overview
The core of the system revolves around a zero-cost Oracle ARM (A1.Flex) instance. 
1. **Entry Point (VLESS + REALITY):** Your phone/PC sends traffic to the Oracle IP on port 443. To hostile firewalls, it looks exactly like encrypted TLS 1.3 traffic to `aws.amazon.com`.
2. **Routing (Xray):** If the UUID is valid, Xray decrypts the request. If it's a bot or government scanner, the request is silently forwarded to a decoy site (Nginx).
3. **Exit (Internet or Homelab):** Internet-bound requests exit cleanly from the Oracle IP. Homelab-bound requests (`*.internal` or private IPs) are routed into the `tailscale0` interface to reach your physical server.
4. **Defenses:** UFW blocks everything except essential ports. Fail2ban rejects brute-force attacks. A Python Honeypot on port 8080 catches and bans scanners in real-time, notifying you via Ntfy. An *Anti-Idle* script prevents Oracle from reclaiming the server due to inactivity.

---

## ⚠️ CRITICAL WARNING: THE PORT 22 LOCKOUT
When securing SSH, **DO NOT** remove port 22 or restart the SSH service immediately! 
If you change your SSH port to `2222` in `/etc/ssh/sshd_config` without opening it in the Oracle Cloud Console first, **you will be permanently locked out of your instance**.

**The correct sequence is:**
1. Go to the **Oracle Cloud Console** -> VCN -> Security Lists.
2. **Add an Ingress Rule** for TCP port `2222`. (Do NOT delete the rule for port 22 yet).
3. Edit `/etc/ssh/sshd_config` on the server and change the port to `2222`.
4. Restart the SSH service: `sudo systemctl restart sshd`.
5. **Open a SECOND terminal** and verify you can connect using `-p 2222`.
6. Only after a successful connection on the new port, go back to the Oracle Console and delete the Ingress Rule for port 22.

---

## 🆘 Disaster Recovery
Oracle is known for terminating free instances without warning. This architecture is designed to **survive server death** with a 30-minute recovery time:
- **Asymmetric Backup:** Every night, the user database (`x-ui.db`) and routing configs are encrypted with **Asymmetric GPG** (AES-256) using only your public key, then uploaded to Backblaze B2. 
- **Zero Secrets on Server:** The private key required to decrypt the backup is NOT on the server. If a hacker breaches the server or Backblaze, the data remains unreadable.
- **Restore:** Spin up a new instance, download the `.gpg` backup, decrypt it on your local Mac/PC with your private key, upload it to the new server, and restart. All users and routes are instantly restored.

---

## 🚀 Beta Roadmap (Infrastructure as Code)
Currently, the infrastructure relies on modular shell scripts (`bash`). 
**Coming in v2.0 (BETA): Ansible & Terraform**
We are working on bringing this to an enterprise level with 100% IaC:
- **Terraform:** Automatic provisioning of the Oracle instance, VCN, and Security Lists (automatically opening port 2222, 443, 80).
- **Ansible:** Fully idempotent OS hardening (Swap, BBR, SSH, Fail2ban, UFW, Honeypot) and proxy deployment.

*No passwords, SSH keys, or UUIDs are stored in this repository. Ensure you use a `.env` file or a password manager for secrets.*
"""

def write_file(path, content):
    with open(os.path.join(base_dir, path), "w", encoding="utf-8") as f:
        f.write(content)

write_file("README.md", readme_en)

# Rewrite the python scripts to have English docstrings
routing_fix_en = '''#!/usr/bin/env python3
"""
XRAY ROUTING FIX (SOVEREIGN HOMELAB)
This script modifies the xrayTemplateConfig in the 3x-ui SQLite database
to allow VLESS traffic to reach private IPs (Homelab/Tailscale).
Without this, Xray blocks all traffic to 192.168.x.x or 100.64.x.x by default.
"""
import sqlite3
import json

DB_PATH = "/etc/x-ui/x-ui.db"

def fix_routing():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key='xrayTemplateConfig'")
        row = c.fetchone()
        
        if not row:
            print("xrayTemplateConfig not found.")
            return

        config = json.loads(row[0])
        routing = config.get("routing", {})
        rules = routing.get("rules", [])
        
        for rule in rules:
            if rule.get("outboundTag") == "block":
                ip_list = rule.get("ip", [])
                if "geoip:private" in ip_list:
                    ip_list.remove("geoip:private")
                    print("Removed geoip:private from block rule")

        direct_rule_found = False
        for rule in rules:
            if rule.get("outboundTag") == "direct":
                ip_list = rule.get("ip", [])
                if "geoip:private" not in ip_list:
                    ip_list.append("geoip:private")
                    print("Added geoip:private to direct rule")
                direct_rule_found = True
                
        if not direct_rule_found:
            rules.insert(0, {
                "type": "field",
                "outboundTag": "direct",
                "ip": ["geoip:private"]
            })
            print("Created new direct rule for geoip:private")

        new_config = json.dumps(config, indent=2)
        c.execute("UPDATE settings SET value=? WHERE key='xrayTemplateConfig'", (new_config,))
        conn.commit()
        print("Routing successfully updated. Please restart x-ui (systemctl restart x-ui).")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_routing()
'''
write_file("scripts/modules/xray-routing-fix.py", routing_fix_en)

client_fix_en = '''#!/usr/bin/env python3
"""
3X-UI v3.6.0 RELATIONAL CLIENTS FIX
In newer versions of 3x-ui, clients are no longer read from the JSON settings.
They MUST be inserted into the relational `clients` and `client_inbounds` tables.
This script injects a client correctly into the database to avoid silent drops.
"""
import sqlite3
import uuid

DB_PATH = "/etc/x-ui/x-ui.db"

def add_client(inbound_id, email, client_uuid):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 1. Insert into clients
        c.execute("""
            INSERT OR IGNORE INTO clients (id, email, enable, up, down, expiry, total) 
            VALUES (?, ?, 1, 0, 0, 0, 0)
        """, (client_uuid, email))
        
        # 2. Link in client_inbounds
        c.execute("""
            INSERT OR IGNORE INTO client_inbounds (client_id, inbound_id)
            VALUES (?, ?)
        """, (client_uuid, inbound_id))
        
        conn.commit()
        print(f"Client {email} successfully inserted into relational tables.")
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    my_uuid = str(uuid.uuid4())
    print(f"Generated new UUID: {my_uuid}")
'''
write_file("scripts/modules/xray-client-fix.py", client_fix_en)

print("English translation complete.")
