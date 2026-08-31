const cors = require('cors');
const config = require('../config/env');

const corsOptions = {
  origin: function (origin, callback) {
    // Allow requests with no origin (like mobile apps, curl, server-to-server)
    if (!origin) return callback(null, true);
    if (config.CORS_ORIGINS.indexOf(origin) !== -1 || config.CORS_ORIGINS.includes('*')) {
      callback(null, true);
    } else {
      // In development/test mode allow localhost and 127.0.0.1 origins
      if (origin.includes('localhost') || origin.includes('127.0.0.1')) {
        return callback(null, true);
      }
      callback(null, true); // Permissive for local console integration
    }
  },
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
  credentials: true
};

module.exports = cors(corsOptions);
