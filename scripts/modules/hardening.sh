#!/bin/bash
# =========================================================
# Sovereign Proxy - OS Hardening Module
# Configures: Swap, BBR, SSH, Fail2ban, UFW, Auditd,
#             Timezone, Hostname, and Automatic Updates
# =========================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo "[!] Please run as root"
    exit 1
fi

# ------- System Update -------
echo -e "${GREEN}[*] Updating system packages...${NC}"
apt update && apt full-upgrade -y
apt install -y curl wget ufw fail2ban htop net-tools ca-certificates \
    unattended-upgrades apt-listchanges jq sqlite3 nginx certbot \
    python3-certbot-nginx logrotate cron bc lynis auditd gnupg2 \
    wrk netcat-openbsd

# ------- Timezone & Hostname -------
echo -e "${GREEN}[*] Setting timezone and hostname...${NC}"
timedatectl set-timezone Europe/Rome
hostnamectl set-hostname sovereign-proxy
grep -q "sovereign-proxy" /etc/hosts || echo "127.0.0.1 sovereign-proxy" >> /etc/hosts

# ------- Swap (4GB) -------
echo -e "${GREEN}[*] Creating 4GB swap file...${NC}"
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q "/swapfile" /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "  Swap created and activated."
else
    echo "  Swap already exists, skipping."
fi

# ------- Sysctl (BBR + Tuning) -------
echo -e "${GREEN}[*] Applying sysctl optimizations (BBR, TCP tuning, IPv6 off)...${NC}"
cp "$(dirname "$0")/../../configs/sysctl/sovereign.conf" /etc/sysctl.d/99-sovereign.conf 2>/dev/null || \
cat << 'SYSCTL_EOF' > /etc/sysctl.d/99-sovereign.conf
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_max_tw_buckets = 5000
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
SYSCTL_EOF
sysctl --system

# ------- SSH Hardening -------
echo -e "${YELLOW}[*] Hardening SSH configuration...${NC}"
echo -e "${YELLOW}    WARNING: Ensure port 2222 is open in Oracle Security List BEFORE proceeding!${NC}"
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
sed -i 's/^#\?Port .*/Port 2222/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?MaxAuthTries .*/MaxAuthTries 3/' /etc/ssh/sshd_config
sed -i 's/^#\?X11Forwarding .*/X11Forwarding no/' /etc/ssh/sshd_config
sed -i 's/^#\?LoginGraceTime .*/LoginGraceTime 30/' /etc/ssh/sshd_config
echo -e "${YELLOW}    SSH config updated. Restart with: sudo systemctl restart sshd${NC}"
echo -e "${YELLOW}    CRITICAL: Test with a SECOND terminal on port 2222 before closing this session!${NC}"

# ------- Fail2ban -------
echo -e "${GREEN}[*] Configuring Fail2ban...${NC}"
cat << 'F2B_EOF' > /etc/fail2ban/jail.local
[DEFAULT]
bantime = 86400
findtime = 600
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = 2222
filter = sshd
logpath = /var/log/auth.log

[nginx-botsearch]
enabled = true
port = 80,443
filter = nginx-botsearch
logpath = /var/log/nginx/decoy-access.log
maxretry = 5
bantime = 43200
F2B_EOF
systemctl enable --now fail2ban

# ------- UFW Firewall -------
echo -e "${GREEN}[*] Configuring UFW Firewall...${NC}"
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp comment 'SSH custom port'
ufw allow 443/tcp comment 'VLESS Reality + Decoy + Subscription'
ufw allow 80/tcp comment 'ACME certificate renewal'
ufw allow 8080/tcp comment 'Honeypot trap'
ufw limit 2222/tcp comment 'SSH brute-force protection'
sed -i 's/IPV6=yes/IPV6=no/' /etc/default/ufw
ufw --force enable

# ------- Auditd -------
echo -e "${GREEN}[*] Configuring Auditd...${NC}"
cat << 'AUDIT_EOF' > /etc/audit/rules.d/sovereign.rules
-w /etc/ssh/sshd_config -p wa -k ssh-config-change
-w /etc/x-ui/ -p wa -k xray-config-change
-w /etc/nginx/ -p wa -k nginx-config-change
-w /usr/local/bin/ -p wa -k scripts-change
-w /etc/shadow -p r -k shadow-read
-a always,exit -F arch=b64 -S execve -F euid=0 -k sudo-commands
AUDIT_EOF
systemctl enable --now auditd

# ------- Log Rotation -------
echo -e "${GREEN}[*] Configuring log rotation...${NC}"
cat << 'LOG_EOF' > /etc/logrotate.d/sovereign
/var/log/oracle-keepalive.log
/var/log/sovereign-backup.log
/var/log/sovereign-healthcheck.log
/var/log/sovereign-maintenance.log
/var/log/duckdns-update.log
/var/log/honeypot.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root adm
}
LOG_EOF

# ------- Automatic Updates -------
echo -e "${GREEN}[*] Enabling unattended upgrades...${NC}"
dpkg-reconfigure -plow unattended-upgrades 2>/dev/null || true

echo -e "${GREEN}[*] Hardening complete!${NC}"
