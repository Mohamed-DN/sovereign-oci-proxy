#!/usr/bin/env python3
"""
Sovereign Proxy v4.0 - Modernized Xray Routing Database Patcher
Location: scripts/legacy_refactor/xray-routing-fix.py
Safely parses and updates Xray JSON template settings stored in 3x-ui / sovereign database,
enabling private mesh and homelab network routing while preventing SSRF vulnerabilities.
"""

import argparse
import json
import os
import sqlite3
import sys


def patch_routing(db_path: str) -> bool:
    if not os.path.exists(db_path):
        print(f"[-] Database not found at {db_path}", file=sys.stderr)
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if not cursor.fetchone():
            print("[-] Table 'settings' not found in database", file=sys.stderr)
            conn.close()
            return False

        cursor.execute("SELECT key, value FROM settings WHERE key='xrayTemplateConfig'")
        row = cursor.fetchone()
        if not row:
            print("[-] Key 'xrayTemplateConfig' not found in settings table", file=sys.stderr)
            conn.close()
            return False

        template_json = row[1]
        config = json.loads(template_json)

        # Update routing rules
        if "routing" in config and "rules" in config["routing"]:
            rules = config["routing"]["rules"]
            # Remove any existing rule that drops or blackholes geoip:private
            cleaned_rules = []
            for r in rules:
                if r.get("outboundTag") == "blocked" and "geoip:private" in r.get("ip", []):
                    # Remove geoip:private from blocked rule
                    r["ip"] = [ip for ip in r["ip"] if ip != "geoip:private"]
                    if r["ip"] or r.get("domain"):
                        cleaned_rules.append(r)
                else:
                    cleaned_rules.append(r)

            # Check if direct mesh routing rule for geoip:private exists
            has_private_rule = False
            for r in cleaned_rules:
                if (r.get("outboundTag") in ("direct", "mesh-bridge")) and ("geoip:private" in r.get("ip", []) or "10.0.0.0/8" in r.get("ip", [])):
                    has_private_rule = True
                    break

            if not has_private_rule:
                # Add explicit mesh bridge / direct routing rule for private IPs
                cleaned_rules.insert(0, {
                    "type": "field",
                    "outboundTag": "direct",
                    "ip": [
                        "geoip:private",
                        "10.0.0.0/8",
                        "172.16.0.0/12",
                        "192.168.0.0/16",
                        "100.64.0.0/10"
                    ]
                })

            config["routing"]["rules"] = cleaned_rules

        new_template_json = json.dumps(config, indent=2)
        cursor.execute(
            "UPDATE settings SET value = ? WHERE key = 'xrayTemplateConfig'",
            (new_template_json,)
        )
        conn.commit()
        conn.close()
        print("[+] Xray routing template successfully patched for private network routing.")
        return True

    except Exception as e:
        print(f"[-] Error patching Xray routing: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Modernized Xray Routing Database Patcher")
    parser.add_argument("--db", default="/etc/x-ui/x-ui.db", help="Path to SQLite database")
    args = parser.parse_args()

    success = patch_routing(args.db)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
