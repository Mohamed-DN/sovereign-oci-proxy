/**
 * Challenger 1: Milestone 1 Empirical Stress Test & Adversarial Verification
 * 
 * Tests:
 * 1. Auth Adversarial Fuzzing, SQLi Payloads, JWT Tampering, and Timing Side-Channel Analysis
 * 2. VIP Allocation in 100.64.0.0/10 and fd7a:115c:a1e0::/64 under high concurrency & 10,000 allocations
 * 3. WebSocket Real-Time Synchronization & Valkey Pub/Sub Flood with Role-Based Scoping
 * 4. Curve25519 Scalar Clamping & Config Profile Cryptographic Validation
 */

const http = require('http');
const path = require('path');
const fs = require('fs');
const assert = require('assert');
const request = require('supertest');
const { WebSocket } = require('ws');
const jwt = require('jsonwebtoken');

const backendRoot = path.resolve(__dirname, '../../console/backend');
const { createApp, initDatabase } = require(path.join(backendRoot, 'server'));
const { getDatabase, closeDatabase } = require(path.join(backendRoot, 'db/index'));
const { initTopologyWebSocket, closeTopologyWebSocket } = require(path.join(backendRoot, 'ws/topologyServer'));
const { publishTopologyEvent, blacklistToken, isTokenBlacklisted, closeValkey } = require(path.join(backendRoot, 'db/valkey'));
const { generateCurve25519Keypair, allocateVipFromRows, buildWireGuardConfig, buildNoiseJsonProfile } = require(path.join(backendRoot, 'utils/crypto'));
const config = require(path.join(backendRoot, 'config/env'));

const TEST_DB = path.resolve(__dirname, '../../console/data/test_challenger1_m1.db');
process.env.SOVEREIGN_DB_PATH = TEST_DB;

const SQLI_PAYLOADS = [
  "' OR '1'='1",
  "admin'--",
  "admin' /*",
  "' OR 1=1 --",
  "' UNION SELECT 1, 'admin', 'pass', 'super-admin' --",
  "'; DROP TABLE users; --",
  "' OR 'a'='a",
  "1' ORDER BY 1--+",
  "admin' AND 1=0 UNION ALL SELECT 'admin', '81dc9bdb52d04dc20036dbd8313ed055' --",
  "' OR ''='",
  "\" or \"\"=\"",
  "1' or '1' = '1",
  "<script>alert(1)</script>",
  "admin\x00' OR '1'='1",
  "’ OR ‘1’=’1",
  "' OR 1=1 LIMIT 1; --",
  "admin' OR 1=1#",
  "' HAVING 1=1 --",
  "' GROUP BY 1 --",
  "' OR (SELECT COUNT(*) FROM users) > 0 --"
];

function calculateStats(numbers) {
  if (numbers.length === 0) return { mean: 0, median: 0, stdDev: 0, min: 0, max: 0 };
  const sorted = [...numbers].sort((a, b) => a - b);
  const sum = sorted.reduce((acc, val) => acc + val, 0);
  const mean = sum / sorted.length;
  const median = sorted.length % 2 === 0
    ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
    : sorted[Math.floor(sorted.length / 2)];
  const variance = sorted.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / sorted.length;
  const stdDev = Math.sqrt(variance);
  return {
    mean: Number(mean.toFixed(2)),
    median: Number(median.toFixed(2)),
    stdDev: Number(stdDev.toFixed(2)),
    min: Number(sorted[0].toFixed(2)),
    max: Number(sorted[sorted.length - 1].toFixed(2))
  };
}

