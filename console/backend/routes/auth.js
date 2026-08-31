const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');
const { getDatabase } = require('../db/index');
const { signToken, signRefreshToken, authenticateToken } = require('../middleware/auth');
const { logAuditEvent } = require('../utils/audit');

// 1. Register User (Public)
router.post('/register', (req, res) => {
  const { username, password, email, role, tier } = req.body || {};

  if (!username || !password) {
    return res.status(400).json({ error: 'Missing required registration fields' });
  }

  const db = getDatabase();
  const existing = db.prepare('SELECT id FROM users WHERE username = ?').get(username);
  if (existing) {
    return res.status(409).json({ error: 'Username already exists' });
  }

  const userId = `usr-${uuidv4().substring(0, 8)}`;
  const userRole = role === 'super-admin' ? 'super-admin' : 'user';
  const userTier = tier || 'hybrid_byos';
  const userEmail = email || `${username}@sovereign.local`;
  const salt = bcrypt.genSaltSync(10);
  const passwordHash = bcrypt.hashSync(password, salt);

  const maxNodes = userTier === 'cloud_managed' || userTier === 'managed_cloud' ? 50 : 5;
  const maxBwGb = userTier === 'cloud_managed' || userTier === 'managed_cloud' ? 1000 : 100;

  db.prepare(`
    INSERT INTO users (
      id, username, email, password_hash, role, tier, status,
      bandwidth_quota_gb, bandwidth_used_bytes, max_nodes
    ) VALUES (
      ?, ?, ?, ?, ?, ?, 'active', ?, 0, ?
    )
  `).run(userId, username, userEmail, passwordHash, userRole, userTier, maxBwGb, maxNodes);

  logAuditEvent({
    eventType: 'USER_REGISTER',
    severity: 'info',
    actorUserId: userId,
    actorUsername: username,
    targetId: userId,
    targetType: 'user',
    message: `User ${username} registered successfully`,
    ipAddress: req.ip
  });

  const userObj = {
    id: userId,
    username,
    role: userRole,
    tier: userTier,
    quota: {
      max_nodes: maxNodes,
      max_bandwidth_gb: maxBwGb
    }
  };

  const token = signToken(userObj);
  const refreshToken = signRefreshToken(userObj);

  return res.status(201).json({
    token,
    refreshToken,
    user: userObj
  });
});

// 2. Login User (Public)
router.post('/login', (req, res) => {
  const { username, password } = req.body || {};

  if (!username || !password) {
    return res.status(400).json({ error: 'Missing username or password' });
  }

  const db = getDatabase();
  const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username);

  if (!user) {
    return res.status(401).json({ error: 'Invalid username or password' });
  }

  let isMatch = false;
  try {
    isMatch = bcrypt.compareSync(password, user.password_hash);
  } catch (err) {
    isMatch = false;
  }

  if (!isMatch) {
    return res.status(401).json({ error: 'Invalid username or password' });
  }

  if (user.status === 'suspended' || user.status === 'revoked') {
    return res.status(403).json({ error: 'Account is suspended or revoked' });
  }

  const userPayload = {
    id: user.id,
    username: user.username,
    role: user.role,
    tier: user.tier,
    quota: {
      max_nodes: user.max_nodes,
      max_bandwidth_gb: user.bandwidth_quota_gb
    }
  };

  const token = signToken(userPayload);
  const refreshToken = signRefreshToken(userPayload);

  logAuditEvent({
    eventType: 'AUTH_LOGIN',
    severity: 'info',
    actorUserId: user.id,
    actorUsername: user.username,
    targetId: user.id,
    targetType: 'user',
    message: `User ${user.username} logged in successfully`,
    ipAddress: req.ip
  });

  return res.status(200).json({
    token,
    refreshToken,
    user: userPayload
  });
});

// 3. Refresh Token
router.post('/refresh', (req, res) => {
  const authHeader = req.headers['authorization'] || req.headers['Authorization'] || '';
  let token = '';

  if (authHeader.startsWith('Bearer ')) {
    token = authHeader.substring(7).trim();
  } else if (req.body && req.body.refreshToken) {
    token = req.body.refreshToken;
  }

  if (!token) {
    return res.status(401).json({ error: 'Missing token for refresh' });
  }

  const db = getDatabase();
  const revoked = db.prepare('SELECT id FROM refresh_tokens WHERE token_hash = ? AND revoked = 1').get(token);
  if (revoked) {
    return res.status(401).json({ error: 'Token has been revoked' });
  }

  const { verifyToken, verifyRefreshToken } = require('../middleware/auth');
  const decoded = verifyToken(token) || verifyRefreshToken(token);

  if (!decoded) {
    return res.status(401).json({ error: 'Invalid or expired refresh token' });
  }

  const newToken = signToken({
    id: decoded.sub || decoded.id,
    username: decoded.username,
    role: decoded.role,
    tier: decoded.tier
  });

  return res.status(200).json({ token: newToken });
});

// 4. Get Current User (Authenticated)
router.get('/me', authenticateToken, (req, res) => {
  const db = getDatabase();
  const user = db.prepare('SELECT id, username, email, role, tier, status, bandwidth_quota_gb, bandwidth_used_bytes, max_nodes, created_at FROM users WHERE id = ?').get(req.user.id);

  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }

  return res.status(200).json({
    user: {
      id: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      tier: user.tier,
      status: user.status,
      quota: {
        max_nodes: user.max_nodes,
        max_bandwidth_gb: user.bandwidth_quota_gb,
        bandwidth_used_bytes: user.bandwidth_used_bytes
      },
      created_at: user.created_at
    }
  });
});

// 5. Logout (Authenticated)
router.post('/logout', authenticateToken, (req, res) => {
  const db = getDatabase();
  const token = req.token;

  if (token) {
    db.prepare(`
      INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, revoked, ip_address)
      VALUES (?, ?, ?, datetime('now', '+7 days'), 1, ?)
    `).run(`tok-${uuidv4().substring(0, 8)}`, req.user.id, token, req.ip || '127.0.0.1');
  }

  logAuditEvent({
    eventType: 'AUTH_LOGOUT',
    severity: 'info',
    actorUserId: req.user.id,
    actorUsername: req.user.username,
    targetId: req.user.id,
    targetType: 'user',
    message: `User ${req.user.username} logged out`,
    ipAddress: req.ip
  });

  return res.status(200).json({
    success: true,
    message: 'Logged out successfully'
  });
});

module.exports = router;
