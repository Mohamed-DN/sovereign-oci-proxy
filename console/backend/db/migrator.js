const logger = require('../utils/logger');

const MIGRATIONS = [
  {
    name: '001_initial_schema',
    sql: `
      -- 1. Users Table
      CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY,
          username TEXT UNIQUE NOT NULL,
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('super-admin', 'user')),
          tier TEXT NOT NULL DEFAULT 'free_core' CHECK (tier IN ('cloud_managed', 'managed_cloud', 'hybrid_byos', 'free_core')),
          status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'revoked')),
          bandwidth_quota_gb INTEGER NOT NULL DEFAULT 100,
          bandwidth_used_bytes INTEGER NOT NULL DEFAULT 0,
          max_nodes INTEGER NOT NULL DEFAULT 5,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
      CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
      CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
      CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);

      -- 2. Nodes Table
      CREATE TABLE IF NOT EXISTS nodes (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL,
          public_key TEXT NOT NULL UNIQUE,
          preshared_key TEXT,
          overlay_ipv4 TEXT NOT NULL UNIQUE,
          overlay_ipv6 TEXT NOT NULL UNIQUE,
          role TEXT NOT NULL DEFAULT 'CLIENT_ORIGIN' CHECK (role IN ('CLIENT_ORIGIN', 'EXIT_BRIDGE', 'HYBRID', 'RELAY')),
          ip_class TEXT NOT NULL DEFAULT 'RESIDENTIAL' CHECK (ip_class IN ('RESIDENTIAL', 'MOBILE_5G', 'DATACENTER', 'UNKNOWN')),
          country_code TEXT NOT NULL DEFAULT 'US',
          city TEXT DEFAULT '',
          asn INTEGER DEFAULT 0,
          endpoints TEXT DEFAULT '[]',
          onion_routing_enabled INTEGER NOT NULL DEFAULT 0,
          is_healthy INTEGER NOT NULL DEFAULT 1,
          is_quarantined INTEGER NOT NULL DEFAULT 0,
          quarantine_reason TEXT,
          last_heartbeat DATETIME,
          latency_ms REAL NOT NULL DEFAULT 0.0,
          tx_bytes INTEGER NOT NULL DEFAULT 0,
          rx_bytes INTEGER NOT NULL DEFAULT 0,
          cpu_usage_pct REAL DEFAULT 0.0,
          memory_usage_pct REAL DEFAULT 0.0,
          battery_pct REAL DEFAULT 100.0,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_nodes_user_id ON nodes(user_id);
      CREATE INDEX IF NOT EXISTS idx_nodes_public_key ON nodes(public_key);
      CREATE INDEX IF NOT EXISTS idx_nodes_overlay_ipv4 ON nodes(overlay_ipv4);
      CREATE INDEX IF NOT EXISTS idx_nodes_role ON nodes(role);
      CREATE INDEX IF NOT EXISTS idx_nodes_country_code ON nodes(country_code);
      CREATE INDEX IF NOT EXISTS idx_nodes_is_quarantined ON nodes(is_quarantined);

      -- 3. App Bundles Table
      CREATE TABLE IF NOT EXISTS app_bundles (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL,
          type TEXT NOT NULL CHECK (type IN ('guacamole', 'nextcloud', 'immich', 'seafile')),
          tier TEXT NOT NULL DEFAULT 'managed_cloud' CHECK (tier IN ('managed_cloud', 'self_hosted_byos')),
          status TEXT NOT NULL DEFAULT 'stopped' CHECK (status IN ('provisioning', 'running', 'stopped', 'error', 'suspended', 'hibernated')),
          endpoint_url TEXT NOT NULL,
          internal_port INTEGER NOT NULL DEFAULT 8080,
          container_id TEXT,
          cpu_cores REAL NOT NULL DEFAULT 2.0,
          memory_mb INTEGER NOT NULL DEFAULT 2048,
          storage_gb INTEGER NOT NULL DEFAULT 50,
          scale_to_zero INTEGER NOT NULL DEFAULT 1,
          inactivity_timeout_min INTEGER DEFAULT 30,
          config_json TEXT DEFAULT '{}',
          last_accessed_at DATETIME,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_app_bundles_user_id ON app_bundles(user_id);
      CREATE INDEX IF NOT EXISTS idx_app_bundles_type ON app_bundles(type);
      CREATE INDEX IF NOT EXISTS idx_app_bundles_status ON app_bundles(status);

      -- 4. Audit Events Table
      CREATE TABLE IF NOT EXISTS audit_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          event_type TEXT NOT NULL,
          severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('info', 'warn', 'error', 'critical')),
          actor_user_id TEXT,
          actor_username TEXT,
          target_id TEXT,
          target_type TEXT,
          message TEXT NOT NULL,
          ip_address TEXT,
          user_agent TEXT,
          metadata_json TEXT DEFAULT '{}',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events(created_at DESC);
      CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events(event_type);
      CREATE INDEX IF NOT EXISTS idx_audit_events_severity ON audit_events(severity);
      CREATE INDEX IF NOT EXISTS idx_audit_events_actor ON audit_events(actor_user_id);

      -- 5. System Metrics Table
      CREATE TABLE IF NOT EXISTS system_metrics (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          active_nodes INTEGER NOT NULL DEFAULT 0,
          active_users INTEGER NOT NULL DEFAULT 0,
          total_bandwidth_rx INTEGER NOT NULL DEFAULT 0,
          total_bandwidth_tx INTEGER NOT NULL DEFAULT 0,
          cpu_usage_pct REAL NOT NULL DEFAULT 0.0,
          memory_usage_mb REAL NOT NULL DEFAULT 0.0,
          active_circuits INTEGER NOT NULL DEFAULT 0,
          network_health_score INTEGER NOT NULL DEFAULT 100
      );

      CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp DESC);

      -- 6. Refresh Tokens Table
      CREATE TABLE IF NOT EXISTS refresh_tokens (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          token_hash TEXT NOT NULL UNIQUE,
          expires_at DATETIME NOT NULL,
          revoked INTEGER NOT NULL DEFAULT 0,
          user_agent TEXT,
          ip_address TEXT,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
      CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);

      -- 7. NeroDrop P2P File Transfer Sessions Table
      CREATE TABLE IF NOT EXISTS nerodrop_sessions (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          source_node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
          target_node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
          file_name TEXT NOT NULL,
          file_size_bytes INTEGER NOT NULL,
          file_type TEXT DEFAULT 'application/octet-stream',
          blake3_hash TEXT NOT NULL,
          chunk_size_bytes INTEGER NOT NULL DEFAULT 65536,
          total_chunks INTEGER NOT NULL,
          transferred_chunks INTEGER NOT NULL DEFAULT 0,
          bytes_transferred INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'ready' CHECK (status IN ('ready', 'pending', 'transferring', 'completed', 'failed', 'cancelled')),
          webrtc_signal_json TEXT DEFAULT '{}',
          started_at DATETIME,
          completed_at DATETIME,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_nerodrop_user_id ON nerodrop_sessions(user_id);
      CREATE INDEX IF NOT EXISTS idx_nerodrop_status ON nerodrop_sessions(status);

      -- 8. App Share Links Table (Guacamole Clientless RDP Public Gateway)
      CREATE TABLE IF NOT EXISTS app_share_links (
          id TEXT PRIMARY KEY,
          app_id TEXT NOT NULL REFERENCES app_bundles(id) ON DELETE CASCADE,
          user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          share_token TEXT NOT NULL UNIQUE,
          public_url TEXT NOT NULL,
          auth_mode TEXT NOT NULL DEFAULT 'temporary_password' CHECK (auth_mode IN ('temporary_password', 'sso_gateway', 'passkey')),
          temporary_password TEXT,
          expires_at DATETIME NOT NULL,
          max_uses INTEGER DEFAULT 0,
          use_count INTEGER DEFAULT 0,
          is_revoked INTEGER NOT NULL DEFAULT 0,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_app_share_links_token ON app_share_links(share_token);
      CREATE INDEX IF NOT EXISTS idx_app_share_links_app_id ON app_share_links(app_id);
      CREATE INDEX IF NOT EXISTS idx_app_share_links_user_id ON app_share_links(user_id);
    `
  },
  {
    name: '002_onion_and_share_links',
    sql: `
      CREATE TABLE IF NOT EXISTS app_share_links (
          id TEXT PRIMARY KEY,
          app_id TEXT NOT NULL REFERENCES app_bundles(id) ON DELETE CASCADE,
          user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          share_token TEXT NOT NULL UNIQUE,
          public_url TEXT NOT NULL,
          auth_mode TEXT NOT NULL DEFAULT 'temporary_password' CHECK (auth_mode IN ('temporary_password', 'sso_gateway', 'passkey')),
          temporary_password TEXT,
          expires_at DATETIME NOT NULL,
          max_uses INTEGER DEFAULT 0,
          use_count INTEGER DEFAULT 0,
          is_revoked INTEGER NOT NULL DEFAULT 0,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_app_share_links_token ON app_share_links(share_token);
      CREATE INDEX IF NOT EXISTS idx_app_share_links_app_id ON app_share_links(app_id);
      CREATE INDEX IF NOT EXISTS idx_app_share_links_user_id ON app_share_links(user_id);
    `,
    run: (db) => {
      // Safely alter nodes table to add onion_routing_enabled if missing
      const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'").all();
      if (tables.length > 0) {
        const nodeCols = db.pragma('table_info(nodes)').map(c => c.name);
        if (!nodeCols.includes('onion_routing_enabled')) {
          db.exec('ALTER TABLE nodes ADD COLUMN onion_routing_enabled INTEGER NOT NULL DEFAULT 0;');
        }
      }
    }
  }
];

