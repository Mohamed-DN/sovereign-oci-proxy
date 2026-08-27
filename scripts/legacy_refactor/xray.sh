#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Core Ingress & Xray Deployment Engine
# Location: scripts/legacy_refactor/xray.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SECRETS_HELPER="${SCRIPT_DIR}/secrets.sh"

source "${SECRETS_HELPER}"

XRAY_CONF_TEMPLATE="${PROJECT_ROOT}/configs/xray/config.json.template"
XRAY_CONF_OUTPUT="${SOVEREIGN_XRAY_CONF_OUTPUT:-/etc/xray/config.json}"
DB_PATH="${SOVEREIGN_DB_PATH:-/etc/x-ui/x-ui.db}"

log_info() { echo -e "\033[0;34m[+] INFO:\033[0m $1"; }
log_ok() { echo -e "\033[0;32m[✓] SUCCESS:\033[0m $1"; }
log_err() { echo -e "\033[0;31m[✗] ERROR:\033[0m $1" >&2; }

provision_xray_config() {
    log_info "Provisioning hardened Xray VLESS + REALITY configuration..."

    local client_uuid
    client_uuid="$(sovereign_load_secret CLIENT_UUID "$(sovereign_generate_uuid)")"

    local client_email
    client_email="$(sovereign_load_secret CLIENT_EMAIL "user@sovereign.local")"

    local reality_priv
    reality_priv="$(sovereign_load_secret REALITY_PRIVATE_KEY "$(sovereign_generate_base64 32)")"

    local reality_short_id
    reality_short_id="$(sovereign_load_secret REALITY_SHORT_ID "$(sovereign_generate_hex 8)")"

    local warp_priv
    warp_priv="$(sovereign_load_secret WARP_PRIVATE_KEY "$(sovereign_generate_base64 32)")"

    local warp_pub
    warp_pub="$(sovereign_load_secret WARP_PUBLIC_KEY "$(sovereign_generate_base64 32)")"

    local warp_endpoint
    warp_endpoint="$(sovereign_load_secret WARP_ENDPOINT "engage.cloudflareclient.com:2408")"

    mkdir -p "$(dirname "$XRAY_CONF_OUTPUT")"

    # Safely substitute placeholders using Python to avoid sed delimiter corruption
    python3 -c "
import json

with open('${XRAY_CONF_TEMPLATE}', 'r') as f:
    content = f.read()

content = content.replace('{{CLIENT_UUID}}', '${client_uuid}')
content = content.replace('{{CLIENT_EMAIL}}', '${client_email}')
content = content.replace('{{REALITY_PRIVATE_KEY}}', '${reality_priv}')
content = content.replace('{{REALITY_SHORT_ID}}', '${reality_short_id}')
content = content.replace('{{WARP_PRIVATE_KEY}}', '${warp_priv}')
content = content.replace('{{WARP_PUBLIC_KEY}}', '${warp_pub}')
content = content.replace('{{WARP_ENDPOINT}}', '${warp_endpoint}')

# Validate JSON
data = json.loads(content)

with open('${XRAY_CONF_OUTPUT}', 'w') as f:
    json.dump(data, f, indent=2)
"

    log_ok "Hardened Xray configuration rendered and validated at ${XRAY_CONF_OUTPUT}"
}

patch_database_rules() {
    log_info "Patching routing rules in database for private network support..."
    if [[ -f "$DB_PATH" ]]; then
        python3 "${SCRIPT_DIR}/xray-routing-fix.py" --db "$DB_PATH" || true
    fi
}

main() {
    provision_xray_config
    patch_database_rules
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
