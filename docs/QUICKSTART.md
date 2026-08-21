# 🚀 Quickstart Guide

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
