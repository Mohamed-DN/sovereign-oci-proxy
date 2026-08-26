#!/bin/bash
# =========================================================
# Sovereign Proxy - WireGuard to WARP Chaining
# Routes native WireGuard clients (wg0) through Cloudflare WARP.
# This hides the Oracle IP for gaming/VPN clients,
# bypassing Netflix/AI restrictions.
# =========================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[!] Please run as root${NC}"
    exit 1
fi

echo -e "${GREEN}[*] Installing wgcf (Cloudflare WARP generator)...${NC}"
if ! command -v wgcf &>/dev/null; then
    curl -fsSL https://github.com/ViRb3/wgcf/releases/latest/download/wgcf_linux_arm64 -o /usr/local/bin/wgcf
    chmod +x /usr/local/bin/wgcf
fi

echo -e "${GREEN}[*] Generating WARP WireGuard profile...${NC}"
cd /etc/wireguard
if [ ! -f wgcf-account.toml ]; then
    yes | wgcf register
fi

if [ ! -f wgcf-profile.conf ]; then
    wgcf generate
fi

echo -e "${GREEN}[*] Configuring wg-warp interface...${NC}"
# Copy generated profile and modify it for Policy Routing
cp wgcf-profile.conf wg-warp.conf

# We don't want WARP to become the default route for the host OS.
# We only want it for traffic originating from the wg0 tunnel.
# Remove standard AllowedIPs and add Table=200
sed -i 's/^AllowedIPs = .*/AllowedIPs = 0.0.0.0\/0/' wg-warp.conf
if ! grep -q "^Table = " wg-warp.conf; then
    sed -i '/^\[Interface\]/a Table = 200' wg-warp.conf
fi

# Add NAT masquerade so wg0 clients can go out through wg-warp
if ! grep -q "^PostUp" wg-warp.conf; then
    cat >> wg-warp.conf << 'EOF'

# Policy Routing for wg0 clients -> wg-warp
PostUp = ip rule add from 10.66.66.0/24 table 200
PostUp = iptables -t nat -A POSTROUTING -o wg-warp -j MASQUERADE
PostDown = ip rule del from 10.66.66.0/24 table 200
PostDown = iptables -t nat -D POSTROUTING -o wg-warp -j MASQUERADE
EOF
fi

chmod 600 wg-warp.conf

echo -e "${GREEN}[*] Starting wg-warp...${NC}"
systemctl enable wg-quick@wg-warp
systemctl start wg-quick@wg-warp || {
    wg-quick down wg-warp 2>/dev/null || true
    wg-quick up wg-warp
}

# Fix wg0 routing (remove old NAT over eth0, use wg-warp)
echo -e "${GREEN}[*] Updating wg0 (client tunnel) routing...${NC}"
if [ -f /etc/wireguard/wg0.conf ]; then
    # Disable wg0 temporarily
    wg-quick down wg0 2>/dev/null || true
    
    # We remove the eth0 masquerade because traffic is now handled by wg-warp PostUp
    sed -i '/iptables -t nat -A POSTROUTING -s .* -o .* -j MASQUERADE/d' /etc/wireguard/wg0.conf
    sed -i '/iptables -t nat -D POSTROUTING -s .* -o .* -j MASQUERADE/d' /etc/wireguard/wg0.conf
    
    wg-quick up wg0
fi

echo ""
echo -e "${GREEN}  ╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}  ║   ✅ WireGuard -> WARP Chaining Active                   ║${NC}"
echo -e "${GREEN}  ╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}  ║   Your WireGuard clients now connect to the Oracle        ║${NC}"
echo -e "${GREEN}  ║   server, and their traffic is automatically forwarded    ║${NC}"
echo -e "${GREEN}  ║   through Cloudflare WARP.                               ║${NC}"
echo -e "${GREEN}  ║                                                           ║${NC}"
echo -e "${GREEN}  ║   Netflix, ChatGPT, and Gaming will now see a trusted    ║${NC}"
echo -e "${GREEN}  ║   Cloudflare IP instead of the Oracle Datacenter IP.      ║${NC}"
echo -e "${GREEN}  ╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
