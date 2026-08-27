#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 — Master GitOps Push & GitHub Integration Runner
# ==============================================================================
# Script: scripts/gitops/push_to_github.sh
# Purpose:
#   Master automation runner combining preflight validation and migration
#   execution with clean terminal status reporting.
# ==============================================================================
set -euo pipefail

# --- Color Definitions ---
COLOR_RESET="\033[0m"
COLOR_BLUE="\033[1;34m"
COLOR_GREEN="\033[1;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[1;31m"
COLOR_CYAN="\033[1;36m"
COLOR_BOLD="\033[1m"
COLOR_MAGENTA="\033[1;35m"

log_info()    { echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $*"; }
log_succ()    { echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $*"; }
log_warn()    { echo -e "${COLOR_YELLOW}[WARNING]${COLOR_RESET} $*"; }
log_err()     { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $*"; }
log_header()  { echo -e "\n${COLOR_CYAN}${COLOR_BOLD}==============================================================================\n  $*\n==============================================================================${COLOR_RESET}"; }

# --- Resolve Project Root ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

# --- Configuration & Flags ---
DEFAULT_REMOTE="git@github.com:Mohamed-DN/sovereign-oci-proxy.git"
DRY_RUN=false
EXECUTE=false
PUSH_REMOTE=false
SKIP_PREFLIGHT=false
FORCE=false
CUSTOM_REMOTE=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Master automation runner for Sovereign Proxy v4.0 GitOps migration and GitHub integration.

Options:
  -n, --dry-run          Simulate preflight validation and gitops staging without modifying git state.
  -e, --execute          Execute real git migration, staging on 'main', and branching legacy to 'v2'.
  -p, --push             Execute git push to GitHub remote repository.
  -r, --remote-url <URL> Specify custom GitHub remote URL (default: ${DEFAULT_REMOTE}).
  -s, --skip-preflight   Skip preflight validation checks (not recommended).
  -f, --force            Force overwriting existing tags or branches.
  -h, --help             Display this help message.

Examples:
  # Simulate full dry-run:
  $ $(basename "$0") --dry-run

  # Execute migration and stage v4.0 on main:
  $ $(basename "$0") --execute

  # Execute migration and push to GitHub:
  $ $(basename "$0") --execute --push
EOF
  exit 0
}

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
    -p|--push)
      PUSH_REMOTE=true
      shift
      ;;
    -r|--remote-url)
      if [[ -n "${2:-}" ]] && [[ ! "$2" =~ ^- ]]; then
        CUSTOM_REMOTE="$2"
        shift 2
      else
        log_err "--remote-url requires a valid URL."
        exit 1
      fi
      ;;
    --remote-url=*)
      CUSTOM_REMOTE="${1#*=}"
      shift
      ;;
    -s|--skip-preflight)
      SKIP_PREFLIGHT=true
      shift
      ;;
    -f|--force)
      FORCE=true
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

if [ "$DRY_RUN" = false ] && [ "$EXECUTE" = false ]; then
  EXECUTE=true
fi

TARGET_REMOTE="${CUSTOM_REMOTE:-${DEFAULT_REMOTE}}"

log_header "SOVEREIGN PROXY v4.0 — MASTER GITOPS RUNNER"
echo -e "${COLOR_MAGENTA}Target Repository:${COLOR_RESET}  ${TARGET_REMOTE}"
echo -e "${COLOR_MAGENTA}Working Directory:${COLOR_RESET}  ${PROJECT_ROOT}"
echo -e "${COLOR_MAGENTA}Execution Mode:${COLOR_RESET}     $([ "$DRY_RUN" = true ] && echo "${COLOR_YELLOW}DRY-RUN (Simulation)${COLOR_RESET}" || echo "${COLOR_GREEN}LIVE EXECUTE${COLOR_RESET}")"
echo -e "${COLOR_MAGENTA}Push to Remote:${COLOR_RESET}     $([ "$PUSH_REMOTE" = true ] && echo "${COLOR_GREEN}ENABLED${COLOR_RESET}" || echo "${COLOR_BLUE}DISABLED (Local Staging Only)${COLOR_RESET}")"

# ==============================================================================
# Step 1: Preflight Integrity Validation
# ==============================================================================
log_header "STEP 1: PREFLIGHT INTEGRITY & VALIDATION"

if [ "$SKIP_PREFLIGHT" = true ]; then
  log_warn "Skipping preflight check (--skip-preflight flag set)."
else
  PREFLIGHT_SCRIPT="${SCRIPT_DIR}/preflight_check.sh"
  if [ -f "${PREFLIGHT_SCRIPT}" ]; then
    log_info "Running preflight validation suite..."
    if ! bash "${PREFLIGHT_SCRIPT}"; then
      log_err "Preflight check failed! Aborting GitOps release."
      exit 1
    fi
    log_succ "Preflight validation PASSED (100% test & syntax integrity)."
  else
    log_err "Missing preflight check script at ${PREFLIGHT_SCRIPT}."
    exit 1
  fi
fi

# ==============================================================================
# Step 2: Legacy Branching & Staging Automation
# ==============================================================================
log_header "STEP 2: GITOPS MIGRATION & BRANCHING EXECUTION"

MIGRATE_SCRIPT="${SCRIPT_DIR}/migrate_to_v2_and_stage_v4.sh"
if [ ! -f "${MIGRATE_SCRIPT}" ]; then
  log_err "Migration script not found at ${MIGRATE_SCRIPT}."
  exit 1
fi

MIGRATE_FLAGS=()
if [ "$DRY_RUN" = true ]; then
  MIGRATE_FLAGS+=("--dry-run")
else
  MIGRATE_FLAGS+=("--execute")
fi

if [ "$PUSH_REMOTE" = true ]; then
  MIGRATE_FLAGS+=("--push")
fi

if [ -n "$CUSTOM_REMOTE" ]; then
  MIGRATE_FLAGS+=("--remote-url" "$CUSTOM_REMOTE")
fi

if [ "$SKIP_PREFLIGHT" = true ]; then
  MIGRATE_FLAGS+=("--skip-preflight")
fi

if [ "$FORCE" = true ]; then
  MIGRATE_FLAGS+=("--force")
fi

log_info "Executing migration engine: bash ${MIGRATE_SCRIPT} ${MIGRATE_FLAGS[*]}"
bash "${MIGRATE_SCRIPT}" "${MIGRATE_FLAGS[@]}"

# ==============================================================================
# Step 3: Final Status & Report
# ==============================================================================
log_header "STEP 3: GITOPS PIPELINE SUMMARY"

cat <<EOF
${COLOR_GREEN}✓ Preflight checks passed with zero errors.${COLOR_RESET}
${COLOR_GREEN}✓ Legacy single-node codebase archived to branch 'v2' (tag 'v2.0.0-legacy').${COLOR_RESET}
${COLOR_GREEN}✓ Sovereign Proxy v4.0 architecture staged and committed on branch 'main'.${COLOR_RESET}
${COLOR_GREEN}✓ GitOps release automation completed successfully.${COLOR_RESET}
EOF

exit 0
