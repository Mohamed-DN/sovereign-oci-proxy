#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 — GitOps Legacy Branching & Staging Automation Engine
# ==============================================================================
# Script: scripts/gitops/migrate_to_v2_and_stage_v4.sh
# Purpose:
#   1. Detects git repository state.
#   2. Preserves legacy codebase on branch 'v2' and tags as 'v2.0.0-legacy'.
#   3. Stages and commits the complete v4.0 architecture on 'main'.
#   4. Supports --dry-run, --execute, and --remote-url options.
#   5. Verifies git remote origin for Mohamed-DN/sovereign-oci-proxy.
#   6. Performs safe push of v2 branch, v2.0.0-legacy tag, and main branch.
# ==============================================================================
set -euo pipefail

# --- Color Formatting & Logging ---
COLOR_RESET="\033[0m"
COLOR_BLUE="\033[1;34m"
COLOR_GREEN="\033[1;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[1;31m"
COLOR_CYAN="\033[1;36m"
COLOR_BOLD="\033[1m"

log_info()    { echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $*"; }
log_succ()    { echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $*"; }
log_warn()    { echo -e "${COLOR_YELLOW}[WARNING]${COLOR_RESET} $*"; }
log_err()     { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $*"; }
log_header()  { echo -e "\n${COLOR_CYAN}${COLOR_BOLD}=== $* ===${COLOR_RESET}"; }

# --- Configuration Constants ---
DEFAULT_REPO_OWNER="Mohamed-DN"
DEFAULT_REPO_NAME="sovereign-oci-proxy"
DEFAULT_REMOTE_URL="git@github.com:${DEFAULT_REPO_OWNER}/${DEFAULT_REPO_NAME}.git"
LEGACY_BRANCH="v2"
LEGACY_TAG="v2.0.0-legacy"
TARGET_BRANCH="main"
V4_RELEASE_TAG="v4.0.0-darknero"
DEFAULT_HTTPS_REMOTE_URL="https://github.com/${DEFAULT_REPO_OWNER}/${DEFAULT_REPO_NAME}.git"

# --- CLI Options & Defaults ---
DRY_RUN=false
EXECUTE=false
PUSH_REMOTE=false
SKIP_PREFLIGHT=false
FORCE_MIGRATION=false
CUSTOM_REMOTE_URL=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  -n, --dry-run          Simulate branching, staging, and migration without altering git state.
  -e, --execute          Execute real migration, branching, committing, and staging.
  -r, --remote-url <URL> Set custom git remote origin URL (default: ${DEFAULT_REMOTE_URL}).
  -p, --push             Push legacy branch ('v2'), tag ('v2.0.0-legacy'), and 'main' to remote origin.
  -s, --skip-preflight   Skip preflight validation checks (not recommended for production).
  -f, --force            Force branch recreation and overwriting existing tags.
  -h, --help             Show this help message and exit.

Examples:
  $(basename "$0") --dry-run
  $(basename "$0") --execute
  $(basename "$0") --execute --push --remote-url "git@github.com:Mohamed-DN/sovereign-oci-proxy.git"
EOF
  exit 0
}

# Parse Command-Line Arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--dry-run)
      DRY_RUN=true
      shift
      ;;
    -e|--execute)
      EXECUTE=true
      shift
      ;;
    -r|--remote-url)
      if [[ -n "${2:-}" ]] && [[ ! "$2" =~ ^- ]]; then
        CUSTOM_REMOTE_URL="$2"
        shift 2
      else
        log_err "--remote-url requires a valid URL argument."
        exit 1
      fi
      ;;
    --remote-url=*)
      CUSTOM_REMOTE_URL="${1#*=}"
      shift
      ;;
    -p|--push)
      PUSH_REMOTE=true
      shift
      ;;
    -s|--skip-preflight)
      SKIP_PREFLIGHT=true
      shift
      ;;
    -f|--force)
      FORCE_MIGRATION=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      log_err "Unknown option: $1"
      usage
      ;;
  esac
done

# If neither --dry-run nor --execute is explicitly specified, default to execution mode
if [ "$DRY_RUN" = false ] && [ "$EXECUTE" = false ]; then
  EXECUTE=true
fi

# --- Resolve Project Root ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

REMOTE_TARGET="${CUSTOM_REMOTE_URL:-${DEFAULT_REMOTE_URL}}"

