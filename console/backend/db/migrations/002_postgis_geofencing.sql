-- ============================================================================
-- NeroNet Sovereign Mesh Enterprise Management Console
-- Migration 002: PostGIS Geo-Fencing & Telemetry History
-- ============================================================================

-- 1. Geo-Fencing Policies Table
CREATE TABLE IF NOT EXISTS geofencing_policies (
    id VARCHAR(64) PRIMARY KEY,
    country_code VARCHAR(2) NOT NULL UNIQUE,
    country_name VARCHAR(128) NOT NULL,
    action VARCHAR(32) NOT NULL DEFAULT 'ALLOW' CHECK (action IN ('ALLOW', 'BLOCK', 'QUARANTINE')),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geofencing_policies_country ON geofencing_policies(country_code);

-- 2. Node Telemetry History (For Velocity & Impossible Travel Tracking)
CREATE TABLE IF NOT EXISTS node_telemetry_history (
    id BIGSERIAL PRIMARY KEY,
    node_id VARCHAR(64) NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    ip_address VARCHAR(45) NOT NULL,
    latitude REAL,
    longitude REAL,
    country_code VARCHAR(2) NOT NULL DEFAULT 'US',
    latency_ms REAL NOT NULL DEFAULT 0.0,
    calculated_speed_kmh REAL DEFAULT 0.0,
    is_impossible_travel BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_node_telemetry_node_time ON node_telemetry_history(node_id, recorded_at DESC);
