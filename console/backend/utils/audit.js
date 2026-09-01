const { isPostgres, getPgPool, getDatabase } = require('../db/index');
const logger = require('./logger');

async function logAuditEvent({
  eventType,
  severity = 'info',
  actorUserId = null,
  actorUsername = 'system',
  targetId = null,
  targetType = null,
  message,
  ipAddress = '127.0.0.1',
  userAgent = null,
  metadata = {}
}) {
  try {
    if (isPostgres()) {
      const pool = getPgPool();
      await pool.query(`
        INSERT INTO audit_events (
          event_type, severity, actor_user_id, actor_username,
          target_id, target_type, message, ip_address, user_agent, metadata
        ) VALUES (
          $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
        )
      `, [
        eventType,
        severity,
        actorUserId,
        actorUsername,
        targetId,
        targetType,
        message,
        ipAddress,
        userAgent,
        typeof metadata === 'object' ? JSON.stringify(metadata) : metadata
      ]);
    } else {
      const db = getDatabase();
      const stmt = db.prepare(`
        INSERT INTO audit_events (
          event_type, severity, actor_user_id, actor_username,
          target_id, target_type, message, ip_address, user_agent, metadata_json
        ) VALUES (
          @eventType, @severity, @actorUserId, @actorUsername,
          @targetId, @targetType, @message, @ipAddress, @userAgent, @metadataJson
        )
      `);

      stmt.run({
        eventType,
        severity,
        actorUserId,
        actorUsername,
        targetId,
        targetType,
        message,
        ipAddress,
        userAgent,
        metadataJson: typeof metadata === 'string' ? metadata : JSON.stringify(metadata)
      });
    }
  } catch (err) {
    logger.error('Failed to write audit event:', err.message);
  }
}

module.exports = { logAuditEvent };
