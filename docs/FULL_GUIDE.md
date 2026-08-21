# 📖 S.O.A.P.
### Sovereign Operations & Architecture Playbook

*"Dedicated to the protection of knowledge, freedom of communication, and human dignity, respecting all beliefs."*

This is the definitive, field-tested master guide for deploying and maintaining the Sovereign OCI Proxy.

---

## 1. Instance Provisioning & Security Lists

### 1.1 Specifications
*   **Shape:** `VM.Standard.A1.Flex` (ARM Ampere)
*   **Resources:** 2 OCPU / 12 GB RAM
*   **Boot Volume:** Custom 200 GB
*   **Image:** Ubuntu 24.04 Minimal aarch64 (Latest build)
*   **Region:** Milan (or closest preferred region)
*   **Advanced:** Fault Domain default, Stateless OFF, IMDS "Require authorization header" OFF, cloud-init EMPTY.

### 1.2 The Oracle Console Security List (CRITICAL)
Before touching the server via SSH, you must configure the cloud firewall.
Navigate to **Networking -> VCN -> Security Lists -> Default Security List** and add the following **Ingress Rules** (CIDR `0.0.0.0/0`, Protocol TCP, Stateless OFF):
*   **Port 2222** (Custom SSH)
*   **Port 443** (VLESS Reality + Decoy)
*   **Port 80** (ACME Certificate Renewal)
*   **Port 8080** (Python Honeypot Trap)

⚠️ **DO NOT delete the default port 22 rule yet!**

---

## 2. Hardening & Port 22 Lockout Prevention

### 2.1 Base Packages & Swap
Connect to the server via standard SSH on port 22. Update the system and create a 4GB swap file to prevent Out-Of-Memory (OOM) errors during heavy traffic spikes.
Run the `./scripts/modules/hardening.sh` script to automate this, which also applies BBR congestion control for maximum network throughput.

### 2.2 Securing SSH
Edit `/etc/ssh/sshd_config`:
```text
Port 2222
PasswordAuthentication no
PermitRootLogin no
MaxAuthTries 3
```
Restart the service: `sudo systemctl restart sshd`.
🚨 **CRITICAL STEP:** Open a *second* terminal window and verify you can connect using `ssh -p 2222 ...`. 
Only after a successful connection on the new port, return to the Oracle Cloud Console and **delete the Ingress Rule for Port 22**.

---

## 3. Decoy & Evasion (Nginx)

To defeat Deep Packet Inspection (DPI) and active probing, the server must look like a legitimate web server to unauthorized visitors.
Running `./scripts/modules/decoy.sh` configures Nginx on a local loopback port (`127.0.0.1:8443`). It serves a realistic, unbranded "Cloud Infrastructure Monitor" HTML page. 

When Xray receives a connection on port 443 with a mismatched cryptographic signature, it silently hands the connection to Nginx. The prober sees the fake website and assumes the server is just a standard web host.

---

## 4. Xray Core & 3x-ui Setup

The core routing engine is installed via the official 3x-ui script:
```bash
bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh)
```
### VLESS + REALITY Configuration
1.  **Protocol:** VLESS
2.  **Port:** 443
3.  **Security:** REALITY (Flow: `xtls-rprx-vision`)
4.  **SNI spoofing:** Choose a highly reputable domain belonging to a major corporation (e.g., `aws.amazon.com`, `www.cisco.com`).
5.  **Fallback:** Set the fallback port to `127.0.0.1:8443` (pointing to the Nginx Decoy).

### Fixing Homelab Routing (Tailscale)
By default, Xray blocks all traffic to private IP ranges (`geoip:private`) to prevent Server-Side Request Forgery (SSRF). To allow your VPN to reach your Tailscale Homelab:
Execute `sudo python3 ./scripts/modules/xray-routing-fix.py`. This moves the `geoip:private` rule into the `direct` outbound, unlocking access to your home network.

---

## 5. Defense Mechanisms (Anti-Idle & Honeypot)

Oracle enforces a strict "Idle Reclamation" policy. If a free instance uses <10% CPU and network for 7 days, it is permanently deleted.
Running `./scripts/modules/monitoring.sh` deploys two critical systems:
1.  **Anti-Idle Keepalive:** A cronjob that runs every 4 hours, spiking the CPU (calculating Pi), allocating 500MB of RAM, and generating outbound network traffic to Google/Cloudflare. This completely bypasses Oracle's idle detection.
2.  **Honeypot Trap:** A Python script listening on port 8080. Any scanner touching this port receives a fake HTTP banner and is instantly banned at the UFW firewall level.

---

## 6. Disaster Recovery & Asymmetric Backups

If the server is compromised or deleted by Oracle, recovery must take less than 30 minutes without losing user configurations.
1. Generate an RSA 4096 GPG Keypair on your **local machine** (Mac/Windows).
2. Export only the **Public Key** and upload it to the Oracle server.
3. The `./scripts/modules/backup.sh` script runs nightly via cron. It archives the `x-ui.db` SQLite database, encrypts it using *only* your public key (AES-256), and pushes the `.gpg` file to Backblaze B2.
4. **The Security Guarantee:** The server holds no private keys. If a bad actor steals the backup files, they cannot decrypt them. To restore, you download the file locally, decrypt it with your private key, and upload the plaintext database to a new server.

---

## 7. Cloudflare WARP & IP Reputation

Datacenter IPs (like Oracle's) are frequently blocked by Netflix, OpenAI, and banking applications.
To bypass this, configure a **Cloudflare WARP** outbound inside the 3x-ui panel:
1. Navigate to Outbounds -> Add WARP (Create Account).
2. Navigate to Routing Rules.
3. Route strict domains (e.g., `geosite:netflix, domain:chatgpt.com`) to the `warp` outbound tag. 
4. This initiates a Double-Hop VPN: Your traffic is encrypted to Oracle, then re-encrypted via WireGuard to Cloudflare. Destination websites will see a highly trusted Cloudflare IP instead of your Oracle Datacenter IP.
