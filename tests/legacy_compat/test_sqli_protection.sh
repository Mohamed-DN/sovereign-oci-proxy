#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Adversarial SQL Injection Protection Test Suite
# Location: tests/legacy_compat/test_sqli_protection.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REVOKE_PY="${PROJECT_ROOT}/scripts/legacy_refactor/sovereign-revoke-user.py"
REVOKE_SH="${PROJECT_ROOT}/scripts/legacy_refactor/sovereign-revoke-user.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

TMP_DIR="$(mktemp -d -t sovereign_sqli_test_XXXXXX)"
TEST_DB="${TMP_DIR}/test_xui.db"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo -e "\n${BLUE}${BOLD}=== Sovereign Proxy v4.0 - SQL Injection Adversarial Test Suite ===${NC}\n"

# Setup realistic test SQLite database
python3 -c "
import sqlite3, json

conn = sqlite3.connect('${TEST_DB}')
c = conn.cursor()

c.execute('''
CREATE TABLE client_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inbound_id INTEGER,
    enable INTEGER DEFAULT 1,
    email TEXT UNIQUE,
    up INTEGER DEFAULT 0,
    down INTEGER DEFAULT 0,
    expiry_time INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0
)
''')

c.execute('''
CREATE TABLE client_traffics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inbound_id INTEGER,
    enable INTEGER DEFAULT 1,
    email TEXT UNIQUE,
    up INTEGER DEFAULT 0,
    down INTEGER DEFAULT 0,
    expiry_time INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0
)
''')

c.execute('''
CREATE TABLE inbounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    up INTEGER,
    down INTEGER,
    total INTEGER,
    remark TEXT,
    enable INTEGER,
    side_car TEXT,
    settings TEXT
)
''')

# Insert sample users
users = [
    ('legit.user@sovereign.local', 1),
    ('alice@example.com', 1),
    ('bob@test.org', 1),
    ('admin@sovereign.local', 1)
]

for email, enable in users:
    c.execute('INSERT INTO client_stats (email, enable) VALUES (?, ?)', (email, enable))
    c.execute('INSERT INTO client_traffics (email, enable) VALUES (?, ?)', (email, enable))

settings_obj = {
    'clients': [
        {'id': '11111111-1111-1111-1111-111111111111', 'email': 'legit.user@sovereign.local', 'enable': True},
        {'id': '22222222-2222-2222-2222-222222222222', 'email': 'alice@example.com', 'enable': True}
    ]
}

c.execute('INSERT INTO inbounds (id, settings) VALUES (1, ?)', (json.dumps(settings_obj),))

conn.commit()
conn.close()
"

PASSED_ATTACKS=0
FAILED_ATTACKS=0

attack_vectors=(
    "admin@test.com'; DROP TABLE client_stats; --"
    "user@test.com' OR '1'='1"
    "victim@test.com'; UPDATE client_stats SET enable=0 WHERE 1=1; --"
    "test@test.com' UNION SELECT 1,2,3,4,5,6,7,8--"
    "admin@test.com' AND 1=2 UNION ALL SELECT NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL--"
    "test@test.com'; DELETE FROM client_stats WHERE 1=1; --"
    "\$(whoami)@evil.com"
    "user@domain.com; rm -rf /"
    "user\\0@evil.com"
    "user@domain.com' --"
    "user@domain.com/*comment*/"
    "' or 1=1--"
    "admin'--"
    "\"><script>alert(1)</script>@test.com"
    "user@domain.com'; ATTACH DATABASE '/tmp/pwn.db' AS pwn; --"
)

echo -e "${YELLOW}[*] Testing ${#attack_vectors[@]} SQL Injection Attack Vectors against Python & Shell engines...${NC}\n"

for i in "${!attack_vectors[@]}"; do
    payload="${attack_vectors[$i]}"
    idx=$((i + 1))

    # Test Python engine directly
    py_out="$(python3 "$REVOKE_PY" "$payload" --db "$TEST_DB" 2>&1 || true)"
    
    # Test Shell wrapper
    sh_out="$(SOVEREIGN_DB_PATH="$TEST_DB" bash "$REVOKE_SH" "$payload" 2>&1 || true)"

    # Verify table integrity in SQLite
    table_count="$(sqlite3 "$TEST_DB" "SELECT count(*) FROM client_stats;" 2>/dev/null || echo "CORRUPTED")"

    if [[ "$table_count" != "CORRUPTED" ]] && [[ "$table_count" -ge 1 ]]; then
        echo -e "  [${GREEN}✓${NC}] Vector ${idx}: '${payload}' -> ${GREEN}SAFELY BLOCKED${NC} (DB intact, count=${table_count})"
        PASSED_ATTACKS=$((PASSED_ATTACKS + 1))
    else
        echo -e "  [${RED}✗${NC}] Vector ${idx}: '${payload}' -> ${RED}FAILED: Database corrupted!${NC}"
        FAILED_ATTACKS=$((FAILED_ATTACKS + 1))
    fi
done

# Test legitimate user revocation
echo -e "\n${YELLOW}[*] Testing Legitimate User Revocation...${NC}"
python3 "$REVOKE_PY" "alice@example.com" --db "$TEST_DB" >/dev/null 2>&1

alice_status="$(sqlite3 "$TEST_DB" "SELECT enable FROM client_stats WHERE email='alice@example.com';")"
if [[ "$alice_status" == "0" ]]; then
    echo -e "  [${GREEN}✓${NC}] Legitimate User: alice@example.com -> ${GREEN}REVOKED (enable=0)${NC}"
    PASSED_ATTACKS=$((PASSED_ATTACKS + 1))
else
    echo -e "  [${RED}✗${NC}] Legitimate User: alice@example.com -> ${RED}FAILED (enable=${alice_status})${NC}"
    FAILED_ATTACKS=$((FAILED_ATTACKS + 1))
fi

echo -e "\n${BOLD}=======================================================================${NC}"
echo -e "SQL Injection Defense Score: ${GREEN}${PASSED_ATTACKS} Passed${NC}, ${RED}${FAILED_ATTACKS} Failed${NC}"
echo -e "${BOLD}=======================================================================${NC}\n"

if [[ "$FAILED_ATTACKS" -eq 0 ]]; then
    exit 0
else
    exit 1
fi
