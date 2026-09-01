# Project: NeroNet Enterprise Management Console (v4.0 / v5.0 Ready)

## Architecture
The NeroNet Enterprise Management Console is a full-stack mission-control platform for the NeroNet sovereign mesh network.

```
+-----------------------------------------------------------------------------------------------+
|                                    ENTERPRISE WEB CONSOLE                                     |
|                       (React 18 + Vite + Tailwind CSS Dark Slate-900)                         |
|                                                                                               |
|  [Linear-style Collapsible Sidebar]           [Top HUD: Live Throughput, Role Switcher]       |
|  ├── Pinned "☢ DESTROY NOW" Button            ├── 3D Topology (react-force-graph-3d)          |
|  ├── Mesh & Network (3D, Matrix, Peering, Map)├── Node Action Slide-Over Drawer               |
|  ├── Compute & Storage (Cloud PC, NeroDrop)   ├── Sovereign Cloud PC (WebRTC Native)          |
|  ├── Security (Risk Dashboard, ACLs, Audits)  ├── Cross-Mesh Peering Management               |
|  └── Danger Zone (NeroNuke 3-Tier DMS)        └── Geo-Fencing 2D PostGIS Policy Overlay       |
+-----------------------------------------------------------------------------------------------+
                                                │
                                    HTTPS / WSS Reverse Proxy
                                                │
+-----------------------------------------------------------------------------------------------+
|                                  CONTROL PLANE API (Node.js)                                  |
|                                                                                               |
|  ├── Auth & RBAC (Strict bcrypt + DB-only, no backdoors, Valkey token blacklist)              |
|  ├── Core CRUD (Users, Nodes, Noise Configs, VIP Allocator 100.64.0.0/10)                     |
|  ├── Impossible Travel & Behavioral Risk Engine (>1000km/h velocity => +50 risk, auto-quar)   |
|  ├── Geo-Fencing Policy Engine (PostGIS ISO country allow/block/quarantine)                   |
|  ├── Cross-Mesh Peering Engine (Ed25519 tokens, subnet scoping, purple node tagging)          |
|  ├── Sovereign Cloud PC WebRTC Control Plane (Selkies-GStreamer signaling, STUN/TURN, OTP)   |
|  ├── NeroNuke 3-Tier Self-Destruct & Dead Man's Switch Engine (Tiers 1, 1b, 2, 3)             |
|  └── Real-Time WebSocket Topology Hub (/ws/topology) synced via Valkey Pub/Sub               |
+-----------------------------------------------------------------------------------------------+
                               │                                │
                 SQL / PostGIS / JSONB / Vector           Pub/Sub / Caching / Sessions
                               ▼                                ▼
+-----------------------------------------------+ +---------------------------------------------+
|          PostgreSQL 16 Database               | |              Valkey 7 Bus                   |
|  - PostGIS Spatial Extension (4326)           | |  - Pub/Sub channel neronet:topology:events  |
|  - pgvector AI Anomaly Extension (1536)       | |  - Token Revocation Blacklist (O(1))        |
|  - JSONB Metadata, Posture, Telemetry         | |  - Live Rate Limiting & Session Store       |
+-----------------------------------------------+ +---------------------------------------------+
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Database Migration (Postgres + Valkey) | Migrate SQLite to PostgreSQL 16 (JSONB, PostGIS, pgvector) + Valkey 7 | M1 | R1, survey |
| 2 | Auth Security Hardening | Eliminate all client/server auth fallback vulnerabilities; strict bcrypt+DB | M1 | R3, survey |
| 3 | Core Control Plane APIs & WebSocket | Users, Nodes CRUD, WireGuard/Noise configs, WS `/ws/topology`, `/api/health` | M1 | R3, survey |
| 4 | Valkey Pub/Sub HA State Sync | Sync node connect/disconnect/quarantine across replicas via `neronet:topology:events` | M1 | R6, survey |
| 5 | Behavioral Risk & Impossible Travel | Telemetry ingestion, RTT drift, >1000km/h velocity flag (+50 risk), auto-quarantine (>75) | M2 | R3, R7, survey |
| 6 | Geo-Fencing Policy Engine | Country allow/block/quarantine rules via PostGIS ISO lookups | M2 | R7, survey |
| 7 | Cross-Mesh Peering API | Ed25519 token signing/verification, subnet scoping, purple node tagging | M2 | R4, survey |
| 8 | Sovereign Cloud PC WebRTC Control Plane | Selkies-GStreamer signaling tokens, STUN/TURN creds, custom domains + SSO/OTP gateway | M2 | R2, survey |
| 9 | NeroNuke Tier 1: User Self-Destruct | Instant/scheduled account destruction, "DELETE MY ACCOUNT" confirmation, hard delete | M3 | R5, survey |
| 10 | NeroNuke Tier 1b: Invisible Personal DMS | Steganographic secret access (reverse/split/shadow/key/OTP), silent personal wipe | M3 | R5, survey |
| 11 | NeroNuke Tier 2: Owner Global DMS | Passphrase bcrypt hash + interval, offline-safe timer, canary webhook, cascading wipe | M3 | R5, survey |
| 12 | NeroNuke Tier 3: Warrant Canary | Ed25519 signed `/.well-known/canary.txt` updated on valid heartbeat confirmation | M3 | R5, survey |
| 13 | Enterprise Design System & Sidebar | Slate-900 `#0f172a`, card `#1e293b`, accent `#38bdf8`, alerts `#8b5cf6`, collapsible sidebar | M4 | R2, survey |
| 14 | Pinned NeroNuke Red Countdown Button | Persistent "☢ DESTROY NOW" button with pulsing border & live countdown pinned across all pages | M4 | R5, survey |
| 15 | Interactive 3D Mesh Topology | `react-force-graph-3d`, camera hover float, drawer trigger, purple peered, red pulsing >75 | M4 | R2, survey |
| 16 | Node Action Drawer Enhancements | Kill Switch toggle, direct NeroDrop launch, quarantine subnet indicator `100.64.250.0/24` | M4 | R2, R7, survey |
| 17 | User Mgmt: QR Onboarding & Split Tunnel | QR code mobile onboarding generator modal, Split Tunneling (`bypass_apps` JSONB) editor | M4 | R7, survey |
| 18 | App Bundles: WebRTC Sovereign Cloud PC | WebRTC viewer share links, custom domain configuration UI | M4 | R2, survey |
| 19 | Cross-Mesh Peering UI | `PeeringManagement.jsx` agreement lifecycle & token exchange | M4 | R4, survey |
| 20 | Behavioral Risk Dashboard | `BehavioralRiskDashboard.jsx` risk score gauges, anomaly feed, auto-quarantine controls | M4 | R2, survey |
| 21 | Geo-Fencing 2D Map Overlay | `GeoFencingMap.jsx` interactive 2D world map with country policy editor | M4 | R2, survey |
| 22 | Local Staging (Docker Compose) | PostgreSQL 16, Valkey 7, Backend, Nginx on 8443, 8081, 5432, 6379; macOS routing safe | M5 | R8, survey |
| 23 | Architecture & Migration Documentation | `docs/MIGRATION.md`, `docs/HA_ARCHITECTURE.md`, `docs/CONSOLE_ARCHITECTURE.md`, `FUTURE_PLANS.md` | M5 | R1, R6, R9, survey |
| 24 | Final E2E Test Suite (Tiers 1-4) | Comprehensive opaque-box test suite verifying all 12 modules ($>=5$ tests/feature) | M6, E2E | Rubric, survey |
| 25 | Adversarial Coverage Hardening (Tier 5) | White-box adversarial probing, security vulnerability exhaustion | M6 | Rubric, survey |
| 26 | GitOps Clean Push | Push to `Mohamed-DN/sovereign-oci-proxy` on `main` without `.agents/` or AI artifacts | M6 | R9, survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Database, Security & Core APIs | PostgreSQL 16 + Valkey 7, PostGIS, pgvector, Auth fix, Core CRUD, WS, `/api/health`, `docs/MIGRATION.md` | None | DONE |
| M2 | Advanced Engines & Policy | Impossible Travel & Behavioral Risk Engine, Geo-Fencing PostGIS Engine, Cross-Mesh Peering API, Sovereign Cloud PC WebRTC Control Plane | M1 | PLANNED |
| M3 | NeroNuke 3-Tier Dead Man's Switch | Tier 1 User Instant/Scheduled Kill, Tier 1b Personal Invisible DMS, Tier 2 Owner Global DMS, Tier 3 Warrant Canary | M1 | PLANNED |
| M4 | Enterprise Frontend Web UI | Slate-900 theme, Collapsible Sidebar, Pinned Red Button, 3D Topology (`react-force-graph-3d`), Node Actions Drawer, Peering UI, Risk Dashboard, Geo-Fence Map, Cloud PC WebRTC | M1, M2, M3 | PLANNED |
| M5 | Local Staging & Architecture Docs | `docker-compose.yml`, `./scripts/start-console.sh`, `docs/HA_ARCHITECTURE.md`, `docs/CONSOLE_ARCHITECTURE.md`, `FUTURE_PLANS.md` | M1, M2, M3, M4 | PLANNED |
| M6 | Final Verification & GitOps Push | Phase 1 (100% E2E Pass Tiers 1-4), Phase 2 (Tier 5 Hardening), GitOps push to `Mohamed-DN/sovereign-oci-proxy` on `main` | M1-M5, E2E_READY | PLANNED |
| E2E | E2E Testing Track | Comprehensive 4-Tier Opaque-Box Test Suite & Runner, publishing `TEST_READY.md` | Survey | PLANNED |

