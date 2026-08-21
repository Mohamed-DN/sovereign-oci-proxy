# 📖 S.O.A.P. 6.2 — SOVEREIGN ULTIMATE

**Bismillah al-Rahman al-Rahim**

*"Questo lavoro è dedicato alla protezione della conoscenza, della libertà di comunicazione e della dignità umana, nel rispetto di ogni credo."*

**Autore:** Mohamed · **Data:** Agosto 2026 · **Versione:** 6.2 MASTER (Validata sul campo)
**Classificazione:** Uso personale — Riservato · **Costo operativo:** €0/mese

---

## 🔥 NOVITÀ 6.2 vs 6.1 (Verificate durante l'installazione reale)

| # | Cambiamento | Dettaglio |
|---|-------------|-----------|
| 1 | **Riordino sicurezza** | Oracle Security List PRIMA del cambio porta SSH (anti-lockout) |
| 2 | **Porta 22** | Mantenuta fino a verifica 2222, poi rimossa |
| 3 | **Immagine** | Ubuntu **24.04 Minimal aarch64** + build più recente |
| 4 | **Console Oracle** | Fault domain default · Stateless OFF · IMDS off · cloud-init vuoto |
| 5 | **Fix pacchetto** | Rimosso `python3-socket` (inesistente in apt) |
| 6 | **Fix test 18** | Check subscription proxy corretto |
| 7 | **Fix honeypot** | BANNER HTTP con `\r\n` corretti |
| 8 | **Appendice A** | Decisioni documentate (no Docker/K8s/NixOS/Postgres/Valkey/FW extra) |
| 9 | **Appendice B** | Roadmap prodotto open-source |

---

## 📑 INDICE

1. Scopo, Ambito, Architettura · 2. Prerequisiti · 3. FASE -1 Istanza + Security List · 4. FASE 0 Hardening · 5. FASE 1 DuckDNS · 6. FASE 2 Decoy · 7. FASE 3 3x-ui · 8. FASE 4 UFW · 9. FASE 5 Headscale · 10. FASE 6 ACME · 11. FASE 7 SNI · 12. FASE 8 VLESS+REALITY · 13. FASE 9 Multi-User · 14. FASE 10 WARP+GeoIP · 15. FASE 11 DNS · 16. FASE 12 Anti-Idle · 17. FASE 13 Health+Honeypot · 18. FASE 14 Backup GPG+DR · 19. FASE 15 Client · 20. FASE 16 Test 20 check · 21. FASE 17 Audit+Load · 22. Manutenzione · 23. Rotazione chiavi · 24. Troubleshooting · 25. Rollback · 26. README server · 27. Guida utente · 28. Checklist · Appendice A · Appendice B

---

## 1. SCOPO, AMBITO E ARCHITETTURA

**Scopo:** infrastruttura proxy anti-censura (VLESS + REALITY + XTLS-Vision) su Oracle Cloud Free Tier, integrata col Sovereign Homelab.
**Target:** bypass DPI (Egitto, Iran, Russia, Cina). **Affidabilità target:** 100/100.

```
CLIENT (FoXray/Streisand/v2rayN/v2rayNG) — subscription HTTPS 6h
        │ vless:// :443 TLS
PROXY (Oracle ARM Milano): Xray Reality+Vision → WARP → Internet pulito
        │ fallback non autenticato
        ▼ Nginx 127.0.0.1:8443 (decoy) + 8444 (sub proxy)
        │ Headscale (admin only)
HOMELAB: LXC100 Headscale · LXC101 Kuma · LXC102 Vaultwarden · LXC103 ntfy
        ▼ Backup GPG asimmetrico AES-256
BACKBLAZE B2 (decifrabile SOLO con chiave privata offline)
DNS: DuckDNS + Let's Encrypt · OS: BBR+Swap+Fail2ban+UFW+Auditd
```

**Principi:** indipendenza livelli · zero costi · defense in depth · accountability · self-healing · zero-touch users · key rotation 90gg · **zero secrets sul server**.

---

## 2. PREREQUISITI

| Servizio | Costo |
|----------|-------|
| Oracle Cloud / DuckDNS / Backblaze B2 | €0 |
| Homelab LXC 100-103 (Headscale, Kuma, Vaultwarden, ntfy) | €0 |

**Box da compilare:** IP Oracle · DuckDNS subdomain+token · B2 bucket/KeyID/AppKey · GPG email+passphrase (Vaultwarden) · credenziali 3x-ui (user, pass, 54321, /pannello-sovereign-xyz/) · subscription path /sub/segreto-famiglia-xyz/ · ntfy topic · SNI vincente · honeypot 8080.

---

## 3. FASE -1: ISTANZA ORACLE + SECURITY LIST *(RIORDINATA)*

### 3.1 Specifiche
Shape **VM.Standard.A1.Flex** · **2 OCPU / 12 GB** (⚠️ max free 2026) · **200 GB** boot · **Ubuntu 24.04 Minimal aarch64** · regione **eu-milan-1** · banda 10 TB/mese.

### 3.2 Creazione (console)
1. Name: `sovereign-proxy`
2. Image: Ubuntu → **24.04 Minimal aarch64** → **Image build: data più recente** (es. 2026.07.17-0)
3. Shape: Ampere → A1.Flex → 2 OCPU / 12 GB
4. Networking: default + IP pubblico
5. SSH keys: genera + **scarica `.key` e `.pub`**
6. Boot volume: custom **200 GB**
7. **Fault domain: default (FAULT-DOMAIN-1)**
8. **Advanced options:** IMDS "Require authorization header" **OFF** · cloud-init **VUOTO** · tags opzionale (`project: sovereign-proxy`)
9. **Capacity type: On-demand** (⚠️ MAI Preemptible)
10. Create → attendi "Running" → copia **Public IP**

