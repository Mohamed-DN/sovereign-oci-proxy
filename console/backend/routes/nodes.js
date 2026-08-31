const express = require('express');
const router = express.Router();
const crypto = require('crypto');
const { getDatabase } = require('../db/index');
const { authenticateToken } = require('../middleware/auth');
const { logAuditEvent } = require('../utils/audit');
const { allocateNextVip, generateCurve25519Keypair } = require('../utils/crypto');

router.use(authenticateToken);

function formatNode(row) {
  if (!row) return null;
  const isQuarantined = Boolean(row.is_quarantined);
  const isExit = row.role === 'EXIT_BRIDGE';
  const onionEnabled = Boolean(row.onion_routing_enabled);
  return {
    id: row.id,
    user_id: row.user_id,
    name: row.name,
    public_key: row.public_key,
    overlay_ipv4: row.overlay_ipv4,
    overlay_ipv6: row.overlay_ipv6,
    role: row.role,
    ip_class: row.ip_class,
    country_code: row.country_code,
    city: row.city || '',
    asn: row.asn || 0,
    endpoints: typeof row.endpoints === 'string' ? JSON.parse(row.endpoints || '[]') : row.endpoints,
    onion_routing_enabled: onionEnabled,
    onion_hops: onionEnabled ? 3 : 0,
    is_healthy: Boolean(row.is_healthy),
    is_quarantined: isQuarantined,
    quarantine_reason: row.quarantine_reason || null,
    is_exit_node: isExit,
    status: isQuarantined ? 'quarantined' : (row.is_healthy ? 'active' : 'degraded'),
    latency_ms: row.latency_ms || 15.0,
    jitter_ms: 1.0,
    tx_bytes: row.tx_bytes || 0,
    rx_bytes: row.rx_bytes || 0,
    cpu_usage_pct: row.cpu_usage_pct || 0.0,
    memory_usage_pct: row.memory_usage_pct || 0.0,
    battery_pct: row.battery_pct !== undefined ? row.battery_pct : 100.0,
    posture: {
      compliant: !isQuarantined,
      os: 'Linux',
      disk_encrypted: true
    },
    last_heartbeat: row.last_heartbeat,
    created_at: row.created_at,
    updated_at: row.updated_at
  };
}

// 1. List Nodes (Scoped by Super-Admin vs Regular User)
router.get('/', (req, res) => {
  const db = getDatabase();
  let rows;
  if (req.user.role === 'super-admin') {
    rows = db.prepare('SELECT * FROM nodes ORDER BY created_at ASC').all();
  } else {
    rows = db.prepare('SELECT * FROM nodes WHERE user_id = ? ORDER BY created_at ASC').all(req.user.id);
  }
  const nodes = rows.map(formatNode);
  return res.status(200).json({ nodes, total: nodes.length });
});

