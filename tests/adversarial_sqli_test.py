#!/usr/bin/env python3
"""
Adversarial SQL Injection & Command Injection Stress Harness
Tests: scripts/legacy_refactor/sovereign-revoke-user.py and sovereign-revoke-user.sh
"""

import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_SCRIPT = os.path.join(WORKSPACE_ROOT, "scripts", "legacy_refactor", "sovereign-revoke-user.py")
SHELL_SCRIPT = os.path.join(WORKSPACE_ROOT, "scripts", "legacy_refactor", "sovereign-revoke-user.sh")

# Dynamically import the Python revocation module for in-process direct fuzzing
spec = importlib.util.spec_from_file_location("sovereign_revoke", PYTHON_SCRIPT)
sovereign_revoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sovereign_revoke)

SQLI_CLI_PAYLOADS = [
    # Classic Tautologies
    "' OR '1'='1",
    "' OR 1=1 --",
    "' OR 'a'='a",
    "\" OR \"1\"=\"1",
    "admin'--",
    "admin' #",
    "admin'/*",
    "' or 1=1 or ''='",

    # Destructive / Stacked Queries
    "'; DROP TABLE client_stats; --",
    "\"; DROP TABLE client_stats; --",
    "'; DROP TABLE inbounds; --",
    "'; DROP TABLE client_traffics; --",
    "'; DELETE FROM client_stats; --",
    "'; UPDATE client_stats SET enable=0; --",

    # Union & Extraction
    "' UNION SELECT 1, 'hacked', 0, 0, 0, 0 --",
    "' UNION ALL SELECT null, null, null, null --",

    # Quoting & Format Breaks
    "alice@sovereign.local' OR '1'='1",
    "alice@sovereign.local'; DROP TABLE client_stats; --",
    "alice@sovereign.local'--",
    "' OR email LIKE '%",
    "\" OR 1=1 --",
    "` OR 1=1 --",

    # Shell Metacharacters & Command Injections
    "alice@example.com; rm -rf /tmp/sqli_test",
    "$(cat /etc/passwd)@example.com",
    "`id`@example.com",
    "alice@example.com | echo hacked",
    "alice@example.com && whoami",
    "alice@example.com > /tmp/pwned",

    # Edge Cases & Format Violations
    "a" * 300 + "@example.com",  # Buffer overflow length (> 254 chars)
    "user@localhost",            # Invalid TLD
    "@missing-user.com",
    "user@.com",
    "user@com",
    "user\n@example.com",        # Newline injection
    "user\r\n@example.com",      # CRLF injection
]

DIRECT_IN_PROCESS_PAYLOADS = [
    "user\x00@example.com",      # NULL byte
    "user@example\x00.com",
    "\x00' OR 1=1 --",
    "",
    "   ",
    "'; DROP TABLE client_stats; --\x00",
    "admin'--\x00",
]


def init_test_db(db_path: str):
    """Initializes a realistic SQLite database with 3x-ui schemas and test data."""
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Legacy client_stats table
    cur.execute("""
        CREATE TABLE client_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            enable INTEGER DEFAULT 1,
            up INTEGER DEFAULT 0,
            down INTEGER DEFAULT 0
        )
    """)
    cur.executemany(
        "INSERT INTO client_stats (email, enable) VALUES (?, 1)",
        [
            ("alice@sovereign.local",),
            ("bob@sovereign.local",),
            ("charlie@victim.org",),
            ("admin@sovereign.internal",),
        ]
    )

    # 2. Modern client_traffics table
    cur.execute("""
        CREATE TABLE client_traffics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            enable INTEGER DEFAULT 1,
            up INTEGER DEFAULT 0,
            down INTEGER DEFAULT 0
        )
    """)
    cur.executemany(
        "INSERT INTO client_traffics (email, enable) VALUES (?, 1)",
        [
            ("alice@sovereign.local",),
            ("bob@sovereign.local",),
            ("charlie@victim.org",),
            ("admin@sovereign.internal",),
        ]
    )

    # 3. JSON Inbounds table
    cur.execute("""
        CREATE TABLE inbounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT,
            settings TEXT
        )
    """)
    inbounds_settings = {
        "clients": [
            {"id": "uuid-alice", "email": "alice@sovereign.local", "enable": True},
            {"id": "uuid-bob", "email": "bob@sovereign.local", "enable": True},
            {"id": "uuid-charlie", "email": "charlie@victim.org", "enable": True},
        ]
    }
    cur.execute(
        "INSERT INTO inbounds (tag, settings) VALUES (?, ?)",
        ("vless-inbound", json.dumps(inbounds_settings))
    )

    conn.commit()
    conn.close()


