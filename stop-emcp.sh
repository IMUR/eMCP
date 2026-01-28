#!/usr/bin/env bash
set -euo pipefail

# eMCP Stop Script
# Clean shutdown of all docker-compose services

# Color codes for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

main() {
  echo ""
  log_info "Stopping eMCP services..."
  echo ""
  docker compose down
  echo ""
  log_info "All services stopped"
  echo ""
}

main