function ensureSchemaIntegrity(db) {
  // Guarantee all columns exist even if previous migrations had execution gaps
  const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'").all();
  if (tables.length > 0) {
    const nodeCols = db.pragma('table_info(nodes)').map(c => c.name);
    if (!nodeCols.includes('onion_routing_enabled')) {
      logger.info('Schema healing: Adding missing onion_routing_enabled column to nodes table...');
      db.exec('ALTER TABLE nodes ADD COLUMN onion_routing_enabled INTEGER NOT NULL DEFAULT 0;');
    }
  }
}

function runMigrations(db) {
  // Create migrations table
  db.exec(`
    CREATE TABLE IF NOT EXISTS _migrations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT UNIQUE NOT NULL,
      applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
  `);

  const appliedRows = db.prepare('SELECT name FROM _migrations').all();
  const appliedSet = new Set(appliedRows.map(r => r.name));

  for (const migration of MIGRATIONS) {
    if (!appliedSet.has(migration.name)) {
      logger.info(`Applying SQLite migration: ${migration.name}...`);
      db.transaction(() => {
        if (migration.sql) {
          db.exec(migration.sql);
        }
        if (typeof migration.run === 'function') {
          migration.run(db);
        }
        db.prepare('INSERT INTO _migrations (name) VALUES (?)').run(migration.name);
      })();
      logger.info(`Migration ${migration.name} applied successfully.`);
    }
  }

  // Schema integrity guarantee for persistent databases
  ensureSchemaIntegrity(db);
}

module.exports = { runMigrations, ensureSchemaIntegrity, MIGRATIONS };
