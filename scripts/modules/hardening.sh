#!/bin/bash
# OS Hardening, Swap, BBR, and Firewall Setup

echo "Setting up 4GB Swap..."
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

echo "Applying BBR and Sysctl optimizations..."
cat << 'SYSCTL_EOF' > /etc/sysctl.d/99-sovereign.conf
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
SYSCTL_EOF
sysctl --system

echo "Configuring UFW Firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp comment 'SSH'
ufw allow 443/tcp comment 'VLESS'
ufw allow 80/tcp comment 'ACME'
ufw allow 8080/tcp comment 'Honeypot'
ufw --force enable
