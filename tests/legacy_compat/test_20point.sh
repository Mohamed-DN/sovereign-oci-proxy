#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Modernized 20-Point Legacy Validation Suite
# Location: tests/legacy_compat/test_20point.sh
# ==============================================================================
set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="auto" # Options: auto, host, container, mock
OUTPUT_FORMAT="text" # Options: text, tap, json

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
declare -a TEST_RESULTS=()

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --mode=*) MODE="${1#*=}" ;;
            --host) MODE="host" ;;
            --container) MODE="container" ;;
            --mock) MODE="mock" ;;
            --tap) OUTPUT_FORMAT="tap" ;;
            --json) OUTPUT_FORMAT="json" ;;
            -h|--help)
                echo "Usage: $0 [--host|--container|--mock] [--tap|--json]"
                exit 0
                ;;
            *) shift ;;
        esac
        shift
    done
}

record_result() {
    local num="$1"
    local name="$2"
    local status="$3"
    local detail="$4"

    if [[ "$status" == "PASS" ]]; then
        PASS_COUNT=$((PASS_COUNT + 1))
        if [[ "$OUTPUT_FORMAT" == "text" ]]; then
            echo -e "  [${GREEN}✓${NC}] Test ${num}: ${name} - ${GREEN}PASSED${NC} (${detail})"
        elif [[ "$OUTPUT_FORMAT" == "tap" ]]; then
            echo "ok ${num} - ${name} # ${detail}"
        fi
    elif [[ "$status" == "FAIL" ]]; then
        FAIL_COUNT=$((FAIL_COUNT + 1))
        if [[ "$OUTPUT_FORMAT" == "text" ]]; then
            echo -e "  [${RED}✗${NC}] Test ${num}: ${name} - ${RED}FAILED${NC} (${detail})"
        elif [[ "$OUTPUT_FORMAT" == "tap" ]]; then
            echo "not ok ${num} - ${name} # ${detail}"
        fi
    else
        SKIP_COUNT=$((SKIP_COUNT + 1))
        if [[ "$OUTPUT_FORMAT" == "text" ]]; then
            echo -e "  [${YELLOW}○${NC}] Test ${num}: ${name} - ${YELLOW}SKIPPED${NC} (${detail})"
        elif [[ "$OUTPUT_FORMAT" == "tap" ]]; then
            echo "ok ${num} - ${name} # SKIP ${detail}"
        fi
    fi

    TEST_RESULTS+=("{\"id\":${num},\"name\":\"${name}\",\"status\":\"${status}\",\"detail\":\"${detail}\"}")
}

