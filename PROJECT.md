# Project: NeroNet v4.0 (DarkNero Mesh / Sovereign Proxy Upgrade)

## Architecture
NeroNet v4.0 (DarkNero Mesh) is a proprietary, decentralized, Kubernetes-ready mesh network and residential proxy routing system on DARKNERO.COM (neronet.darknero.com) where client devices act as exit nodes.

```
+-----------------------------------------------------------------------------------+
|                              CONTROL PLANE (gRPC / Raft)                          |
|  - Peer Topology & Key Registry (Noise IKpsk2 public keys)                       |
|  - VIP Allocator (CGNAT 100.64.0.0/10)                                            |
|  - GeoIP / Node Capability Catalog & Composite Scorer                             |
+------------------------------------------+----------------------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
+-------------------v-------------------+     +-------------------v-------------------+
|       CAMOUFLAGED RELAY FLEET         |     |        NERONET MESH CLIENT / NODE     |
|  - WSS / TLS 1.3 on Port 443          |     |  - Userspace Netstack                 |
|  - Anti-Probing Decoy Web Engine      |     |  - Disco-v4 NAT Traversal Engine      |
|  - Line-Rate STUN (3478 UDP)          |     |  - DirectFrame SVRN Framing           |
+---------------------------------------+     +-------------------+-------------------+
                                                                  |
                                              +-------------------+-------------------+
                                              |                                       |
                               +--------------v--------------+         +--------------v--------------+
                               |     CLIENT EXIT BRIDGE      |         |     ROUTING & OBFUSCATION   |
                               |  - Userspace Socket Bridge  |         |  - Country Dynamic Scoring  |
                               |  - RFC 1918 Bogon Filter    |         |  - Specific Host ID Egress  |
                               |  - Anti-Abuse Port Filter   |         |  - 3-Hop Onion Routing      |
                               |  - Battery & Data Guardian  |         |  - Anti-Leak DoH Multi-Res  |
                               +-----------------------------+         +-----------------------------+
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | VLESS/REALITY Camouflage | Inbound proxy config with XTLS Reality & TLS fingerprint imitation | M1 | Survey (Legacy Audit) |
| 2 | Decoy Web Engine | Nginx fallback site with automated HTTPS certificates | M1 | Survey (Legacy Audit) |
| 3 | Dynamic DNS & Discovery | Automated DuckDNS / external IP discovery daemon | M1 | Survey (Legacy Audit) |
| 4 | Parameterized Revocation | SQL injection-safe client revocation with prepared statements | M1 | Survey (Legacy Audit) |
| 5 | DB Injector & Routing | Client config injector and automated database patcher | M1 | Survey (Legacy Audit) |
| 6 | Master CLI Setup Console | Interactive & non-interactive `sovereign-setup` control script | M1 | Survey (Legacy Audit) |
| 7 | Active Defense Honeypot | Security daemon with token-bucket limiter and exponential threat scorer | M1 | Survey (Legacy Audit) |
| 8 | Multi-Factor Secret Mgmt | Zero-plaintext vault system with `umask 077` and env isolation | M1 | Survey (Legacy Audit) |
| 9 | Rootless Container Runtime | Hardened unprivileged Docker container profiles (`UID 10001:10001`) | M1 | Survey (Legacy Audit) |
| 10 | Host Hardening & Cleanup | Sysctl BBR tuning, firewall lockdown, and zero-leak uninstallation | M1 | Survey (Legacy Audit) |
| 11 | Noise Cryptographic Plane | `Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s` handshake and data cipher | M2 | Survey (Mesh Architecture) |
| 12 | DirectFrame SVRN Framing | 24-byte header binary wire protocol with 64-bit anti-replay window | M2 | Survey (Mesh Architecture) |
| 13 | Camouflaged DERP-v4 Relay | TLS 1.3 / WebSocket relay multiplexer with active probing decoy | M2 | Survey (Mesh Architecture) |
| 14 | Adaptive Disco-v4 NAT | Multi-strategy hole puncher (STUN, Prediction, 256-port Birthday Spray) | M2 | Survey (Mesh Architecture) |
| 15 | Sandboxed Client Bridge | Userspace netstack exit node with strict RFC 1918 bogon suppression | M2 | Survey (Mesh Architecture) |
| 16 | Multi-Mode Routing Engine | Dynamic country selection, host ID routing, and 3-hop onion obfuscation | M2 | Survey (Mesh Architecture) |
| 17 | Unified Multi-Cloud Schema | Declarative `mesh-cluster.yaml` (`apiVersion: sovereign.mesh/v4alpha1`) | M3 | Survey (Multi-Cloud/K8s) |
| 18 | Multi-Cloud IaC Modules | Modular OpenTofu/Terraform modules for OCI, AWS, GCP, DO, Hetzner, Vultr | M3 | Survey (Multi-Cloud/K8s) |
| 19 | Universal Node Bootstrap | Distro-agnostic cloud-init & bootstrap script for Ubuntu, RHEL, Alpine | M3 | Survey (Multi-Cloud/K8s) |
| 20 | Kubernetes Helm Chart | Enterprise Helm chart (`charts/sovereign-mesh/`) with HA Deployment, StatefulSet, DaemonSet | M3 | Survey (Multi-Cloud/K8s) |
| 21 | K8s Kustomize Overlays | Cloud-specific NLB/LB annotations and ingress definitions | M3 | Survey (Multi-Cloud/K8s) |
| 22 | GitOps Branch Migration | Automated script branching legacy to `v2`, tagging `v2.0.0-legacy`, staging `main` | M6 | Survey (GitOps/CI) |
| 23 | Production CI/CD Fleet | GitHub Actions for linting, cloud IaC tests, SAST scanning, Cosign signing | M6 | Survey (GitOps/CI) |
| 24 | Full E2E Test Pass | 100% pass across 5 Tiers of requirement-driven test cases (289+ tests) | M5 | Survey (E2E Test Track) |
| 25 | Adversarial Hardening | White-box stress testing, chaos fuzzing, and forensic integrity audit | M5 | Survey (E2E Test Track) |
| 26 | Dynamic Peer ACL Engine | Directional/bidirectional peer group security policies & protocol filtering | M4 | NetBird Parity Analysis |
| 27 | Extra Subnet Route Dist | CIDR route publishing, routing peers, and high-availability route failover | M4 | NetBird Parity Analysis |
| 28 | Real-time Peer Posture | Client OS/version, geo-fencing, and compliance posture check validation | M4 | NetBird Parity Analysis |
| 29 | Management Dashboard API | Dynamic REST/gRPC topology visualization, peer metrics & web UI concepts | M4 | NetBird Parity Analysis |
| 30 | Future Roadmap Spec | Comprehensive `FUTURE_PLANS.md` architecture guide for v5.0 | M5 | System Architecture Review |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Legacy Audit & Security Parity | Features 1-10: Legacy script refactoring, SQLi fix, honeypot daemon, secrets vault, container hardening | none | DONE |
| M2 | Proprietary P2P Mesh & Exit Bridge | Features 11-16: Noise protocol, SVRN wire framing, DERP-v4, Disco-v4, client-bridge netstack, country/host/onion routing | M1 | DONE |
| M3 | Multi-Cloud Config & Kubernetes | Features 17-21: `mesh-cluster.yaml`, Terraform modules (6 clouds), bootstrap engine, Helm charts, Kustomize overlays | M1, M2 | DONE |
| M4 | NetBird Parity & Feature Implementation | Features 26-29: Dynamic ACL/Policy Engine, Route Distribution & Subnets, Posture Checks, Real-time Management APIs | M2, M3 | DONE |
| M5 | System-Wide Review & Future Planning | Features 24-25, 30: Holistic codebase review, 100% E2E test suite pass across all tiers, and `FUTURE_PLANS.md` (v5.0 roadmap) | M1..M4 | DONE |
| M6 | GitOps & GitHub Automation | Features 22-23: Automated GitHub migration (`migrate_to_v2_and_stage_v4.sh`, push to `Mohamed-DN/sovereign-oci-proxy`), CI/CD workflows | M1..M5 | DONE |
| M7 | Netmaker, AnywhereLAN & NeroNet Branding | eBPF fast-path routing, ICE NAT, Multi-Path scoring, NeroNet project website, and final GitHub push | M1..M6 | DONE |

## Interface Contracts

### Control Plane ↔ Client / Node (`api/proto/mesh_control.proto`)
- `RegisterNode(RegisterRequest) returns (RegisterResponse)`: Registers public Noise key, metadata (country, capabilities, version), receives VIP (`100.64.x.y`).
- `NodeHeartbeat(HeartbeatRequest) returns (HeartbeatResponse)`: Reports load, latency, battery/quota guardian state, receives topology changes.
- `DiscoverExitBridges(DiscoverRequest) returns (DiscoverResponse)`: Queries exit nodes filtered by Country Code, Latency, Bandwidth, or specific Host ID.
- `BuildCircuitPath(CircuitRequest) returns (CircuitResponse)`: Obtains a 3-hop cryptographic circuit path for onion obfuscation.

### Data Plane Wire Framing (`pkg/crypto/wire.go`)
- Header: `[0:4] Magic (0x5356524E / SVRN)`, `[4:6] Version (0x0004)`, `[6:8] MsgType`, `[8:16] Sequence (uint64)`, `[16:24] SessionID (uint64)`, `[24:] Ciphertext + Poly1305 Tag`.

### Sandboxed Egress Interface (`pkg/bridge/sandbox.go`)
- `ValidateEgressTarget(target net.IP, port uint16) error`:
  - Rejects Bogon / RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `100.64.0.0/10`, `fc00::/7`).
  - Rejects Abusive Ports (25, 465, 587, 137-139, 445).

### Unified Multi-Cloud Configuration Schema (`configs/mesh-cluster.yaml`)
- `apiVersion: sovereign.mesh/v4alpha1`
- `kind: SovereignCluster`
- `spec.global`: overlay CIDR, cipher suite, keepalive, DNS servers.
- `spec.controlPlane`: HA replicas, Raft consensus, SQLite storage path.
- `spec.relays`: Multi-cloud region array (OCI, AWS, GCP, Hetzner, DO, Vultr).
- `spec.exitGateways`: Allowed egress modes, bandwidth quotas, bogon filters.

## Code Layout
- `api/proto/`: Protobuf service definitions (`mesh_control.proto`).
- `cmd/`: Application entrypoints (`sovereign-control-plane`, `sovereign-node`, `sovereign-security-daemon`, `sovereign-derp-relay`).
- `pkg/crypto/`: Noise protocol state machine, key generation, wire framing.
- `pkg/nat/`: STUN client, Disco-v4 port prediction & spray engine.
- `pkg/derp/`: WebSocket/TLS relay server and packet multiplexer.
- `pkg/bridge/`: Userspace netstack dialer, RFC 1918 sandbox filter, device resource guardians.
- `pkg/routing/`: Multi-mode routing engine (Country, Host ID, 3-Hop Onion).
- `pkg/config/`: Schema parser, semantic validator, Terraform/Helm generator.
- `configs/`: Unified cluster configurations, Nginx, sysctl, and Xray templates.
- `terraform/`: Cloud provider infrastructure modules (OCI, AWS, GCP, DO, Hetzner, Vultr).
- `charts/sovereign-mesh/`: Production Kubernetes Helm chart.
- `k8s/overlays/`: Cloud-specific Kustomize manifests.
- `scripts/`: Operational, legacy refactor, bootstrap, and GitOps migration scripts.
- `tests/`: Comprehensive unit, legacy compatibility, integration, and E2E test suites.
- `.github/workflows/`: Production CI/CD pipelines.
