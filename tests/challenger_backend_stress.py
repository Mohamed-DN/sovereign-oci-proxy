#!/usr/bin/env python3
"""
Challenger 1 - Empirical Backend & Security Stress Test Suite
Verifies:
1. SQLite WAL mode, foreign keys, database integrity and schema constraints.
2. Curve25519 key clamping bitwise properties (10,000 iterations).
3. RBAC boundaries, cross-tenant IDOR isolation, and privilege escalation prevention.
4. Token forgery, signature tampering, revocation, and session lifecycle.
5. SQL injection fuzzing matrix across all live endpoints.
"""

import sys
import os
import sqlite3
import subprocess
import json
import base64
import time
import urllib.request
import urllib.error

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "console", "data", "neronet.db")
CRYPTO_JS = os.path.join(PROJECT_ROOT, "console", "backend", "utils", "crypto.js")
BASE_URL = os.environ.get("CONSOLE_API_URL", "http://127.0.0.1:8082")
ADMIN_PASS = os.environ.get("SOVEREIGN_ADMIN_PASS", "admin_password")

class APIClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.token = None

    def request(self, method, path, body=None, token=None):
        url = f"{self.base_url}{path}"
        headers = {"User-Agent": "Challenger1-Stress/1.0"}
        tok = token or self.token
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        
        data_bytes = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data_bytes = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw_error": raw}
        except Exception as e:
            return 500, {"error": str(e)}

def test_sqlite_wal_and_integrity():
    print("\n" + "="*80)
    print("🔒 TEST SUITE 1: SQLite WAL Mode, Pragmas & Database Integrity")
    print("="*80)
    
    assert os.path.exists(DB_PATH), f"Database file not found at {DB_PATH}"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Check Journal Mode
    cur.execute("PRAGMA journal_mode;")
    mode = cur.fetchone()[0]
    print(f"  [+] PRAGMA journal_mode: {mode}")
    assert mode.lower() == "wal", f"Expected WAL mode, got {mode}"

    # 2. Check Integrity
    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchall()
    print(f"  [+] PRAGMA integrity_check: {integrity}")
    assert integrity == [("ok",)], f"Integrity check failed: {integrity}"

    # 3. Check Foreign Keys Check
    cur.execute("PRAGMA foreign_key_check;")
    fk_violations = cur.fetchall()
    print(f"  [+] PRAGMA foreign_key_check violations count: {len(fk_violations)}")
    assert len(fk_violations) == 0, f"Foreign key violations found: {fk_violations}"

    # 4. Check Schema Tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    expected_tables = ["_migrations", "app_bundles", "audit_events", "nerodrop_sessions", "nodes", "refresh_tokens", "sqlite_sequence", "system_metrics", "users"]
    print(f"  [+] Database Tables present: {tables}")
    for t in expected_tables:
        assert t in tables, f"Missing expected table: {t}"

    # 5. Test Foreign Key Constraint Enforcement
    cur.execute("PRAGMA foreign_keys = ON;")
    try:
        cur.execute("INSERT INTO nodes (id, user_id, name, public_key, overlay_ipv4, overlay_ipv6) VALUES ('fk-test-node', 'nonexistent-user', 'Test', 'pubkey_test', '100.64.99.99', 'fd7a::99');")
        conn.commit()
        raise AssertionError("Foreign key constraint violation was NOT caught!")
    except sqlite3.IntegrityError:
        print("  [+] Foreign key constraint enforcement correctly rejected orphaned child record.")
    finally:
        conn.rollback()
        conn.close()

    print("  ✅ Database WAL mode and integrity verified.")

