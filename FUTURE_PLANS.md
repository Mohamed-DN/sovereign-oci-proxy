# NeroNet v5.0 (DarkNero Mesh): Next-Generation Architecture Roadmap & Technical Specification

## Executive Summary

NeroNet v4.0 established an enterprise-grade, decentralized peer-to-peer mesh and residential proxy routing platform leveraging Noise IKpsk2 cryptography, userspace TCP/IP netstack sandboxing, multi-cloud declarative orchestration, and NetBird-compatible dynamic access controls.

**NeroNet v5.0 (DarkNero Mesh)** represents the quantum leap into ubiquity, line-rate kernel acceleration, post-quantum cryptographic resilience, and global zero-trust governance on `DARKNERO.COM` (`neronet.darknero.com`). This document outlines the definitive architectural blueprint, engineering specifications, protocol wire formats, and deployment strategies for v5.0.

```
+-------------------------------------------------------------------------------------------------------+
|                              NERONET v5.0 (DARKNERO MESH) GLOBAL ARCHITECTURE                         |
+-------------------------------------------------------------------------------------------------------+
|                                                                                                       |
|  +-------------------------------------------------------------------------------------------------+  |
|  |                FEDERATED ZERO-TRUST CONTROL PLANE (Multi-Region Raft + Wasm Plugins)            |  |
|  |  * Quantum-Safe Identity (ML-DSA-65)       * Dynamic Topology & VIP Swarm                       |  |
|  |  * Continuous Behavioral Risk Engine       * Loadable Wasm Traffic Inspection & Transforms      |  |
|  +-------------------------------------------------------------------------------------------------+  |
|                                                  |                                                    |
|                   +------------------------------+------------------------------+                     |
|                   |                                                             |                     |
|  +----------------v-----------------------------+             +-----------------v------------------+  |
|  |    eBPF / XDP LINE-RATE RELAY SWITCHING     |             |   MULTIPATH QUIC (MPQUIC) ENGINE   |  |
|  |  * AF_XDP Zero-Copy Kernel Ring Buffers      |             |  * Cellular + Wi-Fi Bandwidth Agg  |  |
|  |  * 100Gbps Line-Rate DERP-v5 Relay          |             |  * Sub-Millisecond Path Failover   |  |
|  |  * In-Kernel Anti-Probing Deep Decoy         |             |  * Congestion Control (BBRv3/MP)   |  |
|  +----------------------------------------------+             +------------------------------------+  |
|                   |                                                             |                     |
|                   +------------------------------+------------------------------+                     |
|                                                  |                                                    |
|  +-----------------------------------------------v-------------------------------------------------+  |
|  |                      CROSS-PLATFORM NATIVE CLIENT ECOSYSTEM (v5.0 Native)                       |  |
|  |  +--------------------+  +--------------------+  +--------------------+  +-------------------+  |  |
|  |  |   iOS & iPadOS     |  |       macOS        |  |      Android       |  |  Windows & Linux  |  |  |
|  |  | Swift 6 / SwiftUI  |  | AppKit / SystemExt |  | Jetpack Compose    |  | WinTUN / Wails v2 |  |  |
|  |  | NEPacketTunnel     |  | Touch ID / Menubar |  | VpnService + JNI   |  | systemd / GTK-4   |  |  |
|  |  +--------------------+  +--------------------+  +--------------------+  +-------------------+  |  |
|  |                                                                                                 |  |
|  |  * Core Shared Engine: Gomobile C-Shared Go Core (`libsovereign.a` / `libsovereign.so`)         |  |
|  |  * Post-Quantum Hybrid Handshake: ML-KEM-768 (Kyber) + X25519 in Noise IKpsk2 Handshake        |  |
|  |  * Intelligent Battery Guardian (<15% Auto-Pause) & QR Code Onboarding                         |  |
|  +-------------------------------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------------------------------+
```

---

### 1. Native Client Applications Architecture

The core tenet of NeroNet v5.0 (DarkNero Mesh) is frictionless consumer and enterprise client adoption across all major desktop and mobile operating systems. All native clients leverage a shared high-performance Go core (`libsovereign`) compiled via Gomobile and CGO, encapsulated by platform-native modern declarative user interfaces.

### 1.1 Shared Core Architecture (`pkg/client/core`)

The Go core is packaged as:
- **Apple (iOS/macOS)**: `SovereignCore.xcframework` (C-archive / Gomobile bindings for arm64/x86_64).
- **Android**: `libsovereign.so` (JNI dynamic library for `arm64-v8a`, `armeabi-v7a`, `x86_64`) + `SovereignCore.aar`.
- **Windows**: `sovereign-core.dll` + WinTUN userspace ring driver.
- **Linux**: `sovereign-daemon` standalone binary with D-Bus IPC interface.

