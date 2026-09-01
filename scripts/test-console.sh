#!/usr/bin/env bash
# ==============================================================================
# NeroNet Sovereign Mesh Enterprise Management Console - Test Suite Runner
# 
# Executes all test tiers:
# 1. Backend Unit & Integration Tests (node --test)
# 2. Python 5-Tier E2E Test Suite (console_runner.py)
# 3. Node.js E2E Test Suite (test_console_suite.js)
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONSOLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$CONSOLE_DIR/.." && pwd)"

echo "======================================================================"
echo "    NERONET CONSOLE — FULL TEST SUITE EXECUTION                       "
echo "======================================================================"

# 1. Backend Unit & Integration Tests
echo ""
echo "----------------------------------------------------------------------"
echo "[1/3] Running Backend Unit & Integration Test Suite (node:test)..."
echo "----------------------------------------------------------------------"
(
    cd "$CONSOLE_DIR/backend"
    npm test
)

# 2. Python 5-Tier Opaque-Box E2E Tests
echo ""
echo "----------------------------------------------------------------------"
echo "[2/3] Running Python 5-Tier Opaque-Box E2E Test Suite..."
echo "----------------------------------------------------------------------"
(
    cd "$ROOT_DIR"
    python3 tests/e2e/console_runner.py --tier all --format text
)

# 3. Node.js E2E Test Suite
if [ -f "$ROOT_DIR/tests/e2e/test_console_suite.js" ]; then
    echo ""
    echo "----------------------------------------------------------------------"
    echo "[3/3] Running Node.js E2E Test Suite..."
    echo "----------------------------------------------------------------------"
    (
        cd "$ROOT_DIR"
        node tests/e2e/test_console_suite.js
    )
fi

echo ""
echo "======================================================================"
echo "    [✔] ALL CONSOLE TEST SUITES COMPLETED SUCCESSFULLY (100% PASS)"
echo "======================================================================"