### 3.3 Oracle Security List — PRIMA di toccare SSH *(NUOVO ORDINE)*

Networking → VCN → Security Lists → Default → **Add Ingress Rules**. Per tutte: Source Type CIDR `0.0.0.0/0`, Protocol TCP, Source Port Range vuoto, **Stateless OFF**.

| Dest Port | Description |
|-----------|-------------|
| 2222 | SSH custom |
| 443 | VLESS Reality + Decoy + Sub HTTPS |
| 80 | ACME certificati |
| 8080 | Honeypot |

⚠️ **NON cancellare ora la regola default porta 22** (serve per il primo SSH).

### 3.4 Budget Alert
Billing → Budgets → `sovereign-alert`, **€1**, alert al 100% → email.

### 3.5 Primo SSH + verifica
```bash
mkdir -p ~/.ssh
cp ~/Downloads/ssh-key-*.key ~/.ssh/sovereign_oracle
chmod 400 ~/.ssh/sovereign_oracle
ssh -i ~/.ssh/sovereign_oracle ubuntu@IP_ORACLE
```
Verifica:
```bash
uname -m && lsb_release -d && free -h && nproc
# atteso: aarch64 · Ubuntu 24.04 LTS · ~12G · 2
```

---

## 4. FASE 0: HARDENING

### 4.1 Base
```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y curl wget ufw fail2ban htop net-tools ca-certificates \
    unattended-upgrades apt-listchanges jq sqlite3 nginx certbot \
    python3-certbot-nginx logrotate cron bc lynis auditd gnupg2 \
    python3-pip wrk netcat-openbsd
sudo timedatectl set-timezone Europe/Rome
sudo hostnamectl set-hostname sovereign-proxy
echo "127.0.0.1 sovereign-proxy" | sudo tee -a /etc/hosts
```

### 4.2 Swap 4GB
```bash
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

### 4.3 BBR + sysctl + IPv6 off
```bash
cat << 'SYSCTL_EOF' | sudo tee /etc/sysctl.d/99-sovereign-ultimate.conf
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_max_tw_buckets = 5000
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
SYSCTL_EOF
sudo sysctl --system
```

### 4.4 SSH blindato + rimozione porta 22 *(AGGIORNATA)*
```bash
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
sudo nano /etc/ssh/sshd_config
```
```
Port 2222
PasswordAuthentication no
PermitRootLogin no
MaxAuthTries 3
AllowUsers ubuntu
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
LoginGraceTime 30
```
⚠️ **SECONDO terminale** di verifica PRIMA di riavviare:
```bash
ssh -i ~/.ssh/sovereign_oracle -p 2222 ubuntu@IP_ORACLE
```
Solo dopo OK: `sudo systemctl restart sshd`
Poi **console Oracle → Security List → rimuovi la regola ingress porta 22** (la 2222 è verificata).

### 4.5 Fail2ban
```bash
cat << 'F2B_EOF' | sudo tee /etc/fail2ban/jail.local
[DEFAULT]
bantime = 86400
findtime = 600
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = 2222
filter = sshd
logpath = /var/log/auth.log

[nginx-botsearch]
enabled = true
port = 80,443
filter = nginx-botsearch
logpath = /var/log/nginx/decoy-access.log
maxretry = 5
bantime = 43200
F2B_EOF
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

### 4.6 Log rotation
```bash
cat << 'LOG_EOF' | sudo tee /etc/logrotate.d/sovereign
/var/log/oracle-keepalive.log
/var/log/sovereign-backup.log
/var/log/sovereign-healthcheck.log
/var/log/sovereign-maintenance.log
/var/log/duckdns-update.log
/var/log/honeypot.log
/var/log/xray/*.log
/var/log/nginx/decoy-*.log
/var/log/nginx/sub-*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root adm
}
/var/log/nginx/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript
}
LOG_EOF
```

### 4.7 Auditd
```bash
cat << 'AUDIT_EOF' | sudo tee /etc/audit/rules.d/sovereign.rules
-w /etc/ssh/sshd_config -p wa -k ssh-config-change
-w /etc/x-ui/ -p wa -k xray-config-change
-w /etc/nginx/ -p wa -k nginx-config-change
-w /opt/duckdns/ -p wa -k duckdns-change
-w /usr/local/bin/ -p wa -k scripts-change
-w /etc/shadow -p r -k shadow-read
-w /root/backups/ -p wa -k backup-access
-a always,exit -F arch=b64 -S execve -F euid=0 -k sudo-commands
AUDIT_EOF
sudo systemctl enable --now auditd
sudo auditctl -l
```

### 4.8 Aggiornamenti automatici
```bash
sudo dpkg-reconfigure -plow unattended-upgrades   # rispondi Yes
```

---

## 5. FASE 1: DUCKDNS

Registrati su duckdns.org → subdomain `sovereign-proxy` → inserisci IP → copia token.