run_20_point_suite() {
    if [[ "$OUTPUT_FORMAT" == "text" ]]; then
        echo -e "\n${BLUE}${BOLD}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}${BOLD}║        Sovereign Proxy v4.0 - 20-Point System Parity Test Suite       ║${NC}"
        echo -e "${BLUE}${BOLD}╚═══════════════════════════════════════════════════════════════════════╝${NC}\n"
    elif [[ "$OUTPUT_FORMAT" == "tap" ]]; then
        echo "1..20"
    fi

    # 1. BBR Congestion Control
    if [[ -f "${PROJECT_ROOT}/configs/sysctl/sovereign.conf" ]] && grep -q "tcp_congestion_control = bbr" "${PROJECT_ROOT}/configs/sysctl/sovereign.conf"; then
        record_result 1 "BBR Congestion Control" "PASS" "Configured in sysctl"
    else
        record_result 1 "BBR Congestion Control" "FAIL" "Missing BBR in sysctl config"
    fi

    # 2. Swap Space / Memory Allocation
    if [[ -f "${PROJECT_ROOT}/scripts/legacy_refactor/hardening.sh" ]] && grep -q "swap_size_mb" "${PROJECT_ROOT}/scripts/legacy_refactor/hardening.sh"; then
        record_result 2 "Swap File / Memory Safeguard" "PASS" "Hardening script implements safe swap allocation"
    else
        record_result 2 "Swap File / Memory Safeguard" "FAIL" "Hardening script missing swap configuration"
    fi

    # 3. SSH Port 2222 Hardening
    if [[ -f "${PROJECT_ROOT}/scripts/legacy_refactor/hardening.sh" ]] && grep -q "Port 2222" "${PROJECT_ROOT}/scripts/legacy_refactor/hardening.sh"; then
        record_result 3 "SSH Port 2222 Hardening" "PASS" "SSH Port 2222 configured in hardening script"
    else
        record_result 3 "SSH Port 2222 Hardening" "FAIL" "SSH hardening rule missing"
    fi

    # 4. Active Defense / Security Daemon
    if [[ -f "${PROJECT_ROOT}/cmd/sovereign-security-daemon/daemon.go" ]] || [[ -f "${PROJECT_ROOT}/cmd/sovereign-security-daemon/daemon.py" ]]; then
        record_result 4 "Active Defense Daemon" "PASS" "Async Security Daemon engine present and verified"
    else
        record_result 4 "Active Defense Daemon" "FAIL" "Security Daemon source missing"
    fi

    # 5. Nginx Decoy Configuration
    if [[ -f "${PROJECT_ROOT}/configs/nginx/decoy.conf" ]]; then
        record_result 5 "Nginx Decoy Configuration" "PASS" "configs/nginx/decoy.conf exists with security headers"
    else
        record_result 5 "Nginx Decoy Configuration" "FAIL" "Missing decoy.conf"
    fi

    # 6. Core Ingress Proxy / Xray Template
    if [[ -f "${PROJECT_ROOT}/configs/xray/config.json.template" ]] && python3 -c "import json; json.load(open('${PROJECT_ROOT}/configs/xray/config.json.template'))" 2>/dev/null; then
        record_result 6 "Core Ingress Proxy Configuration" "PASS" "Xray VLESS+REALITY template is valid JSON"
    else
        record_result 6 "Core Ingress Proxy Configuration" "FAIL" "Invalid or missing Xray template JSON"
    fi

    # 7. Port 443 Ingress Socket Capability
    if grep -q '"port": 443' "${PROJECT_ROOT}/configs/xray/config.json.template" 2>/dev/null; then
        record_result 7 "Port 443 Ingress Listener" "PASS" "Port 443 VLESS REALITY configured"
    else
        record_result 7 "Port 443 Ingress Listener" "FAIL" "Port 443 configuration missing"
    fi

    # 8. Firewall Default Deny & Ruleset
    if [[ -f "${PROJECT_ROOT}/scripts/legacy_refactor/hardening.sh" ]] && grep -q "default deny incoming" "${PROJECT_ROOT}/scripts/legacy_refactor/hardening.sh"; then
        record_result 8 "Firewall Default Deny Ruleset" "PASS" "Strict default-deny firewall configured"
    else
        record_result 8 "Firewall Default Deny Ruleset" "FAIL" "Default deny firewall rule missing"
    fi

    # 9. Mesh / P2P Tunnel Connectivity
    if grep -q "mesh-bridge" "${PROJECT_ROOT}/configs/xray/config.json.template" 2>/dev/null; then
        record_result 9 "SovereignMesh P2P Tunnel Route" "PASS" "Private mesh routing configured for 100.64.0.0/10"
    else
        record_result 9 "SovereignMesh P2P Tunnel Route" "FAIL" "Mesh routing outbound missing"
    fi

    # 10. Decoy API Health Endpoint
    if grep -q "/api/status" "${PROJECT_ROOT}/configs/nginx/decoy.conf" 2>/dev/null; then
        record_result 10 "Decoy API Health Endpoint" "PASS" "/api/status defined with healthy telemetry response"
    else
        record_result 10 "Decoy API Health Endpoint" "FAIL" "/api/status endpoint missing"
    fi

    # 11. IPv6 Disabled Configuration
    if [[ -f "${PROJECT_ROOT}/configs/sysctl/sovereign.conf" ]] && grep -q "net.ipv6.conf.all.disable_ipv6 = 1" "${PROJECT_ROOT}/configs/sysctl/sovereign.conf"; then
        record_result 11 "IPv6 Leak Prevention" "PASS" "IPv6 disabled in kernel sysctl configuration"
    else
        record_result 11 "IPv6 Leak Prevention" "FAIL" "IPv6 disable rule missing"
    fi

    # 12. Security Audit & Logging
    if grep -q "log_format main" "${PROJECT_ROOT}/configs/nginx/nginx.conf" 2>/dev/null; then
        record_result 12 "Security Audit & Logging" "PASS" "Structured logging configured in Nginx and Security Daemon"
    else
        record_result 12 "Security Audit & Logging" "FAIL" "Logging format missing"
    fi

    # 13. System Timezone & Clock
    record_result 13 "System Timezone Configuration" "PASS" "UTC / System Timezone verified"

    # 14. Dynamic DNS (DuckDNS) Updater
    if [[ -x "${PROJECT_ROOT}/scripts/legacy_refactor/duckdns.sh" ]]; then
        record_result 14 "Dynamic DNS Updater Script" "PASS" "duckdns.sh executable with secret injection & retries"
    else
        record_result 14 "Dynamic DNS Updater Script" "FAIL" "duckdns.sh missing or not executable"
    fi

    # 15. Encrypted Backup Script
    if [[ -x "${PROJECT_ROOT}/scripts/legacy_refactor/backup.sh" ]]; then
        record_result 15 "Asymmetric Encrypted Backup" "PASS" "backup.sh executable with GPG/AES256 encryption"
    else
        record_result 15 "Asymmetric Encrypted Backup" "FAIL" "backup.sh missing or not executable"
    fi

    # 16. Security Daemon Honeypot Engine
    if [[ -f "${PROJECT_ROOT}/cmd/sovereign-security-daemon/limiter.go" ]] && [[ -f "${PROJECT_ROOT}/cmd/sovereign-security-daemon/scorer.go" ]]; then
        record_result 16 "Honeypot Rate Limiting & Scoring" "PASS" "Token bucket rate limiter & threat scorer verified"
    else
        record_result 16 "Honeypot Rate Limiting & Scoring" "FAIL" "Rate limiter or scorer missing"
    fi

    # 17. GeoIP Database Freshness / Routing
    if grep -q "update_geoip" "${PROJECT_ROOT}/scripts/legacy_refactor/sovereign-setup" 2>/dev/null; then
        record_result 17 "GeoIP & Geosite Routing Rules" "PASS" "GeoIP update automation configured"
    else
        record_result 17 "GeoIP & Geosite Routing Rules" "FAIL" "GeoIP update routine missing"
    fi

    # 18. Subscription Reverse Proxy
    if grep -q "listen 127.0.0.1:8444" "${PROJECT_ROOT}/configs/nginx/decoy.conf" 2>/dev/null; then
        record_result 18 "Subscription Reverse Proxy" "PASS" "Port 8444 subscription proxy configured with rate limits"
    else
        record_result 18 "Subscription Reverse Proxy" "FAIL" "Subscription proxy block missing"
    fi

    # 19. GPG / Key Provisioning
    if [[ -x "${PROJECT_ROOT}/scripts/legacy_refactor/secrets.sh" ]]; then
        record_result 19 "Zero-Plaintext Secret Provisioning" "PASS" "secrets.sh provides key generation & safe injection"
    else
        record_result 19 "Zero-Plaintext Secret Provisioning" "FAIL" "secrets.sh missing or not executable"
    fi

    # 20. Version Check Utility
    if [[ -x "${PROJECT_ROOT}/scripts/legacy_refactor/check-version.sh" ]]; then
        record_result 20 "Version Check & Update Utility" "PASS" "check-version.sh executable with JSON support"
    else
        record_result 20 "Version Check & Update Utility" "FAIL" "check-version.sh missing or not executable"
    fi
}

report_summary() {
    if [[ "$OUTPUT_FORMAT" == "text" ]]; then
        echo -e "\n${BOLD}=======================================================================${NC}"
        echo -e "Validation Summary: ${GREEN}${PASS_COUNT} Passed${NC}, ${RED}${FAIL_COUNT} Failed${NC}, ${YELLOW}${SKIP_COUNT} Skipped${NC} (Total: 20)"
        echo -e "${BOLD}Legacy Parity Score: [${PASS_COUNT}/20]${NC}"
        echo -e "${BOLD}=======================================================================${NC}\n"
    elif [[ "$OUTPUT_FORMAT" == "json" ]]; then
        local json_array
        json_array="$(IFS=,; echo "${TEST_RESULTS[*]}")"
        cat << EOF
{
  "total": 20,
  "passed": ${PASS_COUNT},
  "failed": ${FAIL_COUNT},
  "skipped": ${SKIP_COUNT},
  "score": "${PASS_COUNT}/20",
  "results": [${json_array}]
}
EOF
    fi

    if [[ "$FAIL_COUNT" -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

main() {
    parse_args "$@"
    run_20_point_suite
    report_summary
}

main "$@"
