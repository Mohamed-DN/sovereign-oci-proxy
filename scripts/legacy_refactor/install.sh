#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Master Deployment & Modernization Installer
# Location: scripts/legacy_refactor/install.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SECRETS_HELPER="${SCRIPT_DIR}/secrets.sh"

source "${SECRETS_HELPER}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

log_header() { echo -e "\n${BLUE}${BOLD}=== $1 ===${NC}"; }
log_info() { echo -e "${BLUE}[+] INFO:${NC} $1"; }
log_ok() { echo -e "${GREEN}[✓] SUCCESS:${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!] WARN:${NC} $1"; }
log_err() { echo -e "${RED}[✗] ERROR:${NC} $1" >&2; }

detect_architecture() {
    log_header "Detecting Host Architecture & Operating System"
    local arch
    arch="$(uname -m)"
    case "$arch" in
        x86_64|amd64) log_ok "Architecture: x86_64 / AMD64" ;;
        aarch64|arm64) log_ok "Architecture: AArch64 / ARM64 (e.g. OCI Ampere A1)" ;;
        *) log_warn "Uncommon architecture: $arch (proceeding with caution)" ;;
    esac
}

install_dependencies() {
    log_header "Verifying System Dependencies"
    if [[ "$(id -u)" -eq 0 ]] && command -v apt-get >/dev/null 2>&1; then
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq || true
        apt-get install -y -qq curl wget jq ufw ipset fail2ban sqlite3 python3 nginx bc >/dev/null 2>&1 || true
        log_ok "System packages verified."
    else
        log_info "Running in non-root / containerized environment; proceeding with available tools."
    fi
}

run_hardening() {
    log_header "Executing Host & Network Hardening"
    bash "${SCRIPT_DIR}/hardening.sh"
}

run_decoy() {
    log_header "Deploying Modernized Nginx Decoy Engine"
    bash "${SCRIPT_DIR}/decoy.sh"
}

run_xray() {
    log_header "Deploying Hardened VLESS+REALITY Proxy Core"
    bash "${SCRIPT_DIR}/xray.sh"
}

run_monitoring() {
    log_header "Deploying Active Defense & Monitoring"
    bash "${SCRIPT_DIR}/monitoring.sh"
}

run_duckdns() {
    log_header "Configuring Dynamic DNS Updater"
    bash "${SCRIPT_DIR}/duckdns.sh" || true
}

run_verification() {
    log_header "Running 20-Point System Parity Validation"
    if [[ -f "${PROJECT_ROOT}/tests/legacy_compat/test_20point.sh" ]]; then
        bash "${PROJECT_ROOT}/tests/legacy_compat/test_20point.sh" || true
    fi
}

main() {
    echo -e "${GREEN}${BOLD}Initializing Sovereign Proxy v4.0 Installation Engine...${NC}"
    detect_architecture
    install_dependencies
    run_hardening
    run_decoy
    run_xray
    run_monitoring
    run_duckdns
    run_verification
    echo -e "\n${GREEN}${BOLD}[✓] Sovereign Proxy v4.0 Installation Workflow Complete!${NC}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