// 2. Create Node
router.post('/', (req, res) => {
  const { name, role, country_code, public_key, ip_class, city, asn, onion_routing_enabled, onion_hops } = req.body || {};

  if (!name || !name.trim()) {
    return res.status(400).json({ error: 'Missing node name' });
  }

  const db = getDatabase();

  // Quota check for regular users
  if (req.user.role !== 'super-admin') {
    const userRow = db.prepare('SELECT max_nodes FROM users WHERE id = ?').get(req.user.id);
    const maxNodes = userRow ? userRow.max_nodes : 5;
    const currentCount = db.prepare('SELECT count(*) as count FROM nodes WHERE user_id = ?').get(req.user.id).count;
    if (currentCount >= maxNodes) {
      return res.status(403).json({ error: `Node quota exceeded (${currentCount}/${maxNodes})` });
    }
  }

  let finalPubKey = public_key;
  if (!finalPubKey) {
    const kp = generateCurve25519Keypair();
    finalPubKey = kp.publicKeyBase64;
  }

  // Duplicate public key check
  const existingKey = db.prepare('SELECT id FROM nodes WHERE public_key = ?').get(finalPubKey);
  if (existingKey) {
    return res.status(409).json({ error: 'Public key already registered' });
  }

  const VALID_ROLES = ['CLIENT_ORIGIN', 'EXIT_BRIDGE', 'HYBRID', 'RELAY'];
  const VALID_IP_CLASSES = ['RESIDENTIAL', 'MOBILE_5G', 'DATACENTER', 'UNKNOWN'];

  const nodeRole = role && VALID_ROLES.includes(role) ? role : 'CLIENT_ORIGIN';
  const nodeIpClass = ip_class && VALID_IP_CLASSES.includes(ip_class) ? ip_class : 'RESIDENTIAL';
  const nodeCountry = country_code || 'US';
  const onionRouting = onion_routing_enabled !== undefined ? (onion_routing_enabled ? 1 : 0) : (onion_hops > 0 ? 1 : 0);
  const { overlayIpv4, overlayIpv6 } = allocateNextVip(db);
  const nodeId = `svrn-node-${crypto.randomBytes(4).toString('hex')}`;

  db.prepare(`
    INSERT INTO nodes (
      id, user_id, name, public_key, overlay_ipv4, overlay_ipv6,
      role, ip_class, country_code, city, asn, onion_routing_enabled, is_healthy, is_quarantined, latency_ms
    ) VALUES (
      ?, ?, ?, ?, ?, ?,
      ?, ?, ?, ?, ?, ?, 1, 0, 15.0
    )
  `).run(
    nodeId, req.user.id, name.trim(), finalPubKey, overlayIpv4, overlayIpv6,
    nodeRole, nodeIpClass, nodeCountry, city || '', asn || 0, onionRouting
  );

  logAuditEvent({
    eventType: 'NODE_REGISTER',
    severity: 'info',
    actorUserId: req.user.id,
    actorUsername: req.user.username,
    targetId: nodeId,
    targetType: 'node',
    message: `Node ${name} registered`,
    ipAddress: req.ip
  });

  const createdNode = formatNode(db.prepare('SELECT * FROM nodes WHERE id = ?').get(nodeId));
  return res.status(201).json({ node: createdNode });
});

// 3. Get Node By ID
router.get('/:id', (req, res) => {
  const db = getDatabase();
  const node = db.prepare('SELECT * FROM nodes WHERE id = ?').get(req.params.id);
  if (!node) {
    return res.status(404).json({ error: 'Node not found' });
  }
  if (req.user.role !== 'super-admin' && node.user_id !== req.user.id) {
    return res.status(403).json({ error: 'Access forbidden' });
  }
  return res.status(200).json({ node: formatNode(node) });
});

// 4. Update Node
router.put('/:id', (req, res) => {
  if (!req.body || Object.keys(req.body).length === 0) {
    return res.status(400).json({ error: 'Missing update body' });
  }

  const db = getDatabase();
  const node = db.prepare('SELECT * FROM nodes WHERE id = ?').get(req.params.id);
  if (!node) {
    return res.status(404).json({ error: 'Node not found' });
  }
  if (req.user.role !== 'super-admin' && node.user_id !== req.user.id) {
    return res.status(403).json({ error: 'Access forbidden' });
  }

  const updates = [];
  const params = [];

  if (req.body.name) {
    updates.push('name = ?');
    params.push(req.body.name);
  }
  if (req.body.latency_ms !== undefined) {
    updates.push('latency_ms = ?');
    params.push(req.body.latency_ms);
  }
  if (req.body.is_healthy !== undefined) {
    updates.push('is_healthy = ?');
    params.push(req.body.is_healthy ? 1 : 0);
  }
  if (req.body.role) {
    updates.push('role = ?');
    params.push(req.body.role);
  }
  if (req.body.onion_routing_enabled !== undefined) {
    updates.push('onion_routing_enabled = ?');
    params.push(req.body.onion_routing_enabled ? 1 : 0);
  } else if (req.body.onion_hops !== undefined) {
    updates.push('onion_routing_enabled = ?');
    params.push(req.body.onion_hops > 0 ? 1 : 0);
  }
  if (req.body.status) {
    if (req.body.status === 'quarantined') {
      updates.push('is_quarantined = 1, is_healthy = 0');
    } else if (req.body.status === 'active') {
      updates.push('is_quarantined = 0, is_healthy = 1');
    }
  }

  if (updates.length > 0) {
    updates.push("updated_at = datetime('now')");
    params.push(req.params.id);
    db.prepare(`UPDATE nodes SET ${updates.join(', ')} WHERE id = ?`).run(...params);
  }

  const updatedNode = formatNode(db.prepare('SELECT * FROM nodes WHERE id = ?').get(req.params.id));
  return res.status(200).json({ node: updatedNode });
});

