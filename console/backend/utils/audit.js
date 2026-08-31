const { getDatabase } = require('../db/index');
const logger = require('./logger');

function logAuditEvent({
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
  } catch (err) {
    logger.error('Failed to write audit event:', err);
  }
}

module.exports = { logAuditEvent };
