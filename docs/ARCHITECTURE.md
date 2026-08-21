# 🏗️ Architecture Design

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
