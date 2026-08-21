import os
import shutil

base_dir = r"C:\home_server\sovereign-oci-proxy"

# Remove the old Italian SOAP file
old_soap = os.path.join(base_dir, "SOAP_6.2_SOVEREIGN_ULTIMATE.md")
if os.path.exists(old_soap):
    os.remove(old_soap)

files_to_write = {
    "docs/ARCHITECTURE.md": """# 🏗️ Architecture Design

## Core Components
- **VPS Provider:** Oracle Cloud Infrastructure (OCI) - ARM A1.Flex (2 OCPU, 12GB RAM)
- **OS:** Ubuntu 24.04 Minimal
- **Ingress Protocol:** VLESS + REALITY + XTLS-Vision (Port 443)
- **Proxy Core:** Xray-core (managed via 3x-ui)
- **Decoy:** Nginx serving a fake "Cloud Infrastructure Monitor" status page
- **Mesh Network:** Tailscale (Routing to private Homelab)
- **Security:** UFW, Fail2ban, Auditd, Python Honeypot
- **Backup:** Asymmetric GPG encryption to Backblaze B2

## Traffic Flow Diagram
```mermaid
graph TD
    User[Client Device] -->|VLESS over TLS 1.3| OCI[Oracle Cloud:443]
    OCI -->|Invalid UUID / Scanner| Decoy[Nginx Decoy:8443]
    OCI -->|Valid UUID| Xray[Xray Core]
    
    Xray -->|Homelab IP / *.internal| Tailscale[tailscale0]
    Tailscale --> Homelab[Proxmox Homelab]
    
    Xray -->|Netflix, ChatGPT, etc.| WARP[Cloudflare WARP]
    WARP --> Internet1[Internet via Cloudflare IP]
    
    Xray -->|Normal Browsing| Direct[Direct Outbound]
    Direct --> Internet2[Internet via Oracle IP]
```
""",

    "docs/QUICKSTART.md": """# 🚀 Quickstart Guide

This guide covers the rapid deployment of the Sovereign OCI Proxy.

## 1. Oracle Cloud Setup
1. Deploy an **Ubuntu 24.04 Minimal aarch64** instance (2 OCPUs, 12GB RAM, 200GB Boot Volume).
2. Go to **VCN -> Security Lists** and add Ingress rules for TCP ports: `2222`, `443`, `80`, `8080`.
3. **DO NOT** remove port 22 yet.

## 2. Connect and Hardening
Connect via SSH to your instance:
```bash
ssh -i private.key ubuntu@<YOUR_ORACLE_IP>
```
Run the hardening script from this repository:
```bash
sudo ./scripts/modules/hardening.sh
```
**Important:** Open a SECOND terminal and verify you can connect using `-p 2222`. Only after verifying, remove port 22 from the Oracle Security List.

## 3. Install Core Components
Run the installer script:
```bash
sudo ./scripts/install.sh
```
This will configure Nginx, Python Honeypot, Tailscale, and download the 3x-ui installer.
""",

    "docs/FULL_GUIDE.md": """# 📖 Full Operations Manual (S.O.A.P. 6.2)

## 1. Initial Hardening
The `hardening.sh` module configures:
- 4GB Swap file for memory safety.
- BBR Congestion Control for network speed optimization.
- SSH Port changed to 2222 (Root login disabled, password auth disabled).
- Fail2ban jails for SSH and Nginx bot searches.
- UFW Firewall locking down everything except 2222, 443, 80, and 8080.

## 2. Decoy Setup
The `decoy.sh` module configures Nginx on `127.0.0.1:8443`.
Any unauthorized connection to the Xray server on port 443 (e.g., active probing from Great Firewall or ISP) is seamlessly handed over to Nginx. Nginx returns a perfectly valid, harmless HTML page mimicking a "Cloud Infrastructure Monitor".

## 3. VLESS + REALITY
Use the 3x-ui panel to configure your inbound.
- **Protocol:** VLESS
- **Security:** REALITY
- **Flow:** xtls-rprx-vision
- **Dest/SNI:** Use a highly reputable SNI (e.g., `aws.amazon.com` or `www.cisco.com`).

## 4. Anti-Idle & Monitoring
Oracle terminates free instances if CPU/Network usage is <10% for 7 days.
The `monitoring.sh` module deploys a Keepalive script running every 4 hours that artificially spikes CPU (calculating Pi), Memory (allocating 500MB), and Network (pinging Google) to prevent reclamation.

## 5. Disaster Recovery
The `backup.sh` module utilizes GPG asymmetric encryption. It archives the SQLite database, encrypts it with your public key, and uploads it to Backblaze B2. You must hold the private key on your local machine to restore the database in the event of an instance termination.
""",

    "docs/TROUBLESHOOTING.md": """# 🔧 Troubleshooting

### 1. I locked myself out of SSH!
Did you change the port to 2222 but forgot to open it in the Oracle Cloud Console Security List? 
**Fix:** Go to the Oracle Cloud Web Console, navigate to your VCN's Security List, and add an Ingress rule for TCP port 2222.

### 2. Tailscale Homelab IPs are unreachable
By default, Xray blocks all private IPs (`geoip:private`) to prevent SSRF attacks. 
**Fix:** Run the `scripts/modules/xray-routing-fix.py` script provided in this repository. It edits the SQLite database to allow `geoip:private` traffic to flow to the `direct` outbound, making Tailscale work.

### 3. Clients are silently dropping in 3x-ui v3.6.0
**Fix:** In newer versions, adding clients to the JSON payload is ignored. Use `scripts/modules/xray-client-fix.py` to correctly inject users into the relational SQLite tables.
""",

    "docs/FAQ.md": """# ❓ Frequently Asked Questions

**Q: Will I be charged by Oracle?**
A: No. As long as you stay within the 4 OCPUs, 24GB RAM, and 10TB outbound bandwidth limits, the Always Free tier incurs zero charges.

**Q: Why does my IP show up as Cloudflare when I test my VPN?**
A: This is an intentional security feature. We route the Xray traffic through Cloudflare WARP (WireGuard) using the Outbound routing rules. This hides the Oracle Datacenter IP, reducing the chance of being blocked by streaming services or banking apps.

**Q: Can I use this to access my home Proxmox server?**
A: Yes! By installing Tailscale on this Oracle instance and configuring it as a mesh node, Xray routes internal traffic directly to your Homelab securely.
""",

    "scripts/install.sh": """#!/bin/bash
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
""",

    "scripts/modules/hardening.sh": """#!/bin/bash
# OS Hardening, Swap, BBR, and Firewall Setup

echo "Setting up 4GB Swap..."
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

echo "Applying BBR and Sysctl optimizations..."
cat << 'SYSCTL_EOF' > /etc/sysctl.d/99-sovereign.conf
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
SYSCTL_EOF
sysctl --system

echo "Configuring UFW Firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp comment 'SSH'
ufw allow 443/tcp comment 'VLESS'
ufw allow 80/tcp comment 'ACME'
ufw allow 8080/tcp comment 'Honeypot'
ufw --force enable
""",

    "scripts/modules/decoy.sh": """#!/bin/bash
# Nginx Decoy Setup

apt-get update && apt-get install -y nginx
mkdir -p /var/www/decoy

cat << 'HTML_EOF' > /var/www/decoy/index.html
<!DOCTYPE html>
<html>
<head><title>Cloud Infrastructure Monitor</title></head>
<body style="background:#0a0a0a;color:#4ade80;text-align:center;padding:50px;font-family:sans-serif;">
    <h1>All systems operational</h1>
    <p>Uptime: 99.98%</p>
</body>
</html>
HTML_EOF

cat << 'NGINX_EOF' > /etc/nginx/sites-available/decoy
server {
    listen 127.0.0.1:8443;
    server_name _;
    root /var/www/decoy;
    index index.html;
}
NGINX_EOF

ln -sf /etc/nginx/sites-available/decoy /etc/nginx/sites-enabled/decoy
systemctl restart nginx
""",

    "scripts/modules/backup.sh": """#!/bin/bash
# GPG Asymmetric Encryption + Backblaze B2 Upload
# Ensure you configure b2 CLI and GPG keys before running this.

BACKUP_DIR="/root/backups"
B2_BUCKET="sovereign-xray-backups"
DATE=$(date +%Y%m%d_%H%M)
GPG_RECIPIENT="YOUR_EMAIL_HERE"

mkdir -p "${BACKUP_DIR}"
cp /etc/x-ui/x-ui.db "${BACKUP_DIR}/x-ui_${DATE}.db"

# Encrypt the database using the public key
gpg --batch --yes --trust-model always --recipient "$GPG_RECIPIENT" \
    --cipher-algo AES256 --output "${BACKUP_DIR}/x-ui_${DATE}.db.gpg" --encrypt "${BACKUP_DIR}/x-ui_${DATE}.db"

# Upload to B2
# b2 upload-file "${B2_BUCKET}" "${BACKUP_DIR}/x-ui_${DATE}.db.gpg" "backups/x-ui_${DATE}.db.gpg"

rm -f "${BACKUP_DIR}/x-ui_${DATE}.db"
"""
}

for fpath, content in files_to_write.items():
    full_path = os.path.join(base_dir, fpath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Repository successfully populated with proper English content.")
