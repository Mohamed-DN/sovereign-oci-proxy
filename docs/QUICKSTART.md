# 🚀 Quickstart Guide

Go from zero to a fully operational anti-censorship proxy in under 30 minutes.

---

## Prerequisites

- An [Oracle Cloud](https://cloud.oracle.com/) account (Always Free Tier)
- A [DuckDNS](https://www.duckdns.org/) account (free dynamic DNS)
- A client app: [FoXray](https://apps.apple.com/app/foxray/id6448898396) (macOS), [Streisand](https://apps.apple.com/app/streisand/id6450534064) (iOS), [v2rayNG](https://play.google.com/store/apps/details?id=com.v2ray.ang) (Android), or [v2rayN](https://github.com/2dust/v2rayN) (Windows)

---

## Step 1: Create the Oracle Cloud Instance

1. Log into the [Oracle Cloud Console](https://cloud.oracle.com/)
2. Navigate to **Compute → Instances → Create Instance**
3. Configure:
   - **Name:** `sovereign-proxy`
   - **Image:** Ubuntu 24.04 Minimal (aarch64)
   - **Shape:** VM.Standard.A1.Flex → **2 OCPU, 12 GB RAM**
   - **Boot Volume:** Custom **200 GB**
   - **SSH Keys:** Generate and **download both `.key` and `.pub` files**
   - **Capacity type:** On-demand (never Preemptible)
4. Click **Create** and wait for status "Running"
5. Copy the **Public IP** address

## Step 2: Configure Security Lists

1. Navigate to **Networking → VCN → Security Lists → Default**
2. Add **Ingress Rules** (CIDR `0.0.0.0/0`, Protocol TCP):

| Port | Purpose |
| --- | --- |
| 2222 | Custom SSH |
| 443 | VLESS + Decoy + Subscription |
| 80 | Certificate renewal |
| 8080 | Honeypot trap |

> ⚠️ **DO NOT** delete the default port 22 rule yet!

## Step 3: Connect via SSH

```bash
chmod 400 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_ORACLE_IP
```

Verify:
```bash
uname -m && lsb_release -d && free -h && nproc
# Expected: aarch64, Ubuntu 24.04, ~12G, 2
```

## Step 4: Clone and Install

```bash
git clone https://github.com/Mohamed-DN/sovereign-oci-proxy.git
cd sovereign-oci-proxy
sudo chmod +x scripts/modules/*.sh scripts/*.sh tests/*.sh
sudo ./scripts/install.sh
```

## Step 5: Install 3x-ui

```bash
sudo bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh)
```

Set a **strong username, password, port (54321), and panel path** during installation. Save these credentials in your password manager immediately.

## Step 6: Configure VLESS + REALITY

1. Access the 3x-ui panel (via Tailscale IP only)
2. Navigate to **Inbounds → Add Inbound**
3. Configure:
   - Protocol: **VLESS**
   - Port: **443**
   - Security: **REALITY** (Flow: `xtls-rprx-vision`)
   - SNI: A reputable domain (e.g., `aws.amazon.com`)
   - Fallback: `127.0.0.1:8443` (Nginx decoy)
4. Generate UUID and REALITY keys
5. Save

## Step 7: Remove Port 22

1. Open a **second terminal** and verify connection on port 2222:
   ```bash
   ssh -i ~/Downloads/ssh-key-*.key -p 2222 ubuntu@YOUR_ORACLE_IP
   ```
2. Only after success: go to Oracle Console → Security List → **Delete the port 22 Ingress Rule**

## Step 8: Connect Your Client

1. In the 3x-ui panel, click the QR code icon next to your inbound
2. Scan the QR code with your client app (FoXray, Streisand, v2rayNG)
3. Connect

## Step 9: Verify

Visit these sites with the VPN active:
- [ipleak.net](https://ipleak.net) — Should show Oracle IP (or Cloudflare if WARP is enabled)
- [dnsleaktest.com](https://dnsleaktest.com) — Should show Cloudflare/Google DNS, not your ISP
- [fast.com](https://fast.com) — Speed test

## Step 10: Run the Validation Suite

```bash
sudo ./tests/sovereign-test.sh
```

Target: **20/20** ✅
