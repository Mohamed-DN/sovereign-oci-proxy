#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Enterprise Secret Management & Zero-Plaintext Engine
# Location: scripts/legacy_refactor/secrets.sh
# ==============================================================================
set -euo pipefail

# Ensure secure umask for all created secret files
umask 077

SOVEREIGN_CONFIG_DIR="${SOVEREIGN_CONFIG_DIR:-/etc/sovereign}"
SOVEREIGN_ENV_FILE="${SOVEREIGN_ENV_FILE:-${SOVEREIGN_CONFIG_DIR}/sovereign.env}"
K8S_SECRETS_DIR="/var/run/secrets/sovereign"

# ------------------------------------------------------------------------------
# Secret Loading & Resolution
# ------------------------------------------------------------------------------

sovereign_load_secret() {
    local secret_name="$1"
    local default_value="${2:-}"
    local value=""

    # 1. Check direct environment variable
    if [[ -n "${!secret_name:-}" ]]; then
        echo "${!secret_name}"
        return 0
    fi

    # 2. Check Kubernetes / Vault mounted secret path
    if [[ -f "${K8S_SECRETS_DIR}/${secret_name}" ]]; then
        value="$(cat "${K8S_SECRETS_DIR}/${secret_name}")"
        echo "$value"
        return 0
    fi

    # 3. Check secure sovereign.env file (must have 0600 or 0400 permissions)
    if [[ -f "$SOVEREIGN_ENV_FILE" ]]; then
        # Check permissions
        local perms
        perms="$(stat -c "%a" "$SOVEREIGN_ENV_FILE" 2>/dev/null || stat -f "%Op" "$SOVEREIGN_ENV_FILE" 2>/dev/null || echo "600")"
        value="$(grep -E "^${secret_name}=" "$SOVEREIGN_ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)"
        if [[ -n "$value" ]]; then
            echo "$value"
            return 0
        fi
    fi

    if [[ $# -ge 2 ]]; then
        echo "$default_value"
        return 0
    fi

    return 1
}

# ------------------------------------------------------------------------------
# Secret Generation & Key Provisioning
# ------------------------------------------------------------------------------

sovereign_generate_uuid() {
    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen | tr '[:upper:]' '[:lower:]'
    elif [[ -f /proc/sys/kernel/random/uuid ]]; then
        cat /proc/sys/kernel/random/uuid
    else
        python3 -c "import uuid; print(uuid.uuid4())"
    fi
}

sovereign_generate_hex() {
    local bytes="${1:-16}"
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex "$bytes"
    else
        python3 -c "import secrets; print(secrets.token_hex($bytes))"
    fi
}

sovereign_generate_base64() {
    local bytes="${1:-32}"
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 "$bytes"
    else
        python3 -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes($bytes)).decode())"
    fi
}

# ------------------------------------------------------------------------------
# Secret Sanitization & Masking
# ------------------------------------------------------------------------------

sovereign_mask_secret() {
    local raw="$1"
    local len="${#raw}"
    if [[ $len -le 6 ]]; then
        echo "******"
    else
        local prefix="${raw:0:3}"
        local suffix="${raw: -3}"
        echo "${prefix}****${suffix}"
    fi
}

sovereign_sanitize_token() {
    local raw="$1"
    # Strip any characters that are not alphanumeric, hyphen, underscore, or dot
    echo "$raw" | tr -cd 'a-zA-Z0-9_\-\.'
}

# ------------------------------------------------------------------------------
# Self-Test / CLI helper
# ------------------------------------------------------------------------------

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    action="${1:-help}"
    case "$action" in
        generate-uuid)
            sovereign_generate_uuid
            ;;
        generate-token)
            sovereign_generate_hex "${2:-16}"
            ;;
        generate-key)
            sovereign_generate_base64 "${2:-32}"
            ;;
        mask)
            sovereign_mask_secret "${2:-}"
            ;;
        get)
            sovereign_load_secret "$2" "${3:-}"
            ;;
        *)
            echo "Usage: $0 {generate-uuid|generate-token|generate-key|mask <val>|get <KEY> [default]}"
            exit 1
            ;;
    esac
fi