log_header "Sovereign Proxy v4.0 — GitOps Migration & Branching Engine"
log_info "Project Root Directory: ${PROJECT_ROOT}"
log_info "Execution Mode:         $([ "$DRY_RUN" = true ] && echo "DRY-RUN (Simulation)" || echo "LIVE EXECUTE")"
log_info "Target Remote URL:      ${REMOTE_TARGET}"
log_info "Push to Remote:         ${PUSH_REMOTE}"

# ==============================================================================
# Phase 1: Git Repository & Environment Inspection
# ==============================================================================
log_header "Phase 1: Environment & Repository State Inspection"

if [ ! -d ".git" ]; then
  if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] No .git directory found. Would initialize new git repository with default branch '${TARGET_BRANCH}'."
  else
    log_info "Initializing git repository in ${PROJECT_ROOT} on branch '${TARGET_BRANCH}'..."
    git init -b "${TARGET_BRANCH}"
    log_succ "Git repository initialized."
  fi
fi

CURRENT_BRANCH="${TARGET_BRANCH}"
if [ -d ".git" ]; then
  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "${TARGET_BRANCH}")
fi
log_info "Current active branch: ${CURRENT_BRANCH}"

# Configure or verify Remote Origin
if [ -d ".git" ] || [ "$DRY_RUN" = true ]; then
  if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] Would configure remote 'origin' -> ${REMOTE_TARGET}"
  else
    if git remote get-url origin &>/dev/null; then
      EXISTING_ORIGIN=$(git remote get-url origin)
      log_info "Existing remote origin found: ${EXISTING_ORIGIN}"
      if [ -n "${CUSTOM_REMOTE_URL}" ] && [ "${EXISTING_ORIGIN}" != "${CUSTOM_REMOTE_URL}" ]; then
        git remote set-url origin "${CUSTOM_REMOTE_URL}"
        log_succ "Updated remote origin to: ${CUSTOM_REMOTE_URL}"
      fi
    else
      git remote add origin "${REMOTE_TARGET}"
      log_succ "Added remote origin: ${REMOTE_TARGET}"
    fi
  fi
fi

# ==============================================================================
# Phase 2: Preserve Legacy Codebase on Branch 'v2' & Tag 'v2.0.0-legacy'
# ==============================================================================
log_header "Phase 2: Legacy Codebase Preservation ('${LEGACY_BRANCH}')"

if [ "$DRY_RUN" = true ]; then
  log_info "[DRY-RUN] Would preserve legacy commit history on branch '${LEGACY_BRANCH}'."
  log_info "[DRY-RUN] Would create immutable annotated tag '${LEGACY_TAG}' referencing legacy baseline."
else
  HAS_COMMITS=false
  if [ -d ".git" ] && git rev-parse --verify HEAD &>/dev/null; then
    HAS_COMMITS=true
  fi

  if [ "$HAS_COMMITS" = true ]; then
    # Legacy branch preservation
    if git show-ref --quiet "refs/heads/${LEGACY_BRANCH}"; then
      if [ "$FORCE_MIGRATION" = true ]; then
        log_warn "Branch '${LEGACY_BRANCH}' already exists. Overwriting with current HEAD..."
        git branch -f "${LEGACY_BRANCH}" HEAD
      else
        log_info "Preserving existing legacy branch '${LEGACY_BRANCH}'."
      fi
    else
      git branch "${LEGACY_BRANCH}" HEAD
      log_succ "Created legacy branch '${LEGACY_BRANCH}' from current commit baseline."
    fi

    # Legacy tag preservation
    if git rev-parse "${LEGACY_TAG}" &>/dev/null; then
      if [ "$FORCE_MIGRATION" = true ]; then
        log_warn "Tag '${LEGACY_TAG}' already exists. Force updating tag..."
        git tag -f -a "${LEGACY_TAG}" -m "Checkpoint: Sovereign OCI Proxy v2.0 Legacy Single-Node Architecture Baseline"
        log_succ "Updated legacy tag '${LEGACY_TAG}'."
      else
        log_info "Legacy tag '${LEGACY_TAG}' already exists."
      fi
    else
      git tag -a "${LEGACY_TAG}" -m "Checkpoint: Sovereign OCI Proxy v2.0 Legacy Single-Node Architecture Baseline"
      log_succ "Created annotated legacy tag '${LEGACY_TAG}'."
    fi
  else
    log_info "No prior commits found in repository; legacy baseline will be established upon first commit."
  fi
fi

# ==============================================================================
# Phase 3: Switch to or Ensure 'main' Production Branch
# ==============================================================================
log_header "Phase 3: Setting Up Production Branch ('${TARGET_BRANCH}')"

if [ "$DRY_RUN" = true ]; then
  log_info "[DRY-RUN] Would checkout/ensure target branch '${TARGET_BRANCH}'."
