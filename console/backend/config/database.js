const path = require('path');
const config = require('./env');

const dbConfig = {
  // PostgreSQL 16 Configuration
  postgres: {
    connectionString: process.env.DATABASE_URL || process.env.POSTGRES_URL || null,
    host: process.env.PGHOST || process.env.POSTGRES_HOST || '127.0.0.1',
    port: parseInt(process.env.PGPORT || process.env.POSTGRES_PORT || '5432', 10),
    user: process.env.PGUSER || process.env.POSTGRES_USER || 'neronet',
    password: process.env.PGPASSWORD || process.env.POSTGRES_PASSWORD || 'neronet_secret_pass_2026',
    database: process.env.PGDATABASE || process.env.POSTGRES_DB || 'neronet_db',
    max: parseInt(process.env.PGPOOL_MAX || '20', 10),
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
    ssl: process.env.PGSSL === 'true' ? { rejectUnauthorized: false } : false
  },

  // Valkey 7 / Redis Configuration
  valkey: {
    url: process.env.VALKEY_URL || process.env.REDIS_URL || 'redis://127.0.0.1:6379',
    host: process.env.VALKEY_HOST || process.env.REDIS_HOST || '127.0.0.1',
    port: parseInt(process.env.VALKEY_PORT || process.env.REDIS_PORT || '6379', 10),
    password: process.env.VALKEY_PASSWORD || process.env.REDIS_PASSWORD || null,
    db: parseInt(process.env.VALKEY_DB || '0', 10),
    connectTimeout: 3000,
    lazyConnect: true,
    maxRetriesPerRequest: 1
  },

  // Fallback SQLite Path
  sqlite: {
    path: config.DB_PATH || path.resolve(__dirname, '../../data/neronet.db')
  }
};

module.exports = dbConfig;
