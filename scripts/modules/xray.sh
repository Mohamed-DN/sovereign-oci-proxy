#!/bin/bash
# =========================================================
# 3X-UI AND XRAY CORE SETUP
# =========================================================

echo "Installing 3x-ui panel..."
bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh)

echo "3x-ui installed successfully."
echo "Please configure your inbound settings via the Web UI."
echo "If you need to route Tailscale private IPs (192.168.x.x), run:"
echo "python3 /root/sovereign-oci-proxy/scripts/modules/xray-routing-fix.py"
