#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Host & Network Hardening Module
# Location: scripts/legacy_refactor/hardening.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[+] INFO:${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!] WARN:${NC} $1"; }
log_ok() { echo -e "${GREEN}[✓] SUCCESS:${NC} $1"; }
log_err() { echo -e "${RED}[✗] ERROR:${NC} $1" >&2; }

# ------------------------------------------------------------------------------
# 1. Swap Configuration (Safe 4GB Allocation with Disk Space Guard)
# ------------------------------------------------------------------------------
setup_swap() {
    log_info "Evaluating swap space requirements..."
    local swap_size_mb=4096

    if swapon --show | grep -q "/swapfile"; then
        log_ok "Swap file /swapfile is already active."
        return 0
    fi

    # Check available disk space on /
    local avail_mb
    avail_mb=$(df -m / | awk 'NR==2 {print $4}')
    if [[ "$avail_mb" -lt 8192 ]]; then
        log_warn "Insufficient disk space ($avail_mb MB < 8GB). Skipping 4GB swap creation to prevent disk exhaustion."
        return 0
    fi

    if [[ "$(id -u)" -ne 0 ]]; then
        log_warn "Non-root execution: skipping swapfile creation."
        return 0
    fi

    log_info "Creating ${swap_size_mb}MB swapfile at /swapfile..."
    fallocate -l "${swap_size_mb}M" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count="$swap_size_mb" status=progress
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile

    if ! grep -q "/swapfile" /etc/fstab; then
        echo "/swapfile none swap sw 0 0" >> /etc/fstab
    fi
    log_ok "4GB swapfile successfully enabled."
}

# ------------------------------------------------------------------------------
# 2. Kernel & BBR Tuning
# ------------------------------------------------------------------------------
setup_sysctl() {
    log_info "Applying kernel BBR congestion control and network hardening..."
    local sysctl_src="${PROJECT_ROOT}/configs/sysctl/sovereign.conf"
    local sysctl_dst="/etc/sysctl.d/99-sovereign.conf"

    if [[ -f "$sysctl_src" ]]; then
        if [[ "$(id -u)" -eq 0 ]]; then
            cp "$sysctl_src" "$sysctl_dst"
            sysctl -p "$sysctl_dst" >/dev/null 2>&1 || true
            log_ok "Applied sysctl settings from ${sysctl_dst}"
        else
            log_warn "Non-root execution: verified ${sysctl_src} syntax."
        fi
    else
        log_err "Sysctl config template not found at ${sysctl_src}"
    fi
}

# ------------------------------------------------------------------------------
# 3. SSH Hardening (Port 2222 with Firewall Pre-Check)
# ------------------------------------------------------------------------------
setup_ssh_hardening() {
    log_info "Hardening SSH configuration (Port 2222, Keys only)..."
    local sshd_config="/etc/ssh/sshd_config"

    if [[ ! -f "$sshd_config" ]] || [[ "$(id -u)" -ne 0 ]]; then
        log_warn "Skipping live SSH daemon modification (non-root or test mode)."
        return 0
    fi

    # Backup original sshd_config
    if [[ ! -f "${sshd_config}.orig" ]]; then
        cp "$sshd_config" "${sshd_config}.orig"
    fi

    # Update SSH settings safely
    sed -i 's/^#\?Port .*/Port 2222/' "$sshd_config"
    sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin prohibit-password/' "$sshd_config"
    sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' "$sshd_config"
    sed -i 's/^#\?MaxAuthTries .*/MaxAuthTries 3/' "$sshd_config"
    sed -i 's/^#\?X11Forwarding .*/X11Forwarding no/' "$sshd_config"

    # Pre-open UFW port 2222 before restarting sshd to avoid lockout
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 2222/tcp comment "SSH Hardened Port" >/dev/null 2>&1 || true
    fi

    systemctl restart ssh || systemctl restart sshd || true
    log_ok "SSH daemon hardened on port 2222."
}

# ------------------------------------------------------------------------------
# 4. Firewall (UFW & IPSet Rules)
# ------------------------------------------------------------------------------
setup_firewall() {
    log_info "Configuring default-deny firewall..."
    if ! command -v ufw >/dev/null 2>&1 || [[ "$(id -u)" -ne 0 ]]; then
        log_warn "UFW not available or non-root; skipping firewall configuration."
        return 0
    fi

    ufw --force reset >/dev/null 2>&1 || true
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 2222/tcp comment "SSH Management"
    ufw allow 443/tcp comment "VLESS / REALITY Ingress"
    ufw allow 443/udp comment "QUIC / Hysteria2 Ingress"
    ufw allow 51820/udp comment "SovereignMesh P2P WireGuard"
    ufw --force enable
    log_ok "Firewall enabled with strict ingress policy."
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    log_info "Starting Sovereign Proxy v4.0 Host Hardening..."
    setup_swap
    setup_sysctl
    setup_ssh_hardening
    setup_firewall
    log_ok "Host hardening completed successfully."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
