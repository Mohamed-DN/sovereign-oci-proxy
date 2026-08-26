#!/bin/bash
# Sovereign OCI Proxy - Master Installer
# Run this script as root to orchestrate the entire deployment.

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}[*] Starting Sovereign Proxy Installation...${NC}"

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[!] Please run this script as root (sudo ./scripts/install.sh)${NC}"
  exit 1
fi

if [ ! -f "config.env" ]; then
  echo -e "${RED}[!] ERROR: config.env not found!${NC}"
  echo -e "Please copy config.env.example to config.env and fill in your details:"
  echo -e "  cp config.env.example config.env"
  echo -e "  nano config.env"
  exit 1
fi

source config.env

if [[ "$DUCKDNS_DOMAIN" == *"YOUR-SUBDOMAIN"* ]]; then
  echo -e "${RED}[!] ERROR: You haven't changed the default values in config.env!${NC}"
  exit 1
fi

chmod +x scripts/modules/*.sh

echo -e "${GREEN}[1/6] Running System Hardening (Swap, BBR, Firewall)...${NC}"
./scripts/modules/hardening.sh

echo -e "${GREEN}[2/6] Setting up Nginx Decoy...${NC}"
./scripts/modules/decoy.sh

echo -e "${GREEN}[3/6] Installing Monitoring & Honeypot...${NC}"
./scripts/modules/monitoring.sh

echo -e "${GREEN}[4/6] Setting up DuckDNS Auto-Updater...${NC}"
./scripts/modules/duckdns.sh

echo -e "${GREEN}[5/6] Setting up Xray Core (3x-ui)...${NC}"
./scripts/modules/xray.sh

echo -e "${GREEN}[6/6] Installation Complete!${NC}"
echo -e "${GREEN}Please remember to configure your GPG keys before enabling backup.sh${NC}"