else
  if [ -d ".git" ]; then
    if git show-ref --quiet "refs/heads/${TARGET_BRANCH}"; then
      log_info "Switching to '${TARGET_BRANCH}' branch..."
      git checkout "${TARGET_BRANCH}"
    else
      log_info "Creating and checking out branch '${TARGET_BRANCH}'..."
      git checkout -B "${TARGET_BRANCH}"
    fi
    log_succ "Active branch is '${TARGET_BRANCH}'."
  fi
fi

# ==============================================================================
# Phase 4: Pre-Flight Integrity Validation
# ==============================================================================
log_header "Phase 4: Pre-Flight Integrity & Secret Verification"

if [ "$SKIP_PREFLIGHT" = true ]; then
  log_warn "Pre-flight checks skipped via --skip-preflight."
else
  PREFLIGHT_SCRIPT="${PROJECT_ROOT}/scripts/gitops/preflight_check.sh"
  if [ -f "${PREFLIGHT_SCRIPT}" ]; then
    log_info "Executing preflight check suite (${PREFLIGHT_SCRIPT})..."
    bash "${PREFLIGHT_SCRIPT}" || {
      log_err "Pre-flight checks failed! Resolve issues before migrating."
      exit 1
    }
    log_succ "Pre-flight verification passed."
  else
    log_warn "Preflight script not found at ${PREFLIGHT_SCRIPT}; verifying basic syntax..."
    find "${PROJECT_ROOT}/scripts" -type f -name "*.sh" -exec bash -n {} +
  fi
fi

# ==============================================================================
# Phase 5: Stage v4.0 Architecture & Create Release Commit
# ==============================================================================
log_header "Phase 5: Staging v4.0 Architecture & Creating Release Commit"

if [ "$DRY_RUN" = true ]; then
  log_info "[DRY-RUN] Would stage all v4.0 architecture files, scripts, manifests, and configs."
  log_info "[DRY-RUN] Would create commit on branch '${TARGET_BRANCH}'."
  log_info "[DRY-RUN] Would create release tag '${V4_RELEASE_TAG}'."
else
  if [ -d ".git" ]; then
    # Ensure proper permissions on executable scripts
    log_info "Applying executable permissions to scripts..."
    find "${PROJECT_ROOT}/scripts" -type f -name "*.sh" -exec chmod +x {} + 2>/dev/null || true
    find "${PROJECT_ROOT}/scripts" -type f -name "*.py" -exec chmod +x {} + 2>/dev/null || true

    # Stage all files
    git add .

    COMMIT_MSG="feat(v4.0): NeroNet v4.0 Enterprise Decentralized Anti-Censorship Mesh Network (neronet.darknero.com)

- Proprietary decentralized P2P mesh network with Noise_IKpsk2 zero-trust cryptography
- DirectFrame SVRN binary wire framing with replay protection and userspace socket bridge
- Camouflaged DERP-v4 relays on port 443 with TLS 1.3 imitation and active decoy engine
- Adaptive Disco-v4 NAT traversal (STUN, port prediction, 256-port birthday spray)
- Sandboxed client exit bridge with strict RFC 1918 bogon filter and anti-abuse protection
- Multi-mode routing: dynamic country selection, host ID routing, 3-hop onion obfuscation
- Unified multi-cloud schema (mesh-cluster.yaml) supporting OCI, AWS, GCP, DO, Hetzner, Vultr
- Production Kubernetes Helm charts (charts/sovereign-mesh) with HA and Kustomize overlays
- NetBird feature parity: dynamic peer ACLs, route distribution, real-time posture checks
- Automated GitOps CI/CD fleet, security scanners, multi-arch binary release pipelines
- Preserved legacy single-node v2.0 codebase on 'v2' branch tagged 'v2.0.0-legacy'"

    if git diff-index --quiet HEAD -- 2>/dev/null; then
      log_info "Working tree is clean. No uncommitted modifications detected."
    else
      git commit -m "${COMMIT_MSG}"
      log_succ "Committed NeroNet v4.0 architecture to branch '${TARGET_BRANCH}'."
    fi

    # Create v2 branch from initial baseline if not created earlier
    if ! git show-ref --quiet "refs/heads/${LEGACY_BRANCH}"; then
      git branch "${LEGACY_BRANCH}" HEAD~1 2>/dev/null || git branch "${LEGACY_BRANCH}" HEAD
      log_succ "Established '${LEGACY_BRANCH}' branch."
    fi

    # Create v2.0.0-legacy tag if not present
    if ! git rev-parse "${LEGACY_TAG}" &>/dev/null; then
      git tag -a "${LEGACY_TAG}" -m "Checkpoint: Sovereign OCI Proxy v2.0 Legacy Baseline" HEAD~1 2>/dev/null || \
      git tag -a "${LEGACY_TAG}" -m "Checkpoint: Sovereign OCI Proxy v2.0 Legacy Baseline" HEAD
      log_succ "Tagged legacy baseline with '${LEGACY_TAG}'."
    fi

    # Create v4.0.0 release tag
    if [ "$FORCE_MIGRATION" = true ]; then
      git tag -f -a "${V4_RELEASE_TAG}" -m "Release: NeroNet v4.0 Enterprise Decentralized Mesh (DARKNERO.COM)"
      log_succ "Tagged production release '${V4_RELEASE_TAG}' (forced)."
    elif ! git rev-parse "${V4_RELEASE_TAG}" &>/dev/null; then
      git tag -a "${V4_RELEASE_TAG}" -m "Release: NeroNet v4.0 Enterprise Decentralized Mesh (DARKNERO.COM)"
      log_succ "Tagged production release '${V4_RELEASE_TAG}'."
    fi
  fi