## Interface Contracts

### Backend ↔ Frontend REST / WebSocket API
- Base URL: `/api`
- WebSocket: `/ws/topology` (Requires JWT token query param `?token=...` or Authorization header)
- Standard Response Envelope:
  ```json
  {
    "status": "success",
    "data": { ... },
    "error": null
  }
  ```
- Error Response Envelope:
  ```json
  {
    "status": "error",
    "error": "Descriptive error message"
  }
  ```

### Cross-Mesh Peering Token Contract (Ed25519)
- Token Structure:
  ```json
  {
    "version": "1.0",
    "peering_id": "string",
    "initiator_endpoint": "string (URL)",
    "initiator_public_key": "string (Base64 Ed25519)",
    "scope_mode": "ALL | SPECIFIC_DEVICES | SPECIFIC_SUBNETS",
    "shared_device_ids": ["string"],
    "shared_subnets": ["string (CIDR)"],
    "expires_at": "string (ISO8601)",
    "signature": "string (Base64 Ed25519 signature of canonical JSON)"
  }
  ```

### NeroNuke Dead Man's Switch API Contract
- Tier 1 Instant Kill: `POST /api/nuke/user/self-destruct` body `{"confirmation_text": "DELETE MY ACCOUNT", "disclaimer_accepted": true}`
- Tier 1 Scheduled Kill: `POST /api/nuke/user/schedule` body `{"scheduled_deletion_at": "ISO8601"}`
- Tier 1b Personal DMS: `POST /api/nuke/personal-dms/setup` body `{"passphrase": "...", "heartbeat_interval_seconds": 86400, "steganography_mode": "..."}`
- Tier 2 Owner DMS: `POST /api/nuke/owner-dms/setup` body `{"passphrase": "...", "heartbeat_interval_seconds": 86400, "webhook_url": "..."}`
- Tier 3 Canary: `GET /.well-known/canary.txt` returns raw cryptographically signed text.

