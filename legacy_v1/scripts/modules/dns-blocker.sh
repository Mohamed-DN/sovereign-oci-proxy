#!/bin/bash
# =========================================================
# Sovereign Proxy - DNS Ad-Blocker (dnsmasq)
# Deploys a local DNS server for WireGuard clients that
# automatically blocks ads, trackers, and malware using
# the unified StevenBlack hosts list.
# =========================================================

set -e
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[!] Please run as root${NC}"
    exit 1
fi

WG_NETWORK="${WG_NETWORK:-10.66.66}"
DNS_IP="${WG_NETWORK}.1"

echo -e "${GREEN}[*] Installing dnsmasq...${NC}"
apt update -qq
apt install -y dnsmasq curl

echo -e "${GREEN}[*] Downloading StevenBlack Unified Hosts (Ad/Tracker blocklist)...${NC}"
curl -sL "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts" -o /etc/dnsmasq.hosts

echo -e "${GREEN}[*] Configuring dnsmasq...${NC}"
cat << EOF > /etc/dnsmasq.d/sovereign-adblock.conf
# Listen only on WireGuard interface
listen-address=${DNS_IP},127.0.0.1
bind-interfaces

# Upstream DNS (Cloudflare)
server=1.1.1.1
server=1.0.0.1

# Use the downloaded blocklist
addn-hosts=/etc/dnsmasq.hosts

# Don't read /etc/resolv.conf to avoid loops
no-resolv

# Cache settings
cache-size=10000
EOF

echo -e "${GREEN}[*] Creating Auto-Update Cron Job...${NC}"
cat << 'CRON_EOF' > /etc/cron.weekly/sovereign-dns-update
#!/bin/bash
curl -sL "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts" -o /etc/dnsmasq.hosts.new
if [ -s /etc/dnsmasq.hosts.new ]; then
    mv /etc/dnsmasq.hosts.new /etc/dnsmasq.hosts
    systemctl restart dnsmasq
fi
CRON_EOF
chmod +x /etc/cron.weekly/sovereign-dns-update

echo -e "${GREEN}[*] Restarting dnsmasq...${NC}"
# Stop systemd-resolved from conflicting on port 53 if it's bound to 127.0.0.1
if systemctl is-active --quiet systemd-resolved; then
    sed -i 's/#DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf 2>/dev/null || true
    systemctl restart systemd-resolved 2>/dev/null || true
fi

systemctl restart dnsmasq
systemctl enable dnsmasq

echo ""
echo -e "${GREEN}  ╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}  ║   🛡️  DNS Ad-Blocker Active on ${DNS_IP}                  ║${NC}"
echo -e "${GREEN}  ╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}  ║   Your WireGuard clients will now automatically block:    ║${NC}"
echo -e "${GREEN}  ║   - Ads & Trackers                                        ║${NC}"
echo -e "${GREEN}  ║   - Malware & Phishing domains                            ║${NC}"
echo -e "${GREEN}  ║                                                           ║${NC}"
echo -e "${GREEN}  ║   To apply this, ensure your WG_DNS in config.env is:     ║${NC}"
echo -e "${GREEN}  ║   WG_DNS=\"${DNS_IP}, 1.1.1.1\"                              ║${NC}"
echo -e "${GREEN}  ╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
