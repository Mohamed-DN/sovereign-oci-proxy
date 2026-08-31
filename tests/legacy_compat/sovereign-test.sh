#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Legacy Compatibility Wrapper for sovereign-test.sh
# Location: tests/legacy_compat/sovereign-test.sh
# ==============================================================================
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/test_20point.sh" "$@"
