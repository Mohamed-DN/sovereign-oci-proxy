const express = require('express');
const router = express.Router();
const PolicyEngine = require('../services/PolicyEngine');
const { authenticateToken, requireRole } = require('../middleware/auth');

const requireSuperAdmin = requireRole('super-admin');

router.use(authenticateToken);

// 1. List Geo-Fencing Country Policies
router.get('/policies', async (req, res, next) => {
  try {
    const policies = await PolicyEngine.listPolicies();
    return res.status(200).json({ policies, total: policies.length });
  } catch (err) {
    next(err);
  }
});

// 2. Create or Update Geo-Fencing Policy (Super-Admin only)
router.post('/policies', requireSuperAdmin, async (req, res, next) => {
  try {
    const { country_code, action } = req.body || {};
    if (!country_code || !action) {
      return res.status(400).json({ error: 'Missing country_code or action' });
    }

    const policy = await PolicyEngine.createOrUpdatePolicy(req.body);
    return res.status(201).json({ policy });
  } catch (err) {
    if (err.status) {
      return res.status(err.status).json({ error: err.message });
    }
    next(err);
  }
});

// 3. Delete Geo-Fencing Policy (Super-Admin only)
router.delete('/policies/:id', requireSuperAdmin, async (req, res, next) => {
  try {
    const result = await PolicyEngine.deletePolicy(req.params.id);
    return res.status(200).json(result);
  } catch (err) {
    if (err.status) {
      return res.status(err.status).json({ error: err.message });
    }
    next(err);
  }
});

// 4. Evaluate Country Geo-Fencing Policy
router.post('/evaluate', async (req, res, next) => {
  try {
    const { country_code } = req.body || {};
    if (!country_code) {
      return res.status(400).json({ error: 'Invalid country code for evaluation' });
    }
    const result = await PolicyEngine.evaluateCountry(country_code);
    return res.status(200).json(result);
  } catch (err) {
    if (err.status) {
      return res.status(err.status).json({ error: err.message });
    }
    next(err);
  }
});

module.exports = router;