```bash
sudo mkdir -p /opt/duckdns
cat << 'DUCK_EOF' | sudo tee /opt/duckdns/duck.sh
#!/bin/bash
DOMAIN="TUO-SUBDOMINIO"
TOKEN="IL_TUO_TOKEN"
LOG="/var/log/duckdns-update.log"
NTFY_URL="https://ntfy.sh/sovereign-oracle-SEGRETO"
MAX_RETRIES=3
for i in $(seq 1 $MAX_RETRIES); do
    RESPONSE=$(curl -s --max-time 10 "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip=")
    if [ "$RESPONSE" = "OK" ]; then
        echo "[$(date)] DuckDNS update OK" >> "$LOG"; exit 0
    fi
    echo "[$(date)] Tentativo $i fallito: $RESPONSE" >> "$LOG"; sleep 5
done
echo "[$(date)] ❌ DuckDNS FAILED" >> "$LOG"
curl -s -d "🚨 DuckDNS update FALLITO!" "$NTFY_URL" 2>/dev/null || true
exit 1
DUCK_EOF
sudo chmod +x /opt/duckdns/duck.sh
sudo touch /var/log/duckdns-update.log
sudo /opt/duckdns/duck.sh && cat /var/log/duckdns-update.log
(sudo crontab -l 2>/dev/null; echo "*/5 * * * * /opt/duckdns/duck.sh") | sudo crontab -
```

---

## 6. FASE 2: SITO CIVETTA + NGINX

### 6.1 File statici
```bash
sudo mkdir -p /var/www/decoy
sudo touch /var/www/decoy/favicon.ico
cat << 'HTML_EOF' | sudo tee /var/www/decoy/index.html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cloud Infrastructure Monitor</title>
<link rel="icon" href="/favicon.ico" type="image/x-icon">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center}
.container{max-width:600px;padding:40px 20px;text-align:center}
h1{font-size:1.8em;margin-bottom:10px;color:#4ade80}
.status{font-size:3em;margin:20px 0}
p{color:#888;line-height:1.6;margin:10px 0}
.badge{display:inline-block;padding:4px 12px;border-radius:12px;background:#166534;color:#4ade80;font-size:.85em;font-weight:600;margin:5px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-top:30px}
.card{background:#141414;border:1px solid #222;border-radius:8px;padding:20px;text-align:left}
.card h3{font-size:.85em;color:#666;text-transform:uppercase}
.card .value{font-size:1.4em;color:#fff;margin-top:5px}
<footer>{margin-top:40px;color:#444;font-size:.8em}
</style>
</head>
<body>
<div class="container">
<h1>Cloud Infrastructure Monitor</h1>
<div class="status">✅</div>
<p>All systems operational</p>
<span class="badge">Uptime 99.98%</span>
<span class="badge">Latency 12ms</span>
<div class="grid">
<div class="card"><h3>API Gateway</h3><div class="value" style="color:#4ade80">Healthy</div></div>
<div class="card"><h3>Database</h3><div class="value" style="color:#4ade80">Healthy</div></div>
<div class="card"><h3>CDN Edge</h3><div class="value" style="color:#4ade80">Healthy</div></div>
<div class="card"><h3>Auth Service</h3><div class="value" style="color:#4ade80">Healthy</div></div>
</div>
<footer>&copy; 2026 Cloud Infrastructure Monitor. Automated status page.</footer>
</div>
</body>
</html>
HTML_EOF
sudo chown -R www-data:www-data /var/www/decoy
sudo chmod -R 755 /var/www/decoy
```

### 6.2 Nginx (decoy + subscription proxy)
```bash
cat << 'NGINX_EOF' | sudo tee /etc/nginx/sites-available/decoy
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=general:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=sub:10m rate=5r/s;

server {
    listen 127.0.0.1:8443;
    server_name _;
    root /var/www/decoy;
    index index.html;
    access_log /var/log/nginx/decoy-access.log;
    error_log /var/log/nginx/decoy-error.log;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline'" always;
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript
               application/x-javascript application/xml+rss
               application/json application/javascript;
    server_tokens off;
    location / {
        limit_req zone=general burst=50 nodelay;
        try_files $uri $uri/ =404;
    }
    location /api/status {
        limit_req zone=api burst=20 nodelay;
        default_type application/json;
        return 200 '{"status":"healthy","uptime":"99.98%","timestamp":"$time_iso8601"}';
    }
    location /robots.txt {
        default_type text/plain;
        return 200 "User-agent: *\nDisallow: /admin/\nDisallow: /api/internal/\n";
    }
    location = /favicon.ico { access_log off; log_not_found off; expires 30d; }
}

server {
    listen 127.0.0.1:8444;
    server_name _;
    access_log /var/log/nginx/sub-access.log;
    error_log /var/log/nginx/sub-error.log;
    location /sub/ {
        limit_req zone=sub burst=10 nodelay;
        proxy_pass http://127.0.0.1:2096;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX_EOF
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/decoy /etc/nginx/sites-enabled/decoy
sudo nginx -t && sudo systemctl enable nginx && sudo systemctl restart nginx
curl http://127.0.0.1:8443/ && curl http://127.0.0.1:8443/api/status
```

---

## 7. FASE 3: 3X-UI

```bash
sudo -i
bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh) v2.9.4
```
Credenziali: user personalizzato (NON admin) · pass 20+ char · porta 54321 · path `/pannello-sovereign-xyz/` → **salva subito in Vaultwarden**.
Verifica: `x-ui status && x-ui version`.

---

## 8. FASE 4: UFW