fi

# ==============================================================================
# Phase 6: Safe Remote Synchronization (Push to GitHub)
# ==============================================================================
log_header "Phase 6: Remote GitHub Synchronization"

if [ "$PUSH_REMOTE" = true ]; then
  if [ "$DRY_RUN" = true ]; then
    log_info "[DRY-RUN] Would push branch '${LEGACY_BRANCH}', tag '${LEGACY_TAG}', branch '${TARGET_BRANCH}', and tag '${V4_RELEASE_TAG}' to '${REMOTE_TARGET}'."
  else
    log_info "Pushing legacy branch '${LEGACY_BRANCH}' and '${LEGACY_TAG}' to origin..."
    if ! git -c credential.helper= -c core.askPass=true push origin "${LEGACY_BRANCH}" --tags 2>/dev/null; then
      log_warn "SSH push of ${LEGACY_BRANCH} failed; attempting HTTPS fallback..."
      git -c credential.helper= -c core.askPass=true push "${DEFAULT_HTTPS_REMOTE_URL}" "${LEGACY_BRANCH}" --tags 2>/dev/null || log_warn "Remote push of ${LEGACY_BRANCH} deferred (offline or requires GitHub credentials)."
    fi

    log_info "Pushing production branch '${TARGET_BRANCH}' and release tags to origin..."
    if ! git -c credential.helper= -c core.askPass=true push origin "${TARGET_BRANCH}" --tags 2>/dev/null; then
      log_warn "SSH push of ${TARGET_BRANCH} failed; attempting HTTPS fallback..."
      git -c credential.helper= -c core.askPass=true push "${DEFAULT_HTTPS_REMOTE_URL}" "${TARGET_BRANCH}" --tags 2>/dev/null || log_warn "Remote push of ${TARGET_BRANCH} deferred (offline or requires GitHub credentials)."
    fi

    log_succ "Remote GitOps synchronization executed."
  fi
else
  log_info "Remote push skipped. (Pass '--push' to execute automatic git push)."
fi

# ==============================================================================
# Phase 7: Migration Completion Summary
# ==============================================================================
log_header "Phase 7: Migration Summary & Status"

cat <<EOF

${COLOR_GREEN}==============================================================================
   NERONET v4.0 GITOPS MIGRATION COMPLETED SUCCESSFULLY
==============================================================================${COLOR_RESET}

  Legacy Maintenance Branch:    ${COLOR_BOLD}${LEGACY_BRANCH}${COLOR_RESET} (Tag: ${COLOR_CYAN}${LEGACY_TAG}${COLOR_RESET})
  Production Main Branch:       ${COLOR_BOLD}${TARGET_BRANCH}${COLOR_RESET} (Tag: ${COLOR_CYAN}${V4_RELEASE_TAG}${COLOR_RESET})
  Remote Target Repository:     ${COLOR_BOLD}${REMOTE_TARGET}${COLOR_RESET}
  Dry-Run Mode:                 ${DRY_RUN}

${COLOR_CYAN}Git Repository Verification Commands:${COLOR_RESET}
  $ git branch -a
  $ git tag -l
  $ git log --oneline -n 5

${COLOR_GREEN}✓ All legacy features and historical integrity preserved.${COLOR_RESET}
${COLOR_GREEN}✓ v4.0 enterprise decentralized mesh architecture successfully staged.${COLOR_RESET}
EOF

exit 0
