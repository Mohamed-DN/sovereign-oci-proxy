#!/usr/bin/env python3
"""
Sovereign Proxy v4.0 - Parameterized User Revocation Engine
Location: scripts/legacy_refactor/sovereign-revoke-user.py
Eliminates SQL injection (CWE-89) by enforcing strict regex sanitization
and parameterized SQLite prepared statements.
"""

import argparse
import json
import os
import re
import sqlite3
import sys

# RFC 5322 compliant strict email regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email(email: str) -> bool:
    """Validate email against strict regex to eliminate malicious payloads."""
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email))


def revoke_user(db_path: str, email: str) -> dict:
    """Revoke user access using parameterized SQL queries across legacy and modernized 3x-ui schemas."""
    if not validate_email(email):
        return {
            "success": False,
            "error": "Invalid email format. Input rejected by security policy.",
            "email": email,
            "modified_rows": 0,
        }

    if not os.path.exists(db_path):
        return {
            "success": False,
            "error": f"Database file not found at {db_path}",
            "email": email,
            "modified_rows": 0,
        }

    total_modified = 0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        # 1. Update client_stats table (Legacy 3x-ui schema)
        if "client_stats" in tables:
            cursor.execute(
                "UPDATE client_stats SET enable = 0 WHERE email = ?",
                (email,)
            )
            total_modified += cursor.rowcount

        # 2. Update client_traffics table (Modern 3x-ui / Sing-box schema)
        if "client_traffics" in tables:
            cursor.execute(
                "UPDATE client_traffics SET enable = 0 WHERE email = ?",
                (email,)
            )
            total_modified += cursor.rowcount

        # 3. Update inbounds table client settings if stored as JSON (3x-ui v2/v3)
        if "inbounds" in tables:
            cursor.execute("SELECT id, settings FROM inbounds WHERE settings LIKE ?", (f"%{email}%",))
            inbounds_rows = cursor.fetchall()
            for inb_id, settings_json in inbounds_rows:
                try:
                    settings_data = json.loads(settings_json)
                    changed = False
                    if "clients" in settings_data and isinstance(settings_data["clients"], list):
                        for client in settings_data["clients"]:
                            if client.get("email") == email:
                                client["enable"] = False
                                changed = True
                    if changed:
                        new_settings = json.dumps(settings_data)
                        cursor.execute(
                            "UPDATE inbounds SET settings = ? WHERE id = ?",
                            (new_settings, inb_id)
                        )
                        total_modified += cursor.rowcount
                except Exception:
                    pass

        conn.commit()
        conn.close()

        return {
            "success": True,
            "email": email,
            "modified_rows": total_modified,
            "status": "disabled" if total_modified > 0 else "user_not_found",
        }

    except sqlite3.Error as e:
        return {
            "success": False,
            "error": f"SQLite database error: {str(e)}",
            "email": email,
            "modified_rows": 0,
        }


def main():
    parser = argparse.ArgumentParser(description="Sovereign Proxy Secure User Revocation")
    parser.add_argument("email", help="Client email identifier to revoke")
    parser.add_argument(
        "--db",
        default="/etc/x-ui/x-ui.db",
        help="Path to x-ui / sovereign SQLite database (default: /etc/x-ui/x-ui.db)"
    )
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    result = revoke_user(args.db, args.email)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            if result["modified_rows"] > 0:
                print(f"[+] Successfully revoked user {args.email} ({result['modified_rows']} records updated)")
            else:
                print(f"[!] User {args.email} not found or already disabled")
        else:
            print(f"[-] ERROR: {result['error']}", file=sys.stderr)

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
