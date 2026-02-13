#!/usr/bin/env bash
set -euo pipefail

# eMCP Secret Validation Script
# Validates that all required secrets exist in Infisical
# NEVER reveals actual secret values

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Required secrets (core infrastructure)
REQUIRED_VARS=(
  "POSTGRES_PASSWORD"
  "POSTGRES_USER"
)

# Logging functions
log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

main() {
  echo ""
  log_info "eMCP Secret Validation"
  echo ""

  # Check Infisical CLI
  if ! command -v infisical &> /dev/null; then
    log_error "Infisical CLI not installed"
    echo ""
    echo "Install via:"
    echo "  macOS:  brew install infisical/brew/infisical"
    echo "  Linux:  https://infisical.com/docs/cli/overview"
    exit 1
  fi

  # Check .infisical.json
  if [ ! -f ".infisical.json" ]; then
    log_error "Infisical not configured (.infisical.json not found)"
    exit 1
  fi

  log_info "Infisical CLI found"
  log_info "Configuration found (.infisical.json)"
  echo ""

  # Fetch secrets to temp file (will be deleted)
  log_info "Fetching secrets from Infisical to validate (no values will be shown)..."

  if ! infisical export --path=/emcp --format=dotenv > /tmp/emcp-secrets-test.env 2>/dev/null; then
    log_error "Failed to fetch secrets from Infisical"
    echo ""
    log_error "Please ensure:"
    echo "  1. You are logged in: infisical login"
    echo "  2. You have access to the configured workspace"
    echo "  3. Secrets exist at path: /emcp"
    exit 1
  fi

  log_info "Successfully fetched secrets"

  # Validate each required secret
  log_info "Validating required secrets..."
  local missing=()
  local present=()

  for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${var}=" /tmp/emcp-secrets-test.env 2>/dev/null; then
      present+=("$var")
    else
      missing+=("$var")
    fi
  done

  # Clean up temp file
  rm -f /tmp/emcp-secrets-test.env

  # Report results
  echo ""
  log_info "Validation Results:"
  echo ""

  if [ ${#present[@]} -gt 0 ]; then
    echo -e "${GREEN}Present secrets (${#present[@]}/${#REQUIRED_VARS[@]}):${NC}"
    for var in "${present[@]}"; do
      echo "  + $var"
    done
  fi

  if [ ${#missing[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}Missing secrets (${#missing[@]}/${#REQUIRED_VARS[@]}):${NC}"
    for var in "${missing[@]}"; do
      echo "  - $var"
    done
    echo ""
    log_error "Please add missing secrets to Infisical:"
    echo "  infisical secrets set <KEY>=<VALUE> --path=/emcp"
    exit 1
  fi

  echo ""
  log_info "All required secrets are present in Infisical!"
  log_info "You can now run: ./scripts/start-emcp.sh"
  echo ""
}

main