```
+-----------------------------------------------------------------------------------+
|                        PLATFORM-SPECIFIC NATIVE UI LAYER                          |
|  (SwiftUI on Apple, Jetpack Compose on Android, Wails/Fyne/GTK-4 on Desktop)     |
+-----------------------------------------------------------------------------------+
                                         |
                                 (IPC / JNI / C-Bridge)
                                         |
+----------------------------------------v------------------------------------------+
|                  NERONET SHARED CORE ENGINE (Gomobile / CGO)                      |
|  +-----------------------------------------------------------------------------+  |
|  |  Virtual Network Adapter Interface (TUN / VpnService / NEPacketTunnel)      |  |
|  +-----------------------------------------------------------------------------+  |
|  |  gVisor Netstack (TCP/IP/UDP Userspace Protocol Stack)                      |  |
|  +-----------------------------------------------------------------------------+  |
|  |  Post-Quantum Noise Engine (ML-KEM-768 + X25519 + ChaCha20-Poly1305)         |  |
|  +-----------------------------------------------------------------------------+  |
|  |  MPQUIC Engine / Adaptive Disco-v5 Hole Punching / DERP-v5 Relay Multiplexer|  |
|  +-----------------------------------------------------------------------------+  |
|  |  Anti-Leak DoH Multi-Resolver + RFC 1918 Bogon Isolation + Port Filter      |  |
|  +-----------------------------------------------------------------------------+  |
|  |  Dynamic Route Selector, Latency Matrix Engine & Battery Guardian           |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

### 1.2 Apple iOS & iPadOS Architecture

#### Key Capabilities & Technologies
- **UI Framework**: Modern SwiftUI with iOS 17+ Observation framework and Swift Concurrency (`async`/`await`, `Actor` isolation).
- **Tunneling Mechanism**: `NetworkExtension.framework` utilizing `NEPacketTunnelProvider`.
- **Key Storage**: Hardware Secure Enclave via Keychain Services (`kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`).
- **On-Demand Wi-Fi Rules**: Automated activation via `NEOnDemandRuleConnect` on untrusted SSIDs and cellular data; auto-disconnect on trusted enterprise SSIDs.
- **Push-to-Wake Reconnect**: Apple Push Notification service (APNs) Silent Voip/Background Push triggering tunnel wake-up and key re-negotiation.

#### Data Flow & Lifecycle
1. User activates VPN via toggle or On-Demand rule.
2. iOS starts `PacketTunnelProvider` extension in a separate 15MB/50MB memory-constrained process.
3. The Extension calls `SovereignCoreStartTunnel(fd, configJSON)`.
4. Packets from virtual TUN interface (`packetFlow.readPackets`) are handed to Go userspace netstack without context-switching penalties.
5. Inbound mesh traffic is decrypted via hybrid ML-KEM-768/X25519 and written back to `packetFlow.writePackets`.

---

### 1.3 Apple macOS Architecture

#### Key Capabilities & Technologies
- **UI Framework**: AppKit / SwiftUI Menubar companion with compact popover interface and full dashboard window.
- **Tunneling**: `NEPacketTunnelProvider` as a macOS System Extension (`com.apple.sysext.network-extension`) running rootless with sandboxed capabilities.
- **Per-App Split Tunneling**: `NEAppProxyProvider` and process path matching (`/Applications/Browser.app`) allowing granular routing of developer tools, browsers, or terminal sessions.
- **Biometric Security**: Local authentication policy (`LAPolicyDeviceOwnerAuthenticationWithBiometrics`) requiring Touch ID or Apple Watch proximity confirmation before modifying routing modes or viewing private keys.

---

### 1.4 Android Architecture

#### Key Capabilities & Technologies
- **UI Framework**: Kotlin + Jetpack Compose with Material 3 dynamic color theme and Material You design guidelines.
- **Tunneling Mechanism**: `android.net.VpnService` with direct file descriptor passing (`vpnInterface.detachFd()`) into Go runtime via Gomobile JNI.
- **Always-on VPN & Lockdown**: Full support for Android enterprise `ALWAYS_ON_VPN` and `HTTP_PROXY` per-app isolation.
- **Per-App Routing (Split Tunneling)**: Granular package selection (`builder.addAllowedApplication("com.android.chrome")` / `builder.addDisallowedApplication(...)`).
- **Battery Optimization Bypass**: Foreground Service with persistent low-overhead notification (`NotificationChannel` with `IMPORTANCE_MIN`), `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` prompt, and `JobScheduler` keepalives.

---

### 1.5 Windows Architecture

#### Key Capabilities & Technologies
- **UI Framework**: Wails v2 (Go + Svelte/React web frontend with native WebView2 bindings) or lightweight Fyne native GUI.
- **Driver Integration**: High-performance WinTUN kernel driver (`wintun.dll`), achieving >10 Gbps userspace I/O ring buffer throughput.
- **Background Daemon**: Windows Service (`SovereignMeshService`) registered via `advapi32.dll` with auto-start and crash recovery.
- **Packaging & Delivery**: Signed MSIX / MSI installers with WiX Toolset, embedded code signing via Azure Key Vault / DigiCert HSM, and built-in auto-updater with Ed25519 signature validation.

---

### 1.6 Linux Architecture

#### Key Capabilities & Technologies
- **CLI & Daemon**: Lightweight `sovereign-daemon` daemon with systemd integration (`sovereign.service`), `dbus` notification events, and POSIX socket IPC (`/run/sovereign/mesh.sock`).
- **Desktop UI**: GTK-4 / Libadwaita desktop app and AppIndicator/KStatusNotifierItem system tray applet.
- **Network Stack**: WireGuard kernel module integration where available, with seamless automatic fallback to userspace `water/tun` or `gVisor netstack`.

---

### 1.7 Rich Client App UI Architecture & Interactive Control Specifications

The NeroNet (DARKNERO.COM / DarkNero Mesh) native client applications feature an intuitive, cybersecurity-grade interface designed to give users granular control over their cryptographic privacy, egress paths, and device performance.

```
+-------------------------------------------------------------------------------------------------------+
|                                  NERONET RICH CLIENT UI COMPONENT HIERARCHY                           |
+-------------------------------------------------------------------------------------------------------+
|                                                                                                       |
|  +-------------------------------------------------------------------------------------------------+  |
|  | [1] STATUS & TELEMETRY HEADER                                                                   |  |
|  | - Master Connection Toggle (Instant Connect / Disconnect)                                        |  |
|  | - Protocol Badge (Noise IKpsk2 / ML-KEM-768 Hybrid PQ)                                           |  |
|  | - Real-time Bandwidth & Latency HUD (Downlink, Uplink, EWMA RTT, Jitter, Packet Loss)            |  |
|  +-------------------------------------------------------------------------------------------------+  |
|                                                  |                                                    |
|  +-----------------------------------------------v-------------------------------------------------+  |
|  | [2] EGRESS ROUTING MATRIX & MODE SELECTOR (Tab / Segmented Bar)                                 |  |
|  |                                                                                                 |  |
|  |   Mode A: [Country Exit Selector]       Mode B: [Direct Host Anchor]    Mode C: [3-Hop Onion]  |  |
|  |   - Searchable Country & City List       - Specific Host ID / PubKey     - Random Mesh Circuit |  |
|  |   - Composite Health Score (0-100)       - Device Alias & ASN Anchor     - Circuit Peeling HUD |  |
|  |   - Live Ping (ms) & Avail Bandwidth     - Direct P2P NAT Status         - Jitter Obfuscation  |  |
|  +-------------------------------------------------------------------------------------------------+  |
|                                                  |                                                    |
|  +-----------------------------------------------v-------------------------------------------------+  |
|  | [3] SECURITY, PRIVACY & SYSTEM GUARDIAN TOGGLES                                                 |  |
|  | - Strict Kill Switch (Zero-Leak Firewall)      - Per-App Split Tunneling (App Bypass List)     |  |
|  | - Trusted Wi-Fi On-Demand (SSID Whitelist)      - Battery Guardian (<15% Bridge Auto-Pause)     |  |
|  | - Anti-Leak DNS over HTTPS (DoH Quad9/Cloudflare) - Quantum-Safe Handshake Enforcement (ML-KEM)   |  |
|  +-------------------------------------------------------------------------------------------------+  |
|                                                  |                                                    |
|  +-----------------------------------------------v-------------------------------------------------+  |
|  | [4] LIVE TOPOLOGY & MESH TRAFFIC INSPECTOR                                                      |  |
|  | - Interactive Node Particle Visualizer         - Active Peer Table & Direct P2P vs Relay State  |  |
|  +-------------------------------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------------------------------+
```

#### 1. Country Exit Node Selector with Composite Health & Ping Scores
- **Real-Time Country Browser**: Lists all active exit bridge clusters grouped by ISO-3166-1 country code with national flag glyphs, city identifiers, and ASN details.
- **Composite Health Score Algorithm**: Displays an aggregate quality badge (90-100: Green/Optimal, 70-89: Yellow/Good, <70: Orange/Degraded) calculated from:
  $$\text{Score} = 0.35 \times \frac{\text{BW}_{\text{avail}}}{\text{BW}_{\text{max}}} + 0.30 \times \frac{100}{\text{RTT} + 1} + 0.20 \times (1 - \text{Loss}) + 0.15 \times \text{Reputation} - 0.05 \times \text{Jitter}$$
- **Fast Search & Favorites**: Instant prefix filtering across country names, ISO codes, and cities with one-tap pinning to favorites.

#### 2. Specific Host ID Egress Selector (Direct Node Anchoring)
- **Granular Peer Pinning**: Users can anchor their entire device egress to a specific trusted peer node (e.g. `node-us-east-1a-04f8` or public key prefix `e3b0c44298fc...`).
- **Direct P2P Validation Indicator**: Real-time diagnostic badge displaying whether the path to the anchored host is Direct UDP P2P (green lightning bolt) or routed via DERP Relay fallback (blue tunnel icon).
- **Latency & Uptime Telemetry**: Displays exact round-trip ping (sub-millisecond accuracy), packet loss rate, and continuous node uptime.

#### 3. 3-Hop Onion Obfuscation Toggle & Random Residential Mesh Routing
- **Decentralized Multi-Hop Circuit**: When enabled, wraps outbound traffic in 3 concentric layers of ChaCha20-Poly1305 encryption through randomized Entry Relay $\rightarrow$ Intermediate Relay $\rightarrow$ Residential Exit Bridge.
- **Circuit Inspector HUD**: Visualizes the 3 selected nodes, showing their geographic hops, intermediate latency, and randomized timing jitter delay (2ms - 25ms) injected to defeat correlation attacks.
- **Circuit Re-Seed Button**: One-tap instant rotation of intermediate and entry nodes without dropping active TCP socket streams.

#### 4. Enterprise Security & Device Guardian Toggles
- **Strict Kill Switch (Zero-Leak Protection)**: Immediately cuts all default gateway interfaces (Wi-Fi/Cellular/Ethernet) if the cryptographic mesh tunnel experiences an unexpected drop, preventing IPv4/IPv6 plaintext leaks.
- **Per-App Split Tunneling**: Allows users to include or exclude specific applications from the mesh tunnel (e.g. routing developer terminal or web browser through NeroNet while keeping local video games direct).
- **Trusted Wi-Fi On-Demand**: Automatically activates NeroNet mesh protection upon connecting to public or untrusted Wi-Fi hotspots, while entering low-power standby on trusted home/office SSIDs.
- **Battery Guardian (<15% Auto-Pause)**: Intelligent battery monitor that automatically pauses the client's exit bridge routing capability (stops routing other peers' traffic) whenever battery falls below 15%, conserving battery life while keeping user's own VPN active.

#### 5. Instant QR code Onboarding
- **Zero-Friction Camera Scan**: Control plane generates single-use signed registration tokens encoded as SVG/PNG QR code payloads (`svrn://join?token=JWT&relay=wss://relay.mesh.io:443&kem=MLKEM768`).
- **Instant Pair & Key Exchange**: Mobile cameras scan and onboard nodes in <300ms with zero manual key copying.

