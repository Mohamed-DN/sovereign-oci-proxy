#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Zero-Plaintext Secret Scanner Test Suite
# Location: tests/legacy_compat/test_secret_scanner.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "\n${BLUE}${BOLD}=== Sovereign Proxy v4.0 - Zero-Plaintext Secret Security Scan ===${NC}\n"

TARGET_DIRS=(
    "${PROJECT_ROOT}/scripts/legacy_refactor"
    "${PROJECT_ROOT}/configs"
    "${PROJECT_ROOT}/cmd/sovereign-security-daemon"
    "${PROJECT_ROOT}/docker"
)

VIOLATIONS=0
CHECK_COUNT=0

check_pattern() {
    local pattern_name="$1"
    local regex="$2"
    local dir="$3"

    CHECK_COUNT=$((CHECK_COUNT + 1))
    local matches
    matches="$(grep -rnE "$regex" "$dir" 2>/dev/null | grep -v "test_secret_scanner.sh" | grep -v "secrets.sh" | grep -v "example" || true)"

    if [[ -n "$matches" ]]; then
        echo -e "  [${RED}✗${NC}] ${pattern_name} in ${dir}: ${RED}VIOLATION DETECTED${NC}"
        echo "$matches" | head -n 3 | sed 's/^/      /'
        VIOLATIONS=$((VIOLATIONS + 1))
    else
        echo -e "  [${GREEN}✓${NC}] ${pattern_name} in $(basename "$dir"): ${GREEN}CLEAN (0 secrets leaked)${NC}"
    fi
}

for dir in "${TARGET_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        check_pattern "Hardcoded AWS Secret Key" "(AKIA[0-9A-Z]{16}|aws_secret_access_key\s*=\s*['\"][0-9a-zA-Z/+]{40}['\"])" "$dir"
        check_pattern "Hardcoded RSA/EC Private Key" "-----BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY-----" "$dir"
        check_pattern "Hardcoded DuckDNS Live Token" "duckdns\.org/update\?domains=[a-zA-Z0-9]+&token=[a-f0-9]{8}-[a-f0-9]{4}" "$dir"
        check_pattern "Hardcoded Generic API Token" "(api_key|secret_token|ntfy_token)\s*=\s*['\"][0-9a-zA-Z_-]{20,}['\"]" "$dir"
    fi
done

echo -e "\n${BOLD}=======================================================================${NC}"
echo -e "Secret Audit Summary: ${GREEN}$((CHECK_COUNT - VIOLATIONS)) Checks Passed${NC}, ${RED}${VIOLATIONS} Violations${NC}"
echo -e "${BOLD}=======================================================================${NC}\n"

if [[ "$VIOLATIONS" -eq 0 ]]; then
    exit 0
else
    exit 1
fi
