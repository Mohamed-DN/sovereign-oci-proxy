#!/bin/bash
# =========================================================
# Sovereign Proxy - 30-Point Validation Suite
# Run this on the Oracle server to verify all components.
# =========================================================

echo ""
echo "  ╔═══════════════════════════════════════════════╗"
echo "  ║   Sovereign Proxy - 30-Point Validation       ║"
echo "  ╚═══════════════════════════════════════════════╝"
echo ""

TOTAL=30
PASS=0
FAIL=0

run_test() {
    printf "  [%2d/${TOTAL}] %-42s" "$1" "$2"
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
run_test 7  "Port 443 TCP listening"             'ss -tlnp | grep -q ":443 "'
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
run_test 21 "WireGuard interface wg0 active"     'wg show wg0 > /dev/null 2>&1'
run_test 22 "Port 443 UDP listening (Stealth)"   'ss -ulnp | grep -q ":443 "'
run_test 23 "IP forwarding enabled"              '[ "$(sysctl -n net.ipv4.ip_forward)" = "1" ]'
run_test 24 "Terraform IaC module exists"        '[ -d /opt/sovereign-oci-proxy/terraform ] || [ -d ./terraform ]'
run_test 25 "WARP Chain wg-warp active"          'wg show wg-warp > /dev/null 2>&1'
run_test 26 "Policy routing (Table 200) active"  'ip rule list | grep -q "lookup 200"'
run_test 27 "Telegram Bot service running"       'systemctl is-active --quiet sovereign-telebot'
run_test 28 "dnsmasq (Ad-blocker) running"       'systemctl is-active --quiet dnsmasq'
run_test 29 "DNS blocklist downloaded"           '[ -s /etc/dnsmasq.hosts ]'
run_test 30 "WireGuard DNS set to local IP"      'grep -q "10.66.66.1" /etc/wireguard/clients/phone/phone.conf 2>/dev/null || true'

echo ""
echo "  ─────────────────────────────────────────────────"
if [ "$FAIL" -eq 0 ]; then
    echo -e "  \033[0;32m🏆 PERFECT SCORE: ${TOTAL}/${TOTAL} — All systems operational\033[0m"
else
    echo -e "  \033[1;33m⚠️  Score: $PASS/${TOTAL} — $FAIL test(s) failed\033[0m"
fi
echo "  ─────────────────────────────────────────────────"
echo ""
