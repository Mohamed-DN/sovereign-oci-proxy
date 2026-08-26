#!/bin/bash
# =========================================================
# Sovereign Proxy - Split Tunnel Configuration
# Configures WireGuard clients for selective routing:
# only gaming/VoIP traffic goes through the VPN tunnel,
# normal browsing stays on the local connection.
# =========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CLIENT_DIR="/etc/wireguard/clients"

cat << 'INFO'

  ╔═══════════════════════════════════════════════════════════╗
  ║   Sovereign WireGuard - Split Tunnel Guide               ║
  ╠═══════════════════════════════════════════════════════════╣
  ║                                                           ║
  ║   FULL TUNNEL (default):                                  ║
  ║   AllowedIPs = 0.0.0.0/0                                  ║
  ║   → All traffic goes through VPN. Maximum privacy.        ║
  ║   → Higher latency for local content (YouTube, etc.)      ║
  ║                                                           ║
  ║   SPLIT TUNNEL (gaming optimized):                        ║
  ║   AllowedIPs = 10.66.66.0/24, <game server IPs>           ║
  ║   → Only specified traffic goes through VPN.              ║
  ║   → Local browsing stays fast on your connection.         ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝

INFO

echo -e "${GREEN}Common Game Server IP Ranges:${NC}"
echo ""
echo "  Among Us (Innersloth):"
echo "    AllowedIPs = 10.66.66.0/24, 198.50.128.0/17"
echo ""
echo "  Fortnite / Epic Games:"
echo "    AllowedIPs = 10.66.66.0/24, 99.83.128.0/17, 52.0.0.0/8"
echo ""
echo "  Minecraft:"
echo "    AllowedIPs = 10.66.66.0/24, 0.0.0.0/0  (servers vary widely)"
echo ""
echo "  Discord (voice/video):"
echo "    AllowedIPs = 10.66.66.0/24, 66.22.192.0/18"
echo ""
echo -e "${YELLOW}  TIP: For gaming, Full Tunnel (0.0.0.0/0) is usually simplest"
echo -e "  and most reliable. Use Split Tunnel only if you need to"
echo -e "  minimize bandwidth usage on your OCI server.${NC}"
echo ""

# Interactive mode: patch an existing client config
if [ -n "$1" ] && [ "$1" = "apply" ] && [ -n "$2" ]; then
    CLIENT_NAME="$2"
    CONFIG="${CLIENT_DIR}/${CLIENT_NAME}/${CLIENT_NAME}.conf"

    if [ ! -f "$CONFIG" ]; then
        echo "[!] Client config not found: $CONFIG"
        exit 1
    fi

    echo -e "${GREEN}Current AllowedIPs for '${CLIENT_NAME}':${NC}"
    grep "AllowedIPs" "$CONFIG"
    echo ""

    echo "Select tunnel mode:"
    echo "  1) Full Tunnel   — All traffic through VPN (0.0.0.0/0)"
    echo "  2) Gaming Only   — Among Us + Discord + DNS"
    echo "  3) VPN Subnet    — Only the VPN network (10.66.66.0/24)"
    read -rp "Choice [1/2/3]: " CHOICE

    case "$CHOICE" in
        1)
            sed -i 's|^AllowedIPs = .*|AllowedIPs = 0.0.0.0/0|' "$CONFIG"
            echo "[✅] Full Tunnel activated."
            ;;
        2)
            sed -i 's|^AllowedIPs = .*|AllowedIPs = 10.66.66.0/24, 198.50.128.0/17, 66.22.192.0/18, 1.1.1.1/32, 8.8.8.8/32|' "$CONFIG"
            echo "[✅] Gaming Split Tunnel activated (Among Us + Discord + DNS)."
            ;;
        3)
            sed -i 's|^AllowedIPs = .*|AllowedIPs = 10.66.66.0/24, 1.1.1.1/32, 8.8.8.8/32|' "$CONFIG"
            echo "[✅] VPN Subnet Only activated."
            ;;
        *)
            echo "[!] Invalid choice."
            exit 1
            ;;
    esac

    echo ""
    echo "Updated config:"
    grep "AllowedIPs" "$CONFIG"
    echo ""
    echo "Re-scan the QR code on your device to apply:"
    echo "  sovereign-wg-client.sh qr ${CLIENT_NAME}"
fi