---

### 1.8 Platform-Specific Visual Wireframes & Component Hierarchies

#### A. iOS & iPadOS Visual Wireframe (SwiftUI 6 / NavigationStack)

```
+--------------------------------------------------+
|  [|||]  NeroNet Mesh         (i) Settings    [?] |
+--------------------------------------------------+
|                                                  |
|       +----------------------------------+       |
|       |     (●) CONNECTED (00:42:18)     |       |
|       |      VIP: 100.64.0.42 (US-East)  |       |
|       +----------------------------------+       |
|                                                  |
|  [  DISCONNECT MASTER TOGGLE  (Swipe to Stop)  ] |
|                                                  |
|  PROTOCOL: Hybrid ML-KEM-768 + Noise IKpsk2      |
|  RTT: 18ms | JITTER: 1.2ms | LOSS: 0.0%          |
|  DOWN: 84.2 Mbps  ▲ | UP: 42.1 Mbps  ▼          |
|                                                  |
|  ROUTING EGRESS MODE:                            |
|  [ Country ]   [ Direct Host ]   [ 3-Hop Onion*] |
|                                                  |
|  SELECTED EXIT: 🇺🇸 United States (Ashburn, VA)   |
|  Health Score: 98/100 (Optimal) | RTT: 18ms      |
|  [ Change Country / View 48 Global Nodes > ]     |
|                                                  |
|  SECURITY & BATTERY GUARDIANS:                   |
|  [ON ] Strict Kill Switch (Leak Prevention)      |
|  [ON ] Per-App Split Tunneling (4 Apps Routed)   |
|  [ON ] Trusted Wi-Fi On-Demand ("Home_5G" safe)  |
|  [ON ] Battery Guardian (<15% Bridge Pause)      |
|                                                  |
|  [ 🌐 View Live Particle Topology Simulation  ]  |
+--------------------------------------------------+
|   [Mesh Home]     [Nodes]     [Logs]     [Config]|
+--------------------------------------------------+
```

