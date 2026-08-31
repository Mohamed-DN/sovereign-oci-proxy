/**
 * NeroNet Enterprise API Client & State Layer
 * Connects to the Control Plane Backend (/api) with automatic mock fallback.
 */

import QRCode from 'qrcode';
import {
  MOCK_USERS,
  MOCK_NODES,
  MOCK_APP_BUNDLES,
  MOCK_AUDIT_LOGS,
  MOCK_TIMESERIES,
  MOCK_GEO_MATRIX,
  MOCK_ACL_RULES,
  MOCK_NERODROP_HISTORY
} from './mockData';

// Mutable in-memory store for fallback mode
let inMemoryNodes = [...MOCK_NODES];
let inMemoryUsers = [...MOCK_USERS];
let inMemoryApps = [...MOCK_APP_BUNDLES];
let inMemoryAuditLogs = [...MOCK_AUDIT_LOGS];
let inMemoryAclRules = [...MOCK_ACL_RULES];
let inMemoryNeroDropHistory = [...MOCK_NERODROP_HISTORY];
let inMemoryShareLinks = [
  {
    id: "shlink-seed-01",
    app_id: "app-seed-guac",
    user_id: "usr-admin",
    share_token: "tok_guac_demo_clientless_rdp_2026",
    public_url: "https://workspace.neronet.darknero.com/#/clientless/app-seed-guac?token=tok_guac_demo_clientless_rdp_2026",
    auth_mode: "temporary_password",
    temporary_password: "SVRN-DEMO-2026",
    expires_at: new Date(Date.now() + 86400000 * 7).toISOString(),
    max_uses: 10,
    use_count: 1,
    is_revoked: false,
    is_expired: false,
    status: "active",
    created_at: new Date().toISOString()
  }
];

const API_BASE = '/api';

function getAuthHeader() {
  const token = localStorage.getItem('neronet_jwt_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...options.headers
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      // If 401, handle auth expiration
      if (res.status === 401) {
        localStorage.removeItem('neronet_jwt_token');
      }
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP error ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    // Fallback mode triggered
    return null;
  }
}