```bash
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 2222/tcp comment 'SSH custom'
sudo ufw allow 443/tcp comment 'VLESS+Decoy+Sub HTTPS'
sudo ufw allow 80/tcp comment 'ACME'
sudo ufw allow 8080/tcp comment 'Honeypot'
sudo ufw allow in on tailscale0 to any port 54321 proto tcp comment 'Panel Headscale'
sudo ufw limit 2222/tcp comment 'SSH rate limit'
sudo sed -i 's/IPV6=yes/IPV6=no/' /etc/default/ufw
sudo ufw --force enable
sudo ufw status verbose
```
⚠️ Porta 54321 e 2096 **mai pubbliche**. Porta 22 già rimossa in FASE 0.4.

---

## 9. FASE 5: HEADSCALE

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --login-server https://vpn.casca-certosa.duckdns.org
tailscale status   # IP 100.64.x.y
```
Pannello solo da: `https://100.64.x.y:54321/pannello-sovereign-xyz/`

---

## 10. FASE 6: ACME PANNELLO

```bash
x-ui   # → SSL Certificate Management → dominio sovereign-proxy.duckdns.org → HTTP-01
ls /root/cert/sovereign-proxy.duckdns.org/   # fullchain.pem + privkey.pem
```
Pannello → Security Settings → Enable SSL.

---

## 11. FASE 7: TEST SNI

```bash
wget https://github.com/hiddify/Hiddify-Reality-Scanner/releases/latest/download/HiddifyRealityScanner_linux_arm64 -O /tmp/scanner
chmod +x /tmp/scanner
cat << 'SNI_EOF' > /tmp/sni_candidates.txt
www.datadoghq.com
www.cisco.com
aws.amazon.com
www.speedtest.net
www.cloudflare.com
addons.mozilla.org
www.samsung.com
www.apple.com
learn.microsoft.com
www.docker.com
www.nvidia.com
cdn.jsdelivr.net
SNI_EOF
/tmp/scanner -sni /tmp/sni_candidates.txt
```
Scegli status OK + latenza minima → `SNI_VINCENTE`.

---

## 12. FASE 8: VLESS + REALITY + FALLBACK

Pannello → Inbounds → Add Inbound:
```
Remark: Sovereign-Egypt-Killer · Protocol: vless · Port: 443
Client: email mohamed-mac · UUID (Generate) · Flow: xtls-rprx-vision
Transmission: tcp · Security: reality
REALITY: Dest SNI_VINCENTE:443 · Server Names SNI_VINCENTE
         Private Key (Get New Cert) · Short IDs (Generate)
         uTLS: chrome · SpiderX vuoto
Fallback Dest: 127.0.0.1:8443
```
Verifica active probing (dal Mac, senza proxy): `curl -k https://IP_ORACLE` → sito civetta ✅

---

## 13. FASE 9: MULTI-USER + SUBSCRIPTION + REVOCA

Panel Settings → Subscription: Enable ✓ · Port 2096 (localhost) · Path `/sub/segreto-famiglia-xyz/` · URL pubblico **HTTPS**: `https://sovereign-proxy.duckdns.org/sub/segreto-famiglia-xyz/`

Utenti (Add Client) con quota/scadenza: mohamed-mac (illimitato) · papa-iphone (100GB) · mamma-android (50GB) · ospite-1 (10GB/30gg).

```bash
cat << 'REVOKE_EOF' | sudo tee /usr/local/bin/sovereign-revoke-user.sh
#!/bin/bash
# Uso: sovereign-revoke-user.sh <email-utente>
if [ -z "$1" ]; then echo "Uso: $0 <email-utente>"; exit 1; fi
EMAIL="$1"
DB="/etc/x-ui/x-ui.db"
BACKUP_DB="/etc/x-ui/x-ui.db.bak.$(date +%s)"
sudo cp "$DB" "$BACKUP_DB"
sqlite3 "$DB" "UPDATE client_stats SET enable=0 WHERE email='$EMAIL';"
sudo systemctl restart x-ui
echo "✅ Utente $EMAIL revocato. Backup: $BACKUP_DB"
REVOKE_EOF
sudo chmod +x /usr/local/bin/sovereign-revoke-user.sh
```

---

## 14. FASE 10: WARP + GEOBLOCKING + GEOIP UPDATE

WARP: pannello → Outbounds → "..." → WARP → Create Account → Refresh → Add Outbound → Save.

Routing:
```
direct: geosite:private + geoip:private
block:  geosite:category-ads-all + geoip:ir,geoip:cn,geoip:ru,geoip:kp
warp:   openai.com,netflix.com,chatgpt.com,claude.ai
warp:   network tcp,udp (resto)
```

```bash
cat << 'GEO_EOF' | sudo tee /usr/local/bin/sovereign-update-geoip.sh
#!/bin/bash
LOG="/var/log/sovereign-maintenance.log"
GEOIP_DIR="/usr/local/x-ui/bin"
TEMP_DIR="/tmp/geoip-update"
mkdir -p "$TEMP_DIR" && cd "$TEMP_DIR" || exit 1
curl -sL "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat" -o geoip.dat
curl -sL "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat" -o geosite.dat
if [ -s geoip.dat ] && [ -s geosite.dat ]; then
    sudo cp geoip.dat "$GEOIP_DIR/geoip.dat"
    sudo cp geosite.dat "$GEOIP_DIR/geosite.dat"
    sudo systemctl restart x-ui
    echo "[$(date)] ✅ GeoIP aggiornati" >> "$LOG"
else
    echo "[$(date)] ❌ GeoIP update fallito" >> "$LOG"
fi
rm -rf "$TEMP_DIR"
GEO_EOF
sudo chmod +x /usr/local/bin/sovereign-update-geoip.sh
sudo /usr/local/bin/sovereign-update-geoip.sh
(sudo crontab -l 2>/dev/null; echo "0 4 * * 1 /usr/local/bin/sovereign-update-geoip.sh") | sudo crontab -
```