#### B. macOS Visual Wireframe (AppKit / SwiftUI Menubar Companion + Window)

```
+----------------------------------------------------------------------------------------------------+
|  NeroNet Mesh v4.0 (DARKNERO.COM) -- Production Node Control                            [ _ ][ □ ][ X ] |
+----------------------------------------------------------------------------------------------------+
|  [Sidebar]          |  LIVE MESH TOPOLOGY & ACTIVE CIRCUIT                                         |
|                     |  +------------------------------------------------------------------------+  |
|  * Overview         |  |   [Node: Local] ---> [Relay: Frankfurt] ---> [Exit: Zurich-04]       |  |
|  * Nodes (142)      |  |   Mode: 3-Hop Onion Obfuscation | Jitter: 8.4ms | Path: Direct P2P     |  |
|  * ACL Policies     |  +------------------------------------------------------------------------+  |
|  * App Split Tunnel |                                                                              |
|  * Cryptography     |  REAL-TIME THROUGHPUT & TELEMETRY HUD                                        |
|  * Audit Logs       |  [Graph: 100 Mbps Downlink =========] 92.4 Mbps                              |
|                     |  [Graph: 50 Mbps Uplink    ======   ] 38.1 Mbps                              |
|  -----------------  |  Ping: 22ms | Window: 1024 frames | Replay Protection: 0 Drops               |
|  Connection Status: |                                                                              |
|  [● ACTIVE - SECURE]|  ROUTING CONTROLS:                                                           |
|  Exit: Switzerland  |  Country Exit: [ Switzerland (ZH) ▾ ] Health: 99/100 (5ms ping)             |
|  VIP: 100.64.0.19   |  Host Anchor:  [ None (Country Mode Active)                         ▾ ]      |
|  KEM: ML-KEM-768    |  [x] Enable 3-Hop Onion Obfuscation (Random Residential Mesh Routing)       |
|                     |                                                                              |
|  Security Toggles:  |  SYSTEM GUARDIANS:                                                           |
|  [x] Kill Switch    |  [x] Strict Kill Switch (pf firewall anchor active)                          |
|  [x] Split Tunnel   |  [x] Per-App Split Tunneling (Include: Safari, Chrome, Terminal, Slack)      |
|  [x] Wi-Fi Auto     |  [x] Trusted Wi-Fi On-Demand (Bypass on: "Corporate-HQ-Secure")              |
|  [x] Battery Guard  |  [x] Battery Guardian (Auto-pause exit bridge at <15% battery)              |
+----------------------------------------------------------------------------------------------------+
```

