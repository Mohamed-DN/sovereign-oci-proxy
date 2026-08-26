#!/usr/bin/env python3
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
