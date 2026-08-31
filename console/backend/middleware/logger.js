const logger = require('../utils/logger');

function requestLogger(req, res, next) {
  const start = Date.now();
  const { method, originalUrl, ip } = req;

  res.on('finish', () => {
    const duration = Date.now() - start;
    const { statusCode } = res;
    logger.debug(`[HTTP] ${method} ${originalUrl} ${statusCode} - ${duration}ms (${ip || '127.0.0.1'})`);
  });

  next();
}

module.exports = requestLogger;
