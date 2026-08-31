const express = require('express');
const config = require('./config/env');
const logger = require('./utils/logger');
const corsMiddleware = require('./middleware/cors');
const requestLogger = require('./middleware/logger');
const { errorHandler, notFoundHandler } = require('./middleware/errorHandler');

const { getDatabase } = require('./db/index');
const { runMigrations } = require('./db/migrator');
const { seedDatabase } = require('./db/seed');

// Import Route Handlers
const healthRoutes = require('./routes/health');
const authRoutes = require('./routes/auth');
const usersRoutes = require('./routes/users');
const nodesRoutes = require('./routes/nodes');
const configsRoutes = require('./routes/configs');
const appsRoutes = require('./routes/apps');
const nerodropRoutes = require('./routes/nerodrop');
const statsRoutes = require('./routes/stats');

function createApp() {
  const app = express();

  // Core Middleware
  app.use(corsMiddleware);
  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true }));
  app.use(requestLogger);

  // Mount API Sub-Routers
  app.use('/api', healthRoutes);
  app.use('/api/auth', authRoutes);
  app.use('/api/users', usersRoutes);
  app.use('/api/nodes', nodesRoutes);
  app.use('/api/configs', configsRoutes);
  app.use('/api/apps', appsRoutes);
  app.use('/api/nerodrop', nerodropRoutes);
  app.use('/api/stats', statsRoutes);
  app.use('/api/audit', statsRoutes); // Support /api/audit/logs

  // 404 & Global Error Handling
  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}

function initDatabase() {
  try {
    const db = getDatabase();
    runMigrations(db);
    seedDatabase(db);
    logger.info('Database initialized and verified ready.');
  } catch (err) {
    logger.error('Database initialization failed:', err);
    throw err;
  }
}

const app = createApp();

let server = null;

if (require.main === module) {
  initDatabase();
  server = app.listen(config.PORT, config.HOST, () => {
    logger.info(`=======================================================`);
    logger.info(`🚀 NeroNet Management Console Control Plane API running`);
    logger.info(`📡 URL: http://${config.HOST}:${config.PORT}`);
    logger.info(`🔒 Environment: ${config.NODE_ENV}`);
    logger.info(`=======================================================`);
  });

  const shutdown = () => {
    logger.info('Gracefully stopping NeroNet Console Control Plane...');
    if (server) {
      server.close(() => {
        const { closeDatabase } = require('./db/index');
        closeDatabase();
        process.exit(0);
      });
    } else {
      process.exit(0);
    }
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

module.exports = { app, createApp, initDatabase };
