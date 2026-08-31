const path = require('path');
const dotenv = require('dotenv');

// Load environment variables from .env file
dotenv.config({ path: path.resolve(__dirname, '../../.env') });
dotenv.config(); // fallback to local directory .env

const config = {
  NODE_ENV: process.env.NODE_ENV || 'development',
  HOST: process.env.SOVEREIGN_API_HOST || process.env.HOST || '127.0.0.1',
  PORT: parseInt(process.env.SOVEREIGN_API_PORT || process.env.PORT || '8082', 10),

  // Database Configuration
  DB_PATH: process.env.SOVEREIGN_DB_PATH || path.resolve(__dirname, '../../data/neronet.db'),

  // JWT & Authentication Configuration
  JWT_SECRET: process.env.SOVEREIGN_JWT_SECRET || 'svrn_dev_secret_key_change_in_production_9918237192',
  JWT_EXPIRES_IN: process.env.SOVEREIGN_JWT_EXPIRES_IN || '15m',
  REFRESH_SECRET: process.env.SOVEREIGN_REFRESH_SECRET || 'svrn_dev_refresh_secret_key_88291029381',
  REFRESH_EXPIRES_IN: process.env.SOVEREIGN_REFRESH_EXPIRES_IN || '7d',

  // Default Super-Admin Credentials
  ADMIN_USERNAME: process.env.SOVEREIGN_ADMIN_USER || 'admin',
  ADMIN_PASSWORD: process.env.SOVEREIGN_ADMIN_PASS || 'admin_password',
  ADMIN_EMAIL: process.env.SOVEREIGN_ADMIN_EMAIL || 'admin@darknero.com',

  // CORS Configuration
  CORS_ORIGINS: (process.env.CORS_ORIGIN || 'http://127.0.0.1:8081,http://localhost:8081,http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:3000,http://localhost:3000')
    .split(',')
    .map(origin => origin.trim()),

  // Mesh Relay & Master Server Public Key Configuration
  SERVER_ENDPOINT: process.env.SOVEREIGN_SERVER_ENDPOINT || 'relay-us.neronet.darknero.com:51820',
  SERVER_PUBKEY: process.env.SOVEREIGN_SERVER_PUBKEY || 'NeroNetServerMasterPublicKeyBase64Placeholder=',
  CONTROL_PLANE_URL: process.env.SOVEREIGN_CONTROL_PLANE_URL || 'https://neronet.darknero.com/v4/control',

  // Overlay Network VIP Defaults
  OVERLAY_IPV4_BASE: '100.64.0.',
  OVERLAY_IPV6_BASE: 'fd7a:115c:a1e0::'
};

module.exports = config;
