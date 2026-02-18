#!/usr/bin/env bash
set -euo pipefail

# Validates that required variables exist in .env
# NEVER reveals actual values

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

REQUIRED_VARS=(
  "POSTGRES_PASSWORD"
  "POSTGRES_USER"
)

main() {
  echo ""
  echo -e "${GREEN}[INFO]${NC} eMCP Environment Validation"
  echo ""

  if [ ! -f ".env" ]; then
    echo -e "${RED}[ERROR]${NC} No .env file found"
    echo "  Run: cp .env.example .env"
    exit 1
  fi

  local missing=()
  local present=()

  for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${var}=" .env 2>/dev/null; then
      present+=("$var")
    else
      missing+=("$var")
    fi
  done

  if [ ${#present[@]} -gt 0 ]; then
    echo -e "${GREEN}Present (${#present[@]}/${#REQUIRED_VARS[@]}):${NC}"
    for var in "${present[@]}"; do
      echo "  + $var"
    done
  fi

  if [ ${#missing[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}Missing (${#missing[@]}/${#REQUIRED_VARS[@]}):${NC}"
    for var in "${missing[@]}"; do
      echo "  - $var"
    done
    exit 1
  fi

  echo ""
  echo -e "${GREEN}[INFO]${NC} All required variables present."
}

main
