#!/usr/bin/env python3
"""
Sovereign Proxy v4.0 - Modernized Relational Client Injector (3x-ui v3.6.0+)
Location: scripts/legacy_refactor/xray-client-fix.py
Injects client UUIDs and credentials into 3x-ui relational tables using prepared statements.
"""

import argparse
import json
import os
import sqlite3
import sys
import uuid


def inject_client(db_path: str, email: str, inbound_id: int = 1, client_uuid: str = None) -> bool:
    if not os.path.exists(db_path):
        print(f"[-] Database not found at {db_path}", file=sys.stderr)
        return False

    if not client_uuid:
        client_uuid = str(uuid.uuid4())

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        # 1. Update client_traffics table if exists
        if "client_traffics" in tables:
            cursor.execute(
                """
                INSERT OR REPLACE INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total)
                VALUES (?, 1, ?, 0, 0, 0, 0)
                """,
                (inbound_id, email)
            )

        # 2. Update inbounds table client settings JSON
        if "inbounds" in tables:
            cursor.execute("SELECT settings FROM inbounds WHERE id = ?", (inbound_id,))
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    settings = json.loads(row[0])
                    if "clients" not in settings:
                        settings["clients"] = []
                    
                    # Check if client already exists
                    found = False
                    for c in settings["clients"]:
                        if c.get("email") == email:
                            c["id"] = client_uuid
                            c["enable"] = True
                            found = True
                            break
                    
                    if not found:
                        settings["clients"].append({
                            "id": client_uuid,
                            "flow": "xtls-rprx-vision",
                            "email": email,
                            "limitIp": 0,
                            "totalGB": 0,
                            "expiryTime": 0,
                            "enable": True,
                            "tgId": "",
                            "subId": str(uuid.uuid4()).replace("-", "")[:16]
                        })

                    new_settings_json = json.dumps(settings)
                    cursor.execute(
                        "UPDATE inbounds SET settings = ? WHERE id = ?",
                        (new_settings_json, inbound_id)
                    )
                except Exception as e:
                    print(f"[-] Error updating inbounds settings: {e}", file=sys.stderr)
                    conn.rollback()
                    return False

        conn.commit()
        conn.close()
        print(f"[+] Client {email} ({client_uuid}) successfully configured for inbound {inbound_id}")
        return True

    except sqlite3.Error as e:
        print(f"[-] SQLite error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Modernized 3x-ui Relational Client Injector")
    parser.add_argument("email", help="Client email identifier")
    parser.add_argument("--db", default="/etc/x-ui/x-ui.db", help="Path to SQLite db")
    parser.add_argument("--inbound", type=int, default=1, help="Inbound ID")
    parser.add_argument("--uuid", default=None, help="Client UUID (optional, generated if missing)")
    args = parser.parse_args()

    success = inject_client(args.db, args.email, args.inbound, args.uuid)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
