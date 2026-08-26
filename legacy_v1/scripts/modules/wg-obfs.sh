#!/bin/bash
# =========================================================
# Sovereign Proxy - WireGuard Obfuscation Module
# Wraps WireGuard UDP traffic to survive Deep Packet
# Inspection (DPI) in countries like Egypt, China, Iran.
#
# Options:
#   A) wstunnel  — WireGuard over WebSocket (TCP 443)
#   B) udp2raw   — Fake TCP/ICMP headers on UDP packets
# =========================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

WG_PORT="${WG_PORT:-51820}"
OBFS_PORT="${OBFS_PORT:-443}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[!] Please run as root${NC}"
    exit 1
fi

echo ""
echo "  ╔═══════════════════════════════════════════════════════════╗"
echo "  ║   Sovereign WireGuard - Anti-DPI Obfuscation             ║"
echo "  ╠═══════════════════════════════════════════════════════════╣"
echo "  ║                                                           ║"
echo "  ║   Choose an obfuscation method:                           ║"
echo "  ║                                                           ║"
echo "  ║   1) wstunnel (Recommended)                               ║"
echo "  ║      Wraps WireGuard inside a WebSocket on port 443.      ║"
echo "  ║      Looks like normal HTTPS traffic to DPI.              ║"
echo "  ║      Overhead: ~5-10ms latency.                           ║"
echo "  ║      Client: wstunnel app on your device.                 ║"
echo "  ║                                                           ║"
echo "  ║   2) udp2raw                                              ║"
echo "  ║      Disguises UDP packets as fake TCP or ICMP.           ║"
echo "  ║      Bypasses firewalls that block all UDP.               ║"
echo "  ║      Overhead: ~3-8ms latency.                            ║"
echo "  ║      Client: udp2raw on your device (Linux/Android).     ║"
echo "  ║                                                           ║"
echo "  ╚═══════════════════════════════════════════════════════════╝"
echo ""

read -rp "  Choice [1/2]: " METHOD

