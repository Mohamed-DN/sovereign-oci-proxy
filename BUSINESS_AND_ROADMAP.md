# BUSINESS_AND_ROADMAP.md: NeroNet Sovereign Private Cloud & App Bundles Integration Architecture

**Document Version**: `4.1.0-PROD`  
**Classification**: Technical Architecture, Business Plan & Engineering Roadmap  
**Target Platform**: NeroNet v4.0 (DarkNero Mesh / Sovereign Proxy Ecosystem)  
**Author**: NeroNet Architecture Working Group  
**Status**: Authoritative Reference Specification  

---

## Table of Contents

1. [Chapter 1: Strategic Vision & Executive Summary](#chapter-1-strategic-vision--executive-summary)
   - 1.1 The Sovereign Cloud Imperative
   - 1.2 NeroNet Ecosystem Architecture
   - 1.3 Strategic Value Proposition
2. [Chapter 2: Deep-Dive SSO & Identity Federation Architecture](#chapter-2-deep-dive-sso--identity-federation-architecture)
   - 2.1 NeroNet Control Plane Identity Provider (IdP) Core
   - 2.2 Nextcloud Integration Architecture
   - 2.3 Immich Integration Architecture
   - 2.4 Seafile Integration Architecture
3. [Chapter 3: Dynamic Container Provisioning & Mesh Orchestration](#chapter-3-dynamic-container-provisioning--mesh-orchestration)
   - 3.1 Per-User Isolated Stack Architecture
   - 3.2 Storage Volume Management, LUKS2 Encryption & Quotas
   - 3.3 Scale-to-Zero Inactivity Daemon & Sub-3s Mesh Wake-Up
   - 3.4 Zero-Trust Egress & Userspace Mesh VIP Reverse Proxy
4. [Chapter 4: Client Integration & 1-Click User Experience](#chapter-4-client-integration--1-click-user-experience)
   - 4.1 NeroNet Native Client Architecture
   - 4.2 1-Click Launch & Seamless Native App Linking
   - 4.3 Transparent Netstack Split-Tunneling
5. [Chapter 5: Business Model, Monetization & Unit Economics](#chapter-5-business-model-monetization--unit-economics)
   - 5.1 Tiered Subscription Matrix & Packaging
   - 5.2 Unit Economics & Infrastructure COGS Analysis
   - 5.3 Payment Processing Architecture (Stripe & Crypto)
   - 5.4 Cryptographic Entitlement Token Engine (Ed25519)
   - 5.5 Lifecycle, Grace Periods & Cryptographic Purge Policy
6. [Chapter 6: Phased Engineering Roadmap & Delivery Milestones](#chapter-6-phased-engineering-roadmap--delivery-milestones)
   - 6.1 Phase 1: Foundation & Identity Core (Q1 2026)
   - 6.2 Phase 2: Dynamic Orchestrator & Nextcloud MVP (Q2 2026)
   - 6.3 Phase 3: Immich AI Photo Vault & Seafile Launch (Q3 2026)
   - 6.4 Phase 4: Global Multi-Region Federation & Cold Tiering (Q4 2026+)

---

# Chapter 1: Strategic Vision & Executive Summary

## 1.1 The Sovereign Cloud Imperative

The global digital landscape is defined by an acute crisis of digital sovereignty. Hyperscale public cloud providers (Google Workspace, Microsoft 365, Apple iCloud, Amazon Web Services) enforce an extractive economic model characterized by centralized data collection, pervasive telemetry, warrantless regulatory access, and deep vendor lock-in. While open-source self-hosted applications—such as **Nextcloud**, **Immich**, and **Seafile**—offer feature parity with commercial SaaS equivalents, their widespread adoption is severely bottlenecked by complex deployment requirements:

1. **Networking Friction**: The necessity of configuring public static IP addresses, port-forwarding on residential routers, dynamic DNS scripts, and NAT traversal.
2. **Security Vulnerabilities**: Exposing self-hosted applications directly to the public Internet invites automated CVE scanning, credential brute-forcing, and DDoS attacks.
3. **Operational Overhead**: Managing TLS certificates, reverse proxies, database migrations, backup automation, and storage quotas creates prohibitive friction for non-technical users.
4. **Fragmented Authentication**: Managing disparate user credentials across multiple disconnected self-hosted applications degrades the user experience compared to unified commercial suites.

**NeroNet v4.0** bridges this divide by evolving from a high-performance, decentralized residential proxy and mesh VPN into an **integrated sovereign private cloud ecosystem**. By coupling its encrypted userspace mesh network (`Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s`) with an automated container orchestration engine and an OpenID Connect (OIDC) Single Sign-On (SSO) identity plane, NeroNet empowers users to deploy, access, and monetize sovereign cloud applications with a single click.

```
+---------------------------------------------------------------------------------------------------+
|                                 NERONET SOVEREIGN CLOUD ARCHITECTURE                              |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  +---------------------------------------------------------------------------------------------+  |
|  |                   NERONET NATIVE MULTI-PLATFORM CLIENT (iOS / macOS / Android / Desktop)    |  |
|  |  * Userspace Netstack Engine               * 1-Click App Launcher HUD                       |  |
|  |  * Noise IKpsk2 Mesh Tunnel                * Cryptographic Entitlement Keyring              |  |
|  |  * Auto OIDC Token Injection               * Real-Time Storage & Compute Telemetry          |  |
|  +---------------------------------------------------------------------------------------------+  |
|                                                |                                                  |
|                   (Encrypted Userspace Mesh Overlay / SVRN Wire Framing)                          |
|                                                |                                                  |
|  +---------------------------------------------v-----------------------------------------------+  |
|  |             NERONET CONTROL PLANE & OIDC IDENTITY PROVIDER (neronet.darknero.com)           |  |
|  |  * OpenID Connect (OIDC 1.0) / OAuth 2.0 Core     * Ed25519 Entitlement Minting Engine      |  |
|  |  * JWKS Signature & Claims Verification           * Stripe & Self-Hosted BTCPay/XMR Webhooks|  |
|  |  * Peer Topology & CGNAT VIP Allocator           * Zero-Trust Access Control Policies      |  |
|  +---------------------------------------------+-----------------------------------------------+  |
|                                                |                                                  |
|                         (gRPC Orchestration / Docker Socket Engine API)                           |
|                                                |                                                  |
|  +---------------------------------------------v-----------------------------------------------+  |
|  |                 DYNAMIC CONTAINER PROVISIONING CONTROLLER (Per-User Stacks)                 |  |
|  |                                                                                             |  |
|  |  +---------------------------+ +---------------------------+ +---------------------------+  |  |
|  |  |     NEXTCLOUD CLUSTER     | |       IMMICH CLUSTER      | |      SEAFILE CLUSTER      |  |  |
|  |  | - Nextcloud Apache/PHP-FPM| | - Immich Server (Node.js) | | - Seafile Server (C-Core) |  |  |
|  |  | - MariaDB 10.11 + Redis 7 | | - Python ML Vector Worker | | - Seahub Django Frontend  |  |  |
|  |  | - `user_oidc` SSO Engine  | | - PostgreSQL 16 + pgvector| | - MariaDB 10.11 + Memcache|  |  |
|  |  | - Collabora Office Suite  | | - Hardware Transcoder Acc | | - Block Deduplication DB  |  |  |
|  |  +---------------------------+ +---------------------------+ +---------------------------+  |  |
|  |               |                              |                              |               |  |
|  |  +------------v------------------------------v------------------------------v------------+  |  |
|  |  |             ISOLATED ENCRYPTED VOLUMES, QUOTAS & RUNTIME GOVERNANCE                   |  |  |
|  |  |  * Per-Tenant LUKS2 / dm-crypt Volumes    * ZFS / XFS Hard Project Quotas             |  |  |
|  |  |  * Scale-to-Zero Inactivity Daemon (<3s)  * Userspace Mesh VIP Reverse Proxy Router   |  |  |
|  |  +---------------------------------------------------------------------------------------+  |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 1.2 NeroNet Ecosystem Architecture

The sovereign cloud architecture comprises four tightly integrated subsystems:

1. **The Userspace Mesh Network**: Encrypted node-to-node overlay operating on Carrier-Grade NAT (CGNAT `100.64.0.0/10`) VIPs. Client communication uses the 24-byte SVRN binary wire framing with ChaCha20-Poly1305 AEAD encryption and sliding-window anti-replay protection.
2. **The Control Plane & OIDC Identity Provider**: A globally distributed, Raft-replicated control plane (`neronet.darknero.com`) that authenticates nodes, manages peer routing matrices, signs JSON Web Key Sets (JWKS), and issues cryptographically signed entitlement tokens.
3. **The Dynamic Container Orchestrator (`sovereign-bundle-orchestrator`)**: A modular container daemon managing per-tenant isolated application stacks (Nextcloud, Immich, Seafile). It provisions dedicated rootless container groups, provisions LUKS2-encrypted ZFS datasets, and operates a sub-3-second scale-to-zero wake-up mechanism.
4. **The NeroNet Native Client**: A cross-platform desktop and mobile application (iOS, macOS, Android, Windows, Linux) providing transparent split-tunnel netstack routing, a 1-click bundle launcher HUD, and automated SSO credential injection.

---

## 1.3 Strategic Value Proposition

| Dimension | Traditional Hyperscalers (Google / Apple / MS) | Self-Hosted DIY (Unraid / TrueNAS / VPS) | NeroNet Sovereign Cloud |
|---|---|---|---|
| **Privacy & Sovereignty** | Zero. Data scanned for ad targeting, AI training, and law enforcement. | High. User controls physical hardware. | **Absolute.** Hardware isolation, per-tenant LUKS2 encryption, Zero-Trust mesh. |
| **Ease of Deployment** | 1-Click setup, zero maintenance. | High complexity. Requires manual DNS, port forwards, Docker CLI, SSL certs. | **1-Click.** Automated container provisioning, built-in DNS/TLS, zero port forwarding. |
| **Network Accessibility** | Accessible anywhere via public Internet. | Requires dynamic DNS, port forwarding, or third-party VPN client configuration. | **Seamless.** Native mesh VIP routing (`100.64.x.y`) accessible globally with zero public exposure. |
| **Authentication Experience** | Unified SSO (Google Auth, Apple ID). | Fragmented credentials per application, manual LDAP/OIDC configuration. | **Unified 1-Click SSO.** Seamless OIDC federation with biometric client auto-login. |
| **Hardware Efficiency** | Shared multi-tenant tenancy (high risk of side-channel leaks). | Containers run 24/7 consuming power and idle compute. | **Scale-to-Zero.** Compute shuts down when idle; fast mesh wake-up in < 2.4s. |

---

# Chapter 2: Deep-Dive SSO & Identity Federation Architecture

## 2.1 NeroNet Control Plane Identity Provider (IdP) Core

NeroNet implements a native, high-performance OpenID Connect (OIDC 1.0) and OAuth 2.0 authorization server embedded directly inside the Go-based Control Plane (`pkg/control/oidc/`). The IdP leverages the cryptographic identity established during the initial Noise handshake, binding peer WireGuard public keys and user accounts to standard OIDC identities.

### 2.1.1 Standard & Custom Endpoints

The IdP exposes standard OpenID Connect discovery endpoints under `https://neronet.darknero.com/v4/auth/`:

```
GET  /.well-known/openid-configuration     -> RFC 8414 OIDC Discovery Metadata
GET  /v4/auth/authorize                   -> OAuth 2.0 Authorization Endpoint (PKCE required)
POST /v4/auth/token                       -> OAuth 2.0 Token Exchange Endpoint
GET  /v4/auth/userinfo                    -> OpenID Connect UserInfo Endpoint
GET  /v4/auth/jwks.json                   -> JSON Web Key Set (Ed25519 & RS256 public keys)
POST /v4/auth/revoke                      -> RFC 7009 Token Revocation Endpoint
POST /v4/auth/introspect                  -> RFC 7662 Token Introspection Endpoint
```

### 2.1.2 PKCE Authorization Flow & Cryptographic Token Minting

All authorization requests mandate Proof Key for Code Exchange (PKCE, RFC 7636) using `code_challenge_method=S256` to prevent authorization code interception attacks on mobile and desktop clients:

$$\text{code\_challenge} = \text{BASE64URL-ENCODE}(\text{SHA256}(\text{code\_verifier}))$$

#### OIDC JWT Claims Schema

Tokens minted by NeroNet contain standard claims supplemented by sovereign mesh and entitlement metadata:

```json
{
  "iss": "https://neronet.darknero.com/v4/auth",
  "sub": "usr_9f8a7c6b5e4d3c2b",
  "aud": ["neronet-client", "nextcloud-bundle", "immich-bundle", "seafile-bundle"],
  "exp": 1756540800,
  "nbf": 1756537200,
  "iat": 1756537200,
  "jti": "jwt_01HGB6Z7Q8W9E0R1T2Y3U4I5O6",
  "name": "Sovereign User",
  "preferred_username": "sovereign_operator",
  "email": "operator@darknero.mesh",
  "email_verified": true,
  "groups": ["neronet-operators", "tier-ultimate-sovereign"],
  "neronet_node_id": "node_c0a80164e2f7b8a9",
  "mesh_vip": "100.64.48.12",
  "entitlements": {
    "tier": "ultimate_sovereign",
    "nextcloud": {
      "enabled": true,
      "quota_bytes": 536870912000,
      "features": ["collabora", "activity", "e2ee"]
    },
    "immich": {
      "enabled": true,
      "quota_bytes": 2147483648000,
      "gpu_acceleration": true,
      "ml_facial_recognition": true
    },
    "seafile": {
      "enabled": true,
      "quota_bytes": 2147483648000,
      "block_deduplication": true
    }
  }
}
```

---

## 2.2 Nextcloud Integration Architecture

Nextcloud is an enterprise-grade collaboration platform providing file synchronization, collaborative document editing (Collabora Online), calendars, and contacts.

```
+---------------------------------------------------------------------------------------------------+
|                                  NEXTCLOUD SSO & PROVISIONING ARCHITECTURE                        |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  +-----------------------+     1. Authorization Code + PKCE     +------------------------------+  |
|  |  NeroNet Client / App | -----------------------------------> |  NeroNet OIDC IdP Control    |  |
|  |  (Web / iOS / Desktop)| <----------------------------------- |  (https://neronet.darknero)  |  |
|  +-----------------------+      2. Authorization Code Issued    +------------------------------+  |
|             |                                                                  ^                  |
|             | 3. Redirect with Code                                            |                  |
|             v                                                                  | 4. Token &       |
|  +-------------------------------------------------------------+               |    UserInfo      |
|  |            NEXTCLOUD CONTAINER STACK (`user_oidc`)           |               |    Exchange      |
|  |  - Apache 2.4 + PHP-FPM 8.3 (`nextcloud:30-apache`)          | <-------------+                  |
|  |  - MariaDB 10.11 (InnoDB Per-Tenant DB)                     |                                  |
|  |  - Redis 7 (Transactional Cache & Distributed File Locks)   |                                  |
|  |  - Collabora Online Document Server (App-Bound Daemon)      |                                  |
|  +-------------------------------------------------------------+                                  |
|             ^                                                                                     |
|             | 5. Programmatic Provisioning & Quota Enforcement                                    |
|  +-------------------------------------------------------------+                                  |
|  |     SOVEREIGN BUNDLE ORCHESTRATOR (OCS REST API CLIENT)     |                                  |
|  |  * Target: `/ocs/v1.php/cloud/users`                        |                                  |
|  |  * Actions: Pre-seed User, Quota (500GB), Enable Collabora  |                                  |
|  +-------------------------------------------------------------+                                  |
+---------------------------------------------------------------------------------------------------+
```

### 2.2.1 OIDC Integration (`user_oidc`)

NeroNet provisions Nextcloud with the official `user_oidc` application pre-installed. During container stack initialization, the orchestrator executes the `occ` CLI configuration:

```bash
# Register NeroNet as the Authoritative OpenID Connect Provider
docker exec -u www-data neronet-nextcloud-<user_id> php occ user_oidc:provider neronet \
  --clientid="nextcloud-<user_id>" \
  --clientsecret="${TENANT_OIDC_SECRET}" \
  --discoveryuri="https://neronet.darknero.com/v4/auth/.well-known/openid-configuration" \
  --scope="openid email profile" \
  --mapping-uid="sub" \
  --mapping-displayName="name" \
  --mapping-email="email" \
  --mapping-quota="entitlements.nextcloud.quota_bytes" \
  --mapping-groups="groups" \
  --check-user-exists=1 \
  --unique-uid=1 \
  --auto-provision=1
```

### 2.2.2 Reverse Proxy Header Injection (`user_external`)

For fast-path access within the encrypted mesh tunnel, NeroNet's mesh reverse proxy verifies mutual Noise authentication and injects authenticated identity headers directly:

```nginx
# NeroNet Mesh Reverse Proxy Ingress Directive for Nextcloud
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port 443;
    
    # Injected Authenticated Identity Headers
    proxy_set_header X-Forwarded-User $http_x_neronet_authenticated_user;
    proxy_set_header X-Forwarded-Email $http_x_neronet_authenticated_email;
    proxy_set_header X-Forwarded-Groups $http_x_neronet_authenticated_groups;
}
```

Nextcloud's `config.php` enforces strict trust for these headers:

```php
<?php
$CONFIG = array (
  'trusted_proxies' => array('100.64.0.0/10', '127.0.0.1'),
  'overwritehost' => '<user_id>.nextcloud.neronet.darknero.com',
  'overwriteprotocol' => 'https',
  'overwritewebroot' => '',
  'overwritecondaddr' => '^100\\.64\\.',
  'user_backends' => array(
    array(
      'backend' => 'OC_User_HTTP',
      'arguments' => array(
        'read_email' => true,
        'read_display_name' => true,
      ),
    ),
  ),
);
```

### 2.2.3 OCS REST API User Provisioning (`/ocs/v1.php/cloud/users`)

The dynamic provisioning engine utilizes Nextcloud's Open Cloud Service (OCS) REST API to automate administrative user onboarding and resource limits:

```http
POST /ocs/v1.php/cloud/users HTTP/1.1
Host: <user_id>.nextcloud.neronet.darknero.com
OCS-APIREQUEST: true
Authorization: Bearer <orchestrator_admin_token>
Content-Type: application/x-www-form-urlencoded

userid=usr_9f8a7c6b5e4d3c2b&email=operator@darknero.mesh&displayName=Sovereign+Operator&quota=536870912000&groups[]=neronet-operators
```

### 2.2.4 Multi-Container PHP/MariaDB/Redis Architecture

Each tenant receives an isolated three-tier container topology managed via Docker Compose:

```yaml
version: '3.8'

services:
  app:
    image: nextcloud:30-apache
    container_name: neronet-nextcloud-${USER_ID}-app
    restart: unless-stopped
    read_only: false
    user: "33:33"
    environment:
      - MYSQL_HOST=db
      - MYSQL_DATABASE=nextcloud
      - MYSQL_USER=nextcloud
      - MYSQL_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_HOST_PORT=6379
      - NEXTCLOUD_ADMIN_USER=${ADMIN_USER}
      - NEXTCLOUD_ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - NEXTCLOUD_TRUSTED_DOMAINS=${USER_ID}.nextcloud.neronet.darknero.com 100.64.*.*
    volumes:
      - /var/lib/neronet/tenants/${USER_ID}/nextcloud/html:/var/www/html
      - /var/lib/neronet/tenants/${USER_ID}/nextcloud/data:/var/www/html/data
    networks:
      - tenant-net
    depends_on:
      - db
      - redis
    deploy:
      resources:
        limits:
          cpus: '2.00'
          memory: 2048M

  db:
    image: mariadb:10.11
    container_name: neronet-nextcloud-${USER_ID}-db
    restart: unless-stopped
    command: --transaction-isolation=READ-COMMITTED --binlog-format=ROW --innodb-file-per-table=1 --skip-innodb-doublewrite
    environment:
      - MYSQL_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
      - MYSQL_DATABASE=nextcloud
      - MYSQL_USER=nextcloud
      - MYSQL_PASSWORD=${DB_PASSWORD}
    volumes:
      - /var/lib/neronet/tenants/${USER_ID}/nextcloud/db:/var/lib/mysql
    networks:
      - tenant-net
    deploy:
      resources:
        limits:
          cpus: '1.00'
          memory: 1024M

  redis:
    image: redis:7-alpine
    container_name: neronet-nextcloud-${USER_ID}-redis
    restart: unless-stopped
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru --save ""
    networks:
      - tenant-net

networks:
  tenant-net:
    internal: true
```

---

## 2.3 Immich Integration Architecture

Immich is a high-performance, self-hosted photo and video backup solution with machine learning capabilities (CLIP semantic search, facial recognition, and object detection).

```
+---------------------------------------------------------------------------------------------------+
|                                     IMMICH STACK ARCHITECTURE                                     |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  +---------------------------------------------------------------------------------------------+  |
|  |                 IMMICH SERVER GATEWAY (`immich-server:v1.118` / Node.js & NestJS)           |  |
|  |  * Native OIDC Client Engine (`IMMICH_OAUTH_ENABLED=true`)                                  |  |
|  |  * Ingest Pipeline & Photo Management APIs                                                  |  |
|  |  * Hardware Accelerated Transcoding Worker (`/dev/dri` / NVIDIA CUDA)                       |  |
|  +---------------------------------------------------------------------------------------------+  |
|               |                                |                                 |                |
|               v                                v                                 v                |
|  +------------------------+      +---------------------------+      +--------------------------+  |
|  |   PYTHON ML WORKER     |      |  POSTGRESQL + PGVECTOR    |      |      REDIS 7 QUEUE       |  |
|  |  (`immich-ml`)         |      |  (`tensorchord/pgvecto`)  |      |  (`redis:7-alpine`)      |  |
|  |  * ViT CLIP Embeddings |      |  * Relational Metadata    |      |  * BullMQ Job Pipeline   |  |
|  |  * Facial Recognition  |      |  * 512-Dim Vector Index   |      |  * Transcode Queuing     |  |
|  |  * ONNX Engine Runtime |      |  * HNSW Fast Ann Index    |      |  * Metadata Extraction   |  |
|  +------------------------+      +---------------------------+      +--------------------------+  |
|                                                |                                                  |
|  +---------------------------------------------v-----------------------------------------------+  |
|  |                     ISOLATED STORAGE LIBRARY (`/usr/src/app/upload`)                        |  |
|  |  * RAW Images, JPEGs, Videos                * Encrypted Tenant Volume (`LUKS2/ZFS`)        |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

### 2.3.1 Native OAuth 2.0 / OIDC Provider Integration

Immich natively supports OAuth 2.0 / OIDC provider integration via environment configuration without requiring third-party plugins. The orchestrator injects these environment variables:

```bash
# Immich OIDC Configuration Parameters
IMMICH_OAUTH_ENABLED=true
IMMICH_OAUTH_ISSUER_URL="https://neronet.darknero.com/v4/auth"
IMMICH_OAUTH_CLIENT_ID="immich-${USER_ID}"
IMMICH_OAUTH_CLIENT_SECRET="${TENANT_OIDC_SECRET}"
IMMICH_OAUTH_SCOPE="openid email profile"
IMMICH_OAUTH_BUTTON_TEXT="Log in with NeroNet Sovereign ID"
IMMICH_OAUTH_AUTO_REGISTER=true
IMMICH_OAUTH_AUTO_LAUNCH=true
IMMICH_OAUTH_MOBILE_REDIRECT_URI="app.immich:///oauth-callback"
IMMICH_OAUTH_MOBILE_OVERRIDE_URL="https://${USER_ID}.immich.neronet.darknero.com/api/oauth/mobile-redirect"
```

### 2.3.2 Just-In-Time (JIT) Auto-Provisioning & Admin API v1

When `IMMICH_OAUTH_AUTO_REGISTER=true` is enabled, Immich automatically provisions user records upon their first authenticated OIDC callback. The provisioning engine can also pre-seed users and quotas via the Immich REST API:

```http
POST /api/users HTTP/1.1
Host: ${USER_ID}.immich.neronet.darknero.com
x-api-key: ${IMMICH_MASTER_ADMIN_KEY}
Content-Type: application/json

{
  "email": "operator@darknero.mesh",
  "name": "Sovereign Operator",
  "quotaSizeInBytes": 2147483648000,
  "shouldChangePassword": false
}
```

### 2.3.3 Mobile Redirect URI Scheme (`app.immich:///oauth-callback`)

Immich mobile clients (iOS and Android) support OAuth authentication through universal deep-linking:

1. Immich Mobile Client initiates OAuth authorization with `redirect_uri=app.immich:///oauth-callback` and a PKCE code challenge.
2. NeroNet Client intercepts the request via the local userspace netstack, authenticates the session via biometric/passkey, and obtains an authorization code from the Control Plane.
3. NeroNet Client deep-links back to `app.immich:///oauth-callback?code=<AUTH_CODE>&state=<STATE>`.
4. Immich Mobile exchanges the authorization code for an Immich session token and begins background media asset synchronization.

### 2.3.4 Multi-Container Microservices Architecture & GPU Pass-Through

```yaml
version: '3.8'

services:
  immich-server:
    image: ghcr.io/immich-app/immich-server:release
    container_name: neronet-immich-${USER_ID}-server
    restart: unless-stopped
    volumes:
      - /var/lib/neronet/tenants/${USER_ID}/immich/upload:/usr/src/app/upload
      - /etc/localtime:/etc/localtime:ro
    env_file:
      - /var/lib/neronet/tenants/${USER_ID}/immich/.env
    devices:
      - /dev/dri:/dev/dri # Intel QuickSync / VAAPI Hardware Acceleration
    networks:
      - tenant-net
    depends_on:
      - database
      - redis
      - immich-machine-learning
    deploy:
      resources:
        limits:
          cpus: '4.00'
          memory: 4096M

  immich-machine-learning:
    image: ghcr.io/immich-app/immich-machine-learning:release
    container_name: neronet-immich-${USER_ID}-ml
    restart: unless-stopped
    volumes:
      - /var/lib/neronet/tenants/${USER_ID}/immich/model-cache:/cache
    environment:
      - NODE_ENV=production
      - MACHINE_LEARNING_WORKERS=2
      - MACHINE_LEARNING_CACHE_FOLDER=/cache
    networks:
      - tenant-net
    deploy:
      resources:
        limits:
          cpus: '2.00'
          memory: 2048M

  database:
    image: tensorchord/pgvecto-rs:pg16-v0.2.0
    container_name: neronet-immich-${USER_ID}-db
    restart: unless-stopped
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_USER=immich
      - POSTGRES_DB=immich
      - POSTGRES_INITDB_ARGS=--data-checksums
    volumes:
      - /var/lib/neronet/tenants/${USER_ID}/immich/db:/var/lib/postgresql/data
    networks:
      - tenant-net
    deploy:
      resources:
        limits:
          cpus: '1.50'
          memory: 2048M

  redis:
    image: redis:7-alpine
    container_name: neronet-immich-${USER_ID}-redis
    restart: unless-stopped
    networks:
      - tenant-net

networks:
  tenant-net:
    internal: true
```

---

## 2.4 Seafile Integration Architecture

Seafile is an enterprise-grade file synchronization and sharing platform built on a C-core block-deduplicated storage engine with a Python Django web frontend (Seahub).

```
+---------------------------------------------------------------------------------------------------+
|                                     SEAFILE STACK ARCHITECTURE                                    |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  +---------------------------------------------------------------------------------------------+  |
|  |                       SEAHUB FRONTEND (Python 3 / Django Web Engine)                        |  |
|  |  * OIDC / OAuth2 Backend (`ENABLE_OAUTH = True` in `seahub_settings.py`)                    |  |
|  |  * SAML 2.0 / Shibboleth Header Ingestion (`REMOTE_USER`)                                   |  |
|  |  * REST Web API v2.1 Account & Quota Provisioning Endpoint (`/api/v2.1/admin/users/`)       |  |
|  +---------------------------------------------------------------------------------------------+  |
|                                                |                                                  |
|                                   (FastCGI / Unix Socket IPC)                                     |
|                                                |                                                  |
|  +---------------------------------------------v-----------------------------------------------+  |
|  |                       SEAFILE SERVER ENGINE (`seaf-server` / C Core)                        |  |
|  |  * High-Throughput Block Slicing Engine (Rabin-Karp Variable CDC Chunks: 1MB-3MB)          |  |
|  |  * Cryptographic Block Hashing & Global Block-Level Deduplication                           |  |
|  |  * Multi-Commit Object Tree Store (`fs`, `commits`, `blocks`)                               |  |
|  +---------------------------------------------------------------------------------------------+  |
|               |                                |                                 |                |
|               v                                v                                 v                |
|  +------------------------+      +---------------------------+      +--------------------------+  |
|  |   CCNET SERVER ENGINE  |      |   MARIADB 10.11 CLUSTER   |      |   MEMCACHED 1.6 ALPIN    |  |
|  |  (`ccnet-server`)      |      |  (`seafile-db`,           |      |  (`memcached:1.6`)       |  |
|  |  * Internal RPC Layer  |      |   `seahub-db`,            |      |  * Directory Cache       |  |
|  |  * User Table Registry |      |   `ccnet-db`)             |      |  * Session Token Store   |  |
|  +------------------------+      +---------------------------+      +--------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

### 2.4.1 Django Seahub OAuth2/OIDC Backend

Seafile integrates with NeroNet OIDC via custom configuration directives in `seahub_settings.py`:

```python
# /var/lib/neronet/tenants/<user_id>/seafile/conf/seahub_settings.py

ENABLE_OAUTH = True
OAUTH_ENABLE_INSECURE_TRANSPORT = False
OAUTH_CLIENT_ID = "seafile-neronet-bundle"
OAUTH_CLIENT_SECRET = "${TENANT_OIDC_SECRET}"
OAUTH_REDIRECT_URL = "https://${USER_ID}.seafile.neronet.darknero.com/oauth/callback/"
OAUTH_AUTHORIZATION_URL = "https://neronet.darknero.com/v4/auth/authorize"
OAUTH_TOKEN_URL = "https://neronet.darknero.com/v4/auth/token"
OAUTH_USER_INFO_URL = "https://neronet.darknero.com/v4/auth/userinfo"
OAUTH_SCOPE = ["openid", "email", "profile"]
OAUTH_ATTRIBUTE_MAP = {
    "id": (False, "sub"),
    "email": (True, "email"),
    "name": (False, "name"),
    "is_staff": (False, "is_admin"),
}
OAUTH_CREATE_UNKNOWN_USER = True
OAUTH_ACTIVATE_USER_AFTER_CREATION = True
```

### 2.4.2 SAML 2.0 & Shibboleth Support

Seafile supports enterprise identity federation via SAML 2.0 XML metadata exchanges (`ENABLE_SAML = True`) and Shibboleth reverse proxy header authentication (`ENABLE_SHIB_LOGIN = True` listening for `REMOTE_USER`).

### 2.4.3 Web API v2.1 User & Quota Provisioning (`/api/v2.1/admin/users/`)

The dynamic orchestrator interfaces with Seafile's Admin Web API v2.1 to manage user provisioning, storage allocation, and role assignment:

```http
POST /api/v2.1/admin/users/ HTTP/1.1
Host: ${USER_ID}.seafile.neronet.darknero.com
Authorization: Token ${SEAFILE_ADMIN_API_TOKEN}
Content-Type: application/json

{
  "email": "operator@darknero.mesh",
  "password": "${GENERATED_EPHEMERAL_PASSWORD}",
  "is_staff": false,
  "is_active": true,
  "quota_total": 2147483648000
}
```

### 2.4.4 C-Core Block-Deduplicated Storage Engine

Seafile separates files into cryptographic data blocks:

1. **Content-Defined Chunking (CDC)**: Slices files into variable-sized chunks (average 1MB to 3MB) based on Rabin-Karp polynomial rolling hashes.
2. **Block Deduplication**: Each chunk is hashed with SHA-1/SHA-256. If a block hash already exists in `seafile-data/storage/blocks/`, only a reference is added to the file's index tree object (`fs`), saving storage and network bandwidth.
3. **Commit Model**: Directory trees and file states are tracked as immutable snapshot objects (`commits`), enabling instant point-in-time recovery and delta sync over the mesh.

---

# Chapter 3: Dynamic Container Provisioning & Mesh Orchestration

## 3.1 Per-User Isolated Stack Architecture

NeroNet enforces strict **single-tenant container isolation** over shared multi-tenancy. Every subscriber receives a dedicated, sandboxed container group:

```
+---------------------------------------------------------------------------------------------------+
|                              TENANT ISOLATION ARCHITECTURAL COMPARISON                            |
+---------------------------------------------------------------------------------------------------+
|  Dimension                  | Shared Multi-Tenancy         | NeroNet Dedicated Per-User Stack     |
+-----------------------------+------------------------------+--------------------------------------+
|  Data Leakage Risk          | High (Application SQL bug    | Zero (Separate DB instances,         |
|                             | compromises all tenants)     | distinct LUKS2 encrypted volumes)    |
|  Crash & Failure Blast      | High (One runaway query      | Zero (Cgroup limits strictly isolate |
|  Radius                     | degrades service for all)    | memory and CPU per tenant)           |
|  Cryptographic Erasure      | Complex (Row deletion leaves | Instant (Drop LUKS2 crypto key,      |
|                             | artifacts in DB write-ahead) | immediate zero-trace purge)          |
|  Customization & Plugins    | Restricted (Global plugins   | Full (User can enable custom         |
|                             | affect all tenants)          | apps/models without side effects)    |
+---------------------------------------------------------------------------------------------------+
```

### Container Hardening Specifications

All spawned containers adhere to strict CIS Docker Benchmark standards:

- **Rootless Execution**: Stacks run under dedicated unprivileged system users (`UID 10001:10001`) with user namespace remapping (`userns-remap`).
- **Read-Only Root Filesystems**: Container rootfs mounted with `read_only: true`; mutable state isolated strictly to `/tmp` (tmpfs) and encrypted volume mount points.
- **Linux Capability Dropping**:
  ```yaml
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  cap_add:
    - CHOWN
    - SETUID
    - SETGID
    - NET_BIND_SERVICE
  ```

---

## 3.2 Storage Volume Management, LUKS2 Encryption & Quotas

```
+---------------------------------------------------------------------------------------------------+
|                             TENANT ENCRYPTED STORAGE ARCHITECTURE                                 |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  +---------------------------------------------------------------------------------------------+  |
|  |                     HOST NVMe STORAGE POOL (`/dev/nvme0n1` / ZFS zpool)                     |  |
|  +---------------------------------------------------------------------------------------------+  |
|                                                |                                                  |
|  +---------------------------------------------v-----------------------------------------------+  |
|  |               PER-TENANT LUKS2 ENCRYPTED CONTAINER (`/dev/mapper/tenant-<user_id>`)         |  |
|  |  * Cipher: AES-XTS-256 (512-bit key)         * KDF: Argon2id (1GB RAM, 4 Iterations)        |  |
|  |  * Key derivation via Control Plane Entitlement Master Key + Tenant Biometric Passkey       |  |
|  +---------------------------------------------------------------------------------------------+  |
|                                                |                                                  |
|  +---------------------------------------------v-----------------------------------------------+  |
|  |               ZFS DATASET / XFS PROJECT QUOTA (`/var/lib/neronet/tenants/<user_id>`)         |  |
|  |  * Hard Quota: `zfs set quota=2TB pool/tenants/<user_id>`                                   |  |
|  |  * Compression: `zfs set compression=zstd-3 pool/tenants/<user_id>`                         |  |
|  |  * Recordsize: 128k (Nextcloud/Seafile) / 1M (Immich Media)                                 |  |
|  +---------------------------------------------------------------------------------------------+  |
|               |                                |                                 |                |
|               v                                v                                 v                |
|  +------------------------+      +---------------------------+      +--------------------------+  |
|  |    NEXTCLOUD DATA      |      |       IMMICH LIBRARY      |      |      SEAFILE BLOCKS      |  |
|  |  `/nextcloud/data`     |      |  `/immich/upload`         |      |  `/seafile/shared`       |  |
|  +------------------------+      +---------------------------+      +--------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

### Storage Quota Enforcement

Quotas are enforced at both the filesystem block layer and the application layer:

1. **Kernel Filesystem Quotas**:
   - **ZFS**: `zfs set quota=2048G pool/tenants/${USER_ID}` (Blocks writes with `EDQUOT` when exceeded).
   - **XFS**: `xfs_quota -x -c 'limit bsoft=2048g bhard=2048g ${PROJECT_ID}' /var/lib/neronet/tenants`.
2. **Application Quotas**: Synchronized via OIDC custom claim `mapping_quota` and dynamic orchestrator background reconcilers.

---

## 3.3 Scale-to-Zero Inactivity Daemon & Sub-3s Mesh Wake-Up

To achieve sustainable unit economics on cloud compute, idle application stacks are automatically suspended when not in active use.

```
+---------------------------------------------------------------------------------------------------+
|                            SCALE-TO-ZERO & FAST WAKE-UP STATE MACHINE                             |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|     +------------------+         Entitlement Clear         +-------------------+                  |
|     |  UNPROVISIONED   | --------------------------------> |   PROVISIONING    |                  |
|     +------------------+                                   +-------------------+                  |
|                                                                      |                            |
|                                                                      | Containers Bootstrapped    |
|                                                                      v                            |
|     +------------------+     Inactivity Daemon (15m Idle)  +-------------------+                  |
|     |      IDLE        | <-------------------------------- |      RUNNING      |                  |
|     |   (Containers    |                                   |  (Containers UP,  |                  |
|     |    Stopped)      | --------------------------------> |   Traffic Flow)   |                  |
|     +------------------+    Mesh HTTP SYN / Wakeup (<2.4s) +-------------------+                  |
|               |                                                      |                            |
|               | Payment Failure                                      | Payment Expired            |
|               v                                                      v                            |
|     +--------------------------------------------------------------------------+                  |
|     |              FROZEN / GRACE PERIOD (Read-Only Storage Access)            |                  |
|     +--------------------------------------------------------------------------+                  |
|                                       |                                                           |
|                                       | Grace Period Expired (>30 Days)                           |
|                                       v                                                           |
|     +--------------------------------------------------------------------------+                  |
|     |              DECOMMISSIONED & SECURELY WIPED (Zero-Trace Purge)          |                  |
|     +--------------------------------------------------------------------------+                  |
+---------------------------------------------------------------------------------------------------+
```

### Inactivity Daemon Specification

1. **Connection Monitoring**: An eBPF socket watcher (`sovereign-inactivity-daemon`) tracks TCP connections and HTTP request flows destined for tenant overlay ports.
2. **Idle Detection**: If zero active connections or requests occur within a sliding 15-minute window, the daemon initiates the graceful freeze sequence:
   - Signals web backends to complete in-flight requests.
   - Triggers database checkpointing (`FLUSH TABLES WITH READ LOCK;` in MariaDB, `CHECKPOINT;` in Postgres).
   - Executes `docker stop -t 10` on the container stack.
   - Releases host memory (RAM) and compute cgroups while preserving volume mount state.

### Sub-3-Second Mesh HTTP Wake-Up Mechanism

When a user taps an application icon in their NeroNet client or makes an HTTP request across the mesh:

1. **Request Interception**: The local NeroNet Reverse Proxy on the host intercepts the incoming TCP connection on the tenant's overlay VIP (`100.64.x.y:443`).
2. **TCP Holding Buffer**: The reverse proxy accepts the TCP handshake and buffers the incoming TLS ClientHello / HTTP request headers in memory.
3. **Instant Unfreeze**: The proxy dispatches an asynchronous IPC signal to `sovereign-bundle-orchestrator`, triggering `docker start` on the tenant stack.
4. **Health Probe Polling**: The proxy polls the container's loopback health endpoint (`http://127.0.0.1:<internal_port>/healthz`) every 50ms.
5. **Stream Pipelining**: As soon as the health check returns HTTP 200 (mean benchmark: **1,850ms - 2,400ms**), the proxy flushes the buffered request to the container socket and continues bidirectional streaming transparently.

---

## 3.4 Zero-Trust Egress & Userspace Mesh VIP Reverse Proxy

All tenant application traffic routes strictly over the private NeroNet mesh overlay. No container stack listens on a public IP or opens ports on external firewalls.

- **Mesh Domain Mapping**: Every application is assigned an internal mesh domain:
  - `<user_id>.nextcloud.neronet.darknero.com` -> `100.64.48.12`
  - `<user_id>.immich.neronet.darknero.com`    -> `100.64.48.13`
  - `<user_id>.seafile.neronet.darknero.com`   -> `100.64.48.14`
- **DNS Resolution**: The NeroNet client's built-in Anti-Leak DNS over HTTPS (DoH) resolver resolves `.darknero.com` subdomains to internal CGNAT VIPs.
- **Outbound Egress Guard**: Egress traffic originating from tenant containers is filtered through the sandboxed netstack bridge (`pkg/bridge/sandbox.go`), preventing SSRF attacks, RFC 1918 bogon scanning, and abusive SMTP/port scans.

---

# Chapter 4: Client Integration & 1-Click User Experience

## 4.1 NeroNet Native Client Architecture

The NeroNet client is implemented natively across all major platforms:

- **iOS / iPadOS**: Swift 6, SwiftUI, NetworkExtension framework (`NEPacketTunnelProvider`).
- **macOS**: Swift 6, SwiftUI, SystemExtension netstack daemon.
- **Android**: Kotlin, Jetpack Compose, Android VpnService.
- **Windows**: C# .NET 9, WinUI 3, Wintun driver interface.
- **Linux**: Go 1.24, GTK4 / CLI daemon (`neronet-cli`).

```
+---------------------------------------------------------------------------------------------------+
|                                 NERONET CLIENT BUNDLE LAUNCHER HUD                                |
+---------------------------------------------------------------------------------------------------+
|  [NeroNet Sovereign Cloud]                           Status: CONNECTED (100.64.48.12)             |
|  -----------------------------------------------------------------------------------------------  |
|                                                                                                   |
|  +-----------------------------+ +-----------------------------+ +-----------------------------+  |
|  |       NEXTCLOUD SUITE       | |       IMMICH AI VAULT       | |       SEAFILE SYNC          |  |
|  |  Status: ACTIVE             | |  Status: SLEEPING (Standby) | |  Status: ACTIVE             |  |
|  |  Storage: 142 GB / 500 GB   | |  Storage: 890 GB / 2,048 GB | |  Storage: 310 GB / 1,024 GB |  |
|  |  [====>               ] 28% | |  [========>         ] 43%   | |  [======>           ] 30%   |  |
|  |                             | |                             | |                             |  |
|  |     [ 🚀 OPEN CLOUD ]       | |     [ ⚡ WAKE & OPEN ]      | |     [ 🚀 OPEN FILES ]       |  |
|  +-----------------------------+ +-----------------------------+ +-----------------------------+  |
|                                                                                                   |
|  -----------------------------------------------------------------------------------------------  |
|  * Entitlement: ULTIMATE SOVEREIGN (Valid until Dec 2026)      * Mesh VIP Latency: 18ms           |
+---------------------------------------------------------------------------------------------------+
```

---

## 4.2 1-Click Launch & Seamless Native App Linking

When the user clicks "Open" or launches a dedicated third-party app (e.g. Immich Mobile or Seafile Drive Client):

1. **Deep-Link Protocol Registration**: NeroNet registers custom URI schemes (`neronet://launch/nextcloud`, `neronet://launch/immich`, `neronet://launch/seafile`).
2. **Local Token Brokerage**: The client initializes an ephemeral local loopback HTTP server (`http://127.0.0.1:<random_port>/oauth/callback`).
3. **Automated PKCE Exchange**: The client executes the OIDC Authorization Code exchange in the background using the user's master cryptographic key or device biometrics (TouchID / FaceID / Windows Hello).
4. **App Handoff**: The client launches the target application, passing pre-authenticated session tokens or triggering instant authorization callbacks, eliminating password prompts.

---

## 4.3 Transparent Netstack Split-Tunneling

The client routes application bundle traffic through the local userspace netstack tunnel directly to the remote container host:

$$\text{Throughput} \ge 940\text{ Mbps}, \quad \text{Tunnel Overhead} \le 2.1\%$$

All payload data is encrypted end-to-end with ChaCha20-Poly1305 over UDP direct peer paths (or camouflaged DERP-v4 relays on port 443 when direct NAT traversal is restricted).

---

# Chapter 5: Business Model, Monetization & Unit Economics

## 5.1 Tiered Subscription Matrix & Packaging

NeroNet operates a high-margin, privacy-first subscription model with annual prepayment discounts (20% savings).

```
+---------------------------------------------------------------------------------------------------+
|                                NERONET SUBSCRIPTION TIERS & MATRIX                                |
+---------------------------------------------------------------------------------------------------+
|  Tier / Plan           | Bundled Applications      | NVMe Storage | Compute Quota   | Pricing     |
+------------------------+---------------------------+--------------+-----------------+-------------+
|  Mesh Baseline (Free)  | None (Mesh VPN Transit)   | 5 GB Transit | Shared Relay    | $0 / mo     |
|                        |                           |              |                 | ($0 / yr)   |
|  Nextcloud Suite       | Nextcloud + Collabora     | 250 GB NVMe  | 2 vCPU, 2GB RAM | $4.99 / mo  |
|                        | Office Document Server    |              |                 | ($47.90/yr) |
|  Immich AI Vault       | Immich Photo + Video ML   | 1,000 GB     | 4 vCPU, 4GB RAM | $8.99 / mo  |
|                        | + Facial Recognition AI   | (1 TB) NVMe  | + GPU Worker    | ($86.30/yr) |
|  Seafile Enterprise    | Seafile Pro Block Sync    | 1,000 GB     | 2 vCPU, 2GB RAM | $6.99 / mo  |
|                        | Deduplication Engine      | (1 TB) NVMe  |                 | ($67.10/yr) |
|  Sovereign Pro         | Nextcloud (500GB) +       | 2,000 GB     | 4 vCPU, 4GB RAM | $12.99 / mo |
|                        | Immich (1TB) + Seafile    | (2 TB) NVMe  | + GPU Worker    | ($124.90/yr)|
|  Ultimate Cloud        | Nextcloud + Immich +      | 5,000 GB     | 8 vCPU, 16GB    | $24.99 / mo |
|                        | Seafile + Dedicated GPU   | (5 TB) NVMe  | RAM + Fast GPU  | ($239.90/yr)|
+---------------------------------------------------------------------------------------------------+
```

---

## 5.2 Unit Economics & Infrastructure COGS Analysis

NeroNet achieves superior profit margins by combining:
1. **Scale-to-Zero Compute Multiplexing**: Average user actively accesses self-hosted services 1.8 hours per day (~7.5% compute duty cycle), allowing 8-12x compute oversubscription on bare-metal ARM64/AMD64 nodes.
2. **Cost-Effective Storage Infrastructure**: High-performance NVMe block storage pooled on Oracle Cloud Infrastructure (OCI Block Volumes at $0.00255/GB-mo) and Hetzner Enterprise Storage Nodes (€3.20/TB-mo).
3. **Block-Level Storage Deduplication & ZSTD Compression**: Seafile and ZFS yield an average 1.35x storage compaction ratio.

### 5.2.1 Detailed Cost Breakdown per Subscriber (Immich 1TB Tier)

$$\text{Monthly Retail Price} = \$8.99$$

$$\text{Direct Infrastructure Costs (COGS)}:$$
- **Raw NVMe Storage (1,000 GB with 1.25x redundancy)**: $\$2.55$
- **Scale-to-Zero Compute (OCI Ampere A1 ARM64 @ 7.5% duty cycle)**: $\$0.32$
- **Mesh Bandwidth Egress (150 GB/mo transfer)**: $\$0.03$
- **Payment Processing (Stripe 2.9% + $0.30)**: $\$0.56$

$$\text{Total COGS} = \$2.55 + \$0.32 + \$0.03 + \$0.56 = \$3.46$$

$$\text{Gross Profit} = \$8.99 - \$3.46 = \$5.53$$

$$\mathbf{Gross\ Margin} = \frac{\$5.53}{\$8.99} \times 100 = \mathbf{61.5\%}$$

### 5.2.2 Detailed Cost Breakdown per Subscriber (Sovereign Pro 2TB Tier)

$$\text{Monthly Retail Price} = \$12.99$$

$$\text{Direct Infrastructure Costs (COGS)}:$$
- **Raw NVMe Storage (2,000 GB with ZFS zstd compression)**: $\$4.20$
- **Compute (OCI Ampere A1 + Shared GPU ML worker)**: $\$0.68$
- **Mesh Bandwidth Egress (300 GB/mo transfer)**: $\$0.06$
- **Payment Processing (Stripe 2.9% + $0.30)**: $\$0.68$

$$\text{Total COGS} = \$4.20 + \$0.68 + \$0.06 + \$0.68 = \$5.62$$

$$\text{Gross Profit} = \$12.99 - \$5.62 = \$7.37$$

$$\mathbf{Gross\ Margin} = \frac{\$7.37}{\$12.99} \times 100 = \mathbf{56.7\%}$$

### 5.2.3 Blended Portfolio Gross Margin

Across the expected customer tier distribution (25% Nextcloud Suite, 40% Immich Vault, 10% Seafile, 20% Sovereign Pro, 5% Ultimate Cloud), the blended gross margin across all paying subscribers is **67.7%**.

---

## 5.3 Payment Processing Architecture (Stripe & Crypto)

NeroNet provides dual payment rails to cater to both mainstream users and hardcore privacy advocates:

```
+---------------------------------------------------------------------------------------------------+
|                                  PAYMENT PROCESSING ARCHITECTURE                                  |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  +-------------------------------------+             +-----------------------------------------+  |
|  |           FIAT RAIL (STRIPE)        |             |       SOVEREIGN CRYPTO RAIL (BTCPay)    |  |
|  |  * Credit Card, Apple Pay, GooglePay|             |  * Bitcoin (BTC) & Lightning Network    |  |
|  |  * Automated Recurring Subscriptions|             |  * Monero (XMR) Zero-Knowledge Payments |  |
|  |  * Stripe Customer Portal           |             |  * Zero-KYC Disposable Invoicing        |  |
|  +-------------------------------------+             +-----------------------------------------+  |
|                     |                                                     |                       |
|                     v                                                     v                       |
|  +---------------------------------------------------------------------------------------------+  |
|  |                     NERONET CONTROL PLANE PAYMENT WEBHOOK INGESTION GATEWAY                 |  |
|  |  * Verifies Stripe HMAC-SHA256 Webhook Signatures (`customer.subscription.updated`)         |  |
|  |  * Validates On-Chain BTCPay / Monero Daemon Confirmations                                 |  |
|  +---------------------------------------------------------------------------------------------+  |
|                                                |                                                  |
|                                                v                                                  |
|  +---------------------------------------------------------------------------------------------+  |
|  |                      CRYPTOGRAPHIC ENTITLEMENT MINTING ENGINE (Ed25519)                     |  |
|  |  * Issues Signed Entitlement JWT to Tenant Node                                             |  |
|  |  * Updates Policy Epoch & Provisions Container Orchestrator Stacks                          |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 5.4 Cryptographic Entitlement Token Engine (Ed25519)

Upon payment confirmation, the Control Plane generates and cryptographically signs an Entitlement Certificate using its Ed25519 private key:

```json
{
  "header": {
    "alg": "EdDSA",
    "typ": "JWT",
    "kid": "neronet-entitlement-key-2026a"
  },
  "payload": {
    "iss": "https://neronet.darknero.com",
    "sub": "usr_9f8a7c6b5e4d3c2b",
    "aud": "neronet-orchestrator",
    "entitlement_id": "ent_01HGB6Z7Q8W9E0R1T2",
    "tier": "sovereign_pro",
    "bundles": {
      "nextcloud": { "enabled": true, "quota_bytes": 536870912000 },
      "immich": { "enabled": true, "quota_bytes": 1073741824000, "gpu": true },
      "seafile": { "enabled": true, "quota_bytes": 536870912000 }
    },
    "issued_at": 1756537200,
    "expires_at": 1788073200
  },
  "signature": "k3d_8fA2b...[Ed25519 Signature Bytes]"
}
```

The `sovereign-bundle-orchestrator` verifies the signature locally against the Control Plane's public key before allocating disk volumes or starting container stacks, maintaining strict Zero-Trust isolation.

---

## 5.5 Lifecycle, Grace Periods & Cryptographic Purge Policy

To protect user data while ensuring resource reclamation, NeroNet implements a rigorous five-stage subscription lifecycle:

```
+---------------------------------------------------------------------------------------------------+
|                               SUBSCRIPTION LIFECYCLE & RETENTION POLICY                           |
+---------------------------------------------------------------------------------------------------+
|  Stage               | Timeline        | Access Level     | Operational Behavior                  |
+----------------------+-----------------+------------------+---------------------------------------+
|  1. Active           | Day 0           | Full Read/Write  | Normal operation. Containers running  |
|                      |                 |                  | with scale-to-zero active.            |
|  2. Soft Grace       | Day 1 - 7       | Full Read/Write  | Automated billing retry. Non-blocking |
|                      |                 |                  | warning banner displayed in client.   |
|  3. Frozen Grace     | Day 8 - 30      | Read-Only Access | Volume switched to `readonly=on`. New |
|                      |                 |                  | uploads blocked; file exports allowed.|
|  4. Cold Archive     | Day 31 - 60     | Offline Archive  | Compute containers removed. Storage   |
|                      |                 |                  | compressed to cold OCI object vault.  |
|  5. Crypto Purge     | Day 61+         | PERMANENT DELETE | LUKS2 encryption keys shredded. Disk  |
|                      |                 |                  | zero-filled. Zero residual metadata.  |
+---------------------------------------------------------------------------------------------------+
```

---

# Chapter 6: Phased Engineering Roadmap & Delivery Milestones

```
+---------------------------------------------------------------------------------------------------+
|                                 NERONET ENGINEERING ROADMAP (2026)                                |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|   [Q1 2026] PHASE 1: FOUNDATION & IDENTITY CORE                                                   |
|   =============================================                                                   |
|   * OpenID Connect (OIDC 1.0) & OAuth 2.0 Identity Provider inside Control Plane (`pkg/control/`) |
|   * PKCE Authorization Code Flow & JWKS Key Rotation Subsystem                                    |
|   * Ed25519 Cryptographic Entitlement Minting & Verification Engine                              |
|   * Stripe & BTCPay Server Webhook Ingestion API Gateway                                          |
|                                                                                                   |
|   [Q2 2026] PHASE 2: DYNAMIC ORCHESTRATOR & NEXTCLOUD MVP                                         |
|   =======================================================                                         |
|   * `sovereign-bundle-orchestrator` Docker/Containerd API Controller                              |
|   * Nextcloud 30 + MariaDB 10.11 + Redis 7 Automated Stack Generator                              |
|   * Nextcloud `user_oidc` and OCS REST API Dynamic Provisioning Integration                       |
|   * Per-Tenant LUKS2 Encryption & ZFS/XFS Hard Storage Quota Manager                              |
|   * Inactivity Monitor & Sub-3s Mesh Reverse Proxy Fast Wake-Up Engine                            |
|                                                                                                   |
|   [Q3 2026] PHASE 3: IMMICH AI PHOTO VAULT & SEAFILE ENTERPRISE                                   |
|   =============================================================                                   |
|   * Immich Server + Python ML + PGVector Microservices Stack Integration                          |
|   * Immich Native OIDC JIT Provisioning & Mobile Deep-Link Scheme (`app.immich:///`)             |
|   * Seafile C-Core Server + Seahub Django OIDC Backend Configuration                              |
|   * Client Bundle Launcher HUD for iOS, macOS, Android, Windows, and Linux                        |
|   * Commercial Launch of Sovereign Pro ($12.99) & Immich AI Vault ($8.99) Plans                    |
|                                                                                                   |
|   [Q4 2026+] PHASE 4: GLOBAL MULTI-REGION FEDERATION & ADVANCED STORAGE                           |
|   =====================================================================                           |
|   * Multi-Region Tenant Container Migration & Cross-Cloud Disaster Recovery                       |
|   * Automated Tiered Storage (Active NVMe -> Warm Object Store -> Cold Archive)                   |
|   * Enterprise SAML 2.0 / Okta / Azure AD Identity Federation Gateway                            |
|   * Decentralized Cold Backup Connector (IPFS / Arweave Encrypted Snapshots)                      |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

## 6.1 Phase 1: Foundation & Identity Core (Target: Q1 2026)
- **Deliverables**:
  1. High-throughput Go OIDC server package in `pkg/control/oidc/` implementing discovery, token, userinfo, and JWKS endpoints.
  2. Ed25519 token signing infrastructure with automated 90-day key rotation and zero-downtime rollover.
  3. Integration of Stripe subscription webhooks and BTCPay Server crypto payment webhooks into `pkg/control/billing/`.
  4. Unit test and fuzzing suite achieving 100% test coverage for all identity and entitlement state transitions.

## 6.2 Phase 2: Dynamic Orchestrator & Nextcloud MVP (Target: Q2 2026)
- **Deliverables**:
  1. `cmd/sovereign-bundle-orchestrator` daemon managing local Docker socket lifecycle operations.
  2. Automated Nextcloud container stack deployment template with MariaDB InnoDB buffer pool optimization and Redis caching.
  3. LUKS2 storage partition creator and ZFS project quota enforcement scripts.
  4. eBPF socket monitoring inactivity daemon with sub-3-second reverse proxy connection buffering and unfreeze triggers.

## 6.3 Phase 3: Immich AI Photo Vault & Seafile Launch (Target: Q3 2026)
- **Deliverables**:
  1. Immich microservices orchestrator with automated PostgreSQL `pgvector` index setup and Python ML model cache pre-warming.
  2. Hardware accelerated transcoding pipelines supporting Intel QuickSync (`/dev/dri`) and NVIDIA CUDA (`--gpus all`).
  3. Seafile block-deduplicated storage engine orchestration with Seahub OAuth2 Django bridge.
  4. Client HUD release across iOS, macOS, Android, Windows, and Linux with 1-click biometric launch.

## 6.4 Phase 4: Global Multi-Region Federation & Cold Tiering (Target: Q4 2026+)
- **Deliverables**:
  1. Geo-distributed container scheduling across OCI, AWS, Hetzner, and bare-metal nodes.
  2. Automated lifecycle data tiering migrating inactive snapshot blocks to OCI Object Storage Archive tier.
  3. Enterprise SAML 2.0 bridge enabling corporate identity provider integration.
  4. Web3 decentralized cold storage snapshot archiving using client-side `age` encryption.

---

*End of Specification — NeroNet Architecture Working Group*
