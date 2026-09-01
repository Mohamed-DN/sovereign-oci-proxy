const express = require('express');
const router = express.Router();
const { authenticateToken, requireRole } = require('../middleware/auth');
const NukeEngine = require('../services/NukeEngine');
const CanaryService = require('../services/CanaryService');

// =============================================================================
// TIER 3: Warrant Canary (Public Endpoints - No Auth Required)
// =============================================================================

async function handleCanaryRequest(req, res, next) {
  try {
    const canary = await CanaryService.getLatestCanary();

    if (req.headers.accept === 'text/plain' && !req.headers.accept.includes('json')) {
      res.setHeader('Content-Type', 'text/plain; charset=utf-8');
      return res.status(200).send(canary.raw);
    }

    return res.status(200).json({
      valid: Boolean(canary.valid),
      raw: canary.raw,
      statement_text: canary.statement_text,
      signature: canary.ed25519_signature,
      signer_public_key: canary.signer_public_key,
      published_at: canary.published_at,
      is_active: canary.is_active
    });
  } catch (err) {
    next(err);
  }
}

router.get('/canary', handleCanaryRequest);
router.get('/canary.txt', handleCanaryRequest);
router.get('/.well-known/canary.txt', handleCanaryRequest);

// =============================================================================
// TIER 1: User Account Self-Destruct (Auth Required)
// =============================================================================

// 1. Instant Kill
router.post('/user/self-destruct', authenticateToken, async (req, res, next) => {
  try {
    const { confirmation_text, disclaimer_accepted } = req.body || {};

    if (!confirmation_text || confirmation_text !== 'DELETE MY ACCOUNT' || disclaimer_accepted !== true) {
      return res.status(400).json({
        error: "Confirmation phrase 'DELETE MY ACCOUNT' and disclaimer acceptance required"
      });
    }

    const result = await NukeEngine.executeInstantUserDestruction(
      req.user.id,
      req.token,
      req.user.username
    );

    return res.status(200).json(result);
  } catch (err) {
    next(err);
  }
});

// 2. Scheduled Kill
router.post('/user/schedule', authenticateToken, async (req, res, next) => {
  try {
    const { scheduled_deletion_at } = req.body || {};

    if (!scheduled_deletion_at || scheduled_deletion_at === 'PAST_DATE') {
      return res.status(400).json({
        error: 'Invalid scheduled_deletion_at timestamp'
      });
    }

    const schedDate = new Date(scheduled_deletion_at);
    if (isNaN(schedDate.getTime()) || schedDate.getTime() <= Date.now()) {
      return res.status(400).json({
        error: 'Invalid scheduled_deletion_at timestamp'
      });
    }

    const result = await NukeEngine.scheduleUserDestruction(req.user.id, scheduled_deletion_at);
    return res.status(200).json(result);
  } catch (err) {
    next(err);
  }
});

// 3. Cancel Scheduled Kill
router.post('/user/cancel-scheduled', authenticateToken, async (req, res, next) => {
  try {
    const result = await NukeEngine.cancelScheduledUserDestruction(req.user.id);
    return res.status(200).json(result);
  } catch (err) {
    next(err);
  }
});

// 4. User Nuke Status
router.get('/user/status', authenticateToken, async (req, res, next) => {
  try {
    const status = await NukeEngine.getUserNukeStatus(req.user.id);
    return res.status(200).json(status);
  } catch (err) {
    next(err);
  }
});

// =============================================================================
// TIER 1b: Per-User Personal Dead Man's Switch (Auth Required)
// =============================================================================

// 1. Setup Personal DMS
router.post('/personal-dms/setup', authenticateToken, async (req, res, next) => {
  try {
    const { passphrase, heartbeat_interval_seconds } = req.body || {};

    if (!passphrase || passphrase === undefined || heartbeat_interval_seconds === undefined) {
      return res.status(400).json({
        error: 'Missing passphrase or heartbeat_interval_seconds'
      });
    }

    const interval = Number(heartbeat_interval_seconds);
    if (isNaN(interval) || interval <= 0) {
      return res.status(400).json({
        error: 'heartbeat_interval_seconds must be positive'
      });
    }

    const result = await NukeEngine.setupPersonalDMS(req.user.id, req.body);
    return res.status(200).json(result);
  } catch (err) {
    next(err);
  }
});

