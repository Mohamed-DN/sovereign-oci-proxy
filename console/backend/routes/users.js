const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');
const { getDatabase } = require('../db/index');
const { authenticateToken, requireRole, requireSelfOrAdmin } = require('../middleware/auth');
const { logAuditEvent } = require('../utils/audit');

// All users routes require authentication
router.use(authenticateToken);

function formatUser(row) {
  if (!row) return null;
  return {
    id: row.id,
    username: row.username,
    email: row.email,
    role: row.role,
    tier: row.tier,
    status: row.status,
    quota: {
      max_nodes: row.max_nodes,
      max_bandwidth_gb: row.bandwidth_quota_gb,
      bandwidth_used_bytes: row.bandwidth_used_bytes || 0
    },
    created_at: row.created_at,
    updated_at: row.updated_at
  };
}

// 1. List Users (Super-Admin only)
router.get('/', requireRole('super-admin'), (req, res) => {
  const db = getDatabase();
  const rows = db.prepare('SELECT * FROM users ORDER BY created_at ASC').all();
  const users = rows.map(formatUser);
  return res.status(200).json({ users, total: users.length });
});

// 2. Create User (Super-Admin only)
router.post('/', requireRole('super-admin'), (req, res) => {
  const { username, password, email, role, tier, quota } = req.body || {};

  if (!username || !password) {
    return res.status(400).json({ error: 'Missing required fields' });
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

  const maxNodes = (quota && quota.max_nodes) ? quota.max_nodes : (userTier === 'cloud_managed' || userTier === 'managed_cloud' ? 50 : 5);
  const maxBwGb = (quota && quota.max_bandwidth_gb) ? quota.max_bandwidth_gb : (userTier === 'cloud_managed' || userTier === 'managed_cloud' ? 1000 : 100);

  db.prepare(`
    INSERT INTO users (
      id, username, email, password_hash, role, tier, status,
      bandwidth_quota_gb, bandwidth_used_bytes, max_nodes
    ) VALUES (
      ?, ?, ?, ?, ?, ?, 'active', ?, 0, ?
    )
  `).run(userId, username, userEmail, passwordHash, userRole, userTier, maxBwGb, maxNodes);

  logAuditEvent({
    eventType: 'USER_CREATE',
    severity: 'info',
    actorUserId: req.user.id,
    actorUsername: req.user.username,
    targetId: userId,
    targetType: 'user',
    message: `User ${username} created by ${req.user.username}`,
    ipAddress: req.ip
  });

  const createdUser = formatUser(db.prepare('SELECT * FROM users WHERE id = ?').get(userId));
  return res.status(201).json({ user: createdUser });
});

// 3. Get User By ID (Super-Admin or Self)
router.get('/:id', requireSelfOrAdmin, (req, res) => {
  const db = getDatabase();
  const row = db.prepare('SELECT * FROM users WHERE id = ?').get(req.params.id);
  if (!row) {
    return res.status(404).json({ error: 'User not found' });
  }
  return res.status(200).json({ user: formatUser(row) });
});

// 4. Update User (Super-Admin or Self)
router.put('/:id', requireSelfOrAdmin, (req, res) => {
  if (!req.body || Object.keys(req.body).length === 0) {
    return res.status(400).json({ error: 'Missing update body' });
  }

  const db = getDatabase();
  const existing = db.prepare('SELECT * FROM users WHERE id = ?').get(req.params.id);
  if (!existing) {
    return res.status(404).json({ error: 'User not found' });
  }

  const updates = [];
  const params = [];

  if (req.body.email) {
    updates.push('email = ?');
    params.push(req.body.email);
  }
  if (req.body.tier) {
    updates.push('tier = ?');
    params.push(req.body.tier);
  }
  if (req.body.status && req.user.role === 'super-admin') {
    updates.push('status = ?');
    params.push(req.body.status);
  }
  if (req.body.quota) {
    if (req.body.quota.max_nodes !== undefined) {
      updates.push('max_nodes = ?');
      params.push(req.body.quota.max_nodes);
    }
    if (req.body.quota.max_bandwidth_gb !== undefined) {
      updates.push('bandwidth_quota_gb = ?');
      params.push(req.body.quota.max_bandwidth_gb);
    }
  }
  if (req.body.password) {
    const salt = bcrypt.genSaltSync(10);
    updates.push('password_hash = ?');
    params.push(bcrypt.hashSync(req.body.password, salt));
  }

  if (updates.length > 0) {
    updates.push("updated_at = datetime('now')");
    params.push(req.params.id);
    db.prepare(`UPDATE users SET ${updates.join(', ')} WHERE id = ?`).run(...params);
  }

  logAuditEvent({
    eventType: 'USER_UPDATE',
    severity: 'info',
    actorUserId: req.user.id,
    actorUsername: req.user.username,
    targetId: req.params.id,
    targetType: 'user',
    message: `User ${req.params.id} updated`,
    ipAddress: req.ip
  });

  const updated = formatUser(db.prepare('SELECT * FROM users WHERE id = ?').get(req.params.id));
  return res.status(200).json({ user: updated });
});

// 5. Delete User (Super-Admin only)
router.delete('/:id', requireRole('super-admin'), (req, res) => {
  const db = getDatabase();
  const existing = db.prepare('SELECT id, username FROM users WHERE id = ?').get(req.params.id);
  if (!existing) {
    return res.status(404).json({ error: 'User not found' });
  }

  db.prepare('DELETE FROM users WHERE id = ?').run(req.params.id);

  logAuditEvent({
    eventType: 'USER_DELETE',
    severity: 'warn',
    actorUserId: req.user.id,
    actorUsername: req.user.username,
    targetId: req.params.id,
    targetType: 'user',
    message: `User ${existing.username} (${req.params.id}) deleted by ${req.user.username}`,
    ipAddress: req.ip
  });

  return res.status(200).json({ success: true, message: 'User deleted successfully' });
});

// 6. Get User Quota (Super-Admin or Self)
router.get('/:id/quota', requireSelfOrAdmin, (req, res) => {
  const db = getDatabase();
  const user = db.prepare('SELECT * FROM users WHERE id = ?').get(req.params.id);
  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }

  const nodeCount = db.prepare('SELECT count(*) as count FROM nodes WHERE user_id = ?').get(user.id).count;

  return res.status(200).json({
    user_id: user.id,
    max_nodes: user.max_nodes,
    used_nodes: nodeCount,
    max_bandwidth_gb: user.bandwidth_quota_gb,
    used_bandwidth_bytes: user.bandwidth_used_bytes || 0,
    tier: user.tier
  });
});

module.exports = router;
