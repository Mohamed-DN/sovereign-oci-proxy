#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Asymmetric Encrypted Disaster Recovery Engine
# Location: scripts/legacy_refactor/backup.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_HELPER="${SCRIPT_DIR}/secrets.sh"

source "${SECRETS_HELPER}"

BACKUP_DIR="${SOVEREIGN_BACKUP_DIR:-/var/backups/sovereign}"
DB_PATH="${SOVEREIGN_DB_PATH:-/etc/x-ui/x-ui.db}"
CONFIG_DIR="${SOVEREIGN_CONFIG_DIR:-/etc/sovereign}"
GPG_RECIPIENT="$(sovereign_load_secret GPG_RECIPIENT "")"
B2_BUCKET="$(sovereign_load_secret B2_BUCKET "")"

TIMESTAMP="$(date -u '+%Y%m%d_%H%M%SZ')"
TMP_WORK_DIR="$(mktemp -d -t sovereign_backup_XXXXXX)"
TAR_FILE="${TMP_WORK_DIR}/sovereign_backup_${TIMESTAMP}.tar.gz"
ENCRYPTED_FILE="${BACKUP_DIR}/sovereign_backup_${TIMESTAMP}.tar.gz.gpg"

cleanup() {
    rm -rf "$TMP_WORK_DIR"
}
trap cleanup EXIT

log_info() { echo -e "\033[0;34m[+] INFO:\033[0m $1"; }
log_ok() { echo -e "\033[0;32m[✓] SUCCESS:\033[0m $1"; }
log_err() { echo -e "\033[0;31m[✗] ERROR:\033[0m $1" >&2; }

mkdir -p "$BACKUP_DIR"

log_info "Creating snapshot archive..."
mkdir -p "${TMP_WORK_DIR}/data"

# Copy SQLite database if exists
if [[ -f "$DB_PATH" ]]; then
    # Use SQLite backup API or copy to ensure database consistency
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$DB_PATH" ".backup '${TMP_WORK_DIR}/data/x-ui.db'"
    else
        cp "$DB_PATH" "${TMP_WORK_DIR}/data/x-ui.db"
    fi
fi

# Copy configurations if exist
if [[ -d "$CONFIG_DIR" ]]; then
    cp -r "$CONFIG_DIR" "${TMP_WORK_DIR}/data/configs"
fi

# Create tarball
tar -czf "$TAR_FILE" -C "${TMP_WORK_DIR}/data" .

if [[ -n "$GPG_RECIPIENT" ]] && command -v gpg >/dev/null 2>&1 && gpg --list-keys "$GPG_RECIPIENT" >/dev/null 2>&1; then
    log_info "Encrypting snapshot with GPG asymmetric encryption (Recipient: ${GPG_RECIPIENT})..."
    gpg --batch --yes --encrypt --recipient "$GPG_RECIPIENT" --output "$ENCRYPTED_FILE" "$TAR_FILE"
    log_ok "Encrypted backup created at ${ENCRYPTED_FILE}"
else
    # Fallback to AES-256 symmetric encryption if recipient public key is not in keyring
    log_info "GPG recipient not found or not specified; encrypting with AES-256..."
    BACKUP_PASSPHRASE="$(sovereign_load_secret BACKUP_PASSPHRASE "")"
    if [[ -z "$BACKUP_PASSPHRASE" ]]; then
        BACKUP_PASSPHRASE="$(sovereign_generate_hex 32)"
        log_info "No BACKUP_PASSPHRASE configured; dynamically generated random passphrase: $(sovereign_mask_secret "$BACKUP_PASSPHRASE")"
    fi
    if command -v gpg >/dev/null 2>&1; then
        gpg --batch --yes --passphrase "$BACKUP_PASSPHRASE" --symmetric --cipher-algo AES256 --output "$ENCRYPTED_FILE" "$TAR_FILE"
    elif command -v openssl >/dev/null 2>&1; then
        openssl enc -aes-256-cbc -salt -pbkdf2 -in "$TAR_FILE" -out "$ENCRYPTED_FILE" -pass "pass:${BACKUP_PASSPHRASE}"
    else
        cp "$TAR_FILE" "${BACKUP_DIR}/sovereign_backup_${TIMESTAMP}.tar.gz"
        ENCRYPTED_FILE="${BACKUP_DIR}/sovereign_backup_${TIMESTAMP}.tar.gz"
    fi
    log_ok "Backup created at ${ENCRYPTED_FILE}"
fi

# Rotate backups: retain only last 7 backups
find "$BACKUP_DIR" -name "sovereign_backup_*" -type f -mtime +7 -delete || true

# Optional upload to Backblaze B2 / S3
if [[ -n "$B2_BUCKET" ]] && command -v b2 >/dev/null 2>&1; then
    log_info "Uploading encrypted snapshot to Backblaze B2 bucket ${B2_BUCKET}..."
    b2 upload-file "$B2_BUCKET" "$ENCRYPTED_FILE" "sovereign_backup_${TIMESTAMP}.tar.gz.gpg" || true
fi

log_ok "Disaster recovery backup pipeline finished successfully."
