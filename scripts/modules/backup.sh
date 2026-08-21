#!/bin/bash
# GPG Asymmetric Encryption + Backblaze B2 Upload
# Ensure you configure b2 CLI and GPG keys before running this.

BACKUP_DIR="/root/backups"
B2_BUCKET="sovereign-xray-backups"
DATE=$(date +%Y%m%d_%H%M)
GPG_RECIPIENT="YOUR_EMAIL_HERE"

mkdir -p "${BACKUP_DIR}"
cp /etc/x-ui/x-ui.db "${BACKUP_DIR}/x-ui_${DATE}.db"

# Encrypt the database using the public key
gpg --batch --yes --trust-model always --recipient "$GPG_RECIPIENT"     --cipher-algo AES256 --output "${BACKUP_DIR}/x-ui_${DATE}.db.gpg" --encrypt "${BACKUP_DIR}/x-ui_${DATE}.db"

# Upload to B2
# b2 upload-file "${B2_BUCKET}" "${BACKUP_DIR}/x-ui_${DATE}.db.gpg" "backups/x-ui_${DATE}.db.gpg"

rm -f "${BACKUP_DIR}/x-ui_${DATE}.db"