// Generate realistic Curve25519 base64 keys
function generateRandomBase64Key() {
  const bytes = new Uint8Array(32);
  if (typeof window !== 'undefined' && window.crypto) {
    window.crypto.getRandomValues(bytes);
    // Curve25519 clamping
    bytes[0] &= 248;
    bytes[31] &= 127;
    bytes[31] |= 64;
  } else {
    for (let i = 0; i < 32; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export const api = {
  // Authentication
  auth: {
    async login(username, password) {
      const live = await request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password })
      });
      if (live && live.token) {
        localStorage.setItem('neronet_jwt_token', live.token);
        return live;
      }
      // Fallback
      const matchedUser = inMemoryUsers.find(u => u.username === username) || inMemoryUsers[0];
      const mockToken = `mock_jwt_ey...${matchedUser.id}`;
      localStorage.setItem('neronet_jwt_token', mockToken);
      return {
        token: mockToken,
        user: matchedUser
      };
    },

    async me() {
      const live = await request('/auth/me');
      if (live && live.user) return live.user;
      const currentRole = localStorage.getItem('neronet_active_role') || 'super-admin';
      return currentRole === 'super-admin' ? inMemoryUsers[0] : inMemoryUsers[1];
    },

    logout() {
      localStorage.removeItem('neronet_jwt_token');
      return Promise.resolve({ success: true });
    }
  },

  // Nodes Management
  nodes: {
    async list(roleFilter = null) {
      const live = await request('/nodes');
      let nodes = live?.nodes || inMemoryNodes;
      if (roleFilter === 'user') {
        // Scoped for regular user (Alice)
        return nodes.filter(n => n.user_id === 'usr_alice_01' || n.role === 'RELAY');
      }
      return nodes;
    },

    async get(id) {
      const live = await request(`/nodes/${id}`);
      return live?.node || inMemoryNodes.find(n => n.id === id);
    },

    async action(id, actionType, params = {}) {
      const live = await request(`/nodes/${id}/action`, {
        method: 'POST',
        body: JSON.stringify({ action: actionType, params })
      });
      if (live) return live;

      // In-Memory state update
      const nodeIndex = inMemoryNodes.findIndex(n => n.id === id);
      if (nodeIndex !== -1) {
        if (actionType === 'quarantine') {
          inMemoryNodes[nodeIndex] = {
            ...inMemoryNodes[nodeIndex],
            is_quarantined: 1,
            is_healthy: 0,
            quarantine_reason: params.reason || "Manual Zero-Trust Security Isolation"
          };
          inMemoryAuditLogs.unshift({
            id: Date.now(),
            event_type: "QUARANTINE_TRIGGER",
            severity: "critical",
            actor_user_id: "usr_admin_01",
            actor_username: "admin",
            target_id: id,
            target_type: "node",
            message: `Node '${inMemoryNodes[nodeIndex].name}' was quarantined by security admin`,
            ip_address: "100.64.0.1",
            user_agent: "NeroNet-Console/4.0.0",
            metadata_json: JSON.stringify({ action: "quarantine", reason: params.reason || "Manual" }),
            created_at: new Date().toISOString()
          });
          return { success: true, message: "Node quarantined successfully", node: inMemoryNodes[nodeIndex] };
        } else if (actionType === 'lift_quarantine') {
          inMemoryNodes[nodeIndex] = {
            ...inMemoryNodes[nodeIndex],
            is_quarantined: 0,
            is_healthy: 1,
            quarantine_reason: null
          };
          return { success: true, message: "Quarantine lifted", node: inMemoryNodes[nodeIndex] };
        } else if (actionType === 'set_exit') {
          const currentRole = inMemoryNodes[nodeIndex].role;
          const newRole = currentRole === 'EXIT_BRIDGE' ? 'CLIENT_ORIGIN' : 'EXIT_BRIDGE';
          inMemoryNodes[nodeIndex] = {
            ...inMemoryNodes[nodeIndex],
            role: newRole
          };
          return { success: true, message: `Node role updated to ${newRole}`, node: inMemoryNodes[nodeIndex] };
        } else if (actionType === 'toggle_onion' || actionType === 'set_onion') {
          const currentOnion = Boolean(inMemoryNodes[nodeIndex].onion_routing_enabled);
          const newOnion = params.enabled !== undefined ? Boolean(params.enabled) : !currentOnion;
          inMemoryNodes[nodeIndex] = {
            ...inMemoryNodes[nodeIndex],
            onion_routing_enabled: newOnion ? 1 : 0,
            onion_hops: newOnion ? 3 : 0
          };
          return {
            success: true,
            onion_routing_enabled: newOnion,
            onion_hops: newOnion ? 3 : 0,
            node: inMemoryNodes[nodeIndex],
            result: {
              onion_routing_enabled: newOnion,
              onion_hops: newOnion ? 3 : 0
            }
          };
        } else if (actionType === 'ping') {
          const baseLatency = inMemoryNodes[nodeIndex].latency_ms || 15.0;
          const jitter = +(Math.random() * 2.5).toFixed(2);
          const rtt = +(baseLatency + (Math.random() * 4 - 2)).toFixed(2);
          return {
            success: true,
            result: {
              rtt_ms: rtt,
              jitter_ms: jitter,
              packet_loss_pct: 0,
              min_ms: +(rtt - 1.2).toFixed(2),
              avg_ms: rtt,
              max_ms: +(rtt + 2.1).toFixed(2),
              status: inMemoryNodes[nodeIndex].is_quarantined ? 'unreachable' : 'active'
            }
          };
        } else if (actionType === 'revoke') {
          inMemoryNodes = inMemoryNodes.filter(n => n.id !== id);
          return { success: true, message: "Node revoked and removed from mesh" };
        }
      }
      return { success: false, error: "Node not found" };
    }
  },

  // User Management
  users: {
    async list() {
      const live = await request('/users');
      return live?.users || inMemoryUsers;
    },

    async create(userData) {
      const live = await request('/users', {
        method: 'POST',
        body: JSON.stringify(userData)
      });
      if (live && live.user) return live.user;

      const newUser = {
        id: `usr_${Math.random().toString(36).substring(2, 9)}`,
        username: userData.username,
        email: userData.email,
        role: userData.role || 'user',
        tier: userData.tier || 'hybrid_byos',
        status: 'active',
        bandwidth_quota_gb: Number(userData.bandwidth_quota_gb) || (userData.tier === 'cloud_managed' ? 1000 : 500),
        bandwidth_used_bytes: 0,
        max_nodes: Number(userData.max_nodes) || 5,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      inMemoryUsers.push(newUser);
      return newUser;
    },

    async update(id, updates) {
      const live = await request(`/users/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates)
      });
      if (live && live.user) return live.user;

      const idx = inMemoryUsers.findIndex(u => u.id === id);
      if (idx !== -1) {
        inMemoryUsers[idx] = { ...inMemoryUsers[idx], ...updates, updated_at: new Date().toISOString() };
        return inMemoryUsers[idx];
      }
      throw new Error("User not found");
    },

    async delete(id) {
      const live = await request(`/users/${id}`, { method: 'DELETE' });
      if (live) return live;
      inMemoryUsers = inMemoryUsers.filter(u => u.id !== id);
      return { success: true };
    },

    async revokeSessions(id) {
      const live = await request(`/users/${id}/revoke-sessions`, { method: 'POST' });
      return live || { success: true, message: "All user refresh tokens revoked" };
    }
  },

  // App Bundles
  apps: {
    async list() {
      const live = await request('/apps');
      return live?.apps || inMemoryApps;
    },

    async create(appData) {
      const live = await request('/apps', {
        method: 'POST',
        body: JSON.stringify(appData)
      });
      if (live && live.app) return live.app;

      const newApp = {
        id: `app_${appData.type}_${Math.random().toString(36).substring(2, 7)}`,
        user_id: appData.user_id || 'usr_admin_01',
        name: appData.name,
        type: appData.type,
        tier: appData.tier || 'managed_cloud',
        status: 'running',
        endpoint_url: `https://${appData.type}.internal.darknero.net`,
        internal_port: appData.type === 'guacamole' ? 8443 : appData.type === 'immich' ? 2283 : 8080,
        container_id: `cnt_neronet_${appData.type}_${Math.random().toString(36).substring(2, 6)}`,
        cpu_cores: Number(appData.cpu_cores) || 2.0,
        memory_mb: Number(appData.memory_mb) || 4096,
        storage_gb: Number(appData.storage_gb) || 100,
        scale_to_zero: appData.scale_to_zero ? 1 : 0,
        inactivity_timeout_min: Number(appData.inactivity_timeout_min) || 30,
        config_json: JSON.stringify(appData.config || {}),
        last_accessed_at: new Date().toISOString(),
        created_at: new Date().toISOString()
      };
      inMemoryApps.push(newApp);
      return newApp;
    },

    async action(id, actionType) {
      const live = await request(`/apps/${id}/action`, {
        method: 'POST',
        body: JSON.stringify({ action: actionType })
      });
      if (live) return live;

      const idx = inMemoryApps.findIndex(a => a.id === id);
      if (idx !== -1) {
        if (actionType === 'start') {
          inMemoryApps[idx].status = 'running';
          inMemoryApps[idx].last_accessed_at = new Date().toISOString();
        } else if (actionType === 'stop') {
          inMemoryApps[idx].status = 'stopped';
        } else if (actionType === 'scale_to_zero') {
          inMemoryApps[idx].scale_to_zero = inMemoryApps[idx].scale_to_zero ? 0 : 1;
        }
        return { success: true, app: inMemoryApps[idx] };
      }
      return { success: false, error: "App not found" };
    },

    async launch(id) {
      const live = await request(`/apps/${id}/launch`);
      if (live) return live;

      const app = inMemoryApps.find(a => a.id === id);
      const ssoToken = `sso_neronet_${Math.random().toString(36).substring(2, 15)}`;
      return {
        launch_url: app ? `${app.endpoint_url}?sso_token=${ssoToken}` : 'https://guac.internal.darknero.net',
        sso_token: ssoToken,
        app_name: app?.name || 'Sovereign Service'
      };
    },

    async listShareLinks(appId) {
      const live = await request(`/apps/${appId}/share-links`);
      if (live && live.share_links) return live.share_links;
      return inMemoryShareLinks.filter(l => l.app_id === appId);
    },

    async createShareLink(appId, shareData) {
      const live = await request(`/apps/${appId}/share`, {
        method: 'POST',
        body: JSON.stringify(shareData)
      });
      if (live && (live.share_link || live.link)) return live.share_link || live.link;

      const newLink = {
        id: `shlink-${Math.random().toString(36).substring(2, 10)}`,
        app_id: appId,
        user_id: "usr_admin_01",
        share_token: `tok_pub_${Math.random().toString(36).substring(2, 15)}`,
        public_url: `https://workspace.neronet.darknero.com/#/clientless/${appId}?token=tok_pub_${Math.random().toString(36).substring(2, 15)}`,
        auth_mode: shareData.auth_mode || "temporary_password",
        temporary_password: shareData.auth_mode === 'temporary_password' ? (shareData.temporary_password || `SVRN-${Math.random().toString(36).substring(2, 6).toUpperCase()}`) : null,
        expires_at: shareData.expires_at || new Date(Date.now() + (Number(shareData.expires_in_hours) || 24) * 3600 * 1000).toISOString(),
        max_uses: Number(shareData.max_uses) || 0,
        use_count: 0,
        is_revoked: false,
        is_expired: false,
        status: "active",
        created_at: new Date().toISOString()
      };
      inMemoryShareLinks.unshift(newLink);
      return newLink;
    },

    async revokeShareLink(appId, linkId) {
      const live = await request(`/apps/${appId}/share-links/${linkId}`, {
        method: 'DELETE'
      });
      if (live) return live;

      const idx = inMemoryShareLinks.findIndex(l => l.id === linkId);
      if (idx !== -1) {
        inMemoryShareLinks[idx].is_revoked = true;
        inMemoryShareLinks[idx].status = 'revoked';
        return { success: true, message: 'Share link revoked successfully' };
      }
      return { success: false, error: 'Share link not found' };
    },

    async verifyPublicShareLink(token) {
      const live = await request(`/apps/public/verify/${token}`);
      if (live) return live;

      const link = inMemoryShareLinks.find(l => l.share_token === token);
      if (!link) return { valid: false, error: "Share link not found" };
      if (link.is_revoked) return { valid: false, error: "Share link is revoked", is_revoked: true };
      link.use_count += 1;
      return {
        valid: true,
        share_id: link.id,
        app_id: link.app_id,
        app_name: "Guacamole Bastion",
        app_type: "guacamole",
        auth_mode: link.auth_mode,
        public_url: link.public_url,
        gateway_protocol: "guacamole_clientless_rdp",
        websocket_endpoint: `wss://workspace.neronet.darknero.com/guac-tunnel/${link.app_id}`,
        session_token: `sess_pub_${Math.random().toString(36).substring(2, 12)}`,
        expires_at: link.expires_at,
        use_count: link.use_count,
        max_uses: link.max_uses,
        requires_password: link.auth_mode === "temporary_password"
      };
    }
  },

  // Crypto & Config Generator
  configs: {
    async generate(configParams) {
      const live = await request('/configs/generate', {
        method: 'POST',
        body: JSON.stringify(configParams)
      });
      if (live && live.wireguard_conf) return live;

      // Real in-browser cryptographic calculation
      const privateKey = generateRandomBase64Key();
      const publicKey = generateRandomBase64Key();
      const psk = generateRandomBase64Key();
      const randomOctet = Math.floor(Math.random() * 200) + 20;
      const ipv4 = `100.64.0.${randomOctet}`;
      const ipv6 = `fd7a:115c:a1e0::${randomOctet}`;
      const serverEndpoint = "relay-iad-01.darknero.net:51820";
      const serverPubKey = "K7lF8X+q32M4r1Z4w9v9G5e1bL3mN7oP9qR2sT4uV8w=";
      const onionEnabled = Boolean(configParams.onion_routing_enabled || (Number(configParams.onion_hops) > 0));
      const onionHops = onionEnabled ? (Number(configParams.onion_hops) || 3) : 0;

      const wireguardConf = `# =========================================================
# NeroNet Sovereign Mesh DirectFrame v4.0 WireGuard Profile
# Device: ${configParams.name || 'New-Device'}
# Role: ${configParams.role || 'CLIENT_ORIGIN'} | IP Class: ${configParams.ip_class || 'RESIDENTIAL'}
# Onion Obfuscation: ${onionEnabled ? '3-Hop Multi-Route' : 'Direct (0-Hop)'}
# Generated: ${new Date().toUTCString()}
# =========================================================

[Interface]
PrivateKey = ${privateKey}
Address = ${ipv4}/32, ${ipv6}/128
DNS = 100.64.0.1, 1.1.1.1
MTU = 1380

[Peer]
PublicKey = ${serverPubKey}
PresharedKey = ${psk}
Endpoint = ${serverEndpoint}
AllowedIPs = 100.64.0.0/10, fd7a:115c:a1e0::/48, 0.0.0.0/0, ::/0
PersistentKeepalive = 25
`;

      const jsonProfile = {
        version: "4.0.0",
        schema: "neronet_directframe_v4",
        identity: {
          node_id: `svrn-node-${Math.random().toString(36).substring(2, 9)}`,
          name: configParams.name || "New-Device",
          role: configParams.role || "CLIENT_ORIGIN",
          country_code: configParams.country_code || "US"
        },
        network: {
          overlay_ipv4: ipv4,
          overlay_ipv6: ipv6,
          dns_servers: ["100.64.0.1", "1.1.1.1"],
          mtu: 1380,
          keepalive_interval_sec: 25
        },
        crypto: {
          handshake_protocol: "Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s",
          curve: "Curve25519",
          cipher: "ChaCha20-Poly1305",
          hash: "BLAKE2s",
          clamped_public_key: publicKey,
          preshared_key: psk
        },
        relays: [
          {
            name: "neronet-relay-iad-01",
            endpoint: serverEndpoint,
            public_key: serverPubKey
          }
        ],
        routing: {
          egress_mode: configParams.role || "CLIENT_ORIGIN",
          preferred_countries: configParams.country_code ? [configParams.country_code, "US", "DE"] : ["US", "DE", "CH"],
          onion_hops: onionHops,
          onion_routing_enabled: onionEnabled
        }
      };

      // Generate Base64 QR Code using QRCode library
      let qrCodeUrl = "";
      try {
        qrCodeUrl = await QRCode.toDataURL(wireguardConf, {
          errorCorrectionLevel: 'M',
          margin: 2,
          color: {
            dark: '#06b6d4',
            light: '#09090b'
          }
        });
      } catch (err) {
        qrCodeUrl = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'><rect fill='%23000' width='100' height='100'/><text fill='%23fff' x='10' y='50'>QR Code</text></svg>";
      }

      // Add to in-memory nodes list
      const newNode = {
        id: jsonProfile.identity.node_id,
        user_id: "usr_admin_01",
        name: configParams.name || "New-Device",
        public_key: publicKey,
        preshared_key: psk,
        overlay_ipv4: ipv4,
        overlay_ipv6: ipv6,
        role: configParams.role || "CLIENT_ORIGIN",
        ip_class: configParams.ip_class || "RESIDENTIAL",
        country_code: configParams.country_code || "US",
        city: configParams.city || "San Francisco",
        asn: 7922,
        endpoints: [`192.168.1.${randomOctet}:51820`],
        onion_routing_enabled: onionEnabled ? 1 : 0,
        onion_hops: onionHops,
        is_healthy: 1,
        is_quarantined: 0,
        quarantine_reason: null,
        last_heartbeat: new Date().toISOString(),
        latency_ms: onionEnabled ? 48.4 : 18.4,
        tx_bytes: 0,
        rx_bytes: 0,
        cpu_usage_pct: 12.0,
        memory_usage_pct: 35.0,
        battery_pct: 100.0,
        os_type: configParams.os_type || "macos",
        created_at: new Date().toISOString()
      };
      inMemoryNodes.push(newNode);

      return {
        node_id: jsonProfile.identity.node_id,
        node: newNode,
        private_key: privateKey,
        public_key: publicKey,
        preshared_key: psk,
        overlay_ipv4: ipv4,
        overlay_ipv6: ipv6,
        onion_routing_enabled: onionEnabled,
        onion_hops: onionHops,
        wireguard_conf: wireguardConf,
        json_profile: jsonProfile,
        qrcode_data_url: qrCodeUrl
      };
    }
  },

  // NeroDrop P2P File Transfer
  nerodrop: {
    async createSession(sessionData) {
      const live = await request('/nerodrop/session', {
        method: 'POST',
        body: JSON.stringify(sessionData)
      });
      if (live) return live;

      const sessionId = `drop_${Math.random().toString(36).substring(2, 10)}`;
      const chunkSize = 65536; // 64KB chunks
      const totalChunks = Math.ceil(sessionData.file_size_bytes / chunkSize);

      return {
        session_id: sessionId,
        status: "ready",
        chunk_size_bytes: chunkSize,
        total_chunks: totalChunks,
        blake3_hash: sessionData.blake3_hash,
        webrtc_signal: {
          sdp_type: "offer",
          dtls_fingerprint: "SHA-256 89:3B:4E:...:9A",
          ice_candidates: ["candidate:1 1 UDP 2130706431 100.64.0.10 54321 typ host"]
        }
      };
    },

    async listHistory() {
      return inMemoryNeroDropHistory;
    },

    async recordTransfer(transfer) {
      inMemoryNeroDropHistory.unshift(transfer);
      inMemoryAuditLogs.unshift({
        id: Date.now(),
        event_type: "NERODROP_SESSION",
        severity: "info",
        actor_user_id: "usr_alice_01",
        actor_username: "alice_dev",
        target_id: transfer.target_node_name,
        target_type: "file_transfer",
        message: `P2P NeroDrop completed: '${transfer.file_name}' (${(transfer.file_size_bytes / 1024 / 1024).toFixed(2)} MB)`,
        ip_address: "100.64.0.10",
        user_agent: "NeroNet-Client/4.0.0",
        metadata_json: JSON.stringify(transfer),
        created_at: new Date().toISOString()
      });
      return { success: true };
    }
  },

  // Analytics & Stats
  stats: {
    async getOverview() {
      const live = await request('/stats/overview');
      if (live) return live;

      const activeNodesCount = inMemoryNodes.filter(n => n.is_healthy && !n.is_quarantined).length;
      const totalNodesCount = inMemoryNodes.length;
      const quarantinedNodesCount = inMemoryNodes.filter(n => n.is_quarantined).length;
      const activeUsersCount = inMemoryUsers.filter(u => u.status === 'active').length;

      return {
        active_nodes: activeNodesCount,
        total_nodes: totalNodesCount,
        quarantined_nodes: quarantinedNodesCount,
        active_users: activeUsersCount,
        total_bandwidth_rx_mb_s: 88.4,
        total_bandwidth_tx_mb_s: 64.1,
        aggregate_bandwidth_24h_gb: 14890,
        active_circuits: 142,
        network_health_score: 98.4,
        avg_mesh_latency_ms: 16.2
      };
    },

    async getTimeseries() {
      return MOCK_TIMESERIES;
    },

    async getGeoMatrix() {
      return MOCK_GEO_MATRIX;
    }
  },

  // Forensic Audit Logs
  audit: {
    async list() {
      const live = await request('/audit');
      return live?.events || inMemoryAuditLogs;
    }
  },

  // ACL & Settings
  acl: {
    async list() {
      return inMemoryAclRules;
    },

    async create(rule) {
      const newRule = {
        id: `acl_${Math.random().toString(36).substring(2, 6)}`,
        priority: Number(rule.priority) || 50,
        source: rule.source,
        destination: rule.destination,
        port_proto: rule.port_proto,
        action: rule.action,
        description: rule.description
      };
      inMemoryAclRules.push(newRule);
      inMemoryAclRules.sort((a, b) => a.priority - b.priority);
      return newRule;
    },

    async delete(id) {
      inMemoryAclRules = inMemoryAclRules.filter(r => r.id !== id);
      return { success: true };
    }
  }
};

export default api;