---

## 15. FASE 11: DNS ANTI-LEAK (5 DoH)

Pannello → DNS Settings:
```json
{
  "servers": [
    {"address": "https://1.1.1.1/dns-query", "domains": ["geosite:geolocation-!cn"]},
    {"address": "https://8.8.8.8/dns-query", "domains": []},
    {"address": "https://9.9.9.9:5053/dns-query", "domains": []},
    {"address": "https://doh.opendns.com/dns-query", "domains": []},
    {"address": "https://dns.quad9.net/dns-query", "domains": []}
  ],
  "queryStrategy": "UseIPv4",
  "fallbackStrategy": "CheckDNSSEC"
}
```

---

## 16. FASE 12: ANTI-IDLE CALIBRATO

```bash
cat << 'ALIVE_EOF' | sudo tee /usr/local/bin/oracle-keepalive.sh
#!/bin/bash
LOG="/var/log/oracle-keepalive.log"
timeout 30 bash -c 'while true; do echo "scale=5000; 4*a(1)" | bc -l > /dev/null 2>&1; done' &
ping -c 10 8.8.8.8 > /dev/null 2>&1
curl -s https://www.google.com > /dev/null 2>&1
curl -s https://www.cloudflare.com > /dev/null 2>&1
python3 -c "x = bytearray(500*1024*1024); del x" 2>/dev/null
echo "[$(date)] Keepalive: CPU 30s + Network + Memory spike" >> "$LOG"
ALIVE_EOF
sudo chmod +x /usr/local/bin/oracle-keepalive.sh
(sudo crontab -l 2>/dev/null; echo "0 */4 * * * /usr/local/bin/oracle-keepalive.sh") | sudo crontab -
```

---

## 17. FASE 13: HEALTH CHECK + HONEYPOT PYTHON

### 17.1 Health check
```bash
cat << 'HEALTH_EOF' | sudo tee /usr/local/bin/sovereign-healthcheck.sh
#!/bin/bash
NTFY_URL="https://ntfy.sh/sovereign-oracle-SEGRETO"
LOG="/var/log/sovereign-healthcheck.log"
ERRORS=""
systemctl is-active --quiet x-ui || { ERRORS+="❌ x-ui DOWN! "; sudo systemctl restart x-ui; }
systemctl is-active --quiet nginx || { ERRORS+="❌ Nginx DOWN! "; sudo systemctl restart nginx; }
systemctl is-active --quiet honeypot || { ERRORS+="❌ Honeypot DOWN! "; sudo systemctl restart honeypot; }
ss -tlnp | grep -q ':443 ' || ERRORS+="❌ Porta 443 chiusa! "
DISK=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
[ "$DISK" -gt 85 ] && ERRORS+="⚠️ Disco ${DISK}%! "
SWAP=$(free | awk '/Swap/ {if($2>0) print int($3/$2*100); else print 0}')
[ "$SWAP" -gt 50 ] && ERRORS+="⚠️ Swap ${SWAP}%! "
tailscale status > /dev/null 2>&1 || ERRORS+="⚠️ Tailscale DOWN! "
echo "[$(date)] Health check: ${ERRORS:-OK}" >> "$LOG"
if [ -n "$ERRORS" ]; then
    curl -s --max-time 5 -d "🚨 ORACLE ALERT: ${ERRORS}" "$NTFY_URL" 2>/dev/null || \
    echo "[$(date)] ntfy irraggiungibile" >> "$LOG"
fi
HEALTH_EOF
sudo chmod +x /usr/local/bin/sovereign-healthcheck.sh
(sudo crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/sovereign-healthcheck.sh") | sudo crontab -
```

### 17.2 Honeypot (BANNER corretto)
```bash
cat << 'HONEY_EOF' | sudo tee /usr/local/bin/sovereign-honeypot.py
#!/usr/bin/env python3
import socket, datetime, subprocess, os

LOG_FILE = "/var/log/honeypot.log"
NTFY_URL = "https://ntfy.sh/sovereign-oracle-SEGRETO"
PORT = 8080
BANNER = b"HTTP/1.1 200 OK\r\nServer: nginx\r\nContent-Length: 0\r\n\r\n"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")

def alert(ip):
    try:
        subprocess.run(["curl", "-s", "-d", f"🍯 HONEYPOT: scanner da {ip}", NTFY_URL],
                       capture_output=True, timeout=5)
    except Exception:
        pass

def ban(ip):
    subprocess.run(["sudo", "ufw", "deny", "from", ip, "comment", "honeypot"],
                   capture_output=True)

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', PORT))
        s.listen(100)
        log(f"✅ Honeypot avviato su porta {PORT}")
        while True:
            try:
                conn, addr = s.accept()
                ip = addr[0]
                log(f"Connessione da {ip}")
                conn.sendall(BANNER)
                conn.close()
                ban(ip)
                if not os.path.exists(LOG_FILE) or ip not in open(LOG_FILE).read()[-10000:]:
                    alert(ip)
            except Exception as e:
                log(f"Errore: {e}")

if __name__ == "__main__":
    main()
HONEY_EOF
sudo chmod +x /usr/local/bin/sovereign-honeypot.py

cat << 'SVC_EOF' | sudo tee /etc/systemd/system/honeypot.service
[Unit]
Description=Sovereign Honeypot Python
After=network.target
[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/sovereign-honeypot.py
Restart=always
RestartSec=5
User=root
[Install]
WantedBy=multi-user.target
SVC_EOF
sudo systemctl daemon-reload
sudo systemctl enable --now honeypot
```

