# 🏗️ Architecture Design & Traffic Flow

The Sovereign Proxy utilizes a highly compartmentalized architecture. It is designed to disguise traffic from advanced Deep Packet Inspection (DPI) while seamlessly bridging the user to both the public internet and a private Homelab.

## Core Components
*   **VPS Provider:** Oracle Cloud Infrastructure (OCI) - ARM A1.Flex
*   **Ingress Protocol:** VLESS + REALITY + XTLS-Vision (Port 443)
*   **Decoy System:** Nginx serving a fake corporate "Status Page"
*   **Mesh Network:** Tailscale (Routing to private Homelab resources)
*   **Defense in Depth:** UFW, Fail2ban, Auditd, Python Honeypot

---

## 🗺️ System Topology & Flow Diagram

The following diagram illustrates how incoming traffic is processed, authenticated, and routed.

```mermaid
graph TD
    classDef userbox fill:#f3f4f6,stroke:#4b5563,stroke-width:2px;
    classDef oraclebox fill:#fff1f2,stroke:#e11d48,stroke-width:2px,stroke-dasharray: 5 5;
    classDef proxy fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0f172a;
    classDef secure fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#0f172a;
    classDef danger fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#0f172a;
    classDef decoy fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#0f172a;

    subgraph User [User Environment]
        Client[Client Application<br>v2rayNG / FoXray / Nekobox]:::userbox
    end

    subgraph External [Threats & Probing]
        Attacker[Government DPI / Network Scanners]:::danger
    end

    subgraph Oracle [Oracle Cloud Infrastructure]
        FW[UFW Firewall<br>Ports: 443, 2222, 8080]:::oraclebox
        Xray[Xray Core<br>VLESS + REALITY]:::proxy
        Decoy[Nginx Decoy<br>Port 8443]:::decoy
        Honeypot[Python Honeypot<br>Port 8080]:::danger
        TS[Tailscale Interface<br>tailscale0]:::secure
    end

    subgraph Egress [Egress Networks]
        Homelab[Proxmox Homelab<br>Private IPs]:::secure
        WARP[Cloudflare WARP<br>WireGuard Tunnel]:::secure
        Internet[Public Internet<br>Direct Egress]:::userbox
    end

    %% Connections
    Client -- "Encrypted TLS 1.3<br>SNI: aws.amazon.com" --> FW
    Attacker -- "Active Probing (Port 443)" --> FW
    Attacker -- "Blind Port Scanning (Port 8080)" --> Honeypot
    
    Honeypot -. "Triggers auto-ban" .-> FW

    FW --> Xray
    
    %% Xray Logic
    Xray -- "Invalid UUID or<br>Fingerprint Mismatch" --> Decoy
    
    Xray -- "Valid UUID<br>(Rule: geoip:private)" --> TS
    TS -- "Subnet Routing" --> Homelab
    
    Xray -- "Valid UUID<br>(Rule: Netflix, ChatGPT)" --> WARP
    WARP -- "Trusted IP" --> Internet
    
    Xray -- "Valid UUID<br>(Rule: Direct)" --> Internet
```

### Flow Breakdown

1. **The Ingress (REALITY Protocol):** 
   When your device connects to port 443, the connection looks exactly like a standard TLS 1.3 handshake to a reputable commercial domain (e.g., `aws.amazon.com`).
2. **The Firewall (UFW):** 
   Only ports 2222 (Admin SSH), 443 (VLESS), 80 (Certificates), and 8080 (Honeypot) are open.
3. **The Decoy:** 
   If a government firewall or an unauthorized user attempts to connect to port 443 without the correct UUID and cryptographic short-ID, Xray silently proxies the request to the Nginx Decoy. The prober receives a perfectly valid HTML response of a generic "Status Page", raising zero suspicion.
4. **The Trap (Honeypot):** 
   Port 8080 runs a custom Python script. Any bot scanning this port receives an HTTP banner and is instantly banned by UFW, triggering a push notification to your phone via Ntfy.
5. **The Egress Routing:** 
   Once inside, Xray reads the routing rules:
   *   Requests to private IPs (`192.168.x.x`) are securely pushed into the `tailscale0` interface, bypassing NAT and reaching your Homelab directly.
   *   Requests to strict websites (Netflix, OpenAI) are pushed into the Cloudflare WARP outbound, masking the Oracle Datacenter IP.
   *   All other traffic exits directly to the internet at maximum speed.
