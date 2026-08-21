#!/usr/bin/env python3
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
