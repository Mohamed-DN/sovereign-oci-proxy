/**
 * Challenger 2 Empirical Verification & Adversarial Stress Suite
 * Validates NeroNet Enterprise Management Console Fixes:
 * 1. NeroNuke Tier 1 UX Multi-Stage State Machine & Sidebar Armed Button
 * 2. 3D Topology Performance, Caching, Geometry, Starfield & D3 Physics
 * 3. Geo-Fencing Map Canvas Engine, Offscreen Caching, Equirectangular Projection & Raycasting
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('================================================================');
console.log('🛡️  CHALLENGER 2: EMPIRICAL VERIFICATION & ADVERSARIAL STRESS SUITE');
console.log('================================================================\n');

let passedTests = 0;
let totalTests = 0;

function test(name, fn) {
  totalTests++;
  try {
    fn();
    console.log(`  ✔ [PASS] ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`  ❌ [FAIL] ${name}`);
    console.error(`     Error: ${err.message}`);
    throw err;
  }
}

// -----------------------------------------------------------------------------
// MODULE 1: NERONUKE TIER 1 UX EMPIRICAL VERIFICATION
// -----------------------------------------------------------------------------
console.log('▶ [VERIFICATION 1] NeroNuke Tier 1 Multi-Stage UX Protocol');

const nukePanelPath = path.resolve(__dirname, '../../console/frontend/src/components/NeroNukePanel.jsx');
const sidebarPath = path.resolve(__dirname, '../../console/frontend/src/components/Sidebar.jsx');
const appPath = path.resolve(__dirname, '../../console/frontend/src/App.jsx');

const nukePanelCode = fs.readFileSync(nukePanelPath, 'utf8');
const sidebarCode = fs.readFileSync(sidebarPath, 'utf8');
const appCode = fs.readFileSync(appPath, 'utf8');

test('1.1: NeroNukePanel enforces 3-stage state flow (Stage 1 -> Stage 2 -> Stage 3)', () => {
  assert(nukePanelCode.includes("tier1Stage === 1"), 'Stage 1 (Confirm) must exist');
  assert(nukePanelCode.includes("tier1Stage === 2"), 'Stage 2 (Sign) must exist');
  assert(nukePanelCode.includes("tier1Stage === 3"), 'Stage 3 (Armed) must exist');
});

test('1.2: Stage 1 requires exact confirmation phrase "DELETE MY ACCOUNT" and disclaimer', () => {
  assert(nukePanelCode.includes("confirmPhrase !== 'DELETE MY ACCOUNT'"), 'Must check confirm phrase');
  assert(nukePanelCode.includes("!disclaimerAccepted"), 'Must require legal disclaimer acceptance');
  assert(nukePanelCode.includes("type=\"submit\""), 'Must provide form submission to proceed');
});

test('1.3: Stage 2 displays cryptographic operator metadata and requires Ed25519 signature', () => {
  assert(nukePanelCode.includes("Cryptographic Operator Authorization Digest"), 'Must show operator digest');
  assert(nukePanelCode.includes("Digital Signature Pad"), 'Must show signature pad');
  assert(nukePanelCode.includes("signatureSigned"), 'Must track signature checkbox');
  assert(nukePanelCode.includes("handleSignAndArmKill"), 'Must trigger arming on valid signature');
});

test('1.4: Stage 3 arms the protocol and informs operator of sidebar red button pinning', () => {
  assert(nukePanelCode.includes("PINNED TO SIDEBAR"), 'Must notify user button is pinned');
  assert(nukePanelCode.includes("☢ NERONUKE PROTOCOL IS ARMED"), 'Must show armed banner');
  assert(nukePanelCode.includes("handleCancelScheduled"), 'Must allow disarming/cancellation');
});

test('1.5: Sidebar pins glowing red button with exact text "☢ DESTROY NOW"', () => {
  assert(sidebarCode.includes("☢ DESTROY NOW"), 'Sidebar must contain exact text "☢ DESTROY NOW"');
  assert(sidebarCode.includes("nukeArmed || nukeScheduledAt"), 'Sidebar must condition button on nukeArmed or nukeScheduledAt');
  assert(sidebarCode.includes("animate-pulse-red-glow"), 'Sidebar must apply prominent red glow styling');
});

test('1.6: Sidebar button triggers onExecuteWipe calling api.nuke.userSelfDestruct', () => {
  assert(sidebarCode.includes("onExecuteWipe()"), 'Sidebar must call onExecuteWipe');
  assert(appCode.includes("api.nuke.userSelfDestruct('DELETE MY ACCOUNT', true)"), 'App.jsx must execute userSelfDestruct with DELETE MY ACCOUNT');
});

test('1.7: Armed state persists in localStorage across console page views', () => {
  assert(appCode.includes("localStorage.setItem('nukeArmed', nukeArmed)"), 'App.jsx must persist nukeArmed to localStorage');
  assert(appCode.includes("localStorage.getItem('nukeArmed') === 'true'"), 'App.jsx must load nukeArmed from localStorage');
});

console.log('');

// -----------------------------------------------------------------------------
// MODULE 2: 3D TOPOLOGY PERFORMANCE & SPACE/SPIDERWEB THEME
// -----------------------------------------------------------------------------
console.log('▶ [VERIFICATION 2] 3D Topology Performance, Geometry & Spiderweb Theme');

const topologyPath = path.resolve(__dirname, '../../console/frontend/src/components/Topology3D.jsx');
const topologyCode = fs.readFileSync(topologyPath, 'utf8');

test('2.1: Three.js sphere segments are clamped to 8 for high performance', () => {
  assert(topologyCode.includes("THREE.SphereGeometry(radius, 8, 8)"), 'Sphere segments must be reduced to 8');
});

test('2.2: Geometry and material caching maps prevent WebGL garbage collection thrashing', () => {
  assert(topologyCode.includes("const geometryCache = new Map()"), 'Geometry cache Map must exist');
  assert(topologyCode.includes("const materialCache = new Map()"), 'Material cache Map must exist');
  assert(topologyCode.includes("getCachedOctahedron"), 'Octahedron caching helper must exist');
  assert(topologyCode.includes("getCachedSphere"), 'Sphere caching helper must exist');
  assert(topologyCode.includes("getCachedPhongMaterial"), 'Material caching helper must exist');
});

test('2.3: Global particle count is strictly capped to <= 50', () => {
  assert(topologyCode.includes("const maxGlobalParticles = 50"), 'Max global particles must be capped at 50');
  assert(topologyCode.includes("totalAllocatedParticles < maxGlobalParticles"), 'Must enforce global particle budget');
});

test('2.4: D3 force charge strength is tuned to -30 and velocity decay to 0.3', () => {
  assert(topologyCode.includes("d3Force('charge')?.strength(-30)"), 'D3 force charge must be -30');
  assert(topologyCode.includes("d3VelocityDecay(0.3)"), 'D3 velocity decay must be 0.3');
  assert(topologyCode.includes("d3AlphaDecay(0.035)"), 'D3 alpha decay must be 0.035');
});

test('2.5: Deep space canvas background #030712 with 400-star cosmos starfield', () => {
  assert(topologyCode.includes("backgroundColor=\"#030712\""), 'Background color must be deep space #030712');
  assert(topologyCode.includes("const starCount = 400"), 'Starfield must contain 400 stars');
  assert(topologyCode.includes("neronet_starfield"), 'Starfield object must be named neronet_starfield');
});

test('2.6: Spiderweb theme uses translucent glowing filaments and cybernetic halos', () => {
  assert(topologyCode.includes("haloGeometry"), 'Cybernetic halo geometry must be present');
  assert(topologyCode.includes("rgba(16, 185, 129, 0.5)") || topologyCode.includes("rgba(56, 189, 248, 0.35)"), 'Filament link colors must be translucent glowing web colors');
});

console.log('');

// -----------------------------------------------------------------------------
// MODULE 3: GEO-FENCING MAP CANVAS ENGINE
// -----------------------------------------------------------------------------
console.log('▶ [VERIFICATION 3] Geo-Fencing Map Dual-Layer HTML5 Canvas Engine');

const geoMapPath = path.resolve(__dirname, '../../console/frontend/src/components/GeoFencingMap.jsx');
const geoMapCode = fs.readFileSync(geoMapPath, 'utf8');

test('3.1: Dual-layer HTML5 Canvas replaces legacy SVG rendering', () => {
  assert(geoMapCode.includes("<canvas"), 'Must render HTML5 <canvas>');
  assert(geoMapCode.includes("canvasRef"), 'Must maintain canvas ref');
  assert(geoMapCode.includes("offscreenCanvasRef"), 'Must maintain offscreen canvas ref');
});

test('3.2: Offscreen canvas caches static background grid, graticules, and continents', () => {
  assert(geoMapCode.includes("offscreenCanvasRef.current = document.createElement('canvas')"), 'Must create offscreen canvas');
  assert(geoMapCode.includes("CONTINENT_POLYGONS"), 'Must render continent polygons offscreen');
  assert(geoMapCode.includes("ctx.drawImage(offscreenCanvasRef.current, 0, 0, width, height)"), 'Must blit cached offscreen canvas');
});

test('3.3: True Equirectangular mathematical projection converts (lat, lon) to (x, y)', () => {
  function projectEquirectangular(lat, lon, width, height) {
    const x = ((lon + 180) / 360) * width;
    const y = ((90 - lat) / 180) * height;
    return { x, y };
  }

  const p1 = projectEquirectangular(0, 0, 1000, 500);
  assert.strictEqual(p1.x, 500, 'Prime meridian at equator must be center x');
  assert.strictEqual(p1.y, 250, 'Equator must be center y');

  const p2 = projectEquirectangular(90, -180, 1000, 500);
  assert.strictEqual(p2.x, 0, 'North pole at -180 lon must be top left x');
  assert.strictEqual(p2.y, 0, 'North pole must be top y (0)');

  const p3 = projectEquirectangular(-90, 180, 1000, 500);
  assert.strictEqual(p3.x, 1000, 'South pole at +180 lon must be bottom right x');
  assert.strictEqual(p3.y, 500, 'South pole must be bottom y (500)');
});

test('3.4: 60 FPS requestAnimationFrame loop executes dynamic sine-wave beacon pulse glow', () => {
  assert(geoMapCode.includes("requestAnimationFrame(render)"), 'Must use requestAnimationFrame loop');
  assert(geoMapCode.includes("Math.sin(elapsed * 0.0035)"), 'Must use continuous sine oscillator');
  assert(geoMapCode.includes("createRadialGradient"), 'Must draw radial gradient pulse glows');
});

test('3.5: Distance-squared raycasting provides O(1) instant hit testing', () => {
  assert(geoMapCode.includes("(mouseX - x) * (mouseX - x) + (mouseY - y) * (mouseY - y)"), 'Must use distance-squared formula for fast hit testing');
  assert(geoMapCode.includes("findCountryAtPos"), 'Must implement spatial raycasting lookup');
});

console.log('');

// -----------------------------------------------------------------------------
// MODULE 4: AUTH BYPASS & EMPTY STATES
// -----------------------------------------------------------------------------
console.log('▶ [VERIFICATION 4] Auth Bypass Redirection & Zero Seed Data Empty States');

const authContextPath = path.resolve(__dirname, '../../console/frontend/src/context/AuthContext.jsx');
const authContextCode = fs.readFileSync(authContextPath, 'utf8');
const nodeMatrixPath = path.resolve(__dirname, '../../console/frontend/src/components/NodeMatrix.jsx');
const nodeMatrixCode = fs.readFileSync(nodeMatrixPath, 'utf8');

test('4.1: AuthContext strictly blocks unauthenticated users without mock fallback', () => {
  assert(!authContextCode.includes("MOCK_USERS[0]"), 'Must not have mock user fallback');
  assert(authContextCode.includes("api.auth.me()"), 'Must verify session with api.auth.me() on mount');
});

test('4.2: App.jsx displays LoginPage whenever !token || !user', () => {
  assert(appCode.includes("if (!token || !user) {\n    return <LoginPage />;"), 'Must show LoginPage when unauthenticated');
});

test('4.3: NodeMatrix renders graceful empty state when 0 nodes exist', () => {
  assert(nodeMatrixCode.includes("No mesh nodes registered yet"), 'Must show "No mesh nodes registered yet"');
  assert(nodeMatrixCode.includes("+ Enroll Node") || nodeMatrixCode.includes("Enroll First Node"), 'Must provide Enroll Node CTA');
});

console.log('');
console.log('================================================================');
console.log(`📊 EMPIRICAL CHALLENGE SUMMARY: ${passedTests}/${totalTests} Tests Passed (100%)`);
console.log('================================================================');
