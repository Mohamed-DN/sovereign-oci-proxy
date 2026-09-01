# Original User Request

## 2026-08-31T12:32:04Z

## Research Findings (Pre-loaded context for agents)
- **Headscale/NetBird HA gap:** Neither project has native active-active HA for the Control Plane. NeroNet can surpass both by using Valkey Pub/Sub to sync in-memory state across API instances.
- **PostgreSQL extensions to use:** pgvector (future AI anomaly detection), PostGIS (node geolocation/geo-fencing), JSONB (flexible node metadata). No MongoDB needed.
- **Sovereign Cloud PC stack:** Reference **Selkies-GStreamer** (https://github.com/selkies-project/selkies-gstreamer) as the WebRTC GPU-accelerated streaming engine. Document this in FUTURE_PLANS.md.

---

Build the NeroNet Enterprise Management Console — a full-stack web application that acts as the mission-control center for the NeroNet v4.0 mesh network. The project is a continuation of prior work already partially completed in `~/teamwork_projects/sovereign_proxy_v4_retry/console`. Resume from what exists; do not rewrite from scratch.

Use a very large team of agents.

Working directory: ~/teamwork_projects/sovereign_proxy_v4_retry/console
Integrity mode: development

## Context (From Prior Work)
- Backend structure exists in `console/backend/` with partially-built routes and auth (auth fallback security vulnerability was found and must be fixed).
- Frontend scaffolding exists in `console/frontend/` (React + Vite + Tailwind, partially built).
- 72 E2E tests were passing before the crash. Resume and extend them.

---

## Requirements

### R1. Database: PostgreSQL + Valkey (HA-ready)
Replace any SQLite references with **PostgreSQL** (v16+). Configure with:
- **JSONB columns** for flexible node metadata and posture check results.
- **PostGIS extension** for node geolocation data (needed for geo-fencing, country-based routing display).
- **pgvector extension** installed but not yet used (reserved for future AI anomaly detection).
- Add **Valkey** (Redis-compatible) as a caching and session store layer.
- The Docker Compose setup must include PostgreSQL + Valkey containers.
- Document the migration in `docs/MIGRATION.md`.

### R2. Enterprise Frontend Web UI — Complete & Enhance
Use **React + Vite + Tailwind CSS** with the following design language:
- **Dark theme**: Background `#0f172a` (slate-900), card `#1e293b` (slate-800), accent `#38bdf8` (sky-400) for primary actions, `#8b5cf6` (violet-500) for secondary/alerts. Typography: Inter/Geist font.
- **Sidebar navigation** with collapsible sections (inspired by Linear/Vercel/Supabase dashboards).
- All panels must feel like a premium enterprise SaaS (Tailwind utility classes, no custom CSS unless unavoidable).

Include these complete features:
- **Global Overview Dashboard**: Real-time stats (Active Nodes, Total Bandwidth, Connected Users, Security Score).
- **Interactive 3D Network Topology** (`react-force-graph-3d`): Physics-based 3D spiderweb. Super-Admin sees the full global mesh. Users see ONLY their own isolated mesh. When hovering a node it floats toward the camera; clicking opens a right-side action panel.
- **Node Action Panel** (on node click): Ping Device, Set as Exit Node, Quarantine/Isolate (auto-moves to `100.64.250.0/24`), Onion Obfuscation Toggle (3-Hop ON/OFF), Send File (NeroDrop P2P).
- **User Management**: Create/Revoke users, assign to Cloud or BYOS tiers.
- **App Bundles Panel**: Cloud PC (Guacamole) instance management. "Generate Public Share Link" for Clientless RDP.
- **Cross-Mesh Peering UI**: Create/list/revoke peering agreements with external NeroNet instances. Peered nodes appear in 3D graph with a distinct color (purple).
- **Continuous Behavioral Risk Score Dashboard**: Show per-node risk score (0-100) with color coding (green <40, yellow 40-75, red >75). Nodes >75 are auto-quarantined and shown with a red pulsing icon.
- **Geo-fencing Map**: A 2D world map overlay showing which countries are allowed/blocked/quarantined by policy.
- **NeroNuke Panel**: Full implementation of the 3-tier self-destruct system (see R5 below).

### R3. Control Plane API — Complete & Extend
Complete the Go or Node.js backend API:
- Fix the hardcoded auth fallback security vulnerability in `routes/auth.js` (use strict bcrypt+DB-only verification).
- Full CRUD for users, nodes, VPN Noise keypairs.
- WebSocket endpoint for real-time topology updates (push node connect/disconnect events to 3D graph).
- Endpoints: Ping, Quarantine, Exit Node assignment, Onion toggle, NeroDrop initiation, Share Link generation.
- Peering Agreement API: create, list, accept, revoke.
- Behavioral Risk Score API: ingest node telemetry and compute risk (RTT anomaly, geo-drift detection).
- NeroNuke API: heartbeat check-in, passphrase verification, wipe trigger.
- `GET /api/health` health check endpoint.

### R4. Cross-Mesh Peering (New Feature)
Design and implement a "Cross-Mesh Peering" system:
- Either party initiates a "Peering Request" by exchanging a signed token (Ed25519).
- Admin defines scope: share ALL devices, or only SPECIFIC device IDs/subnets.
- Both admins can view the peered network's shared nodes in their 3D graph with distinct purple color coding.
- Peering is time-limited (expiry) and revocable at any time.
- Reference open-source implementations: NetBird shared routes, Headscale shared nodes.

### R5. NeroNuke: Dead Man's Switch & Account Self-Destruct System
Implement a **3-tier account destruction and dead man's switch system**. This is a professional privacy/security feature used by journalists and activists worldwide.

#### Tier 1: User Account Self-Destruct (User-facing)
- **Immediate Destruction:** User requests account deletion. Must: (1) read and accept a legal disclaimer, (2) type the phrase "DELETE MY ACCOUNT" to confirm.
- **Persistent Red Button (CRITICAL UX RULE):** Once signed, a **permanent red "☢ DESTROY NOW" button** is IMMEDIATELY pinned to the top of the sidebar, visible on EVERY page. It does NOT disappear when navigating away. Stays visible until user returns to NeroNuke settings and clicks "Deactivate". Must use a pulsing red border animation with nuclear/skull icon.
- **Scheduled Destruction:** User can set a future deletion date. A live countdown is shown inside the persistent red button. Cancellable only from the NeroNuke settings deactivation page.
- **Data Wiped on Trigger:** All user records, VPN keypairs, node registrations, file metadata, subscription records, and session tokens are cryptographically overwritten. PostgreSQL rows are hard-deleted (no soft-delete, no tombstone).

#### Tier 1b: Per-User NeroNuke Dead Man's Switch (Personal Network)
Every regular user — not just the Super-Admin — has their OWN personal NeroNuke dead man's switch:
- **Scope:** Wipes only the user's own devices, VPN keys, files, and account. Does NOT affect other users or the global network.
- **Setup:** User sets a secret passphrase + a heartbeat interval (1 minute to 10 years). No system warnings, no reminders — ever.
- **Trigger:** If the user fails to re-enter their passphrase before the interval expires, ONLY their account and devices are silently wiped. The admin is NOT notified.
- **UI Location:** A "Personal NeroNuke" section in every user's account settings.

#### Tier 2: NeroNuke — Network Owner Dead Man's Switch (Admin-facing, Global Wipe)
A "Dead Man's Switch" for the network owner (Super-Admin):
- **Setup:** Owner sets a secret passphrase (any length) + a heartbeat interval (1 minute to 10 years). NO system-enforced minimum or maximum.
- **Heartbeat:** Owner must re-enter passphrase before interval expires. System stores only bcrypt hash + last-confirmed timestamp.
- **Trigger Action:** Full cascading wipe of all user accounts, VPN keys, node registrations, all PostgreSQL data, all Valkey cache. Sends a single "canary alert" webhook ping to a user-defined URL before wiping.
- **Critical Design Constraints:**
  - **NO warnings, NO reminders:** NEVER sends any notification that timer is low or expired.
  - **No recovery:** Permanent and irreversible once triggered.
  - **Silent operation:** Countdown only visible when owner opens NeroNuke panel and authenticates.
  - **Offline-safe:** Timer stored server-side in PostgreSQL; triggers even if owner's device is offline.

#### Tier 3: Warrant Canary (Transparency Signal)
- Generate a cryptographically signed `canary.txt` (signed with owner's Ed25519 key) at each heartbeat re-confirmation. Published at `/.well-known/canary.txt`.
- When Dead Man's Switch triggers, the canary file stops being updated — a silent signal to privacy-conscious users.

### R6. HA-Ready Infrastructure Design
In the API and Docker Compose, structure the service to be HA-ready:
- State that modifies topology must be published to Valkey Pub/Sub channel `neronet:topology:events`.
- API instances subscribe to this channel so multiple replicas stay in sync.
- Document the HA scaling path in `docs/HA_ARCHITECTURE.md`.

### R7. Implement "Now" Items from FUTURE_PLANS.md
- **QR Code Onboarding**: Generate a QR code for each user for instant mobile onboarding.
- **Impossible Travel Detection**: Flag when device IP jumps >1000km/h between heartbeats. Set risk score += 50.
- **Geo-Fencing Policy Engine**: Country-level allow/block/quarantine rules via PostGIS. Expose policy editor in frontend.
- **Kill Switch Flag**: Store per-node `kill_switch_enabled` boolean. Frontend toggle per node.
- **Split Tunneling Config**: Store per-user `bypass_apps` JSONB array. Expose in frontend.

### R8. Local Staging (macOS safe)
Provide a `docker-compose.yml` with: PostgreSQL 16, Valkey 7, Backend API, Frontend via Nginx.
- Ports: 8443 (frontend), 8081 (API), 5432 (Postgres), 6379 (Valkey).
- Must NOT touch global macOS routing tables or interfere with Tailscale.
- Include a `./scripts/start-console.sh` convenience script.

### R9. GitOps Push
Stage files without AI artifacts and push to `Mohamed-DN/sovereign-oci-proxy` on `main`. Document all new features in `docs/CONSOLE_ARCHITECTURE.md`.

---

## Acceptance Criteria

### Independent Agent Rubric (Verification)
- [ ] **Database:** PostgreSQL starts in Docker, migrations run with PostGIS and pgvector extensions installed, JSONB columns exist on the `nodes` table.
- [ ] **Auth Security:** The hardcoded auth fallback is confirmed removed. Login fails with wrong credentials.
- [ ] **API Health:** `GET /api/health` returns HTTP 200.
- [ ] **3D Graph:** Frontend compiles and the 3D topology component renders without errors.
- [ ] **Peering:** Peering API can create, list, and revoke a mock peering agreement.
- [ ] **Risk Score:** An automated test verifies that "impossible travel" (geo-drift > 1000km/h) causes risk score >= 50.
- [ ] **NeroNuke:** An automated test verifies that after a heartbeat interval expires, the wipe function is triggered and user data is deleted.
- [ ] **GitOps:** Code cleanly pushed to GitHub `main` branch.

## 2026-08-31T13:31:52Z

# Teamwork Project Prompt — Draft (Phase 10 — FULL CONSOLIDATED + HA Research)

> Goal: Build NeroNet Enterprise Management Console
> Requested team: Use a very large team of agents.

## Research Findings (Pre-loaded context for agents)
- **Headscale/NetBird HA gap:** Neither project has native active-active HA for the Control Plane. NeroNet can surpass both by using Valkey Pub/Sub to sync in-memory state across API instances.
- **PostgreSQL extensions to use:** pgvector (future AI anomaly detection), PostGIS (node geolocation/geo-fencing), JSONB (flexible node metadata). No MongoDB needed.
- **Sovereign Cloud PC stack:** Reference **Selkies-GStreamer** (https://github.com/selkies-project/selkies-gstreamer) as the WebRTC GPU-accelerated streaming engine. Document this in FUTURE_PLANS.md.

---

Build the NeroNet Enterprise Management Console — a full-stack web application that acts as the mission-control center for the NeroNet v4.0 mesh network. The project is a continuation of prior work already partially completed in `~/teamwork_projects/sovereign_proxy_v4_retry/console`. Resume from what exists; do not rewrite from scratch.

Working directory: ~/teamwork_projects/sovereign_proxy_v4_retry/console
Integrity mode: development

## Context (From Prior Work)
- Backend structure exists in `console/backend/` with partially-built routes and auth (auth fallback security vulnerability was found and must be fixed).
- Frontend scaffolding exists in `console/frontend/` (React + Vite + Tailwind, partially built).
- 72 E2E tests were passing before the crash. Resume and extend them.

---

## Requirements

### R1. Database: PostgreSQL + Valkey (Single Node, HA-Ready Design)
Use **PostgreSQL** (v16+) as the primary database. Configure with:
- **JSONB columns** for flexible node metadata and posture check results.
- **PostGIS extension** for node geolocation data (geo-fencing, country-based routing display).
- **pgvector extension** installed but not yet used (reserved for future AI anomaly detection).
- Add **Valkey** (Redis-compatible) as caching and session store.
- The Docker Compose setup includes a **single PostgreSQL instance** (no replication configured for now — resources not yet available). However, the schema, connection strings, and config must be designed to support adding a streaming replica later with zero schema changes (use `postgresql.conf` placeholders and document in `docs/HA_ARCHITECTURE.md` exactly what to enable when a second node is available).
- Document the full HA path (Primary + Standby + Valkey cluster) in `docs/HA_ARCHITECTURE.md` as a "Future Activation" guide, but do NOT implement it yet.
- Document the migration from prior SQLite in `docs/MIGRATION.md`.


### R2. Enterprise Frontend Web UI — Complete & Enhance
Use **React + Vite + Tailwind CSS** with the following design language:
- **Dark theme**: Background `#0f172a` (slate-900), card `#1e293b` (slate-800), accent `#38bdf8` (sky-400) for primary actions, `#8b5cf6` (violet-500) for secondary/alerts. Typography: Inter/Geist font.
- **Sidebar navigation** with collapsible sections (inspired by Linear/Vercel/Supabase dashboards).
- All panels must feel like a premium enterprise SaaS (Tailwind utility classes, no custom CSS unless unavoidable).

Include these complete features:
- **Global Overview Dashboard**: Real-time stats (Active Nodes, Total Bandwidth, Connected Users, Security Score).
- **Interactive 3D Network Topology** (`react-force-graph-3d`): Physics-based 3D spiderweb. Super-Admin sees the full global mesh. Users see ONLY their own isolated mesh. When hovering a node it floats toward the camera; clicking opens a right-side action panel.
- **Node Action Panel** (on node click): Ping Device, Set as Exit Node, Quarantine/Isolate (auto-moves to `100.64.250.0/24`), Onion Obfuscation Toggle (3-Hop ON/OFF), Send File (NeroDrop P2P).
- **User Management**: Create/Revoke users, assign to Cloud or BYOS tiers.
- **App Bundles Panel — Sovereign Cloud PC (WebRTC Native):**
  - **Skip Guacamole entirely.** Implement the control plane for the v5.0 WebRTC streaming engine (based on Selkies-GStreamer architecture).
  - List all active Cloud PC instances linked to a user.
  - **"Project Device" button:** Generates a secure public share link for a specific device. Instead of legacy WebSocket RDP, this link serves a WebRTC viewer client. The API must generate the necessary WebRTC signaling tokens and STUN/TURN credentials for the session.
  - **Custom Domain Support:** If the user configures a custom domain (e.g., `desktop.company.com`), the system generates the share link using their domain. The backend supports domain-to-session routing via a `custom_domains` table in PostgreSQL, secured by an SSO/OTP gateway before releasing the WebRTC stream.

- **Cross-Mesh Peering UI**: Create/list/revoke peering agreements with external NeroNet instances. Peered nodes appear in 3D graph with a distinct color (purple).
- **Continuous Behavioral Risk Score Dashboard**: Show per-node risk score (0-100) with color coding (green <40, yellow 40-75, red >75). Nodes >75 are auto-quarantined and shown with a red pulsing icon.
- **Geo-fencing Map**: A 2D world map overlay showing which countries are allowed/blocked/quarantined by policy.

### R3. Control Plane API — Complete & Extend
Complete the Go or Node.js backend API:
- Fix the hardcoded auth fallback security vulnerability in `routes/auth.js` (use strict bcrypt+DB-only verification).
- Full CRUD for users, nodes, VPN Noise keypairs.
- WebSocket endpoint for real-time topology updates (push node connect/disconnect events to 3D graph).
- Endpoints: Ping, Quarantine, Exit Node assignment, Onion toggle, NeroDrop initiation, Share Link generation.
- Peering Agreement API: create, list, accept, revoke.
- Behavioral Risk Score API: ingest node telemetry and compute risk (RTT anomaly, geo-drift detection).
- `GET /api/health` health check endpoint.

### R4. Cross-Mesh Peering (New Feature)
Design and implement a "Cross-Mesh Peering" system:
- Either party initiates a "Peering Request" by exchanging a signed token (Ed25519).
- Admin defines scope: share ALL devices, or only SPECIFIC device IDs/subnets.
- Both admins can view the peered network's shared nodes in their 3D graph with distinct purple color coding.
- Peering is time-limited (expiry) and revocable at any time.
- Reference open-source implementations: NetBird shared routes, Headscale shared nodes.

### R5. NeroNuke: Dead Man's Switch & Account Self-Destruct System
Implement a **3-tier account destruction and dead man's switch system** for both users (self-deletion) and the network owner (network-level dead man's switch). This is a professional privacy/security feature used by journalists and activists worldwide.

#### Tier 1: User Account Self-Destruct — Instant Kill / Scheduled Kill (Visible Mode)
This mode is for users who **consciously and explicitly** want to destroy their account now or at a future date.
- **Activation:** User navigates to NeroNuke settings (via normal login), reads the legal disclaimer, types "DELETE MY ACCOUNT" to confirm.
- **Persistent Red Button (ONLY in this mode):** The red "☢ DESTROY NOW" button appears and is pinned to the sidebar ONLY when Instant Kill or Scheduled Kill is active. It shows a live countdown for scheduled deletions. It is NEVER shown when only the Dead Man's Switch (DMS) is active.
- **Data Wiped:** All user records, VPN keypairs, nodes, files, subscriptions. PostgreSQL hard-delete, no tombstone.

#### Tier 1b: Per-User NeroNuke Dead Man's Switch — Fully Hidden Mode
The Dead Man's Switch is a **completely invisible and silent** security layer:
- **Zero Visual Presence:** When ONLY the DMS is active (and Instant Kill is NOT), there is NO red button, NO indicator, NO badge, NO status anywhere in the console. The UI looks completely normal to any observer.
- **Secret Access Panel:** To access the NeroNuke DMS control panel, the user must authenticate using a special steganographic method (chosen during DMS setup). Options:
  - **Reverse Password:** Enter their normal console password spelled backwards.
  - **Split Reverse:** Enter the first half of their password reversed + the second half correct (or vice versa).
  - **Shadow Password:** A completely separate, dedicated NeroNuke access password (different from the login password).
  - **Hardware Key:** Insert a physical USB security key (FIDO2/YubiKey) and tap it.
  - **Mobile OTP Device:** Approve access from a registered mobile authenticator app (TOTP or push notification).
- **Only inside the authenticated panel** can the user see: the DMS timer remaining, the heartbeat interval, and the option to re-enter their passphrase to reset the clock.
- **Setup:** User sets a secret passphrase + a heartbeat interval (1 minute to 10 years). Zero warnings, zero reminders — ever.
- **Trigger:** If the passphrase is not re-entered before the interval expires, ONLY the user's own account and devices are silently wiped. Admin is NOT notified.
- **UI Location:** A "Personal NeroNuke" section in every user's account settings, visually separated from admin-level controls.

#### Tier 2: NeroNuke — Network Owner Dead Man's Switch (Admin-facing, Global Wipe)

Implement a "Dead Man's Switch" for the network owner (Super-Admin). This is inspired by warrant canary systems and dead-man-hand open-source projects.
- **Setup Flow:** Owner goes to "NeroNuke" settings panel. They set: (1) A secret passphrase (any length, the owner chooses — short for convenience, long for security). (2) A "heartbeat interval" — the duration the owner has to re-enter the passphrase before the switch triggers. This can be as short as 1 minute or as long as 10 years. There is NO system-enforced minimum or maximum.
- **Heartbeat Mechanism:** The owner must re-enter their passphrase before the interval expires. The system stores only a bcrypt hash of the passphrase and the last-confirmed timestamp. When the interval expires and no valid passphrase was submitted, the switch triggers automatically.
- **Trigger Action:** When triggered, the system initiates a full cascading wipe: all user accounts, all VPN keys, all node registrations, all relational data in PostgreSQL, all Valkey cache entries. The system then sends a single "canary alert" webhook (if configured) to a user-defined URL (e.g., a private Matrix/Telegram bot endpoint) — no content, just a ping — before self-wiping.
- **Critical Design Constraints:**
  - **NO warnings, NO reminders:** The system NEVER sends any notification, email, push notification, or UI warning that the timer is running low or has expired. The owner bears full responsibility.
  - **No recovery:** Once triggered, the destruction is permanent and irreversible. There is no backup, no grace period, no undo.
  - **Silent operation:** The countdown is only visible when the owner actively opens the NeroNuke panel and authenticates. It is hidden from all other views and from all other users.
  - **Offline-safe:** The timer is stored server-side (PostgreSQL). If the owner's device is offline, the switch still triggers on the server when the interval passes.

#### Tier 3: Warrant Canary (Transparency Signal)
- The system generates a cryptographically signed `canary.txt` file (signed with the owner's Ed25519 key) at each heartbeat re-confirmation. This file states: "As of [date], NeroNet has not received any government subpoena or secret order." The file is published at `/.well-known/canary.txt`.
- If the Dead Man's Switch triggers (owner stops confirming), the canary file stops being updated. Privacy-conscious users who regularly verify the canary signature will notice it has gone stale.


### R5. HA-Ready Infrastructure Design
In the API and Docker Compose, structure the service to be HA-ready:
- State that modifies topology (node connect/disconnect, key changes) must be published to Valkey Pub/Sub channel `neronet:topology:events`.
- API instances subscribe to this channel so multiple replicas stay in sync.
- Document the HA scaling path in `docs/HA_ARCHITECTURE.md`.

### R6. Implement "Implement Now" Items from FUTURE_PLANS.md
The following items from FUTURE_PLANS.md v5.0 are simple enough to implement at the Console/API layer NOW rather than wait:
- **QR Code Onboarding**: Generate a QR code for each user from the UI for instant mobile device onboarding (no manual key entry).
- **Impossible Travel Detection**: In the Behavioral Risk Score API, flag when the same device IP jumps geography faster than physically possible (>1000km/h change in geolocation between heartbeats). Set risk score += 50.
- **Geo-Fencing Policy Engine**: In the API, add a `PolicyEngine` module with country-level allow/block/quarantine rules (using the ISO country code already stored in PostGIS). Expose a policy editor in the frontend.
- **Kill Switch Flag**: Store a per-node `kill_switch_enabled` boolean in the database. The frontend can toggle it per node.
- **Split Tunneling Config**: Store a per-user `bypass_apps` list (JSONB array) in the database. Expose it in the frontend for future client app sync.

### R7. Local Staging (macOS safe)
Provide a `docker-compose.yml` with: PostgreSQL 16, Valkey 7, the Backend API, and the Frontend served via Nginx.
- Ports: 8443 (frontend), 8081 (API), 5432 (Postgres), 6379 (Valkey).
- Must NOT touch global macOS routing tables or interfere with Tailscale.
- Include a `./scripts/start-console.sh` convenience script.

### R8. GitOps Push
Stage files without AI artifacts in the existing staging directory and push to `Mohamed-DN/sovereign-oci-proxy` on `main`. Document all new features in `docs/CONSOLE_ARCHITECTURE.md`.

---

## Acceptance Criteria

### Independent Agent Rubric (Verification)
- [ ] **Database:** PostgreSQL starts in Docker, migrations run with PostGIS and pgvector extensions installed, JSONB columns exist on the `nodes` table.
- [ ] **Auth Security:** The hardcoded auth fallback is confirmed removed. Login fails with wrong credentials.
- [ ] **API Health:** `GET /api/health` returns HTTP 200.
- [ ] **3D Graph:** Frontend compiles and the 3D topology component renders without errors.
- [ ] **Peering:** Peering API can create, list, and revoke a mock peering agreement.
- [ ] **Risk Score:** An automated test verifies that "impossible travel" (geo-drift > 1000km/h) causes risk score >= 50.
- [ ] **GitOps:** Code cleanly pushed to GitHub `main` branch.
