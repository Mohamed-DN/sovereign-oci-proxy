const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');
const config = require('../config/env');
const { getDatabase } = require('../db/index');

function signToken(payload, expiresIn = config.JWT_EXPIRES_IN || '1h') {
  const cleanPayload = {
    sub: payload.id || payload.sub,
    id: payload.id || payload.sub,
    username: payload.username,
    role: payload.role,
    tier: payload.tier,
    jti: uuidv4()
  };
  return jwt.sign(cleanPayload, config.JWT_SECRET, { expiresIn });
}

function signRefreshToken(payload, expiresIn = config.REFRESH_EXPIRES_IN || '7d') {
  const cleanPayload = {
    sub: payload.id || payload.sub,
    id: payload.id || payload.sub,
    username: payload.username,
    role: payload.role,
    jti: uuidv4()
  };
  return jwt.sign(cleanPayload, config.REFRESH_SECRET, { expiresIn });
}

function verifyToken(token) {
  try {
    return jwt.verify(token, config.JWT_SECRET);
  } catch (err) {
    return null;
  }
}

function verifyRefreshToken(token) {
  try {
    return jwt.verify(token, config.REFRESH_SECRET);
  } catch (err) {
    return null;
  }
}

function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'] || req.headers['Authorization'] || '';
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or malformed Authorization header' });
  }

  const token = authHeader.substring(7).trim();
  if (!token) {
    return res.status(401).json({ error: 'Missing token' });
  }

  // Check if token was revoked (in-memory or db refresh token check)
  const db = getDatabase();
  const revoked = db.prepare('SELECT id FROM refresh_tokens WHERE token_hash = ? AND revoked = 1').get(token);
  if (revoked) {
    return res.status(401).json({ error: 'Token has been revoked' });
  }

  try {
    const decoded = jwt.verify(token, config.JWT_SECRET);
    req.user = {
      id: decoded.sub || decoded.id,
      username: decoded.username,
      role: decoded.role,
      tier: decoded.tier
    };
    req.token = token;
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

function requireRole(...roles) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Forbidden: insufficient role permissions' });
    }
    next();
  };
}

function requireSelfOrAdmin(req, res, next) {
  if (!req.user) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  const targetId = req.params.id || req.params.userId;
  if (req.user.role === 'super-admin' || req.user.id === targetId) {
    return next();
  }
  return res.status(403).json({ error: 'Forbidden: cannot access another user resource' });
}

module.exports = {
  signToken,
  signRefreshToken,
  verifyToken,
  verifyRefreshToken,
  authenticateToken,
  requireRole,
  requireSelfOrAdmin
};
