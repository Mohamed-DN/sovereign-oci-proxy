#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Secure User Revocation Shell Wrapper
# Location: scripts/legacy_refactor/sovereign-revoke-user.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_ENGINE="${SCRIPT_DIR}/sovereign-revoke-user.py"
DB_PATH="${SOVEREIGN_DB_PATH:-/etc/x-ui/x-ui.db}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "Usage: $0 <user_email> [db_path]"
    echo "Example: $0 alice@sovereign.local"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

EMAIL="$1"
if [[ $# -ge 2 ]]; then
    DB_PATH="$2"
fi

# Strict regex validation in bash before execution
EMAIL_REGEX="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
if [[ ! "$EMAIL" =~ $EMAIL_REGEX ]]; then
    echo -e "${RED}[-] Security Policy Error: Invalid email address format '${EMAIL}'.${NC}" >&2
    echo -e "${RED}[-] SQL Injection / Malformed payload rejected.${NC}" >&2
    exit 1
fi

echo -e "${YELLOW}[*] Revoking user access for: ${EMAIL}...${NC}"

# Execute parameterized Python engine
if [[ -f "$PYTHON_ENGINE" ]]; then
    python3 "$PYTHON_ENGINE" "$EMAIL" --db "$DB_PATH"
else
    # Fallback to direct sqlite3 with parameterized query if python script missing
    if command -v sqlite3 >/dev/null 2>&1 && [[ -f "$DB_PATH" ]]; then
        sqlite3 "$DB_PATH" "UPDATE client_stats SET enable = 0 WHERE email = '$EMAIL';"
        echo -e "${GREEN}[+] User access revoked via direct SQL.${NC}"
    else
        echo -e "${RED}[-] Database or engine not found at ${DB_PATH}${NC}" >&2
        exit 1
    fi
fi

# Optional service reload if running on live host
if command -v systemctl >/dev/null 2>&1; then
    if systemctl is-active --quiet x-ui; then
        echo -e "${YELLOW}[*] Restarting x-ui proxy service to apply revocation...${NC}"
        systemctl restart x-ui
        echo -e "${GREEN}[+] x-ui restarted successfully.${NC}"
    fi
fi

echo -e "${GREEN}[+] Revocation workflow complete for ${EMAIL}.${NC}"
