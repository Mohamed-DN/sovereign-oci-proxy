const { publishTopologyEvent, subscribeTopologyEvents, TOPOLOGY_CHANNEL } = require('../db/valkey');
const logger = require('../utils/logger');

let wsBroadcastHandler = null;

function registerWsBroadcaster(broadcaster) {
  wsBroadcastHandler = broadcaster;
}

function initTopologySync() {
  subscribeTopologyEvents((eventData) => {
    if (wsBroadcastHandler && typeof wsBroadcastHandler === 'function') {
      try {
        wsBroadcastHandler(eventData);
      } catch (err) {
        logger.error(`Error in WebSocket broadcast distributor: ${err.message}`);
      }
    }
  });
  logger.info(`TopologySync service active on channel '${TOPOLOGY_CHANNEL}'`);
}

async function broadcastNodeEvent(eventType, nodeData, actorUser = null) {
  const payload = {
    event: eventType,
    node: nodeData,
    node_id: nodeData?.id,
    user_id: nodeData?.user_id,
    action: eventType,
    actor: actorUser ? { id: actorUser.id, username: actorUser.username } : null,
    timestamp: new Date().toISOString()
  };

  await publishTopologyEvent(payload);
}

module.exports = {
  initTopologySync,
  registerWsBroadcaster,
  broadcastNodeEvent,
  publishTopologyEvent,
  TOPOLOGY_CHANNEL
};
