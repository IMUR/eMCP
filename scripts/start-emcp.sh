#!/usr/bin/env bash
set -euo pipefail

# eMCP Startup Script
# Validates .env and starts docker-compose services

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REQUIRED_VARS=(
  "POSTGRES_PASSWORD"
  "POSTGRES_USER"
)

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

validate_env() {
  if [ ! -f ".env" ]; then
    log_error "No .env file found"
    echo ""
    echo "Create one from the template:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your values"
    return 1
  fi

  local missing=()
  for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env 2>/dev/null; then
      missing+=("$var")
    fi
  done

  if [ ${#missing[@]} -gt 0 ]; then
    log_error "Missing required variables in .env:"
    for var in "${missing[@]}"; do
      echo "  - $var"
    done
    return 1
  fi

  log_info "Environment validated"
  return 0
}

start_services() {
  log_info "Starting Docker Compose services..."
  echo ""
  docker compose up -d
  echo ""
  log_info "Services started!"
  echo ""
  echo "  Web UI:     http://localhost:5010"
  echo "  Gateway:    http://localhost:8090"
  echo "  Stop:       ./scripts/stop-emcp.sh"
}

main() {
  echo ""
  log_info "eMCP Startup"
  echo ""

  if ! validate_env; then
    exit 1
  fi

  start_services
}

main
