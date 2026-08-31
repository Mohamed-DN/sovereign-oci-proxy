#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Version & Update Discovery Utility
# Location: scripts/legacy_refactor/check-version.sh
# ==============================================================================
set -euo pipefail

CURRENT_VERSION="4.0.0"
REPO="Mohamed-DN/sovereign-oci-proxy"

OUTPUT_JSON=false
if [[ "${1:-}" == "--json" ]]; then
    OUTPUT_JSON=true
fi

# Fetch latest release from GitHub API with fallback
LATEST_VERSION="$(curl -s -m 5 "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/' | tr -d 'v' || echo "")"

if [[ -z "$LATEST_VERSION" ]]; then
    LATEST_VERSION="$CURRENT_VERSION"
    UPDATE_AVAILABLE=false
else
    if [[ "$CURRENT_VERSION" != "$LATEST_VERSION" ]]; then
        UPDATE_AVAILABLE=true
    else
        UPDATE_AVAILABLE=false
    fi
fi

if [[ "$OUTPUT_JSON" == "true" ]]; then
    cat << EOF
{
  "current_version": "${CURRENT_VERSION}",
  "latest_version": "${LATEST_VERSION}",
  "update_available": ${UPDATE_AVAILABLE},
  "repository": "${REPO}"
}
EOF
else
    echo "Sovereign Proxy Version: ${CURRENT_VERSION}"
    echo "Latest Upstream Version: ${LATEST_VERSION}"
    if [[ "$UPDATE_AVAILABLE" == "true" ]]; then
        echo "[!] Update available: ${CURRENT_VERSION} -> ${LATEST_VERSION}"
    else
        echo "[✓] System is up to date."
    fi
fi