// 2. Steganographic Unlock / Access
async function handlePersonalUnlock(req, res, next) {
  try {
    const creds = req.body?.stego_credentials || req.body?.passphrase || req.body?.credentials || '';
    const result = await NukeEngine.unlockPersonalDMS(req.user.id, creds);
    return res.status(200).json(result);
  } catch (err) {
    if (err.status === 404) {
      return res.status(404).json({ error: 'No Personal DMS configured' });
    }
    if (err.status === 401) {
      return res.status(401).json({ error: 'Steganographic verification failed' });
    }
    next(err);
  }
}

router.post('/personal-dms/unlock', authenticateToken, handlePersonalUnlock);
router.post('/personal-dms/access', authenticateToken, handlePersonalUnlock);

// 3. Heartbeat Reset
router.post('/personal-dms/heartbeat', authenticateToken, async (req, res, next) => {
  try {
    const result = await NukeEngine.heartbeatPersonalDMS(req.user.id);
    return res.status(200).json(result);
  } catch (err) {
    if (err.status === 404) {
      return res.status(404).json({ error: 'No Personal DMS configured' });
    }
    next(err);
  }
});

// 4. Personal DMS Status
router.get('/personal-dms/status', authenticateToken, async (req, res, next) => {
  try {
    const status = await NukeEngine.getPersonalDMSStatus(req.user.id);
    return res.status(200).json(status);
  } catch (err) {
    next(err);
  }
});

// =============================================================================
// TIER 2: Network Owner Dead Man's Switch (Super-Admin Only)
// =============================================================================

// 1. Setup Owner DMS
router.post('/owner-dms/setup', authenticateToken, requireRole('super-admin'), async (req, res, next) => {
  try {
    const { passphrase, heartbeat_interval_seconds } = req.body || {};

    if (!passphrase || passphrase === undefined || heartbeat_interval_seconds === undefined) {
      return res.status(400).json({
        error: 'Missing passphrase or heartbeat_interval_seconds'
      });
    }

    const interval = Number(heartbeat_interval_seconds);
    if (isNaN(interval) || interval <= 0) {
      return res.status(400).json({
        error: 'heartbeat_interval_seconds must be positive'
      });
    }

    const result = await NukeEngine.setupOwnerDMS(req.user.id, req.body);
    return res.status(200).json(result);
  } catch (err) {
    next(err);
  }
});

// 2. Owner Heartbeat
router.post('/owner-dms/heartbeat', authenticateToken, requireRole('super-admin'), async (req, res, next) => {
  try {
    const { passphrase } = req.body || {};

    if (!passphrase) {
      return res.status(401).json({ error: 'Invalid owner passphrase' });
    }

    const result = await NukeEngine.heartbeatOwnerDMS(req.user.id, passphrase);
    return res.status(200).json(result);
  } catch (err) {
    if (err.status === 401) {
      return res.status(401).json({ error: 'Invalid owner passphrase' });
    }
    next(err);
  }
});

// 3. Owner Status
router.get('/owner-dms/status', authenticateToken, requireRole('super-admin'), async (req, res, next) => {
  try {
    const status = await NukeEngine.getOwnerDMSStatus(req.user.id);
    return res.status(200).json(status);
  } catch (err) {
    next(err);
  }
});

// 4. Trigger Disaster Wipe (Super-Admin emergency test)
router.post('/owner-dms/trigger', authenticateToken, requireRole('super-admin'), async (req, res, next) => {
  try {
    const result = await NukeEngine.executeOwnerGlobalCascadingWipe();
    return res.status(200).json(result);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
