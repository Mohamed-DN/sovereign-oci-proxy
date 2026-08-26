#!/bin/bash
# =========================================================
# Sovereign OCI Proxy - Uninstaller
# Removes all deployed scripts, services, and crontab entries.
# Does NOT uninstall 3x-ui or delete backups.
# =========================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[!] Please run as root (sudo ./uninstall.sh)${NC}"
    exit 1
fi

echo -e "${YELLOW}[*] Sovereign OCI Proxy - Uninstaller${NC}"
echo -e "${YELLOW}[*] This will remove monitoring scripts, honeypot, and crontab entries.${NC}"
echo -e "${YELLOW}[*] It will NOT uninstall 3x-ui or delete your backups.${NC}"
echo ""
read -p "Are you sure you want to proceed? (y/N): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Aborted."
    exit 0
fi

echo -e "${GREEN}[1/6] Stopping and disabling honeypot service...${NC}"
systemctl stop honeypot 2>/dev/null || true
systemctl disable honeypot 2>/dev/null || true
rm -f /etc/systemd/system/honeypot.service
systemctl daemon-reload

echo -e "${GREEN}[2/6] Removing deployed scripts...${NC}"
rm -f /usr/local/bin/oracle-keepalive.sh
rm -f /usr/local/bin/sovereign-honeypot.py
rm -f /usr/local/bin/sovereign-healthcheck.sh
rm -f /usr/local/bin/sovereign-backup.sh
rm -f /usr/local/bin/sovereign-revoke-user.sh
rm -f /usr/local/bin/sovereign-update-geoip.sh
rm -f /usr/local/bin/sovereign-check-version.sh
rm -f /usr/local/bin/sovereign-test.sh
rm -f /usr/local/bin/sovereign-loadtest.sh
rm -f /usr/local/bin/sovereign-test-restore.sh

echo -e "${GREEN}[3/6] Removing crontab entries...${NC}"
crontab -l 2>/dev/null | grep -v "oracle-keepalive" | grep -v "sovereign-" | grep -v "duck.sh" | crontab -

echo -e "${GREEN}[4/6] Disabling UFW...${NC}"
ufw --force disable

echo -e "${GREEN}[5/6] Removing DuckDNS updater...${NC}"
rm -rf /opt/duckdns

echo -e "${GREEN}[6/6] Cleanup complete.${NC}"
echo ""
echo -e "${YELLOW}NOTE: 3x-ui was NOT removed. To uninstall it manually, run:${NC}"
echo -e "${YELLOW}  x-ui uninstall${NC}"
echo ""
echo -e "${YELLOW}NOTE: Backup archives on Backblaze B2 were NOT deleted.${NC}"
echo -e "${YELLOW}NOTE: Nginx configuration was NOT removed.${NC}"
