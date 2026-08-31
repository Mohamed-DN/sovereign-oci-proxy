const express = require('express');
const router = express.Router();
const { getDatabase } = require('../db/index');

router.get('/health', (req, res) => {
  let dbStatus = 'connected';
  let isHealthy = true;

  try {
    const db = getDatabase();
    db.prepare('SELECT 1').get();
  } catch (err) {
    dbStatus = 'disconnected';
    isHealthy = false;
  }

  const responseData = {
    status: isHealthy ? 'ok' : 'degraded',
    version: '4.0.0',
    database: dbStatus,
    uptime_seconds: Math.floor(process.uptime()),
    timestamp: new Date().toISOString()
  };

  return res.status(isHealthy ? 200 : 503).json(responseData);
});

module.exports = router;
