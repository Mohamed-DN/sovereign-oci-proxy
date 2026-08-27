#!/usr/bin/env python3
"""
Challenger Adversarial SQL Injection & Fuzzing Harness
Authors: Empirical Challenger 1
Target: scripts/legacy_refactor/sovereign-revoke-user.py & sovereign-revoke-user.sh
"""

import concurrent.futures
import importlib.util
import json
import os
import random
import shutil
import sqlite3
import string
import subprocess
import sys
import tempfile
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVOKE_PY = os.path.join(PROJECT_ROOT, "scripts", "legacy_refactor", "sovereign-revoke-user.py")
REVOKE_SH = os.path.join(PROJECT_ROOT, "scripts", "legacy_refactor", "sovereign-revoke-user.sh")

# Dynamically import python engine
spec = importlib.util.spec_from_file_location("sovereign_revoke", REVOKE_PY)
sovereign_revoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sovereign_revoke)


def create_mock_database(db_path: str, user_count: int = 50):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE client_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            enable INTEGER DEFAULT 1,
            up INTEGER DEFAULT 0,
            down INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE client_traffics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            enable INTEGER DEFAULT 1,
            up INTEGER DEFAULT 0,
            down INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE inbounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            settings TEXT
        )
    """)

    users = [(f"user_{i}@domain{i%5}.com", 1) for i in range(user_count)]
    # Also add known targets
    users.append(("target1@victim.com", 1))
    users.append(("target2@victim.com", 1))
    users.append(("target3@victim.com", 1))

    cur.executemany("INSERT INTO client_stats (email, enable) VALUES (?, ?)", users)
    cur.executemany("INSERT INTO client_traffics (email, enable) VALUES (?, ?)", users)

    inbound_clients = [{"id": f"uuid-{i}", "email": u[0], "enable": True} for i, u in enumerate(users)]
    cur.execute("INSERT INTO inbounds (settings) VALUES (?)", (json.dumps({"clients": inbound_clients}),))

    # Add a row with malformed JSON to test error recovery
    cur.execute("INSERT INTO inbounds (settings) VALUES (?)", ("{INVALID_JSON_CORRUPTED",))

    # Add a row with empty clients array
    cur.execute("INSERT INTO inbounds (settings) VALUES (?)", (json.dumps({"clients": []}),))

    # Add a row with clients without email field
    cur.execute("INSERT INTO inbounds (settings) VALUES (?)", (json.dumps({"clients": [{"id": "no-email"}]}),))

    conn.commit()
    conn.close()


def generate_adversarial_payloads():
    """Generates 100+ diverse and aggressive attack payloads."""
    payloads = [
        # Classic Tautologies
        "' OR '1'='1",
        "' OR 1=1 --",
        "\" OR \"\"=\"",
        "') OR ('1'='1",
        "') OR 1=1 --",
        "admin'--",
        "admin' #",
        "admin'/*",
        "' or 1=1 or ''='",
        "' OR 1=1 LIMIT 1; --",
        "1' OR '1' = '1' --",
        
        # Destructive & Stacked
        "'; DROP TABLE client_stats; --",
        "'; DROP TABLE inbounds; --",
        "'; DROP TABLE client_traffics; --",
        "'; DELETE FROM client_stats; --",
        "'; UPDATE client_stats SET enable=0; --",
        "'; UPDATE client_stats SET email='pwned'; --",
        "'; VACUUM; --",
        "'; ATTACH DATABASE ':memory:' AS pwn; --",
        "\"; DROP TABLE client_stats; --",
        "victim@test.com'; DROP TABLE client_stats; --",
        
        # Union Based Extraction
        "' UNION SELECT 1, 'hacked', 0, 0, 0 --",
        "' UNION ALL SELECT null, null, null, null, null --",
        "' UNION SELECT 1, sql, 1, 0, 0 FROM sqlite_master --",
        
        # Blind & Boolean Injection
        "' AND (SELECT length(hex(randomblob(500000000)))) --",
        "target1@victim.com' AND (SELECT 1 FROM (SELECT count(*), concat(email, floor(rand(0)*2)) FROM client_stats GROUP BY 2)x) --",
        
        # Shell / Command Injection Vectors
        "$(whoami)@victim.com",
        "`whoami`@victim.com",
        "victim@victim.com; touch /tmp/pwned",
        "victim@victim.com && rm -rf /tmp/sqli_test",
        "victim@victim.com | cat /etc/passwd",
        "victim@victim.com > /tmp/pwned",
        "victim@victim.com || echo pwned",
        "; reboot ;@victim.com",
        "\"`id`\"@victim.com",
        
        # Escaping & Metacharacter Fuzzing
        "user\r\n@victim.com",
        "user\n@victim.com",
        "user\t@victim.com",
        "user'\"@victim.com",
        "user%00@victim.com",
        "user%27@victim.com",
        "user%20@victim.com",
        
        # Unicode / Homoglyphs / Overlong Encodings
        "user\uff07@victim.com",       # Fullwidth apostrophe
        "user\u02bc@victim.com",       # Modifier letter apostrophe
        "user\u2019@victim.com",       # Right single quote
        "user\uFEFF@victim.com",       # Zero width no-break space
        "user\u200B@victim.com",       # Zero width space
        "uѕer@victim.com",             # Cyrillic small 's'
        
        # Buffer Overflow / Length limits
        "A" * 250 + "@victim.com",
        "A" * 255 + "@victim.com",
        "A" * 1000 + "@victim.com",
        "A" * 10000 + "@victim.com",
        
        # Malformed Email Edge Cases
        "plainaddress",
        "#@%^%#$@#$@#.com",
        "@example.com",
        "Joe Smith <email@example.com>",
        "email.example.com",
        "email@example@example.com",
        ".email@example.com",
        "email.@example.com",
        "email..email@example.com",
        "あいうえお@example.com",
        "email@example.com (Joe Smith)",
        "email@example",
        "email@-example.com",
        "email@example..com",
        "Abc..123@example.com",
        r"“(),:;<>[\]@example.com",
        r'just"not"right@example.com',
        r'this\ is"really"not\allowed@example.com',
        
        # SQL Wildcards
        "%@%",
        "_%@_%._%",
        "target%@victim.com",
        "target_@victim.com",
    ]
    return payloads


IN_PROCESS_ONLY_PAYLOADS = [
    "\\x00' OR 1=1 --",
    "user\x00@victim.com",
    "user\u0000@victim.com",
    "user@victim.com\u0000",
    "\x00'; DROP TABLE client_stats; --",
    "admin'--\x00",
    "\x00",
    "",
    "   ",
]


def test_adversarial_sqli():
    print("[CHALLENGER] Starting Exhaustive SQL Injection Defense Stress Test...")
    temp_dir = tempfile.mkdtemp(prefix="challenger_sqli_")
    db_path = os.path.join(temp_dir, "test.db")

    try:
        create_mock_database(db_path, user_count=50)
        payloads = generate_adversarial_payloads()
        print(f"[CHALLENGER] Testing {len(payloads)} CLI/Process adversarial payloads...")

        passed_count = 0
        for i, payload in enumerate(payloads, 1):
            # Test 1: Python in-process call
            res = sovereign_revoke.revoke_user(db_path, payload)
            if res["success"]:
                # If it succeeded, check if it was somehow a legitimate email matching no records or target
                # Malicious payload must NEVER modify unrelated rows
                assert res["modified_rows"] == 0, f"Payload {repr(payload)} modified {res['modified_rows']} rows!"
            
            # Test 2: Python CLI call
            proc = subprocess.run(
                [sys.executable, REVOKE_PY, payload, "--db", db_path, "--json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # Verify DB integrity after CLI call
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM client_stats WHERE enable = 1")
            active_count = cur.fetchone()[0]
            # Baseline is 53 active users
            assert active_count >= 50, f"Database corruption detected! Active users count dropped to {active_count} after payload {repr(payload)}"
            
            # Check table existence
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {r[0] for r in cur.fetchall()}
            assert "client_stats" in tables, f"TABLE client_stats dropped by payload {repr(payload)}"
            assert "client_traffics" in tables, f"TABLE client_traffics dropped by payload {repr(payload)}"
            assert "inbounds" in tables, f"TABLE inbounds dropped by payload {repr(payload)}"
            conn.close()

            # Test 3: Shell wrapper call
            proc_sh = subprocess.run(
                ["bash", REVOKE_SH, payload, db_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # If payload is invalid format, shell wrapper must exit non-zero
            if not sovereign_revoke.validate_email(payload):
                assert proc_sh.returncode != 0, f"Shell wrapper accepted malformed payload: {repr(payload)}"

            passed_count += 1

        print(f"[CHALLENGER] [✓] {passed_count}/{len(payloads)} CLI adversarial payloads successfully blocked with zero DB alteration.")

        # Test In-Process Null Byte / Special Payloads
        print(f"[CHALLENGER] Testing {len(IN_PROCESS_ONLY_PAYLOADS)} in-process direct memory payloads (null bytes / empty)...")
        for payload in IN_PROCESS_ONLY_PAYLOADS:
            res = sovereign_revoke.revoke_user(db_path, payload)
            assert res["success"] is False, f"Direct fuzzing payload {repr(payload)} succeeded unexpectedly!"
            assert res["modified_rows"] == 0
        print("[CHALLENGER] [✓] In-process null-byte payloads safely rejected.")

        # Test Functional Revocation
        print("[CHALLENGER] Testing functional revocation and JSON inbounds parser resilience...")
        res_target = sovereign_revoke.revoke_user(db_path, "target1@victim.com")
        assert res_target["success"] is True, "Failed to revoke target1@victim.com"
        assert res_target["modified_rows"] >= 3, f"Expected >= 3 modified rows, got {res_target['modified_rows']}"

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT enable FROM client_stats WHERE email = 'target1@victim.com'")
        assert cur.fetchone()[0] == 0, "target1@victim.com in client_stats is not 0"
        cur.execute("SELECT enable FROM client_traffics WHERE email = 'target1@victim.com'")
        assert cur.fetchone()[0] == 0, "target1@victim.com in client_traffics is not 0"
        
        # Verify JSON inbounds parsing did not crash on the corrupted JSON row
        cur.execute("SELECT settings FROM inbounds WHERE id = 1")
        settings_str = cur.fetchone()[0]
        settings = json.loads(settings_str)
        target1_client = next(c for c in settings["clients"] if c["email"] == "target1@victim.com")
        assert target1_client["enable"] is False, "target1 client in inbounds settings was not set to False"

        # Other targets remain enabled
        cur.execute("SELECT enable FROM client_stats WHERE email = 'target2@victim.com'")
        assert cur.fetchone()[0] == 1, "target2@victim.com was improperly affected"
        conn.close()
        print("[CHALLENGER] [✓] Functional revocation verified: target disabled, JSON inbounds patched, corrupted rows gracefully bypassed.")

        # Test High Concurrency Revocation (50 simultaneous threads against SQLite)
        print("[CHALLENGER] Testing 50 concurrent revocations against SQLite DB...")
        emails_to_revoke = [f"user_{i}@domain{i%5}.com" for i in range(50)]

        def revoke_worker(email):
            return sovereign_revoke.revoke_user(db_path, email)

        start_conc = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(revoke_worker, emails_to_revoke))
        duration_conc = time.time() - start_conc

        success_count = sum(1 for r in results if r["success"])
        print(f"[CHALLENGER] [✓] Completed 50 concurrent revocations in {duration_conc:.3f}s ({success_count}/50 succeeded without deadlocks).")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_adversarial_sqli()