// 5. Delete Node
router.delete('/:id', (req, res) => {
  const db = getDatabase();
  const node = db.prepare('SELECT * FROM nodes WHERE id = ?').get(req.params.id);
  if (!node) {
    return res.status(404).json({ error: 'Node not found' });
  }
  if (req.user.role !== 'super-admin' && node.user_id !== req.user.id) {
    return res.status(403).json({ error: 'Access forbidden' });
  }

  db.prepare('DELETE FROM nodes WHERE id = ?').run(req.params.id);

  logAuditEvent({
    eventType: 'NODE_REVOKE',
    severity: 'warn',
    actorUserId: req.user.id,
    actorUsername: req.user.username,
    targetId: req.params.id,
    targetType: 'node',
    message: `Node ${node.name} (${req.params.id}) revoked`,
    ipAddress: req.ip
  });

  return res.status(200).json({ success: true, message: 'Node revoked successfully' });
});

// 6. Node Heartbeat
router.post('/:id/heartbeat', (req, res) => {
  const db = getDatabase();
  const node = db.prepare('SELECT * FROM nodes WHERE id = ?').get(req.params.id);
  if (!node) {
    return res.status(404).json({ error: 'Node not found' });
  }

  const { latency_ms, rx_bytes, tx_bytes, cpu_usage_pct, memory_usage_pct, battery_pct } = req.body || {};

  db.prepare(`
    UPDATE nodes SET
      last_heartbeat = datetime('now'),
      latency_ms = COALESCE(?, latency_ms),
      rx_bytes = COALESCE(?, rx_bytes),
      tx_bytes = COALESCE(?, tx_bytes),
      cpu_usage_pct = COALESCE(?, cpu_usage_pct),
      memory_usage_pct = COALESCE(?, memory_usage_pct),
      battery_pct = COALESCE(?, battery_pct),
      is_healthy = 1,
      updated_at = datetime('now')
    WHERE id = ?
  `).run(
    latency_ms !== undefined ? latency_ms : null,
    rx_bytes !== undefined ? rx_bytes : null,
    tx_bytes !== undefined ? tx_bytes : null,
    cpu_usage_pct !== undefined ? cpu_usage_pct : null,
    memory_usage_pct !== undefined ? memory_usage_pct : null,
    battery_pct !== undefined ? battery_pct : null,
    req.params.id
  );

  return res.status(200).json({ success: true, timestamp: new Date().toISOString() });
});