#### C. Android Visual Wireframe (Jetpack Compose / Material 3)

```
+--------------------------------------------------+
|  =  NeroNet Mesh (DARKNERO)  (PQ) [QR Scan] [:] |
+--------------------------------------------------+
|                                                  |
|     +--------------------------------------+     |
|     |  Status: SECURE & CONNECTED (Wire)   |     |
|     |  Overlay IP: 100.64.0.88             |     |
|     |  Encryption: ML-KEM-768 + X25519     |     |
|     +--------------------------------------+     |
|                                                  |
|     [  ● DISCONNECT (Hold to Deactivate) ]       |
|                                                  |
|  LIVE METRICS:                                   |
|  Latency: 14ms (Direct P2P) | Loss: 0.0%         |
|  Down: 64.5 MB/s ▲ | Up: 28.1 MB/s ▼             |
|                                                  |
|  EXIT NODE CONFIGURATION:                        |
|  (•) Country Exit: 🇩🇪 Germany (Frankfurt am Main)|
|      Score: 97/100 | Ping: 14ms | BW: 500 Mbps   |
|  ( ) Specific Host ID (Select Node...)           |
|  ( ) 3-Hop Random Mesh Onion Obfuscation         |
|                                                  |
|  SECURITY SETTINGS:                              |
|  [ON ] Always-On VPN & Strict Kill Switch        |
|  [ON ] Per-App Split Tunneling (12 Apps)         |
|  [ON ] Trusted Network Bypass (Wi-Fi SSID)       |
|  [ON ] Battery Guardian (Low Power Auto-Pause)   |
|                                                  |
|  [ ⚡ Run Dynamic Latency Diagnostic Test ]       |
+--------------------------------------------------+
|     [Home]          [Topology]          [Profile]|
+--------------------------------------------------+
```