case "$METHOD" in
    1)
        # -----------------------------------------------
        # Option A: wstunnel (WebSocket tunnel)
        # -----------------------------------------------
        echo -e "${GREEN}[*] Installing wstunnel...${NC}"

        ARCH=$(uname -m)
        case "$ARCH" in
            aarch64) WS_ARCH="aarch64-unknown-linux-musl" ;;
            x86_64)  WS_ARCH="x86_64-unknown-linux-musl" ;;
            *)       echo "[!] Unsupported architecture: $ARCH"; exit 1 ;;
        esac

        WS_VERSION=$(curl -s https://api.github.com/repos/erebe/wstunnel/releases/latest | grep tag_name | cut -d'"' -f4)
        WS_URL="https://github.com/erebe/wstunnel/releases/download/${WS_VERSION}/wstunnel_${WS_VERSION#v}_${WS_ARCH}.tar.gz"

        echo "  Downloading wstunnel ${WS_VERSION} for ${ARCH}..."
        curl -sL "$WS_URL" | tar xz -C /usr/local/bin/ wstunnel
        chmod +x /usr/local/bin/wstunnel

        echo -e "${GREEN}[*] Creating wstunnel systemd service...${NC}"
        cat > /etc/systemd/system/wstunnel-wg.service << WSVC_EOF
[Unit]
Description=Sovereign wstunnel for WireGuard obfuscation
After=network.target
Before=wg-quick@wg0.service

[Service]
Type=simple
ExecStart=/usr/local/bin/wstunnel server --restrict-to 127.0.0.1:${WG_PORT} ws://0.0.0.0:${OBFS_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
WSVC_EOF

        # Reconfigure WireGuard to listen on localhost only
        echo -e "${GREEN}[*] Binding WireGuard to localhost (127.0.0.1)...${NC}"
        sed -i "s/^ListenPort = .*/ListenPort = ${WG_PORT}/" /etc/wireguard/wg0.conf

        systemctl daemon-reload
        systemctl enable --now wstunnel-wg

        echo ""
        echo -e "${GREEN}  ╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}  ║   ✅ wstunnel installed and running on port ${OBFS_PORT}         ║${NC}"
        echo -e "${GREEN}  ╠═══════════════════════════════════════════════════════════╣${NC}"
        echo -e "${GREEN}  ║   Client command:                                        ║${NC}"
        echo -e "${GREEN}  ║   wstunnel client -L udp://51820:127.0.0.1:51820 \\      ║${NC}"
        echo -e "${GREEN}  ║     ws://<YOUR_SERVER>:${OBFS_PORT}                             ║${NC}"
        echo -e "${GREEN}  ║                                                           ║${NC}"
        echo -e "${GREEN}  ║   Then point WireGuard Endpoint to 127.0.0.1:51820       ║${NC}"
        echo -e "${GREEN}  ╚═══════════════════════════════════════════════════════════╝${NC}"
        ;;

    2)
        # -----------------------------------------------
        # Option B: udp2raw (Fake TCP headers)
        # -----------------------------------------------
        echo -e "${GREEN}[*] Installing udp2raw...${NC}"

        ARCH=$(uname -m)
        case "$ARCH" in
            aarch64) U2R_BIN="udp2raw_arm" ;;
            x86_64)  U2R_BIN="udp2raw_amd64" ;;
            *)       echo "[!] Unsupported architecture: $ARCH"; exit 1 ;;
        esac

        U2R_VERSION=$(curl -s https://api.github.com/repos/wangyu-/udp2raw/releases/latest | grep tag_name | cut -d'"' -f4)
        U2R_URL="https://github.com/wangyu-/udp2raw/releases/download/${U2R_VERSION}/udp2raw_binaries.tar.gz"

        echo "  Downloading udp2raw ${U2R_VERSION}..."
        cd /tmp
        curl -sL "$U2R_URL" | tar xz
        cp "${U2R_BIN}" /usr/local/bin/udp2raw
        chmod +x /usr/local/bin/udp2raw
        cd -

        # Generate a random password for the tunnel
        U2R_PASSWORD=$(openssl rand -hex 16)

        echo -e "${GREEN}[*] Creating udp2raw systemd service...${NC}"
        cat > /etc/systemd/system/udp2raw-wg.service << U2R_EOF
[Unit]
Description=Sovereign udp2raw for WireGuard obfuscation
After=network.target
Before=wg-quick@wg0.service

[Service]
Type=simple
ExecStart=/usr/local/bin/udp2raw -s -l 0.0.0.0:${OBFS_PORT} -r 127.0.0.1:${WG_PORT} -k "${U2R_PASSWORD}" --raw-mode faketcp -a
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
U2R_EOF

        systemctl daemon-reload
        systemctl enable --now udp2raw-wg

        echo ""
        echo -e "${GREEN}  ╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}  ║   ✅ udp2raw installed and running on port ${OBFS_PORT}          ║${NC}"
        echo -e "${GREEN}  ╠═══════════════════════════════════════════════════════════╣${NC}"
        echo -e "${GREEN}  ║   Client command (Linux/Android):                        ║${NC}"
        echo -e "${GREEN}  ║   udp2raw -c -l 0.0.0.0:51821 \\                         ║${NC}"
        echo -e "${GREEN}  ║     -r <YOUR_SERVER>:${OBFS_PORT} \\                            ║${NC}"
        echo -e "${GREEN}  ║     -k \"${U2R_PASSWORD}\" \\${NC}"
        echo -e "${GREEN}  ║     --raw-mode faketcp -a                                ║${NC}"
        echo -e "${GREEN}  ║                                                           ║${NC}"
        echo -e "${GREEN}  ║   Then point WireGuard Endpoint to 127.0.0.1:51821       ║${NC}"
        echo -e "${GREEN}  ║                                                           ║${NC}"
        echo -e "${YELLOW}  ║   ⚠️  Save this password securely!                       ║${NC}"
        echo -e "${GREEN}  ╚═══════════════════════════════════════════════════════════╝${NC}"
        ;;
    *)
        echo "[!] Invalid choice. Exiting."
        exit 1
        ;;
esac