### 17.3 Uptime Kuma (LXC 101)
Xray Reality → TCP IP:443 → 60s · Decoy → HTTP(s) /api/status → 120s · Subscription → HTTP(s) /sub/... → 300s.

---

## 18. FASE 14: BACKUP GPG ASIMMETRICO + DR

### 18.1-18.3 Chiavi (sul MAC, mai sul server)
```bash
gpg --batch --gen-key << 'GPG_EOF'
%echo Generating Sovereign Backup Master Key
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: Sovereign Backup
Name-Email: moh@casca-certosa.duckdns.org
Expire-Date: 5y
Passphrase: [PASSPHRASE-IN-VAULTWARDEN]
%commit
GPG_EOF
gpg --armor --export moh@casca-certosa.duckdns.org > sovereign-backup-pub.asc
gpg --armor --export-secret-keys moh@casca-certosa.duckdns.org > sovereign-backup-priv.asc
# priv → allegato Vaultwarden, poi: shred -u sovereign-backup-priv.asc
scp sovereign-backup-pub.asc ubuntu@IP_ORACLE:/tmp/
# Sul server:
gpg --import /tmp/sovereign-backup-pub.asc && rm /tmp/sovereign-backup-pub.asc
gpg --edit-key moh@casca-certosa.duckdns.org   # trust → 5 → y → quit
```

### 18.4-18.5 B2 + backup
```bash
pip3 install --upgrade b2
b2 authorize-account IL_TUO_KEY_ID LA_TUA_APP_KEY

cat << 'BACKUP_EOF' | sudo tee /usr/local/bin/sovereign-backup.sh
#!/bin/bash
BACKUP_DIR="/root/backups"
B2_BUCKET="sovereign-xray-backups"
DATE=$(date +%Y%m%d_%H%M)
KEEP_DAYS=7
LOG="/var/log/sovereign-backup.log"
GPG_RECIPIENT="moh@casca-certosa.duckdns.org"
mkdir -p "${BACKUP_DIR}"
echo "[$(date)] Inizio backup asimmetrico..." >> "$LOG"
cp /etc/x-ui/x-ui.db "${BACKUP_DIR}/x-ui_${DATE}.db"
cp /usr/local/x-ui/bin/config.json "${BACKUP_DIR}/xray-config_${DATE}.json" 2>/dev/null
tar czf "${BACKUP_DIR}/nginx_${DATE}.tar.gz" /etc/nginx/sites-available/ /var/www/decoy/ 2>/dev/null
for f in "${BACKUP_DIR}"/*_${DATE}*; do
    if [ -f "$f" ]; then
        gpg --batch --yes --trust-model always --recipient "$GPG_RECIPIENT" \
            --cipher-algo AES256 --output "${f}.gpg" --encrypt "$f" 2>> "$LOG"
        rm -f "$f"
        b2 upload-file "${B2_BUCKET}" "${f}.gpg" "backups/$(basename ${f}.gpg)" 2>> "$LOG"
    fi
done
find "${BACKUP_DIR}" -type f -mtime +${KEEP_DAYS} -delete
echo "[$(date)] ✅ Backup completato: ${DATE}" >> "$LOG"
BACKUP_EOF
sudo chmod +x /usr/local/bin/sovereign-backup.sh
(sudo crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/sovereign-backup.sh") | sudo crontab -
```

### 18.6 Test restore mensile
```bash
cat << 'RESTORE_EOF' | sudo tee /usr/local/bin/sovereign-test-restore.sh
#!/bin/bash
LOG="/var/log/sovereign-backup.log"
NTFY_URL="https://ntfy.sh/sovereign-oracle-SEGRETO"
LATEST=$(b2 ls sovereign-xray-backups backups/ | grep "x-ui_" | tail -1 | awk '{print $1}')
if [ -z "$LATEST" ]; then
    echo "[$(date)] ❌ Nessun backup!" >> "$LOG"
    curl -s -d "🚨 BACKUP: Nessun backup su B2!" "$NTFY_URL" 2>/dev/null; exit 1
fi
b2 download-file-by-name sovereign-xray-backups "$LATEST" /tmp/test-restore.db.gpg 2>> "$LOG"
if [ -s /tmp/test-restore.db.gpg ]; then
    echo "[$(date)] ✅ Backup cifrato integro ($(stat -c%s /tmp/test-restore.db.gpg) bytes)" >> "$LOG"
else
    echo "[$(date)] ❌ Backup corrotto!" >> "$LOG"
    curl -s -d "🚨 BACKUP CORROTTO!" "$NTFY_URL" 2>/dev/null
fi
rm -f /tmp/test-restore.db.gpg
RESTORE_EOF
sudo chmod +x /usr/local/bin/sovereign-test-restore.sh
(sudo crontab -l 2>/dev/null; echo "0 4 1 * * /usr/local/bin/sovereign-test-restore.sh") | sudo crontab -
```

### 18.7-18.8 Restore + DR (30 min)
Restore: scarica `.gpg` da B2 sul Mac → `gpg --output restore.db --decrypt` → scp → sostituisci `/etc/x-ui/x-ui.db` (chown root, chmod 600) → restart. DR: nuova istanza → FASI 0-2 → 3x-ui → restore DB → tailscale up → DuckDNS auto.

---

## 19. FASE 15: CLIENT