#### D. Windows Visual Wireframe (Wails v2 / Fluent Dark UI)

```
+----------------------------------------------------------------------------------------------------+
|  NeroNet v4.0 (DARKNERO.COM - WinTUN Driver Line-Rate)                                  [ _ ][ □ ][ X ] |
+----------------------------------------------------------------------------------------------------+
|  [ Quick Connect ]   Status: PROTECTED (100.64.0.12) | Adapter: WinTUN (10 Gbps Ring)               |
|                                                                                                    |
|  +-------------------------------------+  +-----------------------------------------------------+  |
|  | EGRESS SELECTION MATRIX             |  | PERFORMANCE TELEMETRY & ROUTE METRICS               |  |
|  | Mode: [ Country ] [ Host ] [ Onion] |  | Current Latency: 12.4 ms (Direct P2P UDP)           |  |
|  | Target: 🇯🇵 Japan (Tokyo Cloud-01)  |  | Bandwidth In/Out: 112.4 Mbps / 48.6 Mbps            |  |
|  | Quality Score: 99.4/100             |  | Jitter Sigma: 0.8 ms | Loss Rate: 0.00%             |  |
|  | Latency: 12ms | Load: 14%           |  | Post-Quantum Key: ML-KEM-768 Active                 |  |
|  +-------------------------------------+  +-----------------------------------------------------+  |
|                                                                                                    |
|  SYSTEM SECURITY & GUARDIAN POLICIES:                                                              |
|  [√] Strict Kill Switch (WFP - Windows Filtering Platform Zero-Leak Filter Active)                 |
|  [√] Per-App Split Tunneling (Exclude local gaming traffic / Include browsers and Git CLI)          |
|  [√] Trusted Wi-Fi / Ethernet On-Demand Auto-Connect                                                |
|  [√] Battery Guardian (<15% auto-pause background bridge relaying)                                 |
|                                                                                                    |
|  [ View Complete Mesh Route Map ]   [ Test NAT ICE Candidates ]   [ Export WireGuard Config (.conf) ]|
+----------------------------------------------------------------------------------------------------+
```

---


## 2. Post-Quantum Cryptographic Migration Plan

As quantum computing architectures advance towards Shor's algorithm feasibility, classical discrete logarithm systems (Curve25519, RSA, ECDSA) face eventual compromise. Sovereign Mesh v5.0 implements NIST-standardized Post-Quantum Cryptography (PQC) in a hybrid defense-in-depth model.

```
+---------------------------------------------------------------------------------------------------+
|                         HYBRID NOISE_IKpsk2_PQ HANDSHAKE STATE MACHINE                            |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|     INITIATOR (Client)                                          RESPONDER (Exit / Control)        |
|     ------------------                                          --------------------------        |
|                                                                                                   |
|     Ephemeral: e_classic = X25519_Gen()                                                           |
|     Ephemeral PQ: (pk_pq, sk_pq) = ML-KEM-768.KeyGen()                                            |
|                                                                                                   |
|     Handshake Msg 1:                                                                              |
|     -> e_classic, pk_pq, es_classic, ss_classic, Tag1                                             |
|                                                                                                   |
|                                                                 (ct_pq, ss_pq) =                  |
|                                                                   ML-KEM-768.Encaps(pk_pq)        |
|                                                                 Derive Hybrid SS =                |
|                                                                   BLAKE2s(ss_classic || ss_pq)    |
|                                                                                                   |
|                                      Handshake Msg 2:                                             |
|                                      <- e_classic, ct_pq, ee_classic, se_classic, psk, Tag2       |
|                                                                                                   |
|     ss_pq = ML-KEM-768.Decaps(sk_pq, ct_pq)                                                       |
|     Derive Hybrid SS = BLAKE2s(ss_classic || ss_pq)                                               |
|                                                                                                   |
|     ========================================================================================      |
|     ESTABLISHED TRANSPORT CIPHERSTATE: ChaCha20-Poly1305 with Hybrid Quantum-Safe Key             |
|     ========================================================================================      |
+---------------------------------------------------------------------------------------------------+
```

