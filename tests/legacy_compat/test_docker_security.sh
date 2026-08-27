#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Rootless Container Security Verification Suite
# Location: tests/legacy_compat/test_docker_security.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

DOCKERFILE="${PROJECT_ROOT}/docker/Dockerfile"
COMPOSE_FILE="${PROJECT_ROOT}/docker/docker-compose.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "\n${BLUE}${BOLD}=== Sovereign Proxy v4.0 - Container Security Architecture Scan ===${NC}\n"

PASS=0
FAIL=0

assert_contains() {
    local file="$1"
    local pattern="$2"
    local desc="$3"

    if grep -qE "$pattern" "$file"; then
        echo -e "  [${GREEN}✓${NC}] ${desc}: ${GREEN}PASSED${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "  [${RED}✗${NC}] ${desc}: ${RED}FAILED (Pattern not found: '${pattern}')${NC}"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local file="$1"
    local pattern="$2"
    local desc="$3"

    if ! grep -qE "$pattern" "$file"; then
        echo -e "  [${GREEN}✓${NC}] ${desc}: ${GREEN}PASSED (Dangerous setting absent)${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "  [${RED}✗${NC}] ${desc}: ${RED}FAILED (Dangerous pattern found: '${pattern}')${NC}"
        FAIL=$((FAIL + 1))
    fi
}

# 1. Dockerfile checks
echo -e "${YELLOW}[*] Validating Dockerfile (${DOCKERFILE})...${NC}"
assert_contains "$DOCKERFILE" "USER 10001:10001" "Dockerfile enforces unprivileged UID 10001"
assert_contains "$DOCKERFILE" "FROM.*AS builder" "Dockerfile uses multi-stage build"
assert_not_contains "$DOCKERFILE" "USER root" "Dockerfile does not revert to root"

# 2. Docker Compose checks
echo -e "\n${YELLOW}[*] Validating Docker Compose (${COMPOSE_FILE})...${NC}"
assert_contains "$COMPOSE_FILE" "user: [\"']?10001:10001[\"']?" "Compose enforces UID 10001 execution"
assert_contains "$COMPOSE_FILE" "read_only: true" "Compose enforces read-only root filesystem"
assert_contains "$COMPOSE_FILE" "no-new-privileges:true" "Compose enforces no-new-privileges"
assert_contains "$COMPOSE_FILE" "ALL" "Compose drops all Linux capabilities (cap_drop: ALL)"
assert_not_contains "$COMPOSE_FILE" "privileged: true" "Privileged mode is disabled"
assert_not_contains "$COMPOSE_FILE" "SYS_ADMIN" "CAP_SYS_ADMIN is absent"

echo -e "\n${BOLD}=======================================================================${NC}"
echo -e "Container Security Summary: ${GREEN}${PASS} Passed${NC}, ${RED}${FAIL} Failed${NC}"
echo -e "${BOLD}=======================================================================${NC}\n"

if [[ "$FAIL" -eq 0 ]]; then
    exit 0
else
    exit 1
fi
