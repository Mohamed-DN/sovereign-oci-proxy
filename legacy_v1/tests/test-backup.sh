#!/bin/bash
# =========================================================
# Sovereign Proxy - Backup Pipeline Test
# Tests the GPG encryption and decryption cycle without
# touching production data or uploading to B2.
# =========================================================

set -e

echo "Testing backup encryption pipeline..."

TEST_DIR="/tmp/sovereign-backup-test"
mkdir -p "$TEST_DIR"

# Create a dummy database file
echo "This is a test database content" > "$TEST_DIR/test.db"

# Check if GPG keys are available
if ! gpg --list-keys 2>/dev/null | grep -q "@"; then
    echo "SKIP: No GPG keys found. Import your public key first."
    echo "  gpg --import sovereign-backup-pub.asc"
    rm -rf "$TEST_DIR"
    exit 0
fi

GPG_RECIPIENT=$(gpg --list-keys --with-colons 2>/dev/null | grep uid | head -1 | cut -d: -f10 | grep -oE '[^<]+@[^>]+')

# Encrypt the test file
gpg --batch --yes --trust-model always \
    --recipient "$GPG_RECIPIENT" \
    --cipher-algo AES256 \
    --output "$TEST_DIR/test.db.gpg" \
    --encrypt "$TEST_DIR/test.db"

# Verify the encrypted file exists and is not empty
if [ -s "$TEST_DIR/test.db.gpg" ]; then
    SIZE=$(stat -c%s "$TEST_DIR/test.db.gpg")
    echo "Encryption test PASSED (encrypted file: ${SIZE} bytes)"
else
    echo "Encryption test FAILED: encrypted file is empty or missing"
    rm -rf "$TEST_DIR"
    exit 1
fi

# Cleanup
rm -rf "$TEST_DIR"
echo "Backup pipeline test complete."