### 2.1 Hybrid Key Encapsulation Mechanism (ML-KEM-768 / Kyber)

- **Algorithm**: NIST FIPS 203 ML-KEM-768 (formerly CRYSTALS-Kyber) combined with Curve25519 in a hybrid Noise pattern: `Noise_IKpsk2_PQ`.
- **Security Goal**: IND-CCA2 security against both classical and quantum adversaries. Even if ML-KEM-768 were broken, classical Curve25519 remains; if Curve25519 is broken by quantum computers, ML-KEM-768 maintains confidentiality.
- **Wire Overhead**: ML-KEM-768 public key (1,184 bytes) and ciphertext (1,088 bytes) are transmitted only during initial handshake (Msg 1 and Msg 2), preserving high performance on steady-state 24-byte SVRN data frames.

### 2.2 Quantum-Safe Digital Signatures (ML-DSA-65 / Dilithium)

- **Algorithm**: NIST FIPS 204 ML-DSA-65 (formerly CRYSTALS-Dilithium).
- **Use Case**: Control Plane node identity attestation, cluster join tokens, and policy manifest code signing.
- **Revocation & Root of Trust**: Hierarchical control plane certificates signed by Offline Root ML-DSA-65 key, with dynamic short-lived intermediate certificates (7-day validity) and CRL distribution over gRPC.

---

## 3. High-Performance Kernel & Transport Innovations

```
+---------------------------------------------------------------------------------------------------+
|                        eBPF / XDP LINE-RATE DERP-v5 SWITCHING PIPELINE                            |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|   100Gbps Ethernet NIC  ---> [ XDP_DRV (Native Driver Hook) ]                                     |
|                                            |                                                      |
|                             +--------------v--------------+                                       |
|                             | BPF Map: Session Router     |                                       |
|                             | Key: SessionID (uint64)     |                                       |
|                             | Val: Target Dest IP & MAC   |                                       |
|                             +--------------+--------------+                                       |
|                                            |                                                      |
|                       +--------------------+--------------------+                                 |
|                       |                                         |                                 |
|               (Matched Valid Route)                     (Probing / Decoy)                         |
|                       |                                         |                                 |
|           [ XDP_TX / Line-Rate Forward ]             [ XDP_PASS -> Decoy Web Engine ]             |
|           Latency: < 450 nanoseconds                 Latency: Standard TCP Handshake              |
|           Throughput: 14.88 Mpps / port                                                           |
+---------------------------------------------------------------------------------------------------+
```

### 3.1 eBPF / XDP Line-Rate Relay Switching

- **Architecture**: In v5.0, DERP relay servers implement an XDP (eXpress Data Path) kernel driver hook (`bpf_derp_switch.c`).
- **Fast-Path Switching**: For established relay sessions, SVRN frames arriving over UDP are parsed in-kernel via eBPF. The 8-byte `SessionID` is looked up in an eBPF `BPF_MAP_TYPE_HASH` map, and the frame is rewritten with destination MAC/IP and redirected immediately via `XDP_TX` with zero memory copies or userspace transitions.
- **Throughput Target**: 100 Gbps line-rate switching per relay node (>14 million packets per second on commodity dual-socket Xeon/EPYC servers).

### 3.2 Multipath QUIC (MPQUIC) Engine

- **RFC 9000 / MPQUIC Integration**: Client nodes utilize concurrent multi-homed path bonding across Wi-Fi (e.g. 5GHz 802.11ax) and Cellular (5G NR mmWave/Sub-6).
- **BBRv3 Multipath Scheduling**: Packets are dynamically striped across active sub-flows according to real-time RTT and loss gradients.
- **Zero-Drop Handover**: Seamless mobility when walking out of Wi-Fi range; cellular subflow immediately carries 100% of traffic with zero TCP reset or session interruption.

### 3.3 Zero-Copy Userspace Ring Buffer (AF_XDP) for Exit Bridges

- High-bandwidth exit bridges utilize `AF_XDP` sockets (`UMEM` memory pools) to bypass kernel network stack overhead while maintaining strict userspace RFC 1918 bogon filtering and anti-abuse port blocking.

---

## 4. Federated Zero-Trust Governance