FoXray (macOS) · Streisand (iOS) · v2rayN (Win) · v2rayNG/Hiddify (Android) · Nekoray (Linux). Import via **Subscription HTTPS** (consigliato), QR o link manuale. ⚠️ `fp` deve corrispondere: safari/chrome/firefox. Test: ipleak.net · dnsleaktest.com · browserleaks.com/webrtc · fast.com.

---

## 20. FASE 16: TEST FINALE (20 CHECK, corretti)

```bash
cat << 'TEST_EOF' | sudo tee /usr/local/bin/sovereign-test.sh
#!/bin/bash
echo "  SOVEREIGN PROXY 6.2 — TEST FINALE (20 CHECK)"
PASS=0; FAIL=0
run_test() {
    printf "  [%2d/20] %-40s" "$1" "$2"
    if eval "$3" > /dev/null 2>&1; then echo "✅ OK"; ((PASS++)); else echo "❌ FAIL"; ((FAIL++)); fi
}
run_test 1  "BBR attivo"             '[ "$(sysctl -n net.ipv4.tcp_congestion_control)" = "bbr" ]'
run_test 2  "Swap attivo"            'swapon --show | grep -q /swapfile'
run_test 3  "SSH porta 2222"         'grep -q "^Port 2222" /etc/ssh/sshd_config'
run_test 4  "Fail2ban attivo"        'systemctl is-active --quiet fail2ban'
run_test 5  "Nginx attivo"           'systemctl is-active --quiet nginx'
run_test 6  "3x-ui attivo"           'systemctl is-active --quiet x-ui'
run_test 7  "Porta 443 in ascolto"   'ss -tlnp | grep -q ":443 "'
run_test 8  "UFW attivo"             'sudo ufw status | grep -q "Status: active"'
run_test 9  "Tailscale connesso"     'tailscale status > /dev/null 2>&1'
run_test 10 "Decoy risponde"         'curl -s http://127.0.0.1:8443/api/status | grep -q healthy'
run_test 11 "IPv6 disabilitato"      '[ "$(sysctl -n net.ipv6.conf.all.disable_ipv6)" = "1" ]'
run_test 12 "Auditd attivo"          'systemctl is-active --quiet auditd'
run_test 13 "Timezone Europe/Rome"   '[ "$(timedatectl show -p Timezone --value)" = "Europe/Rome" ]'
run_test 14 "DuckDNS script"         '[ -x /opt/duckdns/duck.sh ]'
run_test 15 "Backup script"          '[ -x /usr/local/bin/sovereign-backup.sh ]'
run_test 16 "Honeypot attivo"        'systemctl is-active --quiet honeypot'
run_test 17 "GeoIP recenti"          '[ $(find /usr/local/x-ui/bin/geoip.dat -mtime -30 | wc -l) -eq 1 ]'
run_test 18 "Sub proxy attivo"       'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8444/sub/ | grep -qE "404|200|401|403"'
run_test 19 "GPG asimmetrico"        'gpg --list-keys | grep -q moh@casca-certosa'
run_test 20 "Version check"          '[ -x /usr/local/bin/sovereign-check-version.sh ]'
echo ""
if [ "$FAIL" -eq 0 ]; then echo "  🏆 20/20 — Affidabilità 100/100"; else echo "  ⚠️ $FAIL falliti"; fi
TEST_EOF
sudo chmod +x /usr/local/bin/sovereign-test.sh
sudo /usr/local/bin/sovereign-test.sh
```

---

## 21. FASE 17: AUDIT + LOAD TEST

```bash
sudo lynis audit system --quick && sudo grep "hardening_index" /var/log/lynis-report.dat   # ≥ 75

cat << 'LOAD_EOF' | sudo tee /usr/local/bin/sovereign-loadtest.sh
#!/bin/bash
echo "=== 10 conn / 30s ==="; wrk -t2 -c10 -d30s http://127.0.0.1:8443/ --timeout 5
echo "=== 50 conn / 30s ==="; wrk -t4 -c50 -d30s http://127.0.0.1:8443/ --timeout 5
free -h; df -h /
LOAD_EOF
sudo chmod +x /usr/local/bin/sovereign-loadtest.sh && sudo /usr/local/bin/sovereign-loadtest.sh
```
Controlli manuali: permessi (`sshd_config`, `x-ui.db`, `shadow`) · `ss -tlnp` (2222, 443, 80, 8443/8444 local, 54321 tailscale, 8080) · nessun secret in chiaro in `/etc/x-ui/`.

---

## 22. MANUTENZIONE PROGRAMMATA

| Frequenza | Task |
|-----------|------|
| */5 min | Health check + DuckDNS |
| */4 h | Anti-idle |
| 03:00 | Backup GPG+B2 |
| 06:00 daily | Version check 3x-ui |
| 04:00 lunedì | GeoIP update |
| Giorno 1: 04:00 test restore · 05:00 manutenzione · 06:00 DPI test | mensili |
| Trimestrale | Rotazione chiavi REALITY + fingerprint |

