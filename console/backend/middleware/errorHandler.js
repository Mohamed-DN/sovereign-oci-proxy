const logger = require('../utils/logger');

function errorHandler(err, req, res, next) {
  const status = err.status || err.statusCode || 500;
  const message = err.message || 'Internal Server Error';

  logger.error(`[${req.method}] ${req.originalUrl || req.path} -> ${status}: ${message}`);
  if (err.stack && (process.env.NODE_ENV === 'development' || process.env.DEBUG)) {
    logger.error(err.stack);
  }

  res.status(status).json({
    error: message,
    ...(process.env.NODE_ENV === 'development' ? { stack: err.stack } : {})
  });
}

function notFoundHandler(req, res, next) {
  res.status(404).json({
    error: `Endpoint '${req.originalUrl || req.path}' not found`
  });
}

module.exports = {
  errorHandler,
  notFoundHandler
};
