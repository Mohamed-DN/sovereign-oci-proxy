#!/bin/bash
# Sovereign OCI Proxy - Master Installer
echo "Starting Sovereign Proxy Installation..."

chmod +x scripts/modules/*.sh

echo "[1/4] Running Hardening..."
./scripts/modules/hardening.sh

echo "[2/4] Setting up Decoy..."
./scripts/modules/decoy.sh

echo "[3/4] Installing Monitoring & Honeypot..."
./scripts/modules/monitoring.sh

echo "[4/4] Setup complete. Please install 3x-ui manually via:"
echo "bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh)"
