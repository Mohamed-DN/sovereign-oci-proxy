#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Clean Safe Uninstallation Engine
# Location: scripts/legacy_refactor/uninstall.sh
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[+] INFO:${NC} $1"; }
log_ok() { echo -e "${GREEN}[✓] SUCCESS:${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!] WARN:${NC} $1"; }

confirm_uninstall() {
    if [[ "${SOVEREIGN_NON_INTERACTIVE:-0}" == "1" ]]; then
        return 0
    fi
    if [[ -t 0 ]]; then
        read -rp "Are you sure you want to uninstall Sovereign Proxy v4.0? [y/N]: " confirm
        if [[ "$confirm" != "y" ]] && [[ "$confirm" != "Y" ]]; then
            echo "Uninstallation cancelled."
            exit 0
        fi
    fi
}

stop_services() {
    log_info "Stopping Sovereign services..."
    if command -v systemctl >/dev/null 2>&1 && [[ "$(id -u)" -eq 0 ]]; then
        for svc in sovereign-security-daemon sovereign-node xray x-ui; do
            systemctl stop "$svc" 2>/dev/null || true
            systemctl disable "$svc" 2>/dev/null || true
            rm -f "/etc/systemd/system/${svc}.service"
        done
        systemctl daemon-reload || true
        log_ok "Systemd services removed."
    fi
}

clean_cron() {
    log_info "Cleaning scheduled maintenance jobs..."
    if command -v crontab >/dev/null 2>&1; then
        crontab -l 2>/dev/null | grep -v "sovereign" | crontab - || true
        log_ok "Crontab entries cleaned."
    fi
}

restore_firewall() {
    log_info "Restoring firewall to baseline secure state..."
    # Note: Unlike legacy uninstall which executed 'ufw --force disable' exposing VPS,
    # v4.0 maintains a secure default-deny firewall posture while removing custom proxy rules.
    if command -v ufw >/dev/null 2>&1 && [[ "$(id -u)" -eq 0 ]]; then
        ufw delete allow 8080/tcp 2>/dev/null || true
        log_ok "Firewall rules cleaned safely."
    fi
}

main() {
    confirm_uninstall
    stop_services
    clean_cron
    restore_firewall
    log_ok "Sovereign Proxy uninstallation completed safely."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