def verify_database_integrity(db_path: str, expected_alice_enabled: bool = True):
    """Verifies that non-target users remain enabled and tables are intact."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    assert "client_stats" in tables, "TABLE client_stats WAS DROPPED!"
    assert "client_traffics" in tables, "TABLE client_traffics WAS DROPPED!"
    assert "inbounds" in tables, "TABLE inbounds WAS DROPPED!"

    # Check Bob, Charlie, Admin are intact and enabled
    for email in ["bob@sovereign.local", "charlie@victim.org", "admin@sovereign.internal"]:
        cur.execute("SELECT enable FROM client_stats WHERE email = ?", (email,))
        row = cur.fetchone()
        assert row is not None and row[0] == 1, f"User {email} in client_stats was corrupted or disabled!"

        cur.execute("SELECT enable FROM client_traffics WHERE email = ?", (email,))
        row = cur.fetchone()
        assert row is not None and row[0] == 1, f"User {email} in client_traffics was corrupted or disabled!"

    # Check Alice
    cur.execute("SELECT enable FROM client_stats WHERE email = 'alice@sovereign.local'")
    alice_row = cur.fetchone()
    expected_val = 1 if expected_alice_enabled else 0
    assert alice_row is not None and alice_row[0] == expected_val, f"Alice state mismatch: got {alice_row[0]}, expected {expected_val}"

    conn.close()


def run_tests():
    temp_dir = tempfile.mkdtemp(prefix="sovereign_sqli_test_")
    db_path = os.path.join(temp_dir, "test_xui.db")

    try:
        print(f"[*] Initializing test database at {db_path}...")
        init_test_db(db_path)
        verify_database_integrity(db_path, expected_alice_enabled=True)
        print("[+] Test database initialized and baseline integrity verified.")

        # --- Phase 1: Test Python Script CLI with SQLi Payloads ---
        print("\n" + "="*80)
        print("[*] Phase 1: Adversarial SQL Injection CLI against sovereign-revoke-user.py")
        print("="*80)

        for i, payload in enumerate(SQLI_CLI_PAYLOADS, 1):
            cmd = [sys.executable, PYTHON_SCRIPT, payload, "--db", db_path, "--json"]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Re-verify DB integrity after each payload
            verify_database_integrity(db_path, expected_alice_enabled=True)

            try:
                out_data = json.loads(proc.stdout)
                # Ensure no rows were modified by an injection payload
                assert out_data.get("modified_rows", 0) == 0, f"Payload '{payload}' modified {out_data['modified_rows']} rows!"
                assert not out_data.get("success", False), f"Payload '{payload}' returned success=True!"
            except json.JSONDecodeError:
                assert proc.returncode != 0

            print(f"  [{i:02d}/{len(SQLI_CLI_PAYLOADS)}] PASS: Payload '{payload[:40]}' safely rejected.")

        # --- Phase 2: In-Process Direct Function Fuzzing (Null Bytes & Malformed Strings) ---
        print("\n" + "="*80)
        print("[*] Phase 2: In-Process Direct Function Fuzzing (Null Bytes & Boundary Cases)")
        print("="*80)

        for i, payload in enumerate(DIRECT_IN_PROCESS_PAYLOADS, 1):
            res = sovereign_revoke.revoke_user(db_path, payload)
            assert res["success"] is False, f"Direct fuzzing payload {repr(payload)} succeeded unexpectedly!"
            assert res["modified_rows"] == 0
            verify_database_integrity(db_path, expected_alice_enabled=True)
            print(f"  [{i:02d}/{len(DIRECT_IN_PROCESS_PAYLOADS)}] PASS: In-process payload {repr(payload)[:40]} safely rejected.")

        # --- Phase 3: Test Shell Wrapper with SQLi Payloads ---
        print("\n" + "="*80)
        print("[*] Phase 3: Adversarial SQL/Command Injection against sovereign-revoke-user.sh")
        print("="*80)

        for i, payload in enumerate(SQLI_CLI_PAYLOADS, 1):
            cmd = ["bash", SHELL_SCRIPT, payload, db_path]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # The shell script must exit with error code 1 for all invalid formats
            assert proc.returncode != 0, f"Shell wrapper exited with code 0 for malicious payload: '{payload}'"
            verify_database_integrity(db_path, expected_alice_enabled=True)

            print(f"  [{i:02d}/{len(SQLI_CLI_PAYLOADS)}] PASS: Shell script safely rejected payload '{payload[:40]}'")

        # --- Phase 4: Legitimate User Revocation ---
        print("\n" + "="*80)
        print("[*] Phase 4: Legitimate User Revocation (Functional Correctness)")
        print("="*80)

        cmd = [sys.executable, PYTHON_SCRIPT, "alice@sovereign.local", "--db", db_path, "--json"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.returncode == 0, f"Valid revocation failed with exit code {proc.returncode}"
        res = json.loads(proc.stdout)
        assert res["success"] is True
        assert res["modified_rows"] >= 3  # client_stats + client_traffics + inbounds
        assert res["status"] == "disabled"

        # Verify Alice is disabled but Bob/Charlie/Admin are untouched
        verify_database_integrity(db_path, expected_alice_enabled=False)
        print("[+] Successfully verified that Alice was revoked while other accounts remained untouched.")

        # Revoking Alice again should succeed safely without affecting other users
        cmd2 = [sys.executable, PYTHON_SCRIPT, "alice@sovereign.local", "--db", db_path, "--json"]
        proc2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc2.returncode == 0
        verify_database_integrity(db_path, expected_alice_enabled=False)

        print("[+] Repeated execution verified safe and non-destructive.")
        print("\n" + "="*80)
        print("🎉 ALL 77+ ADVERSARIAL SQL INJECTION & SHELL EXPLOIT TESTS PASSED WITH 100% IMMUNITY!")
        print("="*80)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