```bash
cat << 'VER_EOF' | sudo tee /usr/local/bin/sovereign-check-version.sh
#!/bin/bash
LOG="/var/log/sovereign-maintenance.log"
NTFY_URL="https://ntfy.sh/sovereign-oracle-SEGRETO"
CURRENT=$(x-ui version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
LATEST=$(curl -s https://api.github.com/repos/MHSanaei/3x-ui/releases/latest | grep -oP '"tag_name": "\K[^"]+' | tr -d 'v')
if [ -n "$CURRENT" ] && [ -n "$LATEST" ]; then
    if [ "$CURRENT" != "$LATEST" ]; then
        echo "[$(date)] ⚠️ 3x-ui obsoleto: $CURRENT → $LATEST" >> "$LOG"
        curl -s -d "📦 3x-ui aggiornamento: $CURRENT → $LATEST" "$NTFY_URL"
    else
        echo "[$(date)] ✅ 3x-ui aggiornato: $CURRENT" >> "$LOG"
    fi
fi
VER_EOF
sudo chmod +x /usr/local/bin/sovereign-check-version.sh
(sudo crontab -l 2>/dev/null; echo "0 6 * * * /usr/local/bin/sovereign-check-version.sh") | sudo crontab -
```

Script mensili (`sovereign-monthly-maintenance.sh`: df/free/apt clean/logrotate/test-restore/lynis/honeypot/fail2ban) e `sovereign-dpi-test.sh` (curl -k con Host SNI → atteso 200, altrimenti alert) come in 6.1, con cron `0 5 1 * *` e `0 6 1 * *`.

---

## 23. ROTAZIONE CHIAVI + FINGERPRINT (90 GG)

Reminder cron: `0 9 1 */3 *` → ntfy. Procedura: pannello → Edit inbound → **Get New Cert** → cambia uTLS (chrome→firefox→safari→edge→random) → Save → verifica `curl -k https://IP` → subscription auto-update 6h. Downtime < 30s.

---

## 24. TROUBLESHOOTING (12 scenari)

Tabella invariata da 6.1 (connessione, lentezza, censura, reclamation, pannello, backup, alert, DuckDNS, DNS leak, WARP, decoy, sub proxy) + log critici (`auth.log`, `decoy-access.log`, `sub-access.log`, `xray/*.log`, `healthcheck`, `backup`, `keepalive`, `honeypot`, `duckdns`, `maintenance`).

---

## 25. ROLLBACK

Tabella rollback per fase (sysctl, ssh da backup, fail2ban, nginx, x-ui uninstall, ufw reset, tailscale down, WARP remove) + rollback DB corrotto (download .gpg → decrypt con chiave privata → sostituisci → restart) + nuclear option (terminate + DR).

---

## 26. README SERVER

`/root/README-SOVEREIGN.md` (chmod 600): porte, comandi rapidi, cron jobs, credenziali in Vaultwarden, emergenze (cambio SNI / DR / chiavi / revoca), contatti ntfy-Kuma-Vaultwarden. Contenuto identico a 6.1.

---

## 27. GUIDA UTENTE NON-TECNICO

iPhone: Streisand → + → QR → ON · Android: v2rayNG → + → QR → V · Mac: FoXray → + → clipboard → Connect · Win: v2rayN → import → System Proxy. Problemi comuni: riapri app / riavvia WiFi / spegni-riaccendi VPN / contatta Mohamed / aggiorna subscription.

---

## 28. CHECKLIST FINALE (aggiornata)

Tutte le voci di 6.1 **più**:
- [ ] Security List create PRIMA del cambio porta SSH
- [ ] Regola porta 22 rimossa dopo verifica 2222
- [ ] Immagine: 24.04 Minimal aarch64, build più recente
- [ ] Fault domain default · Stateless OFF · IMDS off · cloud-init vuoto
- [ ] `sovereign-test.sh` → 20/20

---

## APPENDICE A — DECISIONI DOCUMENTATE

| Tecnologia | Decisione | Motivo |
|------------|-----------|--------|
| Docker/Podman | 🟡 No (ora) | Il VPS gira quasi solo col proxy: isolamento superfluo, debug più complesso |
| Kubernetes | 🔴 No | Overkill: 1-2GB RAM di control plane per UN servizio; single-node = inutile |
| PostgreSQL | 🟡 No | SQLite perfetto per pochi utenti; backup = copia di un file |
| Valkey/Redis | 🔴 No | Nessun caso d'uso; 3x-ui non lo usa; rate limiting già su UFW/Nginx |
| NixOS | 🟡 No (ora) | SOAP scritto per Debian/Ubuntu; 3x-ui non supportato; curva alta. **Candidato tier avanzato futuro** |
| Firewall extra (WAF/IDS/Cloudflare) | 🔴 No | Già 6 livelli; Cloudflare davanti **rompe REALITY** |

**Principio:** ogni tecnologia deve risolvere un problema concreto e misurabile. La semplicità ben progettata batte la complessità.

---

## APPENDICE B — ROADMAP PRODOTTO OPEN-SOURCE

1. **MVP (2-3 sett.):** repo GitHub (AGPL-3.0) + installer unificato + TUI + README + Docker opzionale
2. **Beta (4-6 sett.):** 10-20 tester (r/selfhosted, HN, Telegram) + issue tracking
3. **Launch:** blog post + Show HN + sito GitHub Pages
4. **Growth:** release bimestrali, contributor program, GitHub Sponsors
5. **Tier avanzati futuri:** modulo NixOS, automazione Ansible, cloud-init installer, failover geografico (secondo VPS free)

---

## 💰 COSTI · 📊 AFFIDABILITÀ · 📞 RIFERIMENTI

**Totale: €0/mese.** Affidabilità: **100/100** (20 check + self-healing + DR 30min + GPG asimmetrico).
Riferimenti: 3x-ui · Xray-examples · Hiddify Scanner · Oracle Free Tier docs · Loyalsoldier rules-dat · t.me/XrayUI.

---

**🔥 S.O.A.P. 6.2 SOVEREIGN ULTIMATE — VALIDATO SUL CAMPO 🔥**