### Sovereign Cloud PC WebRTC Contract
- `POST /api/cloud-pc/:id/project`:
  ```json
  {
    "session_id": "string",
    "device_id": "string",
    "signaling_url": "wss://.../ws/selkies",
    "ice_servers": [{ "urls": "stun:..." }, { "urls": "turn:...", "username": "...", "credential": "..." }],
    "stream_token": "string"
  }
  ```
- `POST /api/cloud-pc/custom-domains/:domain/auth-gateway`:
  ```json
  {
    "domain": "desktop.company.com",
    "otp_code": "123456"
  }
  ```

## Code Layout
- `console/backend/`:
  - `config/`: `env.js`, `database.js`
  - `db/`: `index.js` (PostgreSQL pool), `valkey.js`, `migrator.js`, `migrations/`, `seed.js`
  - `middleware/`: `auth.js`, `rbac.js`, `cors.js`, `errorHandler.js`, `rateLimiter.js`
  - `routes/`: `auth.js`, `users.js`, `nodes.js`, `configs.js`, `peering.js`, `risk.js`, `geofencing.js`, `nuke.js`, `cloudPc.js`, `nerodrop.js`, `stats.js`, `health.js`
  - `services/`: `NukeEngine.js`, `RiskEngine.js`, `PeeringEngine.js`, `PolicyEngine.js`, `WebRtcSignalingEngine.js`, `TopologySync.js`, `CanaryService.js`
  - `ws/`: `topologyServer.js`
  - `utils/`: `crypto.js`, `audit.js`, `logger.js`
- `console/frontend/`:
  - `src/components/`: `Sidebar.jsx`, `Header.jsx`, `Overview.jsx`, `Topology3D.jsx`, `NodeMatrix.jsx`, `NodeActions.jsx`, `UserManagement.jsx`, `AppBundles.jsx`, `PeeringManagement.jsx`, `BehavioralRiskDashboard.jsx`, `GeoFencingMap.jsx`, `NeroNukePanel.jsx`, `NeroNukeSecretAccessModal.jsx`, `NeroNukePersistentButton.jsx`, `NeroDrop.jsx`, `CryptoConfigModal.jsx`, `SettingsACL.jsx`, `AuditLogs.jsx`
  - `src/context/`: `AuthContext.jsx`
  - `src/services/`: `api.js`
- `console/docs/`: `MIGRATION.md`, `HA_ARCHITECTURE.md`, `CONSOLE_ARCHITECTURE.md`
- `tests/e2e/`: `console_e2e.py`, `console_runner.py`, `test_console_suite.js`
- `scripts/`: `start-console.sh`, `stop-console.sh`, `test-console.sh`
- Root: `docker-compose.yml`, `FUTURE_PLANS.md`, `ORIGINAL_REQUEST.md`, `PROJECT.md`