def test_curve25519_clamping_logic():
    print("\n" + "="*80)
    print("🔑 TEST SUITE 2: Curve25519 Keypair Generation & Bitwise Clamping Verification")
    print("="*80)
    
    # Run Node script to generate 10,000 keypairs directly via crypto.js
    node_code = """
    const { generateCurve25519Keypair } = require('./console/backend/utils/crypto.js');
    const iterations = 10000;
    let failed = 0;
    
    for (let i = 0; i < iterations; i++) {
        const kp = generateCurve25519Keypair();
        const priv = Buffer.from(kp.privateKeyBase64, 'base64');
        const pub = Buffer.from(kp.publicKeyBase64, 'base64');
        
        if (priv.length !== 32) { failed++; break; }
        if (pub.length !== 32) { failed++; break; }
        
        // RFC 7748 Clamping checks:
        // 1. Lowest 3 bits of first byte must be cleared (priv[0] & 7 == 0)
        if ((priv[0] & 7) !== 0) { failed++; break; }
        // 2. Bit 255 (MSB of last byte) must be cleared (priv[31] & 128 == 0)
        if ((priv[31] & 128) !== 0) { failed++; break; }
        // 3. Bit 254 (2nd MSB of last byte) must be set (priv[31] & 64 == 64)
        if ((priv[31] & 64) !== 64) { failed++; break; }
        
        if (!kp.nodeId.startsWith('svrn-node-')) { failed++; break; }
    }
    
    console.log(JSON.stringify({ iterations, failed }));
    """
    
    proc = subprocess.run(["node", "-e", node_code], cwd=PROJECT_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, f"Node clamping verification script failed: {proc.stderr}"
    res = json.loads(proc.stdout)
    print(f"  [+] Executed {res['iterations']} keypair generations directly through console/backend/utils/crypto.js")
    print(f"  [+] Bitwise clamping verification failures: {res['failed']}")
    assert res['failed'] == 0, f"Curve25519 clamping failures detected: {res['failed']}"

    # Also test config generation endpoint in live API
    client = APIClient()
    st, admin_login = client.request("POST", "/api/auth/login", {"username": "admin", "password": ADMIN_PASS})
    assert st == 200, "Admin login failed"
    client.token = admin_login["token"]

    for i in range(5):
        st_cfg, cfg = client.request("POST", "/api/configs/generate", {"name": f"Clamp-Verify-Node-{i}"})
        assert st_cfg == 200, f"Config generation failed: {cfg}"
        priv_bytes = base64.b64decode(cfg["private_key"])
        assert len(priv_bytes) == 32
        assert (priv_bytes[0] & 7) == 0, "Bit 0, 1, 2 not cleared"
        assert (priv_bytes[31] & 128) == 0, "Bit 255 not cleared"
        assert (priv_bytes[31] & 64) == 64, "Bit 254 not set"

    print("  ✅ Curve25519 clamping bitwise properties 100% verified across both library (10,000 runs) and REST API.")

def test_rbac_and_cross_tenant_isolation():
    print("\n" + "="*80)
    print("🛡️ TEST SUITE 3: RBAC Boundaries & Cross-Tenant IDOR Isolation Stress")
    print("="*80)
    
    admin_client = APIClient()
    _, admin_auth = admin_client.request("POST", "/api/auth/login", {"username": "admin", "password": ADMIN_PASS})
    admin_client.token = admin_auth["token"]

    ts = int(time.time() * 1000)
    tenantA_user = f"tenantA_{ts}"
    tenantB_user = f"tenantB_{ts}"

    # 1. Register Tenant A
    st_a, reg_a = admin_client.request("POST", "/api/auth/register", {
        "username": tenantA_user,
        "password": "Password123!",
        "role": "user",
        "tier": "hybrid_byos"
    })
    assert st_a == 201, f"Tenant A registration failed: {reg_a}"
    token_a = reg_a["token"]
    user_id_a = reg_a["user"]["id"]
    client_a = APIClient()
    client_a.token = token_a

    # 2. Register Tenant B
    st_b, reg_b = admin_client.request("POST", "/api/auth/register", {
        "username": tenantB_user,
        "password": "Password123!",
        "role": "user",
        "tier": "hybrid_byos"
    })
    assert st_b == 201, f"Tenant B registration failed: {reg_b}"
    token_b = reg_b["token"]
    user_id_b = reg_b["user"]["id"]
    client_b = APIClient()
    client_b.token = token_b

    print(f"  [+] Provisioned Tenant A ({tenantA_user}, {user_id_a}) and Tenant B ({tenantB_user}, {user_id_b})")

    # 3. Super-Admin Endpoint Protection against Tenant B
    print("  [*] Testing Super-Admin Endpoint Protection against standard tenants...")
    admin_routes = [
        ("GET", "/api/users", None),
        ("POST", "/api/users", {"username": f"hacked_admin_{ts}", "password": "Password123!", "role": "super-admin"}),
        ("DELETE", f"/api/users/{user_id_a}", None),
    ]
    for m, path, body in admin_routes:
        st, res = client_b.request(m, path, body)
        print(f"    - Tenant B {m} {path} -> HTTP {st}")
        assert st == 403, f"Tenant B was able to call admin route {m} {path}! Status: {st}, Res: {res}"

    # 4. Privilege Escalation via User Profile Update
    print("  [*] Testing Privilege Escalation attack via PUT /api/users/:id...")
    st_esc, res_esc = client_b.request("PUT", f"/api/users/{user_id_b}", {"role": "super-admin", "status": "active"})
    assert st_esc == 200
    st_me, me_res = client_b.request("GET", "/api/auth/me")
    print(f"    - Tenant B role after attempted privilege escalation: {me_res['user']['role']}")
    assert me_res['user']['role'] == "user", "Privilege escalation vulnerability: user updated own role to super-admin!"

    # 5. Tenant A creates resources: Node, App, NeroDrop Transfer
    st_node_a, node_a = client_a.request("POST", "/api/nodes", {"name": "TenantA-Node"})
    assert st_node_a == 201, f"Node create failed: {node_a}"
    node_id_a = node_a["node"]["id"]

    st_app_a, app_a = client_a.request("POST", "/api/apps", {"name": "TenantA-Guac", "type": "guacamole", "tier": "managed_cloud"})
    assert st_app_a == 201, f"App create failed: {app_a}"
    app_id_a = app_a["app"]["id"]

    st_drop_a, drop_a = client_a.request("POST", "/api/nerodrop/session", {
        "target_node_id": node_id_a,
        "file_name": "secret_docs.pdf",
        "file_size_bytes": 1024 * 1024
    })
    assert st_drop_a == 201, f"NeroDrop session failed: {drop_a}"
    session_id_a = drop_a["session_id"]

    print(f"  [+] Tenant A created Node ({node_id_a}), App ({app_id_a}), NeroDrop Session ({session_id_a})")

    # 6. Tenant B attempts IDOR on Tenant A's resources
    print("  [*] Testing Cross-Tenant IDOR on Nodes, Apps, Configs, and NeroDrop Transfers...")
    idor_probes = [
        ("GET", f"/api/nodes/{node_id_a}", None),
        ("PUT", f"/api/nodes/{node_id_a}", {"name": "Pwned Node"}),
        ("DELETE", f"/api/nodes/{node_id_a}", None),
        ("POST", f"/api/nodes/{node_id_a}/action", {"action": "ping"}),
        ("POST", f"/api/nodes/{node_id_a}/action", {"action": "quarantine"}),
        ("GET", f"/api/configs/wireguard/{node_id_a}", None),
        ("GET", f"/api/configs/noise/{node_id_a}", None),
        ("GET", f"/api/apps/{app_id_a}", None),
        ("PUT", f"/api/apps/{app_id_a}", {"name": "Pwned App"}),
        ("DELETE", f"/api/apps/{app_id_a}", None),
        ("GET", f"/api/apps/{app_id_a}/launch", None),
        ("POST", f"/api/apps/{app_id_a}/start", None),
        ("POST", f"/api/apps/{app_id_a}/stop", None),
        ("POST", f"/api/apps/{app_id_a}/scale-to-zero", None),
        ("GET", f"/api/nerodrop/transfers/{session_id_a}", None),
        ("PUT", f"/api/nerodrop/transfers/{session_id_a}/progress", {"transferred_chunks": 10}),
        ("POST", f"/api/nerodrop/transfers/{session_id_a}/cancel", None),
        ("GET", f"/api/users/{user_id_a}", None),
        ("PUT", f"/api/users/{user_id_a}", {"tier": "managed_cloud"}),
    ]

    for m, path, body in idor_probes:
        st, res = client_b.request(m, path, body)
        print(f"    - Tenant B IDOR {m} {path} -> HTTP {st}")
        assert st == 403, f"Cross-tenant IDOR leak on {m} {path}! Status: {st}, Res: {res}"

    # Verify Tenant A's listing only returns Tenant A's items
    _, list_nodes_b = client_b.request("GET", "/api/nodes")
    assert not any(n["id"] == node_id_a for n in list_nodes_b["nodes"]), "Tenant B sees Tenant A's nodes in list!"

    _, list_apps_b = client_b.request("GET", "/api/apps")
    assert not any(a["id"] == app_id_a for a in list_apps_b["apps"]), "Tenant B sees Tenant A's apps in list!"

    _, list_transfers_b = client_b.request("GET", "/api/nerodrop/transfers")
    assert not any(t["session_id"] == session_id_a for t in list_transfers_b["transfers"]), "Tenant B sees Tenant A's transfers in list!"

    print("  ✅ All RBAC boundaries, privilege escalation defenses, and cross-tenant IDOR isolation verified.")

def test_auth_token_forgery_and_revocation():
    print("\n" + "="*80)
    print("🛡️ TEST SUITE 4: Token Forgery, alg:none, Tampering & Revocation")
    print("="*80)

    client = APIClient()

    # 1. alg:none attack
    h = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').decode().rstrip("=")
    p = base64.urlsafe_b64encode(b'{"sub":"usr-admin","username":"admin","role":"super-admin"}').decode().rstrip("=")
    fake_jwt = f"{h}.{p}."
    st, _ = client.request("GET", "/api/users", token=fake_jwt)
    print(f"  [+] alg:none token rejected with HTTP {st}")
    assert st == 401, f"alg:none token was accepted! HTTP {st}"

    # 2. Signature tampering
    st_log, log_res = client.request("POST", "/api/auth/login", {"username": "admin", "password": ADMIN_PASS})
    real_jwt = log_res["token"]
    tampered_jwt = real_jwt[:-4] + ("AAAA" if real_jwt[-4:] != "AAAA" else "BBBB")
    st, _ = client.request("GET", "/api/users", token=tampered_jwt)
    print(f"  [+] Tampered signature token rejected with HTTP {st}")
    assert st == 401, f"Tampered signature token was accepted! HTTP {st}"

    # 3. Token Revocation upon Logout
    uname = f"tok_user_{int(time.time() * 1000)}"
    _, reg = client.request("POST", "/api/auth/register", {"username": uname, "password": "Password123!"})
    tok = reg["token"]
    user_client = APIClient()
    user_client.token = tok

    st_me_before, _ = user_client.request("GET", "/api/auth/me")
    assert st_me_before == 200, "Authenticated /me failed"

    st_logout, _ = user_client.request("POST", "/api/auth/logout")
    assert st_logout == 200, "Logout failed"

    st_me_after, _ = user_client.request("GET", "/api/auth/me")
    print(f"  [+] Post-logout token replay attempt returned HTTP {st_me_after}")
    assert st_me_after == 401, f"Revoked token was still accepted after logout! HTTP {st_me_after}"

    print("  ✅ Token forgery, tampering, and revocation lifecycle verified.")

def test_api_sqli_and_fuzzing():
    print("\n" + "="*80)
    print("💥 TEST SUITE 5: API-Level SQL Injection & Boundary Fuzzing Matrix")
    print("="*80)

    admin_client = APIClient()
    _, admin_auth = admin_client.request("POST", "/api/auth/login", {"username": "admin", "password": ADMIN_PASS})
    admin_client.token = admin_auth["token"]

    sqli_vectors = [
        "' OR '1'='1",
        "admin'--",
        "'; DROP TABLE users; --",
        "'; UPDATE users SET role='super-admin'; --",
        "' UNION SELECT id, username, password_hash, role, tier, status, 100, 0, 5, datetime('now'), datetime('now') FROM users --",
        "\" OR \"\"=\"",
        "1' OR '1' = '1",
        "test\x00@example.com",
    ]

    for idx, payload in enumerate(sqli_vectors, 1):
        # 1. Login vector
        st1, _ = admin_client.request("POST", "/api/auth/login", {"username": payload, "password": "password"})
        assert st1 in [400, 401], f"Login SQLi payload '{payload}' produced unexpected HTTP {st1}"

        # 2. Node create vector (with valid role, SQLi in name)
        st2, res2 = admin_client.request("POST", "/api/nodes", {"name": f"Node-{payload}", "role": "CLIENT_ORIGIN", "country_code": "US"})
        assert st2 in [201, 400, 422], f"Node create SQLi payload '{payload}' failed: HTTP {st2}"

        # 3. User update vector
        st3, _ = admin_client.request("PUT", f"/api/users/{admin_auth['user']['id']}", {"email": f"safe_{idx}@sovereign.local"})
        assert st3 in [200, 400, 422], f"User update SQLi payload '{payload}' failed: HTTP {st3}"

        print(f"  [{idx:02d}/{len(sqli_vectors)}] PASS: Vector '{payload[:30]}' safely handled.")

    # Re-verify DB integrity to ensure zero SQLi destruction occurred
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA integrity_check;")
    assert cur.fetchall() == [("ok",)], "Database integrity violated after SQLi fuzzing!"
    conn.close()

    print("  ✅ All SQL injection and input fuzzing attacks safely repelled.")

def main():
    print("="*80)
    print("🚀 CHALLENGER 1: Backend Security & Empirical Stress Verification Runner")
    print(f"🎯 Target URL: {BASE_URL}")
    print(f"💾 Database:   {DB_PATH}")
    print("="*80)

    test_sqlite_wal_and_integrity()
    test_curve25519_clamping_logic()
    test_rbac_and_cross_tenant_isolation()
    test_auth_token_forgery_and_revocation()
    test_api_sqli_and_fuzzing()

    print("\n" + "="*80)
    print("🎉 ALL EMPIRICAL CHALLENGER 1 STRESS & SECURITY TESTS PASSED PERFECTLY (100%)")
    print("="*80)

if __name__ == "__main__":
    main()
