#!/usr/bin/env bash
set -euo pipefail

# eMCP Startup Script with Infisical Secret Injection
# This script fetches secrets from Infisical and starts docker-compose services

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Required secrets (core infrastructure only)
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

# Check if Infisical CLI is installed
check_infisical_cli() {
  if ! command -v infisical &> /dev/null; then
    log_error "Infisical CLI not installed"
    echo ""
    echo "Install via:"
    echo "  macOS:  brew install infisical/brew/infisical"
    echo "  Linux:  https://infisical.com/docs/cli/overview"
    echo ""
    return 1
  fi
  return 0
}

# Check if .infisical.json exists
check_infisical_config() {
  if [ ! -f ".infisical.json" ]; then
    log_error "Infisical not configured (.infisical.json not found)"
    return 1
  fi
  return 0
}

# Fetch secrets from Infisical
fetch_secrets() {
  log_info "Fetching secrets from Infisical..."

  if ! infisical export --path=/emcp --format=dotenv > .env.tmp 2>/dev/null; then
    log_error "Failed to fetch secrets from Infisical"
    return 1
  fi

  return 0
}

# Validate all required secrets are present
validate_secrets() {
  log_info "Validating required secrets..."

  local missing=()

  for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env.tmp 2>/dev/null; then
      missing+=("$var")
    fi
  done

  if [ ${#missing[@]} -gt 0 ]; then
    log_error "Missing required secrets:"
    for var in "${missing[@]}"; do
      echo "  - $var"
    done
    echo ""
    log_error "Add missing secrets to Infisical:"
    echo "  infisical secrets set <KEY>=<VALUE> --path=/emcp"
    rm -f .env.tmp
    return 1
  fi

  log_info "All required secrets validated (${#REQUIRED_VARS[@]}/${#REQUIRED_VARS[@]})"
  return 0
}

# Backup existing .env
backup_env() {
  if [ -f ".env" ]; then
    log_info "Backing up existing .env to .env.backup"
    cp .env .env.backup
  fi
}

# Install new .env file
install_env() {
  log_info "Installing new .env file"
  mv .env.tmp .env
  chmod 600 .env
}

# Start docker-compose services
start_services() {
  log_info "Starting Docker Compose services..."
  echo ""
  docker compose up -d
  echo ""
  log_info "Services started successfully!"
  echo ""
  echo "Check status: docker compose ps"
  echo "View logs:    docker compose logs -f emcp-server"
  echo "Stop all:     ./scripts/stop-emcp.sh"
}

# Main function
main() {
  echo ""
  log_info "eMCP Startup - Automated Secret Injection"
  echo ""

  # Check prerequisites
  if ! check_infisical_cli; then
    log_warn "Attempting to use existing .env file..."
    if [ -f ".env" ]; then
      log_info "Found existing .env file"
      start_services
      exit 0
    else
      log_error "No existing .env file found and Infisical CLI not available"
      exit 1
    fi
  fi

  if ! check_infisical_config; then
    log_warn "Attempting to use existing .env file..."
    if [ -f ".env" ]; then
      log_info "Found existing .env file"
      start_services
      exit 0
    else
      log_error "No existing .env file found and Infisical not configured"
      exit 1
    fi
  fi

  # Fetch and validate secrets
  if ! fetch_secrets; then
    log_warn "Failed to fetch from Infisical, checking for existing .env..."
    if [ -f ".env" ]; then
      log_info "Using existing .env file as fallback"
      start_services
      exit 0
    else
      log_error "No existing .env file found to fall back to"
      exit 1
    fi
  fi

  if ! validate_secrets; then
    exit 1
  fi

  # Install secrets and start services
  backup_env
  install_env
  start_services
}

main
