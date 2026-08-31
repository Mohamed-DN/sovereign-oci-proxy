const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');
const config = require('../config/env');
const logger = require('../utils/logger');

let dbInstance = null;
let currentPath = null;

function getDatabase(customPath) {
  const dbPath = customPath || process.env.SOVEREIGN_DB_PATH || config.DB_PATH;

  if (dbInstance) {
    if (currentPath === dbPath) {
      return dbInstance;
    }
    closeDatabase();
  }

  // Ensure directory exists if not an in-memory database
  if (dbPath !== ':memory:') {
    const dir = path.dirname(path.resolve(dbPath));
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }

  logger.info(`Opening SQLite database connection at: ${dbPath}`);
  dbInstance = new Database(dbPath, {
    verbose: config.NODE_ENV === 'development' && process.env.DEBUG_SQL ? console.log : null
  });
  currentPath = dbPath;

  // Enable high-performance production Pragmas
  if (dbPath !== ':memory:') {
    dbInstance.pragma('journal_mode = WAL');
  }
  dbInstance.pragma('synchronous = NORMAL');
  dbInstance.pragma('foreign_keys = ON');
  dbInstance.pragma('busy_timeout = 5000');
  dbInstance.pragma('cache_size = -20000'); // 20 MB cache

  return dbInstance;
}

function closeDatabase() {
  if (dbInstance) {
    try {
      dbInstance.close();
      logger.info('SQLite database connection closed.');
    } catch (err) {
      logger.error('Error closing SQLite database:', err);
    } finally {
      dbInstance = null;
      currentPath = null;
    }
  }
}

module.exports = {
  getDatabase,
  closeDatabase
};