```
+---------------------------------------------------------------------------------------------------+
|                     FEDERATED MULTI-REGION RAFT & WASM POLICY PIPELINE                            |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|   +--------------------------+    gRPC Consensus    +--------------------------+                  |
|   | Control Plane Leader     |<-------------------->| Control Plane Follower   |                  |
|   | Region: US-East          |                      | Region: EU-Central       |                  |
|   +-------------+------------+                      +-------------+------------+                  |
|                 |                                                 |                               |
|                 +-----------------------+-------------------------+                               |
|                                         |                                                         |
|                         +---------------v---------------+                                         |
|                         | Wasm Dynamic Inspection Engine|                                         |
|                         | (Wasmtime / Extism Sandbox)   |                                         |
|                         +---------------+---------------+                                         |
|                                         |                                                         |
|         +-------------------------------+-------------------------------+                         |
|         |                               |                               |                         |
|  [ Plugin: Geo-DPI ]          [ Plugin: Protocol Scrub ]     [ Plugin: Behavioral Scorer]         |
|  * TLS Fingerprint Camo       * HTTP/3 Header Sanitizer      * Anomaly Risk Assessment            |
+---------------------------------------------------------------------------------------------------+
```

### 4.1 Distributed Multi-Region Raft Control Plane

- **Cross-Cloud Consensus**: Control plane operates as a 5-node or 7-node geographically distributed Raft cluster across AWS, OCI, GCP, and Hetzner.
- **State Replication**: Subnet routes, active peer VIP assignments, dynamic ACLs, and posture requirements are committed via Raft log entries with sub-second replication latency worldwide.
- **Split-Brain Immunity**: Automatic quorum maintenance ensures partition tolerance; disconnected regional nodes serve cached read-only routing topologies.

### 4.2 WebAssembly (Wasm) Extensible Inspection Engine

- **Sandbox Runtime**: Integrated `wasmtime-go` engine allowing administrators to hot-reload traffic inspection and protocol transform plugins without restarting daemons.
- **Capabilities**:
  - Custom Layer 7 protocol scrubbers (stripping tracker headers, obfuscating SNI headers).
  - Dynamic geo-routing heuristics based on external threat feeds.
  - Active deception responses (injecting synthetic decoys against automated port scanners).

### 4.3 Continuous Behavioral Risk Scoring

- **Telemetry Evaluation**: Control plane computes real-time peer risk index (0.00 - 100.00) based on:
  - RTT anomaly & jitter divergence.
  - TCP sequence number entropy.
  - Geolocation drift velocity (impossible travel detection, e.g. US to JP in 5 minutes).
  - Device health posture attestation telemetry.
- **Automated Remediation**: Peers with risk score > 75.00 are automatically moved to isolated quarantine subnet (`100.64.250.0/24`) with restricted access until multi-factor re-attestation succeeds.

---

## 5. Milestone & Release Timeline for v5.0

| Phase | Milestone Name | Scope & Deliverables | Target Timeline |
|---|---|---|---|
| **Phase 1** | Post-Quantum Cryptographic Core | Implement ML-KEM-768 + X25519 hybrid Noise engine & ML-DSA-65 control plane identities | Q1 2027 |
| **Phase 2** | Native Mobile & Desktop Clients | Deliver native iOS (SwiftUI/NEPacketTunnel), Android (Compose/VpnService), macOS, Windows (WinTUN), and Linux apps | Q2 2027 |
| **Phase 3** | eBPF/XDP & MPQUIC Transport | Ship line-rate eBPF relay switching, AF_XDP zero-copy buffers, and Multipath QUIC cellular/Wi-Fi bonding | Q3 2027 |
| **Phase 4** | Federated Raft & Wasm Governance | Multi-region Raft consensus, Wasm dynamic plugin runtime, and continuous behavioral risk scoring | Q4 2027 |
| **Phase 5** | Global Production Rollout | Security audit, chaos testing, enterprise deployment manifests, and NeroNet v5.0 (DarkNero Mesh) GA | Q1 2028 |

---

## 6. Architecture Verification & Invariants

All future contributions to NeroNet v5.0 (DarkNero Mesh) must uphold the following core invariants:
1. **Zero Plaintext Egress**: No unencrypted payload may ever traverse external network interfaces.
2. **Post-Quantum Forward Secrecy**: Handshakes must guarantee hybrid quantum resistance.
3. **Censorship Evasion by Default**: Geo-fencing remains strictly opt-in; heavily censored jurisdictions (RU, EG, CN, IN) are unconditionally allowed by default.
4. **Strict Bogon Isolation**: RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local, loopback, and CGNAT overlay addresses are dropped at userspace boundaries with zero kernel packet leaks.
5. **Deterministic Testing**: 100% test coverage across unit, integration, stress, and 5-tier E2E suites.
