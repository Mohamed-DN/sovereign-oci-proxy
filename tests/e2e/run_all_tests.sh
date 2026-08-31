#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

echo "================================================================================"
echo "Sovereign Proxy v4.0 - Executing Complete 4-Tier E2E Test Suite"
echo "================================================================================"

python3 "${PROJECT_ROOT}/tests/e2e/runner.py" --tier all --format text "$@"

EXIT_CODE=$?

if [ ${EXIT_CODE} -eq 0 ]; then
  echo ""
  echo ">>> [SUCCESS] 4-Tier E2E Test Suite verified with Exit Code 0."
  exit 0
else
  echo ""
  echo ">>> [FAILURE] E2E Test Suite encountered failures (Exit Code: ${EXIT_CODE})."
  exit ${EXIT_CODE}
fi