// 7. Node Actions: ping, set_exit, quarantine, toggle_onion
router.post('/:id/action', (req, res) => {
  const db = getDatabase();
  const node = db.prepare('SELECT * FROM nodes WHERE id = ?').get(req.params.id);
  if (!node) {
    return res.status(404).json({ error: 'Node not found' });
  }
  if (req.user.role !== 'super-admin' && node.user_id !== req.user.id) {
    return res.status(403).json({ error: 'Access forbidden' });
  }

  const { action } = req.body || {};
  if (!action) {
    return res.status(400).json({ error: 'Missing action parameter' });
  }

  if (action === 'ping') {
    const rtt_ms = node.latency_ms > 0 ? node.latency_ms : 14.2;
    const jitter_ms = 1.1;
    logAuditEvent({
      eventType: 'NODE_PING',
      severity: 'info',
      actorUserId: req.user.id,
      actorUsername: req.user.username,
      targetId: node.id,
      targetType: 'node',
      message: `Node ${node.id} pinged`,
      ipAddress: req.ip,
      metadata: { rtt_ms, jitter_ms }
    });
    return res.status(200).json({
      success: true,
      result: {
        rtt_ms,
        jitter_ms,
        status: node.is_quarantined ? 'quarantined' : 'active'
      }
    });
  }

  if (action === 'set_exit') {
    db.prepare("UPDATE nodes SET role = 'EXIT_BRIDGE', updated_at = datetime('now') WHERE id = ?").run(node.id);
    logAuditEvent({
      eventType: 'NODE_SET_EXIT',
      severity: 'info',
      actorUserId: req.user.id,
      actorUsername: req.user.username,
      targetId: node.id,
      targetType: 'node',
      message: `Node ${node.id} designated as EXIT_BRIDGE`,
      ipAddress: req.ip
    });
    return res.status(200).json({
      success: true,
      result: {
        is_exit_node: true,
        status: node.is_quarantined ? 'quarantined' : 'active'
      }
    });
  }

  if (action === 'toggle_onion' || action === 'set_onion') {
    const currentVal = Boolean(node.onion_routing_enabled);
    let newVal;
    if (req.body.params && req.body.params.enabled !== undefined) {
      newVal = req.body.params.enabled ? 1 : 0;
    } else if (req.body.enabled !== undefined) {
      newVal = req.body.enabled ? 1 : 0;
    } else if (req.body.params && req.body.params.onion_hops !== undefined) {
      newVal = req.body.params.onion_hops > 0 ? 1 : 0;
    } else if (req.body.onion_hops !== undefined) {
      newVal = req.body.onion_hops > 0 ? 1 : 0;
    } else {
      newVal = currentVal ? 0 : 1;
    }

    db.prepare("UPDATE nodes SET onion_routing_enabled = ?, updated_at = datetime('now') WHERE id = ?").run(newVal, node.id);

    logAuditEvent({
      eventType: 'NODE_ONION_TOGGLE',
      severity: 'info',
      actorUserId: req.user.id,
      actorUsername: req.user.username,
      targetId: node.id,
      targetType: 'node',
      message: `Node ${node.id} 3-hop onion obfuscation set to ${Boolean(newVal)}`,
      ipAddress: req.ip,
      metadata: { onion_routing_enabled: Boolean(newVal), onion_hops: newVal ? 3 : 0 }
    });

    const updatedNode = formatNode(db.prepare('SELECT * FROM nodes WHERE id = ?').get(node.id));
    return res.status(200).json({
      success: true,
      onion_routing_enabled: Boolean(newVal),
      onion_hops: newVal ? 3 : 0,
      node: updatedNode,
      result: {
        onion_routing_enabled: Boolean(newVal),
        onion_hops: newVal ? 3 : 0,
        status: updatedNode.status
      }
    });
  }

  if (action === 'quarantine') {
    const reason = req.body.reason || 'Manual security quarantine';
    db.prepare(`
      UPDATE nodes SET
        is_quarantined = 1,
        is_healthy = 0,
        quarantine_reason = ?,
        updated_at = datetime('now')
      WHERE id = ?
    `).run(reason, node.id);

    logAuditEvent({
      eventType: 'NODE_QUARANTINE',
      severity: 'warn',
      actorUserId: req.user.id,
      actorUsername: req.user.username,
      targetId: node.id,
      targetType: 'node',
      message: `Node ${node.id} quarantined: ${reason}`,
      ipAddress: req.ip
    });

    return res.status(200).json({
      success: true,
      result: {
        is_quarantined: true,
        status: 'quarantined'
      }
    });
  }

  return res.status(400).json({ error: `Unsupported action '${action}'` });
});

module.exports = router;