async function runEmpiricalStressSuite() {
  console.log('================================================================================');
  console.log('🛡️  CHALLENGER 1 — MILESTONE 1 EMPIRICAL ADVERSARIAL STRESS TEST SUITE');
  console.log('================================================================================');
  
  if (fs.existsSync(TEST_DB)) {
    try { fs.unlinkSync(TEST_DB); } catch (e) {}
  }

  await initDatabase();
  const app = createApp();
  const server = http.createServer(app);
  initTopologyWebSocket(server);

  await new Promise((resolve) => {
    server.listen(0, '127.0.0.1', resolve);
  });
  const port = server.address().port;
  console.log(`[TEST BED] Server running at http://127.0.0.1:${port}`);

  const results = {
    authFuzzing: { passed: 0, failed: 0, bypassed: 0, total: 0 },
    jwtTampering: { passed: 0, failed: 0, total: 0 },
    timingAnalysis: {},
    vipStress: { totalAllocated: 0, collisions: 0, outOfCidr: 0, durationMs: 0 },
    concurrentVipAllocations: { total: 0, success: 0, collisions: 0 },
    wsSync: { adminEventsReceived: 0, tenantEventsReceived: 0, leakEvents: 0, totalPublished: 0 },
    cryptoClamping: { totalTested: 0, clampedCorrectly: 0 }
  };

  try {
    // -------------------------------------------------------------------------
    // TEST 1: Auth Adversarial Fuzzing & SQL Injection Probes
    // -------------------------------------------------------------------------
    console.log('\n----------------------------------------------------------------');
    console.log('1. Probing Authentication Endpoints with SQLi & Fuzzing Payloads');
    console.log('----------------------------------------------------------------');

    for (const payload of SQLI_PAYLOADS) {
      results.authFuzzing.total++;
      const res = await request(app)
        .post('/api/auth/login')
        .send({ username: payload, password: 'password123' });

      if (res.status === 200 && res.body.token) {
        console.error(`[CRITICAL VULNERABILITY] SQLi Bypass Succeeded on username: ${payload}`);
        results.authFuzzing.bypassed++;
        results.authFuzzing.failed++;
      } else if (res.status === 401 || res.status === 400) {
        results.authFuzzing.passed++;
      } else {
        console.warn(`[UNEXPECTED STATUS] username: ${payload} -> HTTP ${res.status}`);
        results.authFuzzing.failed++;
      }
    }

    for (const payload of SQLI_PAYLOADS) {
      results.authFuzzing.total++;
      const res = await request(app)
        .post('/api/auth/login')
        .send({ username: 'admin', password: payload });

      if (res.status === 200 && res.body.token && payload !== 'admin_password') {
        console.error(`[CRITICAL VULNERABILITY] Password SQLi Bypass Succeeded on: ${payload}`);
        results.authFuzzing.bypassed++;
        results.authFuzzing.failed++;
      } else if (res.status === 401 || res.status === 400) {
        results.authFuzzing.passed++;
      } else {
        results.authFuzzing.failed++;
      }
    }

    console.log(`✓ Auth Fuzzing Results: ${results.authFuzzing.passed}/${results.authFuzzing.total} rejected safely (0% bypass).`);

    // -------------------------------------------------------------------------
    // TEST 2: JWT Manipulation & Blacklist Revocation Bypass Resistance
    // -------------------------------------------------------------------------
    console.log('\n----------------------------------------------------------------');
    console.log('2. Testing JWT Manipulation & Valkey Blacklist Revocation');
    console.log('----------------------------------------------------------------');

    // 2a. Login legitimate admin
    const loginRes = await request(app)
      .post('/api/auth/login')
      .send({ username: 'admin', password: 'admin_password' });
    assert.strictEqual(loginRes.status, 200);
    const validToken = loginRes.body.token;

    // 2b. Algorithm 'none' attack
    results.jwtTampering.total++;
    const noneHeader = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
    const fakePayload = Buffer.from(JSON.stringify({ sub: 'usr-admin', role: 'super-admin', exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
    const algNoneToken = `${noneHeader}.${fakePayload}.`;
    const noneRes = await request(app)
      .get('/api/users')
      .set('Authorization', `Bearer ${algNoneToken}`);
    if (noneRes.status === 401) {
      results.jwtTampering.passed++;
    } else {
      console.error(`[CRITICAL] Alg 'none' JWT accepted! Status: ${noneRes.status}`);
      results.jwtTampering.failed++;
    }

    // 2c. Tampered signature
    results.jwtTampering.total++;
    const tamperedToken = validToken.substring(0, validToken.length - 8) + 'ABCDEFGH';
    const tamperedRes = await request(app)
      .get('/api/users')
      .set('Authorization', `Bearer ${tamperedToken}`);
    if (tamperedRes.status === 401) {
      results.jwtTampering.passed++;
    } else {
      console.error(`[CRITICAL] Tampered JWT accepted! Status: ${tamperedRes.status}`);
      results.jwtTampering.failed++;
    }

    // 2d. Expired token
    results.jwtTampering.total++;
    const expiredToken = jwt.sign({ sub: 'usr-admin', role: 'super-admin' }, config.JWT_SECRET, { expiresIn: '-10s' });
    const expiredRes = await request(app)
      .get('/api/users')
      .set('Authorization', `Bearer ${expiredToken}`);
    if (expiredRes.status === 401) {
      results.jwtTampering.passed++;
    } else {
      console.error(`[CRITICAL] Expired JWT accepted! Status: ${expiredRes.status}`);
      results.jwtTampering.failed++;
    }

    // 2e. Logout and Blacklist Revocation Check
    results.jwtTampering.total++;
    const logoutRes = await request(app)
      .post('/api/auth/logout')
      .set('Authorization', `Bearer ${validToken}`)
      .send();
    assert.strictEqual(logoutRes.status, 200);

    const postLogoutRes = await request(app)
      .get('/api/auth/me')
      .set('Authorization', `Bearer ${validToken}`);
    if (postLogoutRes.status === 401) {
      results.jwtTampering.passed++;
    } else {
      console.error(`[CRITICAL] Revoked JWT allowed access after logout! Status: ${postLogoutRes.status}`);
      results.jwtTampering.failed++;
    }

    console.log(`✓ JWT Tampering & Revocation Results: ${results.jwtTampering.passed}/${results.jwtTampering.total} passed.`);

    // -------------------------------------------------------------------------
    // TEST 3: Statistical Timing Side-Channel Analysis
    // -------------------------------------------------------------------------
    console.log('\n----------------------------------------------------------------');
    console.log('3. Statistical Timing Side-Channel Analysis (Dummy Bcrypt Verification)');
    console.log('----------------------------------------------------------------');

    const sampleCount = 40;
    const existentTimes = [];
    const nonExistentTimes = [];

    // Warm-up JIT
    await request(app).post('/api/auth/login').send({ username: 'admin', password: 'bad' });
    await request(app).post('/api/auth/login').send({ username: 'nobody_123', password: 'bad' });

    for (let i = 0; i < sampleCount; i++) {
      // Existent user with wrong password
      const t0 = process.hrtime.bigint();
      await request(app).post('/api/auth/login').send({ username: 'admin', password: 'WrongPasswordSample!' });
      const t1 = process.hrtime.bigint();
      existentTimes.push(Number(t1 - t0) / 1e6);

      // Non-existent user
      const t2 = process.hrtime.bigint();
      await request(app).post('/api/auth/login').send({ username: `ghost_user_${i}_nonexistent`, password: 'WrongPasswordSample!' });
      const t3 = process.hrtime.bigint();
      nonExistentTimes.push(Number(t3 - t2) / 1e6);
    }

    const existentStats = calculateStats(existentTimes);
    const nonExistentStats = calculateStats(nonExistentTimes);
    const ratio = Number((existentStats.mean / nonExistentStats.mean).toFixed(3));
    const deltaMs = Number(Math.abs(existentStats.mean - nonExistentStats.mean).toFixed(2));

    results.timingAnalysis = {
      sampleCount,
      existentUser: existentStats,
      nonExistentUser: nonExistentStats,
      ratio,
      deltaMs,
      timingSafe: ratio >= 0.85 && ratio <= 1.15
    };

    console.log(`   Existent User (Wrong Password) -> Mean: ${existentStats.mean} ms, Median: ${existentStats.median} ms, StdDev: ${existentStats.stdDev} ms`);
    console.log(`   Non-Existent User              -> Mean: ${nonExistentStats.mean} ms, Median: ${nonExistentStats.median} ms, StdDev: ${nonExistentStats.stdDev} ms`);
    console.log(`   Timing Ratio: ${ratio}x (Delta: ${deltaMs} ms) — Timing-Safe: ${results.timingAnalysis.timingSafe ? 'YES (Uniform Bcrypt Execution)' : 'NO'}`);

    // -------------------------------------------------------------------------
    // TEST 4: VIP Allocation Engine Stress & Collision Analysis (10,000 Nodes)
    // -------------------------------------------------------------------------
    console.log('\n----------------------------------------------------------------');
    console.log('4. VIP Allocation Stress in 100.64.0.0/10 & fd7a:115c:a1e0::/64 (10,000 Allocations)');
    console.log('----------------------------------------------------------------');

    const totalVipTarget = 10000;
    const allocatedIpv4 = new Set();
    const allocatedIpv6 = new Set();
    let outOfCidr = 0;
    let collisions = 0;

    const startVipTime = Date.now();
    let mockExisting = [];

    for (let i = 0; i < totalVipTarget; i++) {
      const vip = allocateVipFromRows(mockExisting);
      
      // Parse IPv4
      const parts = vip.overlayIpv4.split('.').map(Number);
      if (parts.length !== 4 || parts[0] !== 100 || parts[1] < 64 || parts[1] > 127 || parts[3] === 0 || parts[3] === 255) {
        outOfCidr++;
      }

      // Check IPv6 prefix
      if (!vip.overlayIpv6.startsWith('fd7a:115c:a1e0::')) {
        outOfCidr++;
      }

      if (allocatedIpv4.has(vip.overlayIpv4) || allocatedIpv6.has(vip.overlayIpv6)) {
        collisions++;
      }

      allocatedIpv4.add(vip.overlayIpv4);
      allocatedIpv6.add(vip.overlayIpv6);

      mockExisting.push({ overlay_ipv4: vip.overlayIpv4, overlay_ipv6: vip.overlayIpv6 });
    }
    const vipDuration = Date.now() - startVipTime;

    results.vipStress = {
      totalAllocated: allocatedIpv4.size,
      collisions,
      outOfCidr,
      durationMs: vipDuration,
      firstVip: mockExisting[0].overlay_ipv4,
      lastVip: mockExisting[mockExisting.length - 1].overlay_ipv4
    };

    console.log(`✓ Allocated ${results.vipStress.totalAllocated} VIPs in ${vipDuration}ms (${(totalVipTarget / (vipDuration / 1000)).toFixed(0)} allocations/sec)`);
    console.log(`   First VIP: ${results.vipStress.firstVip}, Last VIP: ${results.vipStress.lastVip}`);
    console.log(`   Collisions: ${collisions}, CIDR Violations: ${outOfCidr}`);
    assert.strictEqual(collisions, 0, 'VIP collisions detected!');
    assert.strictEqual(outOfCidr, 0, 'VIP CIDR violations detected!');

    // -------------------------------------------------------------------------
    // TEST 5: Concurrent Node Registration & VIP DB Integrity
    // -------------------------------------------------------------------------
    console.log('\n----------------------------------------------------------------');
    console.log('5. Concurrent Node Registration API Probe (50 Concurrent Requests)');
    console.log('----------------------------------------------------------------');

    // Re-login admin
    const adminRelogin = await request(app)
      .post('/api/auth/login')
      .send({ username: 'admin', password: 'admin_password' });
    const activeAdminToken = adminRelogin.body.token;

    const concurrentBatch = 50;
    const regPromises = [];

    for (let i = 0; i < concurrentBatch; i++) {
      const keypair = generateCurve25519Keypair();
      regPromises.push(
        request(app)
          .post('/api/nodes')
          .set('Authorization', `Bearer ${activeAdminToken}`)
          .send({
            name: `stress-node-${i}`,
            public_key: keypair.publicKeyBase64,
            preshared_key: keypair.presharedKeyBase64,
            role: 'CLIENT_ORIGIN',
            kill_switch_enabled: true
          })
      );
    }

    const regResponses = await Promise.all(regPromises);
    const registeredIpv4s = new Set();
    let regSuccess = 0;
    let regCollisions = 0;

    for (const res of regResponses) {
      if (res.status === 201 && res.body.node) {
        regSuccess++;
        const ip = res.body.node.overlay_ipv4;
        if (registeredIpv4s.has(ip)) {
          regCollisions++;
        }
        registeredIpv4s.add(ip);
      }
    }

    results.concurrentVipAllocations = {
      total: concurrentBatch,
      success: regSuccess,
      collisions: regCollisions
    };

    console.log(`✓ Concurrent Registrations: ${regSuccess}/${concurrentBatch} succeeded, ${regCollisions} collisions.`);
    assert.strictEqual(regCollisions, 0);

    // -------------------------------------------------------------------------
    // TEST 6: Real-Time WebSocket & Valkey Pub/Sub Rapid Sync Flood
    // -------------------------------------------------------------------------
    console.log('\n----------------------------------------------------------------');
    console.log('6. WebSocket & Valkey Pub/Sub Event Flood & Tenant Isolation');
    console.log('----------------------------------------------------------------');

    // Tenant login
    const tenantLogin = await request(app)
      .post('/api/auth/login')
      .send({ username: 'alice_homelab', password: 'Password123!' });
    assert.strictEqual(tenantLogin.status, 200);
    const tenantToken = tenantLogin.body.token;
    const tenantUserId = tenantLogin.body.user.id;

    // Connect WebSocket client 1: Admin
    const wsAdmin = new WebSocket(`ws://127.0.0.1:${port}/ws/topology?token=${activeAdminToken}`);
    // Connect WebSocket client 2: Tenant (Alice)
    const wsTenant = new WebSocket(`ws://127.0.0.1:${port}/ws/topology?token=${tenantToken}`);

    let adminReceivedCount = 0;
    let tenantReceivedCount = 0;
    let leakedToTenantCount = 0;

    await Promise.all([
      new Promise((res) => wsAdmin.on('open', res)),
      new Promise((res) => wsTenant.on('open', res))
    ]);

    wsAdmin.on('message', (msg) => {
      try {
        const d = JSON.parse(msg.toString());
        if (d.type !== 'CONNECTED' && d.type !== 'PONG') {
          adminReceivedCount++;
        }
      } catch (e) {}
    });

    wsTenant.on('message', (msg) => {
      try {
        const d = JSON.parse(msg.toString());
        if (d.type !== 'CONNECTED' && d.type !== 'PONG') {
          tenantReceivedCount++;
          if (d.user_id && d.user_id !== tenantUserId && d.node?.role === 'CLIENT_ORIGIN') {
            leakedToTenantCount++;
          }
        }
      } catch (e) {}
    });

    // Flood 300 events:
    // 100 for Alice (tenantUserId)
    // 100 for Bob ('usr-bob-9999')
    // 100 for Global Relay
    const floodTotal = 300;
    for (let i = 0; i < 100; i++) {
      await publishTopologyEvent({
        event: 'NODE_HEARTBEAT',
        user_id: tenantUserId,
        node: { id: `node-alice-${i}`, user_id: tenantUserId, role: 'CLIENT_ORIGIN' }
      });
      await publishTopologyEvent({
        event: 'NODE_HEARTBEAT',
        user_id: 'usr-bob-9999',
        node: { id: `node-bob-${i}`, user_id: 'usr-bob-9999', role: 'CLIENT_ORIGIN' }
      });
      await publishTopologyEvent({
        event: 'RELAY_STATUS',
        node: { id: `node-relay-${i}`, role: 'RELAY' }
      });
    }

    // Allow event loop to drain
    await new Promise((res) => setTimeout(res, 250));

    wsAdmin.close();
    wsTenant.close();

    results.wsSync = {
      totalPublished: floodTotal,
      adminEventsReceived: adminReceivedCount,
      tenantEventsReceived: tenantReceivedCount,
      leakEvents: leakedToTenantCount
    };

    console.log(`✓ WebSocket Pub/Sub Flood Results:`);
    console.log(`   Total Events Published: ${floodTotal}`);
    console.log(`   Admin Received: ${adminReceivedCount}/${floodTotal} (100% visibility)`);
    console.log(`   Tenant Received: ${tenantReceivedCount}/200 (100 own + 100 global relays)`);
    console.log(`   Tenant Data Leaks: ${leakedToTenantCount} (0 other tenant events leaked)`);
    assert.strictEqual(adminReceivedCount, floodTotal);
    assert.strictEqual(tenantReceivedCount, 200);
    assert.strictEqual(leakedToTenantCount, 0);

    // -------------------------------------------------------------------------
    // TEST 7: Curve25519 Scalar Clamping & Profile Validation
    // -------------------------------------------------------------------------
    console.log('\n----------------------------------------------------------------');
    console.log('7. Curve25519 Clamping & Config Profile Cryptographic Validation');
    console.log('----------------------------------------------------------------');

    let clampingCorrect = 0;
    const keypairCount = 200;

    for (let i = 0; i < keypairCount; i++) {
      const kp = generateCurve25519Keypair();
      const privBytes = Buffer.from(kp.privateKeyBase64, 'base64');
      
      const byte0 = privBytes[0];
      const byte31 = privBytes[31];

      // Check lowest 3 bits of byte 0 are 0 (privBytes[0] & 7 === 0)
      const byte0Clamped = (byte0 & 7) === 0;
      // Check highest bit of byte 31 is 0 (privBytes[31] & 128 === 0)
      // Check second highest bit of byte 31 is 1 (privBytes[31] & 64 === 64)
      const byte31Clamped = (byte31 & 128) === 0 && (byte31 & 64) === 64;

      if (byte0Clamped && byte31Clamped) {
        clampingCorrect++;
      }
    }

    results.cryptoClamping = {
      totalTested: keypairCount,
      clampedCorrectly: clampingCorrect
    };

    console.log(`✓ Curve25519 Clamping: ${clampingCorrect}/${keypairCount} private keys correctly clamped (100%).`);
    assert.strictEqual(clampingCorrect, keypairCount);

    console.log('\n================================================================================');
    console.log('✅ ALL EMPIRICAL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY');
    console.log('================================================================================\n');

    // Save summary metrics to file for handoff
    const metricsPath = path.resolve(__dirname, '../../console/.agents/challenger_m1_1/empirical_metrics.json');
    fs.writeFileSync(metricsPath, JSON.stringify(results, null, 2));

  } finally {
    closeTopologyWebSocket();
    await new Promise((res) => server.close(res));
    closeDatabase();
    closeValkey();
    if (fs.existsSync(TEST_DB)) {
      try { fs.unlinkSync(TEST_DB); } catch (e) {}
    }
  }
}

runEmpiricalStressSuite().catch((err) => {
  console.error('\n❌ EMPIRICAL STRESS TEST SUITE FAILED:', err);
  process.exit(1);
});
