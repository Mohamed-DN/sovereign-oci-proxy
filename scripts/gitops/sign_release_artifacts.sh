#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 — Release Artifact Signing & Provenance Tool
# ==============================================================================
# Script: scripts/gitops/sign_release_artifacts.sh
# Purpose:
#   Generates cryptographically signed checksums and signatures for
#   compiled binaries, container images, and Helm packages.
# ==============================================================================
set -euo pipefail

COLOR_RESET="\033[0m"
COLOR_BLUE="\033[1;34m"
COLOR_GREEN="\033[1;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[1;31m"

log_info() { echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $*"; }
log_succ() { echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $*"; }
log_warn() { echo -e "${COLOR_YELLOW}[WARNING]${COLOR_RESET} $*"; }
log_err()  { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $*"; }

TARGET_DIR="${1:-dist}"
CONTAINER_IMAGE="${2:-}"

log_info "Artifact directory: ${TARGET_DIR}"

if [ -d "${TARGET_DIR}" ]; then
  cd "${TARGET_DIR}"

  log_info "Generating SHA-256 checksums for release assets..."
  if command -v sha256sum &>/dev/null; then
    find . -maxdepth 1 -type f ! -name "SHA256SUMS*" ! -name "*.sig" -exec sha256sum {} + > SHA256SUMS
  elif command -v shasum &>/dev/null; then
    find . -maxdepth 1 -type f ! -name "SHA256SUMS*" ! -name "*.sig" -exec shasum -a 256 {} + > SHA256SUMS
  fi

  if [ -f SHA256SUMS ]; then
    log_succ "Generated SHA256SUMS successfully."
  fi

  # If GPG key is configured, create detached signature
  if command -v gpg &>/dev/null && [ -n "${GPG_KEY_ID:-}" ]; then
    log_info "Signing SHA256SUMS with GPG key: ${GPG_KEY_ID}..."
    gpg --batch --yes --armor --detach-sign --default-key "${GPG_KEY_ID}" SHA256SUMS
    log_succ "Created SHA256SUMS.asc detached signature."
  fi
  cd - >/dev/null
else
  log_warn "Directory ${TARGET_DIR} does not exist yet. Checksum generation skipped."
fi

# Cosign signing for container image
if [ -n "${CONTAINER_IMAGE}" ]; then
  if command -v cosign &>/dev/null; then
    log_info "Signing container image with Cosign: ${CONTAINER_IMAGE}..."
    cosign sign --yes "${CONTAINER_IMAGE}"
    log_succ "Signed container image: ${CONTAINER_IMAGE}"
  else
    log_warn "Cosign utility not found in PATH. Skipping container signing."
  fi
fi

log_succ "Signing & provenance workflow completed."
exit 0
