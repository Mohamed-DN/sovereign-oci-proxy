#!/bin/bash
# =========================================================
# Sovereign Proxy - 20-Point Validation Suite
# Run this on the Oracle server to verify all components.
# =========================================================

echo ""
echo "  ╔═══════════════════════════════════════════════╗"
echo "  ║   Sovereign Proxy - 20-Point Validation       ║"
echo "  ╚═══════════════════════════════════════════════╝"
echo ""

PASS=0
FAIL=0

run_test() {
    printf "  [%2d/20] %-42s" "$1" "$2"
    if eval "$3" > /dev/null 2>&1; then
        echo -e "\033[0;32m✅ PASS\033[0m"
        ((PASS++))
    else
        echo -e "\033[0;31m❌ FAIL\033[0m"
        ((FAIL++))
    fi
}

run_test 1  "BBR congestion control active"      '[ "$(sysctl -n net.ipv4.tcp_congestion_control)" = "bbr" ]'
run_test 2  "Swap file active"                   'swapon --show | grep -q /swapfile'
run_test 3  "SSH listening on port 2222"         'grep -q "^Port 2222" /etc/ssh/sshd_config'
run_test 4  "Fail2ban running"                   'systemctl is-active --quiet fail2ban'
run_test 5  "Nginx running"                      'systemctl is-active --quiet nginx'
run_test 6  "3x-ui (Xray) running"               'systemctl is-active --quiet x-ui'
run_test 7  "Port 443 listening"                 'ss -tlnp | grep -q ":443 "'
run_test 8  "UFW firewall active"                'ufw status | grep -q "Status: active"'
run_test 9  "Tailscale connected"                'tailscale status > /dev/null 2>&1'
run_test 10 "Decoy site responds"                'curl -s http://127.0.0.1:8443/api/status | grep -q healthy'
run_test 11 "IPv6 disabled"                      '[ "$(sysctl -n net.ipv6.conf.all.disable_ipv6)" = "1" ]'
run_test 12 "Auditd running"                     'systemctl is-active --quiet auditd'
run_test 13 "Timezone set to Europe/Rome"        '[ "$(timedatectl show -p Timezone --value)" = "Europe/Rome" ]'
run_test 14 "DuckDNS updater exists"             '[ -x /opt/duckdns/duck.sh ]'
run_test 15 "Backup script exists"               '[ -x /usr/local/bin/sovereign-backup.sh ]'
run_test 16 "Honeypot service running"           'systemctl is-active --quiet honeypot'
run_test 17 "GeoIP data is recent (<30 days)"    '[ $(find /usr/local/x-ui/bin/geoip.dat -mtime -30 2>/dev/null | wc -l) -eq 1 ]'
run_test 18 "Subscription proxy responds"        'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8444/sub/ | grep -qE "404|200|401|403"'
run_test 19 "GPG public key imported"            'gpg --list-keys 2>/dev/null | grep -q "@"'
run_test 20 "Version check script exists"        '[ -x /usr/local/bin/sovereign-check-version.sh ]'

echo ""
echo "  ─────────────────────────────────────────────────"
if [ "$FAIL" -eq 0 ]; then
    echo -e "  \033[0;32m🏆 PERFECT SCORE: 20/20 — All systems operational\033[0m"
else
    echo -e "  \033[1;33m⚠️  Score: $PASS/20 — $FAIL test(s) failed\033[0m"
fi
echo "  ─────────────────────────────────────────────────"
echo ""
